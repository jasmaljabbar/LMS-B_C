# Makefile

# Project configuration
PROJECT_NAME := dubai-lms
BACKEND_DIR := backend
VENV_DIR := .venv
MAIN_MODULE := backend.main:app
APP := $(MAIN_MODULE)
UVICORN_ARGS := --host 0.0.0.0 --port 8000 --reload
PID_FILE := $(BACKEND_DIR)/server.pid  # File to store the process ID
LOG_FILE := $(BACKEND_DIR)/server.log  # File to store server logs

# Make targets phony (not files)
.PHONY: help start stop clean install venv

# Help target: Displays a help message
help: ## Display this help message
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# venv target: Creates a virtual environment
venv: ## Create a virtual environment
	@echo "Creating virtual environment..."
	python3 -m venv $(VENV_DIR) || { echo "Failed to create virtual environment"; exit 1; }
	@echo "Virtual environment created in $(VENV_DIR)"

# install target: Installs dependencies from requirements.txt
install: venv ## Install dependencies
	@echo "Installing dependencies..."
	$(VENV_DIR)/bin/pip install --upgrade pip || { echo "Failed to upgrade pip"; exit 1; }
	$(VENV_DIR)/bin/pip install -r requirements.txt || { echo "Failed to install dependencies"; exit 1; }
	@echo "Dependencies installed."

# start target: Starts the backend server with logging and tailing the log
start: install ## Start the backend server and tail the log
	@echo "Starting backend server..."
	$(VENV_DIR)/bin/uvicorn $(MAIN_MODULE) $(UVICORN_ARGS) 

# stop target: Stops the backend server
stop: ## Stop the backend server
	@echo "Stopping backend server..."
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		kill -9 $$PID 2>/dev/null; \
		rm -f $(PID_FILE); \
		echo "Backend server stopped (PID: $$PID)"; \
	else \
		echo "No backend server PID file found. Server may not be running."; \
	fi

# clean target: Cleans the backend (stops server, removes virtual environment)
clean: stop ## Clean the backend (stop server, remove virtual environment)
	@echo "Cleaning backend..."
	make stop
	@rm -rf $(VENV_DIR)
	find "./" -name __pycache__ -type d -exec rm -rf {} +
	@echo "Backend cleaned."

