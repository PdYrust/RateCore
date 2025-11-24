package wiring

import (
	"time"

	"ratecore/internal/adapters/crypto/binance"
	"ratecore/internal/adapters/forex/exchangerateapi"
	"ratecore/internal/adapters/forex/irr"
	"ratecore/internal/adapters/metals/metalsapi"
	"ratecore/internal/adapters/static"
	"ratecore/internal/core/price"
)

// NewDefaultPriceService composes providers, priorities, and FX converter for the API.
func NewDefaultPriceService(modeProvider price.DisplayModeProvider) *price.DefaultPriceService {
	registry := price.NewProviderRegistry()

	staticProvider := static.NewProvider()
	registry.RegisterCrypto(staticProvider)
	registry.RegisterForex(staticProvider)
	registry.RegisterMetal(staticProvider)

	binanceClient := binance.NewClient(binance.FromEnv())
	registry.RegisterCrypto(binance.NewProvider(binanceClient))

	fxClient := exchangerateapi.NewClient(exchangerateapi.FromEnv())
	registry.RegisterForex(exchangerateapi.NewProvider(fxClient))

	metalClient := metalsapi.NewClient(metalsapi.FromEnv())
	registry.RegisterMetal(metalsapi.NewProvider(metalClient))

	irrClient := irr.NewClient(irr.FromEnv())
	irrProvider := irr.NewProvider(irrClient)
	registry.RegisterForex(irrProvider)

	priorities := price.DefaultProviderPriorities()
	// give static providers highest priority per kind
	priorities[price.ProviderKindCrypto] = append([]string{staticProvider.Name()}, priorities[price.ProviderKindCrypto]...)
	priorities[price.ProviderKindForex] = append([]string{staticProvider.Name()}, priorities[price.ProviderKindForex]...)
	priorities[price.ProviderKindMetal] = append([]string{staticProvider.Name()}, priorities[price.ProviderKindMetal]...)

	fx := price.NewCachedFXConverter(irrProvider, 30*time.Second)

	return price.NewDefaultPriceService(registry, priorities, modeProvider, fx)
}
