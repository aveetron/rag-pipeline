.PHONY: dev

dev:
	docker-up
	docker exec -it ollama ollama pull phi3:mini

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-down-v:
	docker compose down -v
