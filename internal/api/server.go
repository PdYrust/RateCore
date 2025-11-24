package api

import (
	"net/http"
	"time"
)

// NewServer wires the HTTP server with sane timeouts.
func NewServer(port string, handler http.Handler) *http.Server {
	if port == "" {
		port = "8080"
	}

	return &http.Server{
		Addr:         ":" + port,
		Handler:      handler,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  60 * time.Second,
	}
}
