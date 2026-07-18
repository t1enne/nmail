.PHONY: format lint typecheck check install clean

SRC := src/nmail

format:
	uv tool run ruff format $(SRC)

lint:
	uv tool run ruff check $(SRC)

typecheck:
	uv tool run ty check $(SRC)

check: format lint typecheck

install:
	uv tool install --reinstall .

clean:
	rm -rf build/ dist/ src/*.egg-info/ src/**/__pycache__/
