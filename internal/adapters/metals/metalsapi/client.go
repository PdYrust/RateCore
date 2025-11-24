package metalsapi

import (
	"context"
	"net/http"
)

// Client wraps HTTP calls to a metals price API.
type Client struct {
	httpClient *http.Client
	baseURL    string
}

// NewClient builds a metals client from config.
func NewClient(cfg Config) *Client {
	return &Client{
		httpClient: &http.Client{Timeout: cfg.Timeout},
		baseURL:    cfg.BaseURL,
	}
}

// GetMetalsPrices returns metal prices in USD per ounce.
// TODO: replace stub with real HTTP call to chosen provider using c.httpClient and c.baseURL.
func (c *Client) GetMetalsPrices(ctx context.Context) (map[string]float64, error) {
	_ = ctx
	return map[string]float64{
		"XAU": 2300.00, // Gold ounce USD
		"XAG": 28.50,   // Silver ounce USD
		"XPT": 920.00,  // Platinum ounce USD
		"XPD": 1300.00, // Palladium ounce USD
	}, nil
}
