package price

import "time"

// PriceKind categorizes supported asset types.
type PriceKind string

const (
	PriceKindForex     PriceKind = "forex"
	PriceKindCrypto    PriceKind = "crypto"
	PriceKindMetal     PriceKind = "metal"
	PriceKindCommodity PriceKind = "commodity"
)

// DisplayCurrencyMode determines which currency is surfaced to clients.
type DisplayCurrencyMode string

const (
	DisplayCurrencyIRR   DisplayCurrencyMode = "IRR"
	DisplayCurrencyToman DisplayCurrencyMode = "TOMAN"
)

// UnifiedPrice is the normalized price view served via the API.
type UnifiedPrice struct {
	Symbol       string    `json:"symbol"`
	Kind         PriceKind `json:"kind"`
	BaseCurrency string    `json:"base_currency"`
	ValueBase    float64   `json:"value_base"`
	ValueIRR     float64   `json:"value_irr"`
	ValueToman   float64   `json:"value_toman"`
	Provider     string    `json:"provider"`
	UpdatedAt    time.Time `json:"updated_at"`
}

// NewUnifiedPrice constructs a normalized price record and derives toman from IRR.
func NewUnifiedPrice(symbol string, kind PriceKind, baseCurrency string, valueBase, valueIRR float64, provider string, updatedAt time.Time) UnifiedPrice {
	return UnifiedPrice{
		Symbol:       symbol,
		Kind:         kind,
		BaseCurrency: baseCurrency,
		ValueBase:    valueBase,
		ValueIRR:     valueIRR,
		ValueToman:   toToman(valueIRR),
		Provider:     provider,
		UpdatedAt:    updatedAt,
	}
}

// DisplayValue returns the price in the requested display currency.
func (p UnifiedPrice) DisplayValue(mode DisplayCurrencyMode) float64 {
	switch mode {
	case DisplayCurrencyToman:
		// recompute to avoid drift if ValueToman is stale
		return toToman(p.ValueIRR)
	default:
		return p.ValueIRR
	}
}

// CloneWithDisplayMode recalculates derived fields for the given display mode.
func (p UnifiedPrice) CloneWithDisplayMode(mode DisplayCurrencyMode) UnifiedPrice {
	p.ValueToman = toToman(p.ValueIRR)
	return p
}

func toToman(valueIRR float64) float64 {
	return valueIRR / 10
}
