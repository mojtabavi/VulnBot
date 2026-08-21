# Pentest-POMDP lab control.
# PROFILE selects the LLM backend variant: local (RTX 5080, no egress) | api (hosted LLM).
PROFILE ?= local

.PHONY: help up down build shell-kali shell-agent logs test-channel config

help:            ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

config:          ## validate the compose file for the selected PROFILE
	docker compose --profile $(PROFILE) config

up:              ## build + start the lab (PROFILE=local|api)
	docker compose --profile $(PROFILE) up -d --build

down:            ## stop and remove the lab (all profiles)
	docker compose --profile local --profile api down

build:           ## build images for the selected PROFILE
	docker compose --profile $(PROFILE) build

shell-kali:      ## shell into the kali tools host
	docker exec -it kali-tools bash

shell-agent:     ## shell into the agent (container name is 'agent' in both profiles)
	docker exec -it agent bash

logs:            ## follow logs
	docker compose --profile $(PROFILE) logs -f

test-channel:    ## quick smoke test: agent scans target
	docker exec agent bash -lc "nmap -Pn target || true"
