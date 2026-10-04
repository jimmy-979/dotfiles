PYTHON ?= python3

PKG := PYTHONPATH=$(PWD):$(PWD)/src ./bin/pkg

.PHONY: help install check

.DEFAULT_GOAL := help

help:
	@echo "Usage:"
	@echo "  make <target>"
	@echo
	@echo "Targets:"
	@echo "  install    Install a package, e.g. 'make install <package>'. If no package is specified, it will install all packages."
	@echo "  check      Check whether packages are installed"
	@echo "  help       Show this help message"

install:
	@$(PKG) install $(filter-out install,$(MAKECMDGOALS))

check:
	@$(PKG) check

# Allow package names to be passed as additional arguments.
%:
	@: