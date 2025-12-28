.PHONY: dev migrate superuser lint format test coverage static

ENV ?= .env

init:
	python -m pip install -U pip wheel
	pip install -r requirements.txt

migrate:
	python manage.py makemigrations
	python manage.py migrate

superuser:
	python manage.py createsuperuser

run:
	python manage.py runserver 0.0.0.0:8000

lint:
	flake8

format:
	isort .
	black .

test:
	pytest -q --disable-warnings --maxfail=1

coverage:
	coverage run -m pytest
	coverage report -m

static:
	python manage.py collectstatic --noinput

celery-worker:
	celery -A kiaba worker -l info

celery-beat:
	celery -A kiaba beat -l info
