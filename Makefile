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
	mkdir -p ~/.local/bin
	cp dist/disk-check ~/.local/bin/disk-check
	chmod +x ~/.local/bin/disk-check
	@echo "Installed to ~/.local/bin/disk-check"
	@echo "Make sure ~/.local/bin is in your PATH (add to ~/.zshrc: export PATH=\"\$$HOME/.local/bin:\$$PATH\")"
