package price

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// FXConverter provides USD→IRR conversion.
// Prices should stay fresh; implementations should keep a short TTL to balance freshness with API limits.
type FXConverter interface {
	// USDToIRR returns how many IRR for 1 USD.
	USDToIRR(ctx context.Context) (float64, error)
}

// CachedFXConverter caches USD/IRR rates fetched from a PriceProvider.
type CachedFXConverter struct {
	provider PriceProvider
	ttl      time.Duration

	mu       sync.RWMutex
	lastRate float64
	expires  time.Time
}

// NewCachedFXConverter constructs a converter with cache TTL.
func NewCachedFXConverter(provider PriceProvider, ttl time.Duration) *CachedFXConverter {
	return &CachedFXConverter{
		provider: provider,
		ttl:      ttl,
	}
}

// USDToIRR returns cached value when fresh; otherwise fetches from provider using USD_IRR symbol.
func (c *CachedFXConverter) USDToIRR(ctx context.Context) (float64, error) {
	c.mu.RLock()
	if time.Now().Before(c.expires) && c.lastRate > 0 {
		rate := c.lastRate
		c.mu.RUnlock()
		return rate, nil
	}
	c.mu.RUnlock()

	if c.provider == nil {
		return 0, fmt.Errorf("usd/irr provider not configured")
	}

	price, err := c.provider.GetPrice(ctx, usdIRRSymbol)
	if err != nil {
		return 0, err
	}

	rate := price.ValueBase

	if rate <= 0 {
		return 0, fmt.Errorf("usd/irr provider returned invalid rate: %f", rate)
	}

	c.mu.Lock()
	c.lastRate = rate
	c.expires = time.Now().Add(c.ttl)
	c.mu.Unlock()

	return rate, nil
}
