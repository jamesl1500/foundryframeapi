.PHONY: up down logs migrate revision shell test smoke

up:
	docker compose up --build -d
	@echo "API:  http://localhost:8000/docs"

down:
	docker compose down

logs:
	docker compose logs -f api worker

migrate:
	docker compose exec api alembic upgrade head

revision:
	docker compose exec api alembic revision --autogenerate -m "$(m)"

shell:
	docker compose exec db psql -U audit -d audit

test:
	docker compose exec worker python -m pytest -q

smoke:
	python3 scripts/smoke.py
