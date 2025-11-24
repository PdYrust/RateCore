package irr

import (
	"os"
	"time"
)

// Config holds settings for the USD→IRR provider.
type Config struct {
	BaseURL string
	Timeout time.Duration
	APIKey  string
}

// DefaultConfig returns safe defaults for a public FX endpoint.
func DefaultConfig() Config {
	return Config{
		BaseURL: "https://api.exchangerate.host",
		Timeout: 5 * time.Second,
	}
}

// FromEnv overrides defaults with environment variables where present.
// Supported vars: RCORE_IRR_BASE_URL, RCORE_IRR_API_KEY.
func FromEnv() Config {
	cfg := DefaultConfig()
	if v := os.Getenv("RCORE_IRR_BASE_URL"); v != "" {
		cfg.BaseURL = v
	}
	if v := os.Getenv("RCORE_IRR_API_KEY"); v != "" {
		cfg.APIKey = v
	}
	return cfg
}
