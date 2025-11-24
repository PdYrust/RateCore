package main

import (
	"context"
	"errors"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"ratecore/internal/api"
	configcore "ratecore/internal/core/config"
	"ratecore/internal/core/price"
	"ratecore/internal/telemetry/logging"
	"ratecore/internal/wiring"
	"ratecore/pkg/config"
)

func main() {
	cfg := config.Load()

	logger := logging.NewLogger(cfg.LogLevel)
	logger.Info("starting ratecore-api", "port", cfg.HTTPPort)

	displayCfgSvc := configcore.NewInMemoryService(configcore.DisplaySettings{
		CurrencyMode: configcore.CurrencyIRR,
	})
	priceSvc := wiring.NewDefaultPriceService(displayModeAdapter{cfg: displayCfgSvc})

	router := api.NewRouter(api.RouterParams{
		PriceService:     priceSvc,
		DisplayCfg:       displayCfgSvc,
		Logger:           logger,
		EnableRequestLog: true,
	})

	server := api.NewServer(cfg.HTTPPort, router)

	go func() {
		if err := server.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
			logger.Error("http server failed", "err", err)
		}
	}()

	shutdown(logger, server)
}

func shutdown(logger logging.Logger, server *http.Server) {
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	logger.Info("shutting down http server")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		logger.Error("graceful shutdown failed", "err", err)
	}

	logger.Info("server stopped")
}

type displayModeAdapter struct {
	cfg configcore.Service
}

func (a displayModeAdapter) Mode() price.DisplayCurrencyMode {
	settings := a.cfg.GetDisplaySettings()
	if settings.CurrencyMode == configcore.CurrencyToman {
		return price.DisplayCurrencyToman
	}
	return price.DisplayCurrencyIRR
}
