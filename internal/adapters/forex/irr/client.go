package irr

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
)

// Client wraps HTTP calls to retrieve USD/IRR rates.
type Client struct {
	httpClient *http.Client
	baseURL    string
	apiKey     string
}

// NewClient constructs a client from config.
func NewClient(cfg Config) *Client {
	return &Client{
		httpClient: &http.Client{Timeout: cfg.Timeout},
		baseURL:    cfg.BaseURL,
		apiKey:     cfg.APIKey,
	}
}

// USDToIRR fetches IRR per 1 USD from the configured endpoint.
// TODO: adapt path/query to the chosen FX provider when finalized.
func (c *Client) USDToIRR(ctx context.Context) (float64, error) {
	u, err := url.Parse(c.baseURL)
	if err != nil {
		return 0, fmt.Errorf("irr: invalid base url: %w", err)
	}
	u.Path = "/convert"
	q := u.Query()
	q.Set("from", "USD")
	q.Set("to", "IRR")
	if c.apiKey != "" {
		q.Set("apiKey", c.apiKey)
	}
	u.RawQuery = q.Encode()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u.String(), nil)
	if err != nil {
		return 0, fmt.Errorf("irr: build request: %w", err)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return 0, fmt.Errorf("irr: request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 2048))
		return 0, fmt.Errorf("irr: non-200 status %d: %s", resp.StatusCode, string(body))
	}

	var payload struct {
		Result float64 `json:"result"`
		Info   struct {
			Rate float64 `json:"rate"`
		} `json:"info"`
	}

	dec := json.NewDecoder(resp.Body)
	if err := dec.Decode(&payload); err != nil {
		return 0, fmt.Errorf("irr: decode failed: %w", err)
	}

	// Prefer Result if present; fallback to Rate; otherwise error.
	if payload.Result > 0 {
		return payload.Result, nil
	}
	if payload.Info.Rate > 0 {
		return payload.Info.Rate, nil
	}
	return 0, fmt.Errorf("irr: missing rate in response")
}
