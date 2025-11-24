package exchangerateapi

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
)

// Client wraps HTTP calls to the exchange rate API.
type Client struct {
	httpClient *http.Client
	baseURL    string
}

// NewClient constructs a client from config.
func NewClient(cfg Config) *Client {
	return &Client{
		httpClient: &http.Client{Timeout: cfg.Timeout},
		baseURL:    cfg.BaseURL,
	}
}

// GetRates fetches rates for the given base currency.
func (c *Client) GetRates(ctx context.Context, base string) (map[string]float64, error) {
	u, err := url.Parse(c.baseURL)
	if err != nil {
		return fallbackRates(), fmt.Errorf("forex: invalid base url: %w", err)
	}
	u.Path = "/latest"
	q := u.Query()
	q.Set("base", base)
	u.RawQuery = q.Encode()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u.String(), nil)
	if err != nil {
		return fallbackRates(), fmt.Errorf("forex: build request: %w", err)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fallbackRates(), fmt.Errorf("forex: request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 2048))
		return fallbackRates(), fmt.Errorf("forex: non-200 status %d: %s", resp.StatusCode, string(body))
	}

	var payload struct {
		Rates map[string]float64 `json:"rates"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return fallbackRates(), fmt.Errorf("forex: decode failed: %w", err)
	}

	if payload.Rates == nil {
		return fallbackRates(), fmt.Errorf("forex: missing rates in response")
	}
	return payload.Rates, nil
}

func fallbackRates() map[string]float64 {
	return map[string]float64{
		"USD": 1.0,
		"EUR": 0.92,
		"GBP": 0.8,
		"IRR": 42000,
	}
}
