PYTHON ?= python3

PKG := ./bin/pkg

.PHONY: help install check

.DEFAULT_GOAL := help

help:
	@echo "Usage:"
	@echo "  make <target>"
	@echo
	@echo "Targets:"
	@echo "  install    Install all packages"
	@echo "  check      Check whether packages are installed"
	@echo "  help       Show this help message"

install:
	$(PKG) install

check:
	$(PKG) check
