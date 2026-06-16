.PHONY: up down dev test lint

# Создаёт .env из примера, если его ещё нет (нужен и для compose, и для приложения).
.env:
	cp .env.example .env

up: .env   ## Поднять весь стек в Docker
	docker compose up --build

down:      ## Остановить стек и удалить контейнеры
	docker compose down

dev: .env  ## Запустить API локально с автоперезагрузкой
	uv run uvicorn app.main:app --reload

test: .env ## Прогнать тесты
	uv run pytest

lint:      ## Линт, форматирование и типы
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
