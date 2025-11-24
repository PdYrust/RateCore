package config

import "sync"

// Service abstracts display configuration management.
type Service interface {
	GetDisplaySettings() DisplaySettings
	SetCurrencyMode(mode CurrencyMode)
}

type inMemoryService struct {
	mu       sync.RWMutex
	settings DisplaySettings
}

func NewInMemoryService(initial DisplaySettings) Service {
	return &inMemoryService{
		settings: initial,
	}
}

func (s *inMemoryService) GetDisplaySettings() DisplaySettings {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.settings
}

func (s *inMemoryService) SetCurrencyMode(mode CurrencyMode) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.settings.CurrencyMode = mode
}
