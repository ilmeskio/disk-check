PYTHON312   := /usr/local/bin/python3.12
VENV        := .venv-build
PIP         := $(VENV)/bin/pip
PYINSTALLER := $(VENV)/bin/pyinstaller
SPEC        := disk-check.spec

.PHONY: all build venv clean install

all: build

venv: $(VENV)/bin/python
$(VENV)/bin/python:
	$(PYTHON312) -m venv $(VENV)
	$(PIP) install --quiet pyinstaller==6.19.0

build: venv $(SPEC)
	$(PYINSTALLER) $(SPEC)
	@echo "Binary: dist/disk-check"

clean:
	rm -rf build/ dist/ .venv-build/ \
	  disk_check/__pycache__/ disk_check/sections/__pycache__/ __pycache__/

install: build
	cp dist/disk-check /usr/local/bin/disk-check
	chmod +x /usr/local/bin/disk-check
