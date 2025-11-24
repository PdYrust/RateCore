package config

// CurrencyMode defines how prices are displayed.
type CurrencyMode string

const (
	CurrencyIRR   CurrencyMode = "IRR"
	CurrencyToman CurrencyMode = "TOMAN"
)

// DisplaySettings holds global preferences for rendering prices.
type DisplaySettings struct {
	CurrencyMode CurrencyMode `json:"currency_mode"`
}
