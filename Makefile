.PHONY: demo backfill update stats export test lint serve dev-frontend

# Serve API + built dashboard on http://127.0.0.1:8000
demo:
	cd backend && ../.venv/bin/python -m azzurro serve --port 8000

# Scrape all review history for all properties
backfill:
	cd backend && ../.venv/bin/python -m azzurro scrape --mode backfill $(if $(P),--property $(P),)

# Fetch only newly published reviews
#   make update            polite pacing (~3 min, lowest block risk)
#   make update ARGS=--fast  trimmed delays (~1 min, fine for daily refreshes)
#   make update P=olympic-paddington   single property
update:
	cd backend && ../.venv/bin/python -m azzurro scrape --mode update $(ARGS) $(if $(P),--property $(P),)

stats:
	cd backend && ../.venv/bin/python -m azzurro stats

export:
	cd backend && ../.venv/bin/python -m azzurro export

test:
	cd backend && ../.venv/bin/python -m pytest tests/ -q

lint:
	cd backend && ../.venv/bin/ruff check azzurro tests
	cd frontend && npm run lint --silent

serve: demo

dev-frontend:
	cd frontend && npm run dev
