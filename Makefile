.PHONY: dev

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-down-v:
	docker compose down -v
