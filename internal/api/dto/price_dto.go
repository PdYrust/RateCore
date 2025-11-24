package dto

import "time"

// PriceResponse is the outbound representation for a single price.
type PriceResponse struct {
	Symbol          string    `json:"symbol"`
	Kind            string    `json:"kind"`
	ValueIRR        float64   `json:"value_irr"`
	ValueToman      float64   `json:"value_toman"`
	Display         float64   `json:"display"`
	DisplayCurrency string    `json:"display_currency"`
	Provider        string    `json:"provider"`
	UpdatedAt       time.Time `json:"updated_at"`
}

// BatchPricesRequest carries symbols for bulk lookup.
type BatchPricesRequest struct {
	Symbols []string `json:"symbols"`
}

// BatchPricesResponse aggregates price responses.
type BatchPricesResponse struct {
	Items []PriceResponse `json:"items"`
}
