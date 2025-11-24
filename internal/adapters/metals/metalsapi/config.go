package metalsapi

import (
	"os"
	"time"
)

// Config holds configuration for the metals provider client.
type Config struct {
	BaseURL string
	Timeout time.Duration
}

// DefaultConfig returns safe defaults for a public metals API.
func DefaultConfig() Config {
	return Config{
		BaseURL: "https://api.metals.example.com",
		Timeout: 5 * time.Second,
	}
}

// FromEnv overrides defaults with environment variables when present.
// TODO: add API key or auth support if the chosen provider requires it.
func FromEnv() Config {
	cfg := DefaultConfig()
	if v := os.Getenv("RCORE_METALS_BASE_URL"); v != "" {
		cfg.BaseURL = v
	}
	return cfg
}
