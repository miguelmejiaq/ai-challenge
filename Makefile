# MiniTel-Lite Emergency Protocol Client Makefile
# 
# This Makefile provides convenient commands for development, testing,
# and execution of the MiniTel-Lite client.

# Default configuration - auto-detect Python version
PYTHON := $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null || echo "python")
VENV_DIR := .venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip

# Server configuration (must be provided - no defaults for security)
SERVER_HOST ?= 
SERVER_PORT ?= 
TIMEOUT ?= 5.0

# Test configuration
TEST_ARGS ?= -v
COVERAGE_ARGS ?= --cov=src --cov-report=html:htmlcov --cov-report=term-missing

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
CYAN := \033[0;36m
WHITE := \033[0;37m
RESET := \033[0m

.PHONY: help setup install clean test test-unit test-integration test-all run run-verbose replay list-sessions verify lint format check-deps clean-sessions clean-cache clean-all

# Default target
help: ## Show this help message
	@echo "$(CYAN)MiniTel-Lite Emergency Protocol Client$(RESET)"
	@echo "$(CYAN)======================================$(RESET)"
	@echo ""
	@echo "$(YELLOW)Available commands:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Configuration:$(RESET)"
	@echo "  SERVER_HOST=$(SERVER_HOST)"
	@echo "  SERVER_PORT=$(SERVER_PORT)"
	@echo "  TIMEOUT=$(TIMEOUT)"
	@echo ""
	@echo "$(YELLOW)Examples:$(RESET)"
	@echo "  make run SERVER_HOST=35.153.159.192 SERVER_PORT=7321    # Execute mission"
	@echo "  make run SERVER_HOST=localhost SERVER_PORT=8080         # Execute with custom server"
	@echo "  make test-integration SERVER_HOST=host SERVER_PORT=port # Run integration tests"
	@echo "  make test-all                                           # Run all tests with coverage"

setup: ## Create virtual environment and install dependencies
	@echo "$(BLUE)Setting up virtual environment...$(RESET)"
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt
	$(VENV_PIP) install -e .
	@echo "$(GREEN)Setup complete!$(RESET)"

install: setup ## Alias for setup

clean-venv: ## Remove virtual environment
	@echo "$(YELLOW)Removing virtual environment...$(RESET)"
	rm -rf $(VENV_DIR)

reinstall: clean-venv setup ## Clean reinstall of virtual environment

# Testing targets
test: test-unit ## Run unit tests only
	@echo "$(GREEN)Unit tests completed$(RESET)"

test-unit: ## Run unit tests (excluding integration tests)
	@echo "$(BLUE)Running unit tests...$(RESET)"
	$(VENV_PYTHON) -m pytest tests/test_protocol.py tests/test_session.py $(TEST_ARGS)

test-integration: check-server-config ## Run integration tests with real server
	@echo "$(BLUE)Running integration tests with server $(SERVER_HOST):$(SERVER_PORT)...$(RESET)"
	SERVER_HOST=$(SERVER_HOST) SERVER_PORT=$(SERVER_PORT) TIMEOUT=$(TIMEOUT) \
	$(VENV_PYTHON) -m pytest tests/test_integration.py $(TEST_ARGS)

test-client: ## Run client tests (mock-based)
	@echo "$(BLUE)Running client tests...$(RESET)"
	$(VENV_PYTHON) -m pytest tests/test_client.py $(TEST_ARGS)

test-protocol: ## Run protocol tests (mock-based)
	@echo "$(BLUE)Running client tests...$(RESET)"
	$(VENV_PYTHON) -m pytest tests/test_protocol.py $(TEST_ARGS)

test-session: ## Run session tests (mock-based)
	@echo "$(BLUE)Running client tests...$(RESET)"
	$(VENV_PYTHON) -m pytest tests/test_session.py $(TEST_ARGS)

test-tui: ## Run tui tests (mock-based)
	@echo "$(BLUE)Running client tests...$(RESET)"
	$(VENV_PYTHON) -m pytest tests/test_tui.py $(TEST_ARGS)

test-utils: ## Run session tests (mock-based)
	@echo "$(BLUE)Running client tests...$(RESET)"
	$(VENV_PYTHON) -m pytest tests/test_utils.py $(TEST_ARGS)

test-all: check-server-config ## Run all tests with coverage report
	@echo "$(BLUE)Running all tests with coverage...$(RESET)"
	SERVER_HOST=$(SERVER_HOST) SERVER_PORT=$(SERVER_PORT) TIMEOUT=$(TIMEOUT) \
	$(VENV_PYTHON) -m pytest tests/ $(TEST_ARGS) $(COVERAGE_ARGS)

test-fast: check-server-config ## Run tests without coverage (faster)
	@echo "$(BLUE)Running fast tests...$(RESET)"
	SERVER_HOST=$(SERVER_HOST) SERVER_PORT=$(SERVER_PORT) TIMEOUT=$(TIMEOUT) \
	$(VENV_PYTHON) -m pytest tests/ $(TEST_ARGS) --no-cov

# Execution targets
run: check-server-config ## Execute JOSHUA override mission with session recording
	@echo "$(PURPLE)🚀 EXECUTING JOSHUA OVERRIDE MISSION$(RESET)"
	@echo "$(PURPLE)====================================$(RESET)"
	@echo "$(YELLOW)Target: $(SERVER_HOST):$(SERVER_PORT)$(RESET)"
	@echo "$(YELLOW)Timeout: $(TIMEOUT)s$(RESET)"
	@echo ""
	$(VENV_PYTHON) -m src.minitel.client \
		--host $(SERVER_HOST) \
		--port $(SERVER_PORT) \
		--timeout $(TIMEOUT) \
		--record

run-verbose: check-server-config ## Execute mission with verbose logging
	@echo "$(PURPLE)🚀 EXECUTING JOSHUA OVERRIDE MISSION (VERBOSE)$(RESET)"
	@echo "$(PURPLE)=============================================$(RESET)"
	$(VENV_PYTHON) -m src.minitel.client \
		--host $(SERVER_HOST) \
		--port $(SERVER_PORT) \
		--timeout $(TIMEOUT) \
		--record \
		--verbose

run-no-record: check-server-config ## Execute mission without session recording
	@echo "$(PURPLE)🚀 EXECUTING JOSHUA OVERRIDE MISSION (NO RECORDING)$(RESET)"
	@echo "$(PURPLE)=================================================$(RESET)"
	$(VENV_PYTHON) -m src.minitel.client \
		--host $(SERVER_HOST) \
		--port $(SERVER_PORT) \
		--timeout $(TIMEOUT)

# Session management
list-sessions: ## List all recorded sessions
	@echo "$(CYAN)📋 RECORDED SESSIONS$(RESET)"
	@echo "$(CYAN)==================$(RESET)"
	$(VENV_PYTHON) -m src.tui.replay --list

replay: ## Launch TUI session replay (specify SESSION_FILE=filename)
	@if [ -z "$(SESSION_FILE)" ]; then \
		echo "$(RED)Error: Please specify SESSION_FILE=filename$(RESET)"; \
		echo "$(YELLOW)Example: make replay SESSION_FILE=session_20250917_113136.json$(RESET)"; \
		echo "$(YELLOW)Use 'make list-sessions' to see available sessions$(RESET)"; \
		exit 1; \
	fi
	@echo "$(CYAN)🎬 LAUNCHING SESSION REPLAY$(RESET)"
	@echo "$(CYAN)===========================$(RESET)"
	$(VENV_PYTHON) -m src.tui.replay --session sessions/$(SESSION_FILE)

replay-latest: ## Replay the most recent session
	@echo "$(CYAN)🎬 LAUNCHING LATEST SESSION REPLAY$(RESET)"
	@echo "$(CYAN)=================================$(RESET)"
	@if [ ! -d sessions/ ]; then \
		echo "$(RED)Error: sessions directory not found$(RESET)"; \
		echo "$(YELLOW)Run a mission first to create sessions$(RESET)"; \
		exit 1; \
	fi
	@LATEST_SESSION=$$(ls -t sessions/*.json 2>/dev/null | head -n1); \
	if [ -z "$$LATEST_SESSION" ]; then \
		echo "$(RED)Error: No session files found$(RESET)"; \
		echo "$(YELLOW)Run a mission first to create sessions$(RESET)"; \
		exit 1; \
	else \
		echo "$(YELLOW)Replaying: $$LATEST_SESSION$(RESET)"; \
		$(VENV_PYTHON) -m src.tui.replay --session "$$LATEST_SESSION"; \
	fi

# Verification and quality
verify: ## Run requirements verification
	@echo "$(BLUE)🔍 VERIFYING REQUIREMENTS$(RESET)"
	@echo "$(BLUE)=========================$(RESET)"
	$(VENV_PYTHON) verify_requirements.py

lint: ## Run code linting (if flake8 is available)
	@echo "$(BLUE)Running code linting...$(RESET)"
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 src/ tests/ --max-line-length=100 --ignore=E501,W503; \
	else \
		echo "$(YELLOW)flake8 not installed, skipping linting$(RESET)"; \
	fi

format: ## Format code (if black is available)
	@echo "$(BLUE)Formatting code...$(RESET)"
	@if command -v black >/dev/null 2>&1; then \
		black src/ tests/ --line-length=100; \
	else \
		echo "$(YELLOW)black not installed, skipping formatting$(RESET)"; \
	fi

check-deps: ## Check for security vulnerabilities in dependencies
	@echo "$(BLUE)Checking dependencies for security issues...$(RESET)"
	$(VENV_PIP) check
	@if command -v safety >/dev/null 2>&1; then \
		safety check; \
	else \
		echo "$(YELLOW)safety not installed, skipping security check$(RESET)"; \
	fi

# Cleanup targets
clean-sessions: ## Remove all session files
	@echo "$(YELLOW)Removing session files...$(RESET)"
	rm -rf sessions/*.json

clean-cache: ## Remove Python cache files
	@echo "$(YELLOW)Removing Python cache files...$(RESET)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf *.egg-info/

clean: clean-cache ## Remove cache files and build artifacts

clean-all: clean clean-sessions ## Remove all generated files and sessions

# Development targets
dev-setup: setup ## Setup development environment with additional tools
	@echo "$(BLUE)Installing development tools...$(RESET)"
	$(VENV_PIP) install black flake8 safety mypy
	@echo "$(GREEN)Development environment ready!$(RESET)"

# Documentation
docs: ## Generate documentation (placeholder)
	@echo "$(BLUE)Documentation generation not implemented yet$(RESET)"

# Build targets
build: ## Build distribution packages
	@echo "$(BLUE)Building distribution packages...$(RESET)"
	$(VENV_PYTHON) setup.py sdist bdist_wheel

# Status and info
status: ## Show project status
	@echo "$(CYAN)MiniTel-Lite Project Status$(RESET)"
	@echo "$(CYAN)==========================$(RESET)"
	@echo "$(YELLOW)Virtual Environment:$(RESET) $(if $(wildcard $(VENV_DIR)),$(GREEN)✓ Active$(RESET),$(RED)✗ Not found$(RESET))"
	@echo "$(YELLOW)Server Configuration:$(RESET) $(SERVER_HOST):$(SERVER_PORT)"
	@echo "$(YELLOW)Session Directory:$(RESET) $(if $(wildcard sessions/),$(GREEN)✓ Exists$(RESET),$(YELLOW)⚠ Not found$(RESET))"
	@if [ -d sessions/ ]; then \
		echo "$(YELLOW)Recorded Sessions:$(RESET) $$(ls sessions/*.json 2>/dev/null | wc -l | tr -d ' ')"; \
	fi
	@echo "$(YELLOW)Test Coverage:$(RESET) $(if $(wildcard htmlcov/),$(GREEN)✓ Available$(RESET),$(YELLOW)⚠ Run 'make test-all'$(RESET))"

# Quick mission execution
mission: run ## Alias for 'run' - execute the JOSHUA override mission

# Emergency targets
emergency-run: ## Emergency mission execution with minimal output
	@$(VENV_PYTHON) -m src.minitel.client --host $(SERVER_HOST) --port $(SERVER_PORT) --timeout $(TIMEOUT) --record 2>/dev/null

# Show configuration
config: ## Show current configuration
	@echo "$(CYAN)Current Configuration$(RESET)"
	@echo "$(CYAN)====================$(RESET)"
	@echo "SERVER_HOST = $(SERVER_HOST)"
	@echo "SERVER_PORT = $(SERVER_PORT)"
	@echo "TIMEOUT = $(TIMEOUT)"
	@echo "PYTHON = $(PYTHON)"
	@echo "VENV_DIR = $(VENV_DIR)"
	@echo "TEST_ARGS = $(TEST_ARGS)"

# Internal target to check server configuration
check-server-config:
	@if [ -z "$(SERVER_HOST)" ]; then \
		echo "$(RED)Error: SERVER_HOST is required but not set$(RESET)"; \
		echo "$(YELLOW)Please provide SERVER_HOST:$(RESET)"; \
		echo "  make run SERVER_HOST=your.server.com SERVER_PORT=7321"; \
		echo "$(YELLOW)Or set environment variable:$(RESET)"; \
		echo "  export SERVER_HOST=your.server.com"; \
		exit 1; \
	fi
	@if [ -z "$(SERVER_PORT)" ]; then \
		echo "$(RED)Error: SERVER_PORT is required but not set$(RESET)"; \
		echo "$(YELLOW)Please provide SERVER_PORT:$(RESET)"; \
		echo "  make run SERVER_HOST=your.server.com SERVER_PORT=7321"; \
		echo "$(YELLOW)Or set environment variable:$(RESET)"; \
		echo "  export SERVER_PORT=7321"; \
		exit 1; \
	fi
