package static

import (
	"context"
	"fmt"
	"strings"
	"time"

	"ratecore/internal/core/price"
)

// Provider serves static prices for offline or test usage.
type Provider struct {
	name string
	data map[string]price.UnifiedPrice
}

// NewProvider builds a static provider with preloaded prices.
func NewProvider() *Provider {
	now := time.Now().UTC()
	data := map[string]price.UnifiedPrice{
		"USD": {
			Symbol:       "USD",
			Kind:         price.PriceKindForex,
			BaseCurrency: "USD",
			ValueBase:    1.0,
			Provider:     "static",
			UpdatedAt:    now,
		},
		"EUR": {
			Symbol:       "EUR",
			Kind:         price.PriceKindForex,
			BaseCurrency: "USD",
			ValueBase:    0.92,
			Provider:     "static",
			UpdatedAt:    now,
		},
		"GBP": {
			Symbol:       "GBP",
			Kind:         price.PriceKindForex,
			BaseCurrency: "USD",
			ValueBase:    0.80,
			Provider:     "static",
			UpdatedAt:    now,
		},
		"IRR": {
			Symbol:       "IRR",
			Kind:         price.PriceKindForex,
			BaseCurrency: "IRR",
			ValueBase:    42000,
			Provider:     "static",
			UpdatedAt:    now,
		},
		"BTC": {
			Symbol:       "BTC",
			Kind:         price.PriceKindCrypto,
			BaseCurrency: "USDT",
			ValueBase:    62000,
			Provider:     "static",
			UpdatedAt:    now,
		},
		"ETH": {
			Symbol:       "ETH",
			Kind:         price.PriceKindCrypto,
			BaseCurrency: "USDT",
			ValueBase:    3200,
			Provider:     "static",
			UpdatedAt:    now,
		},
		"XAU": {
			Symbol:       "XAU",
			Kind:         price.PriceKindMetal,
			BaseCurrency: "USD",
			ValueBase:    2300,
			Provider:     "static",
			UpdatedAt:    now,
		},
	}
	return &Provider{name: "static", data: data}
}

// Name returns provider identifier.
func (p *Provider) Name() string {
	return p.name
}

// GetPrice returns a static price when present.
func (p *Provider) GetPrice(ctx context.Context, symbol string) (price.UnifiedPrice, error) {
	_ = ctx
	if val, ok := p.data[strings.ToUpper(symbol)]; ok {
		return val, nil
	}
	return price.UnifiedPrice{}, fmt.Errorf("static price not found for %s", symbol)
}

// GetPricesBatch returns static prices when available.
func (p *Provider) GetPricesBatch(ctx context.Context, symbols []string) ([]price.UnifiedPrice, error) {
	_ = ctx
	var res []price.UnifiedPrice
	for _, s := range symbols {
		if val, ok := p.data[strings.ToUpper(s)]; ok {
			res = append(res, val)
		}
	}
	if len(res) == 0 {
		return nil, fmt.Errorf("static prices not found for requested symbols")
	}
	return res, nil
}
