package binance

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"time"

	"ratecore/internal/core/price"
)

// Provider implements PriceProvider for Binance spot prices.
type Provider struct {
	client *Client
}

// NewProvider builds a Provider with the given client.
func NewProvider(client *Client) *Provider {
	return &Provider{client: client}
}

// Name returns the provider identifier.
func (p *Provider) Name() string {
	return "binance"
}

// GetPrice fetches a single symbol price from Binance.
func (p *Provider) GetPrice(ctx context.Context, symbol string) (price.UnifiedPrice, error) {
	binanceSymbol, err := mapToBinanceSymbol(symbol)
	if err != nil {
		return price.UnifiedPrice{}, err
	}

	var resp tickerPriceResponse
	if err := p.client.doGet(ctx, "/api/v3/ticker/price", map[string][]string{"symbol": {binanceSymbol}}, &resp); err != nil {
		return price.UnifiedPrice{}, err
	}

	val, err := strconv.ParseFloat(resp.Price, 64)
	if err != nil {
		return price.UnifiedPrice{}, fmt.Errorf("binance: parse price for %s: %w", symbol, err)
	}

	return price.UnifiedPrice{
		Symbol:       strings.ToUpper(symbol),
		Kind:         price.PriceKindCrypto,
		BaseCurrency: "USDT",
		ValueBase:    val,
		Provider:     p.Name(),
		UpdatedAt:    time.Now().UTC(),
	}, nil
}

// GetPricesBatch fetches multiple symbols sequentially.
// TODO: use Binance batch endpoints and cache them locally.
func (p *Provider) GetPricesBatch(ctx context.Context, symbols []string) ([]price.UnifiedPrice, error) {
	results := make([]price.UnifiedPrice, 0, len(symbols))
	for _, sym := range symbols {
		up, err := p.GetPrice(ctx, sym)
		if err != nil {
			return nil, err
		}
		results = append(results, up)
	}
	return results, nil
}

// mapToBinanceSymbol maps logical symbols to Binance trading pairs.
// TODO: expand coverage and load from config or a map.
func mapToBinanceSymbol(symbol string) (string, error) {
	switch strings.ToUpper(symbol) {
	case "BTC":
		return "BTCUSDT", nil
	case "ETH":
		return "ETHUSDT", nil
	default:
		return "", fmt.Errorf("unsupported symbol: %s", symbol)
	}
}

type tickerPriceResponse struct {
	Symbol string `json:"symbol"`
	Price  string `json:"price"`
}
