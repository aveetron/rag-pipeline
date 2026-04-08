.PHONY: dev

dev:
	docker compose up -d && docker compose exec ollama ollama pull phi3:mini && uvicorn main:app --reload

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-down-v:
	docker compose down -v
