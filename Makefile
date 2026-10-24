.PHONY: install check lint typecheck test e2e run report dashboard

install:
	uv sync
	cd dashboard && npm install && npx playwright install chromium

check: lint typecheck test

lint:
	uv run ruff check .
	uv run ruff format --check .
	cd dashboard && npm run lint

typecheck:
	uv run pyright
	cd dashboard && npm run typecheck

test:
	uv run pytest
	cd dashboard && npm test

e2e:
	cd dashboard && npm run test:e2e

run:
	uv run negotiate run

report:
	uv run negotiate report

dashboard:
	cd dashboard && npm run dev
