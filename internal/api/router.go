package api

import (
	"net/http"

	"github.com/go-chi/chi/v5"

	"ratecore/internal/api/handlers"
	"ratecore/internal/api/middleware"
	configcore "ratecore/internal/core/config"
	"ratecore/internal/core/price"
	"ratecore/internal/telemetry/logging"
)

// RouterParams bundles dependencies required by the HTTP router.
type RouterParams struct {
	PriceService     price.Service
	DisplayCfg       configcore.Service
	Logger           logging.Logger
	EnableRequestLog bool
}

func NewRouter(params RouterParams) http.Handler {
	r := chi.NewRouter()

	if params.EnableRequestLog {
		r.Use(middleware.Logging(params.Logger))
	}

	health := handlers.NewHealthHandler()
	priceHandler := handlers.NewPriceHandler(params.PriceService)

	r.Route("/api/v1", func(r chi.Router) {
		// TODO: add auth and rate limiting middleware here.
		r.Get("/healthz", health.Health)
		r.Get("/readyz", health.Ready)

		r.Get("/price/{symbol}", priceHandler.GetPrice)
		r.Post("/prices/batch", priceHandler.GetPricesBatch)
	})

	return r
}
