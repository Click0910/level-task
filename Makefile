SHELL := /bin/bash
export TEMP_FOLDER = ./tmp
export DATASET_PATH = ./data

build:
	pip install -r requirements.txt
	docker-compose build

up:
	docker-compose up -d --scale ticket_worker=2
	timeout /t 3 /nobreak > NUL

down:
	docker-compose down

seed:
	python src/database/scripts/seed.py && $(MAKE) psql-check

psql-check:
	docker-compose exec database psql -U postgres -d tickets_db -c "SELECT COUNT(*) FROM customer_support_tickets;"


_test:
	docker-compose run --rm api pytest tests/ -v

test: up _test down
