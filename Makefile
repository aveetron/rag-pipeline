.PHONY: dev

dev:
	docker compose up -d && sleep 5 && uvicorn main:app --reload

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-down-v:
	docker compose down -v
