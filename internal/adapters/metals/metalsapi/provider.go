package metalsapi

import (
	"context"
	"fmt"
	"strings"
	"time"

	"ratecore/internal/core/price"
)

// Provider implements PriceProvider for metals prices in USD.
type Provider struct {
	client *Client
}

// NewProvider builds a metals provider with the given client.
func NewProvider(client *Client) *Provider {
	return &Provider{client: client}
}

// Name returns the provider identifier.
func (p *Provider) Name() string {
	return "metalsapi"
}

// GetPrice fetches a single metal price.
func (p *Provider) GetPrice(ctx context.Context, symbol string) (price.UnifiedPrice, error) {
	prices, err := p.client.GetMetalsPrices(ctx)
	if err != nil {
		return price.UnifiedPrice{}, err
	}

	s := strings.ToUpper(symbol)
	val, ok := prices[s]
	if !ok {
		return price.UnifiedPrice{}, fmt.Errorf("metal price not found for %s", s)
	}

	return price.UnifiedPrice{
		Symbol:       s,
		Kind:         price.PriceKindMetal,
		BaseCurrency: "USD",
		ValueBase:    val, // USD per ounce
		Provider:     p.Name(),
		UpdatedAt:    time.Now().UTC(),
	}, nil
}

// GetPricesBatch returns multiple metal prices using a single fetch.
func (p *Provider) GetPricesBatch(ctx context.Context, symbols []string) ([]price.UnifiedPrice, error) {
	prices, err := p.client.GetMetalsPrices(ctx)
	if err != nil {
		return nil, err
	}

	now := time.Now().UTC()
	results := make([]price.UnifiedPrice, 0, len(symbols))
	for _, sym := range symbols {
		s := strings.ToUpper(sym)
		val, ok := prices[s]
		if !ok {
			return nil, fmt.Errorf("metal price not found for %s", s)
		}
		results = append(results, price.UnifiedPrice{
			Symbol:       s,
			Kind:         price.PriceKindMetal,
			BaseCurrency: "USD",
			ValueBase:    val, // USD per ounce
			Provider:     p.Name(),
			UpdatedAt:    now,
		})
	}
	return results, nil
}
