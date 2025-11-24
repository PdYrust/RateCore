package handlers

import (
	"encoding/json"
	"net/http"
	"strings"

	"github.com/go-chi/chi/v5"

	"ratecore/internal/api/dto"
	"ratecore/internal/core/price"
)

type PriceHandler struct {
	svc price.Service
}

func NewPriceHandler(svc price.Service) *PriceHandler {
	return &PriceHandler{svc: svc}
}

// GetPrice handles GET /api/v1/price/{symbol}.
func (h *PriceHandler) GetPrice(w http.ResponseWriter, r *http.Request) {
	// TODO: add auth and rate limiting.
	symbol := strings.TrimSpace(chi.URLParam(r, "symbol"))
	if symbol == "" {
		writeError(w, http.StatusBadRequest, "symbol is required")
		return
	}

	p, err := h.svc.GetPrice(r.Context(), symbol)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}

	resp := mapPriceResponse(p)
	writeJSON(w, http.StatusOK, resp)
}

// GetPricesBatch handles POST /api/v1/prices/batch.
func (h *PriceHandler) GetPricesBatch(w http.ResponseWriter, r *http.Request) {
	// TODO: add auth and rate limiting.
	var req dto.BatchPricesRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if len(req.Symbols) == 0 {
		writeError(w, http.StatusBadRequest, "symbols cannot be empty")
		return
	}

	prices, err := h.svc.GetPricesBatch(r.Context(), req.Symbols)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	resp := dto.BatchPricesResponse{Items: make([]dto.PriceResponse, 0, len(prices))}
	for _, p := range prices {
		resp.Items = append(resp.Items, mapPriceResponse(p))
	}

	writeJSON(w, http.StatusOK, resp)
}

func mapPriceResponse(p price.UnifiedPrice) dto.PriceResponse {
	display := p.ValueIRR
	displayCurrency := string(price.DisplayCurrencyIRR)
	if p.ValueToman > 0 {
		// TODO: pick display currency from user preference once available.
		display = p.ValueToman
		displayCurrency = string(price.DisplayCurrencyToman)
	}

	return dto.PriceResponse{
		Symbol:          p.Symbol,
		Kind:            string(p.Kind),
		ValueIRR:        p.ValueIRR,
		ValueToman:      p.ValueToman,
		Display:         display,
		DisplayCurrency: displayCurrency,
		Provider:        p.Provider,
		UpdatedAt:       p.UpdatedAt,
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]any{"error": msg})
}
