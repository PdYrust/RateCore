package irr

import (
	"context"
	"fmt"
	"time"

	"ratecore/internal/core/price"
)

// Provider supplies live USD/IRR conversion using an HTTP FX API.
type Provider struct {
	client *Client
}

// NewProvider constructs a provider with the given client.
func NewProvider(client *Client) *Provider {
	return &Provider{client: client}
}

// Name returns the provider identifier.
func (p *Provider) Name() string {
	return "irr"
}

// GetPrice fetches USD→IRR (IRR per 1 USD) and returns it as a UnifiedPrice.
func (p *Provider) GetPrice(ctx context.Context, symbol string) (price.UnifiedPrice, error) {
	if symbol != "USD_IRR" {
		return price.UnifiedPrice{}, fmt.Errorf("unsupported symbol: %s", symbol)
	}

	rate, err := p.client.USDToIRR(ctx)
	if err != nil {
		return price.UnifiedPrice{}, err
	}

	return price.UnifiedPrice{
		Symbol:       "USD_IRR",
		Kind:         price.PriceKindForex,
		BaseCurrency: "IRR",      // valueBase is IRR per 1 USD
		ValueBase:    rate,       // IRR per USD
		Provider:     p.Name(),
		UpdatedAt:    time.Now().UTC(),
	}, nil
}

func (p *Provider) GetPricesBatch(ctx context.Context, symbols []string) ([]price.UnifiedPrice, error) {
	results := make([]price.UnifiedPrice, 0, len(symbols))
	for _, s := range symbols {
		up, err := p.GetPrice(ctx, s)
		if err != nil {
			return nil, err
		}
		results = append(results, up)
	}
	return results, nil
}
