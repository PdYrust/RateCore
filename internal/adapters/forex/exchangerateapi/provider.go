package exchangerateapi

import (
	"context"
	"fmt"
	"strings"
	"time"

	"ratecore/internal/core/price"
)

// Provider implements PriceProvider using a public FX rates API.
type Provider struct {
	client *Client
}

// NewProvider creates a provider with the given client.
func NewProvider(client *Client) *Provider {
	return &Provider{client: client}
}

// Name returns the provider identifier.
func (p *Provider) Name() string {
	return "exchangerateapi"
}

// GetPrice interprets symbol as a fiat currency code and returns its rate vs USD.
// ValueBase is the amount of symbol currency per 1 USD (base = USD).
func (p *Provider) GetPrice(ctx context.Context, symbol string) (price.UnifiedPrice, error) {
	rates, err := p.client.GetRates(ctx, "USD")
	if err != nil {
		return price.UnifiedPrice{}, err
	}

	s := strings.ToUpper(symbol)
	if s == "USD" {
		return price.UnifiedPrice{
			Symbol:       "USD",
			Kind:         price.PriceKindForex,
			BaseCurrency: "USD",
			ValueBase:    1.0,
			Provider:     p.Name(),
			UpdatedAt:    time.Now().UTC(),
		}, nil
	}

	rate, ok := rates[s]
	if !ok {
		return price.UnifiedPrice{}, fmt.Errorf("forex: rate not found for %s", s)
	}

	return price.UnifiedPrice{
		Symbol:       s,
		Kind:         price.PriceKindForex,
		BaseCurrency: "USD",
		// ValueBase: units of currency s per 1 USD, as returned by exchangerate.host.
		ValueBase: rate,
		Provider:  p.Name(),
		UpdatedAt: time.Now().UTC(),
	}, nil
}

// GetPricesBatch fetches rates once and returns all requested symbols.
func (p *Provider) GetPricesBatch(ctx context.Context, symbols []string) ([]price.UnifiedPrice, error) {
	rates, err := p.client.GetRates(ctx, "USD")
	if err != nil {
		return nil, err
	}

	now := time.Now().UTC()
	results := make([]price.UnifiedPrice, 0, len(symbols))
	for _, sym := range symbols {
		s := strings.ToUpper(sym)
		switch s {
		case "USD":
			results = append(results, price.UnifiedPrice{
				Symbol:       s,
				Kind:         price.PriceKindForex,
				BaseCurrency: "USD",
				ValueBase:    1.0,
				Provider:     p.Name(),
				UpdatedAt:    now,
			})
		default:
			rate, ok := rates[s]
			if !ok {
				return nil, fmt.Errorf("forex: rate not found for %s", s)
			}
			results = append(results, price.UnifiedPrice{
				Symbol:       s,
				Kind:         price.PriceKindForex,
				BaseCurrency: "USD",
				// ValueBase: units of currency s per 1 USD, as returned by exchangerate.host.
				ValueBase: rate,
				Provider:  p.Name(),
				UpdatedAt: now,
			})
		}
	}
	return results, nil
}
