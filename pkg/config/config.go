package config

import "os"

type Config struct {
	HTTPPort string
	LogLevel string
}

// Load populates configuration from environment variables.
// TODO: extend with YAML file loading and validation.
func Load() Config {
	return Config{
		HTTPPort: getenvDefault("RCORE_HTTP_PORT", "8080"),
		LogLevel: getenvDefault("RCORE_LOG_LEVEL", "info"),
	}
}

func getenvDefault(key, def string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return def
}
