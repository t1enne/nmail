.PHONY: format lint typecheck check install clean

SRC := src/nmail

format:
	uv run ruff format $(SRC)

lint:
	uv run ruff check $(SRC)

typecheck:
	uv run ty check $(SRC)

test:
	uv run pytest tests/ -v

check: format lint typecheck test

install:
	uv tool install --reinstall .

clean:
	rm -rf build/ dist/ src/*.egg-info/ src/**/__pycache__/
