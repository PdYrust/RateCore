package price

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"
)

const (
	usdIRRSymbol    = "USD_IRR"
	// defaultCacheTTL keeps provider responses warm briefly to avoid hammering APIs while staying fresh.
	defaultCacheTTL = 25 * time.Second
	// defaultFXTTL is intentionally short to keep USD→IRR fresh (important for normalization accuracy).
	defaultFXTTL = 30 * time.Second
)

// ProviderKind represents logical categories of upstream price sources.
type ProviderKind string

const (
	ProviderKindForex     ProviderKind = "forex"
	ProviderKindCrypto    ProviderKind = "crypto"
	ProviderKindMetal     ProviderKind = "metal"
	ProviderKindCommodity ProviderKind = "commodity"
)

// PriceProvider fetches prices from an upstream source in its native base currency.
type PriceProvider interface {
	Name() string
	GetPrice(ctx context.Context, symbol string) (UnifiedPrice, error)
	GetPricesBatch(ctx context.Context, symbols []string) ([]UnifiedPrice, error)
}

// Service exposes price lookup operations.
type Service interface {
	GetPrice(ctx context.Context, symbol string) (UnifiedPrice, error)
	GetPricesBatch(ctx context.Context, symbols []string) ([]UnifiedPrice, error)
}

// DisplayModeProvider supplies the desired display currency mode.
type DisplayModeProvider interface {
	Mode() DisplayCurrencyMode
}

// ProviderRegistry stores providers grouped by their kind.
type ProviderRegistry struct {
	Crypto []PriceProvider
	Forex  []PriceProvider
	Metal  []PriceProvider
	IRR    []PriceProvider
}

// ProviderPriority defines ordered provider names per kind.
type ProviderPriority map[ProviderKind][]string

type cacheEntry struct {
	price     UnifiedPrice
	expiresAt time.Time
}

// DefaultPriceService resolves prices via providers with caching and normalization.
type DefaultPriceService struct {
	registry     *ProviderRegistry
	priorities   ProviderPriority
	modeProvider DisplayModeProvider
	fx           FXConverter

	cache  map[string]cacheEntry
	mu     sync.RWMutex
	cacheTTL time.Duration
	nowFn  func() time.Time
}

// NewDefaultPriceService builds a service with provided registry, priorities, and FX converter.
func NewDefaultPriceService(registry *ProviderRegistry, priorities ProviderPriority, modeProvider DisplayModeProvider, fx FXConverter) *DefaultPriceService {
	if registry == nil {
		registry = NewProviderRegistry()
	}
	priorities = ensureDefaultPriorities(priorities, registry)
	if fx == nil {
		fx = ensureDefaultFXConverter(registry)
	}

	return &DefaultPriceService{
		registry:     registry,
		priorities:   priorities,
		modeProvider: modeProvider,
		fx:           fx,
		cache:        make(map[string]cacheEntry),
		cacheTTL:     defaultCacheTTL,
		nowFn:        time.Now,
	}
}

// NewProviderRegistry creates an empty registry.
func NewProviderRegistry() *ProviderRegistry {
	return &ProviderRegistry{
		Crypto: make([]PriceProvider, 0),
		Forex:  make([]PriceProvider, 0),
		Metal:  make([]PriceProvider, 0),
		IRR:    make([]PriceProvider, 0),
	}
}

// DefaultProviderPriorities returns a hardcoded priority order per provider kind.
func DefaultProviderPriorities() ProviderPriority {
	return ProviderPriority{
		ProviderKindCrypto: []string{"binance"},
		ProviderKindForex:  []string{"exchangerateapi", "irr"},
		ProviderKindMetal:  []string{"metalsapi"},
	}
}

// RegisterCrypto registers a crypto provider.
func (r *ProviderRegistry) RegisterCrypto(p PriceProvider) {
	r.Crypto = append(r.Crypto, p)
}

// RegisterForex registers a forex provider.
func (r *ProviderRegistry) RegisterForex(p PriceProvider) {
	r.Forex = append(r.Forex, p)
}

// RegisterMetal registers a metal provider.
func (r *ProviderRegistry) RegisterMetal(p PriceProvider) {
	r.Metal = append(r.Metal, p)
}

func (r *ProviderRegistry) providersForKind(kind ProviderKind, priority ProviderPriority) []PriceProvider {
	var providers []PriceProvider
	switch kind {
	case ProviderKindCrypto:
		providers = r.Crypto
	case ProviderKindForex:
		providers = append(r.Forex, r.IRR...)
	case ProviderKindMetal:
		providers = r.Metal
	case ProviderKindCommodity:
		// TODO: add commodity providers once available.
	}

	if priority == nil || len(priority[kind]) == 0 {
		return providers
	}

	var ordered []PriceProvider
	used := make(map[string]bool)
	for _, name := range priority[kind] {
		for _, p := range providers {
			if p.Name() == name && !used[p.Name()] {
				ordered = append(ordered, p)
				used[p.Name()] = true
			}
		}
	}
	for _, p := range providers {
		if !used[p.Name()] {
			ordered = append(ordered, p)
		}
	}
	return ordered
}

// GetPrice fetches a single symbol, respecting cache and provider priority.
func (s *DefaultPriceService) GetPrice(ctx context.Context, symbol string) (UnifiedPrice, error) {
	key := strings.ToUpper(symbol)
	if price, ok := s.getFromCache(key); ok {
		return price, nil
	}

	kind := detectKind(key)
	if kind == "" {
		return UnifiedPrice{}, fmt.Errorf("unsupported symbol kind for %s", key)
	}

	price, err := s.fetchFromProviders(ctx, kind, key)
	if err != nil {
		return UnifiedPrice{}, err
	}

	normalized, err := s.normalize(ctx, price)
	if err != nil {
		return UnifiedPrice{}, err
	}

	normalized = s.applyDisplayMode(normalized)
	s.setCache(key, normalized)
	return normalized, nil
}

// GetPricesBatch fetches multiple symbols with caching and provider-aware batching.
func (s *DefaultPriceService) GetPricesBatch(ctx context.Context, symbols []string) ([]UnifiedPrice, error) {
	resultBySymbol := make(map[string]UnifiedPrice, len(symbols))
	missingByKind := make(map[ProviderKind][]string)

	for _, raw := range symbols {
		key := strings.ToUpper(strings.TrimSpace(raw))
		if key == "" {
			return nil, errors.New("symbol cannot be empty")
		}
		if cached, ok := s.getFromCache(key); ok {
			resultBySymbol[key] = cached
			continue
		}
		kind := detectKind(key)
		if kind == "" {
			return nil, fmt.Errorf("unsupported symbol kind for %s", key)
		}
		missingByKind[kind] = append(missingByKind[kind], key)
	}

	for kind, kindSymbols := range missingByKind {
		if err := s.fetchBatchForKind(ctx, kind, kindSymbols, resultBySymbol); err != nil {
			return nil, err
		}
	}

	ordered := make([]UnifiedPrice, 0, len(symbols))
	for _, raw := range symbols {
		key := strings.ToUpper(strings.TrimSpace(raw))
		if p, ok := resultBySymbol[key]; ok {
			ordered = append(ordered, p)
		}
	}
	return ordered, nil
}

func (s *DefaultPriceService) fetchBatchForKind(ctx context.Context, kind ProviderKind, symbols []string, sink map[string]UnifiedPrice) error {
	providers := s.registry.providersForKind(kind, s.priorities)
	if len(providers) == 0 {
		return fmt.Errorf("no providers registered for kind %s", kind)
	}

	var lastErr error
	for _, provider := range providers {
		prices, err := provider.GetPricesBatch(ctx, symbols)
		if err != nil {
			lastErr = err
			continue
		}
		for _, p := range prices {
			normalized, err := s.normalize(ctx, p)
			if err != nil {
				lastErr = err
				continue
			}
			normalized = s.applyDisplayMode(normalized)
			s.setCache(strings.ToUpper(p.Symbol), normalized)
			sink[strings.ToUpper(p.Symbol)] = normalized
		}
		return nil
	}

	// Fallback to per-symbol fetch to salvage partial data.
	for _, symbol := range symbols {
		p, err := s.fetchFromProviders(ctx, kind, symbol)
		if err != nil {
			lastErr = err
			continue
		}
		normalized, err := s.normalize(ctx, p)
		if err != nil {
			lastErr = err
			continue
		}
		normalized = s.applyDisplayMode(normalized)
		s.setCache(strings.ToUpper(p.Symbol), normalized)
		sink[strings.ToUpper(p.Symbol)] = normalized
	}

	if len(sink) == 0 && lastErr != nil {
		return lastErr
	}
	return nil
}

func (s *DefaultPriceService) fetchFromProviders(ctx context.Context, kind ProviderKind, symbol string) (UnifiedPrice, error) {
	providers := s.registry.providersForKind(kind, s.priorities)
	if len(providers) == 0 {
		return UnifiedPrice{}, fmt.Errorf("no providers registered for kind %s", kind)
	}

	var lastErr error
	for _, provider := range providers {
		price, err := provider.GetPrice(ctx, symbol)
		if err == nil {
			return price, nil
		}
		lastErr = err
	}
	if lastErr == nil {
		lastErr = errors.New("no providers configured")
	}
	return UnifiedPrice{}, fmt.Errorf("price fetch failed for %s: %w", symbol, lastErr)
}

func (s *DefaultPriceService) getFromCache(symbol string) (UnifiedPrice, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	entry, ok := s.cache[symbol]
	if !ok || s.nowFn().After(entry.expiresAt) {
		return UnifiedPrice{}, false
	}
	return entry.price, true
}

func (s *DefaultPriceService) setCache(symbol string, price UnifiedPrice) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.cache[symbol] = cacheEntry{
		price:     price,
		expiresAt: s.nowFn().Add(s.cacheTTL),
	}
}

// normalize fills ValueIRR and ValueToman based on BaseCurrency and the USD→IRR converter.
func (s *DefaultPriceService) normalize(ctx context.Context, p UnifiedPrice) (UnifiedPrice, error) {
	switch strings.ToUpper(p.BaseCurrency) {
	case "IRR":
		p.ValueIRR = p.ValueBase
		p.ValueToman = toToman(p.ValueIRR)
		return p, nil
	case "USD", "USDT":
		rate, err := s.fx.USDToIRR(ctx)
		if err != nil {
			return UnifiedPrice{}, fmt.Errorf("normalize %s: fetch USD/IRR: %w", p.Symbol, err)
		}
		p.ValueIRR = p.ValueBase * rate
		p.ValueToman = toToman(p.ValueIRR)
		return p, nil
	default:
		// TODO: add conversion for other base currencies (e.g., EUR) via forex rates.
		return p, nil
	}
}

func (s *DefaultPriceService) applyDisplayMode(price UnifiedPrice) UnifiedPrice {
	mode := DisplayCurrencyIRR
	if s.modeProvider != nil {
		mode = s.modeProvider.Mode()
	}
	// Currently only IRR vs Toman; future: expand to other currencies.
	switch mode {
	case DisplayCurrencyToman:
		price.ValueToman = toToman(price.ValueIRR)
	default:
		price.ValueToman = toToman(price.ValueIRR)
	}
	return price
}

func detectKind(symbol string) ProviderKind {
	s := strings.ToUpper(symbol)
	switch {
	case s == usdIRRSymbol || strings.Contains(s, "IRR") || strings.HasPrefix(s, "USD") || strings.HasPrefix(s, "EUR"):
		return ProviderKindForex
	case len(s) == 3 && s == strings.ToUpper(s):
		// treat unknown 3-letter codes as forex for now (e.g., GBP)
		return ProviderKindForex
	case strings.HasPrefix(s, "BTC") || strings.HasPrefix(s, "ETH"):
		return ProviderKindCrypto
	case s == "XAU" || s == "XAG" || s == "XPT" || s == "XPD" || strings.HasPrefix(s, "XAU"):
		return ProviderKindMetal
	default:
		// TODO: add better symbol classification for commodities/metals.
		return ProviderKindCommodity
	}
}

func ensureDefaultPriorities(priorities ProviderPriority, reg *ProviderRegistry) ProviderPriority {
	if priorities == nil {
		priorities = DefaultProviderPriorities()
	}
	if _, ok := priorities[ProviderKindCrypto]; !ok {
		if reg != nil {
			for _, p := range reg.Crypto {
				priorities[ProviderKindCrypto] = append(priorities[ProviderKindCrypto], p.Name())
			}
		}
	}
	if _, ok := priorities[ProviderKindForex]; !ok {
		if reg != nil {
			for _, p := range reg.Forex {
				priorities[ProviderKindForex] = append(priorities[ProviderKindForex], p.Name())
			}
			for _, p := range reg.IRR {
				priorities[ProviderKindForex] = append(priorities[ProviderKindForex], p.Name())
			}
		}
	}
	if _, ok := priorities[ProviderKindMetal]; !ok {
		if reg != nil {
			for _, p := range reg.Metal {
				priorities[ProviderKindMetal] = append(priorities[ProviderKindMetal], p.Name())
			}
		}
	}
	return priorities
}

func ensureDefaultFXConverter(reg *ProviderRegistry) FXConverter {
	if reg != nil {
		for _, p := range reg.IRR {
			return NewCachedFXConverter(p, defaultFXTTL)
		}
		for _, p := range reg.Forex {
			return NewCachedFXConverter(p, defaultFXTTL)
		}
	}
	return NewCachedFXConverter(nil, defaultFXTTL)
}
