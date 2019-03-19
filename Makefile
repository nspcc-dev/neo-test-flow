B=\033[0;1m
G=\033[0;92m
R=\033[0m

DEFAULT: up

.PHONY: env-up up down connect help

# Show this help prompt
help:
	@echo '  Usage:'
	@echo ''
	@echo '    make <target>'
	@echo ''
	@echo '  Targets:'
	@echo ''
	@awk '/^#/{ comment = substr($$0,3) } comment && /^[a-zA-Z][a-zA-Z0-9_-]+ ?:/{ print "   ", $$1, comment }' $(MAKEFILE_LIST) | column -t -s ':' | grep -v 'IGNORE' | sort | uniq

# Start only privnet environment
env-up: 
	@echo "\n${B}${G}Start privnet${R}\n"
	@docker-compose up -d neo-cli-privatenet-1 neo-cli-privatenet-2 neo-cli-privatenet-3 neo-cli-privatenet-4

# Start privnet environment with neo-python
up: 
	@echo "\n${B}${G}Start environment${R}\n"
	@docker-compose up -d

# Shut down environment
down: 
	@echo "\n${B}${G}Stop environment${R}\n"
	@docker-compose down -v

# Connect to neo-python
connect:
	@echo "\n${B}${G}Connect to neo-python${R}\n"
	@docker exec -it neo-python /bin/bash
