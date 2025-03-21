.PHONY: create-migrate migrate-up-1 migrate-down-1

create-migrate:
	alembic revision --autogenerate -m "$(name)"

migrate-up:
	alembic upgrade head

migrate-down-1:
	alembic downgrade -1