SHELL := /bin/bash
DOCKER_COMPOSE ?= docker compose
GO_ENV := GOCACHE=$(CURDIR)/.cache/go-build GOPATH=$(CURDIR)/.gopath

.PHONY: install setup run check build-api run-api run-bot up down logs clean update

install:
	./scripts/install.sh

setup:
	./scripts/setup.sh

run:
	./scripts/run.sh

check:
	./scripts/check.sh

build-api:
	mkdir -p ./.cache/go-build ./.gopath
	$(GO_ENV) go build -o ./bin/ratecore-api ./cmd/ratecore-api

run-api: build-api
	./bin/ratecore-api

run-bot:
	@if [ ! -d ".venv" ]; then echo ".venv missing. Run make install first."; exit 1; fi
	. .venv/bin/activate && python -m ratecore_bot.main

up:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f

clean:
	rm -rf ./bin ./logs ./runtime ./.venv ./data

update:
	./scripts/update.sh
