package binance

import (
	"os"
	"time"
)

// Config holds Binance client configuration.
type Config struct {
	BaseURL string
	Timeout time.Duration
}

// DefaultConfig returns sane defaults for Binance public API.
func DefaultConfig() Config {
	return Config{
		BaseURL: "https://api.binance.com",
		Timeout: 5 * time.Second,
	}
}

// FromEnv overrides defaults with environment variables when present.
// TODO: extend with more options (proxy, retry, etc).
func FromEnv() Config {
	cfg := DefaultConfig()
	if v := os.Getenv("RCORE_BINANCE_BASE_URL"); v != "" {
		cfg.BaseURL = v
	}
	return cfg
}
