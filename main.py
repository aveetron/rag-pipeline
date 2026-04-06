import uvicorn
from fastapi import FastAPI

from app.routers import health

app = FastAPI()
app.include_router(health.router)

if __name__ == "__main__":
  uvicorn.run(app, host="0.0.0.0", port=8000)