.PHONY: up down dev test lint

up:        ## Поднять весь стек в Docker
	docker compose up --build

down:      ## Остановить стек и удалить контейнеры
	docker compose down

dev:       ## Запустить API локально с автоперезагрузкой
	uv run uvicorn app.main:app --reload

test:      ## Прогнать тесты
	uv run pytest

lint:      ## Линт, форматирование и типы
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
