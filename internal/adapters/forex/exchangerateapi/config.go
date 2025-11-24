package exchangerateapi

import (
	"os"
	"time"
)

// Config holds exchangerate API settings.
type Config struct {
	BaseURL string
	Timeout time.Duration
}

// DefaultConfig returns sane defaults.
func DefaultConfig() Config {
	return Config{
		BaseURL: "https://api.exchangerate.host",
		Timeout: 5 * time.Second,
	}
}

// FromEnv loads config overriding defaults with environment variables where present.
// TODO: extend with API key support if a paid tier is used.
func FromEnv() Config {
	cfg := DefaultConfig()
	if v := os.Getenv("RCORE_FOREX_BASE_URL"); v != "" {
		cfg.BaseURL = v
	}
	return cfg
}
