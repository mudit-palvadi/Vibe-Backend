from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import SQLModel

from app.db.database import engine
from app.routes.auth_routes import router as auth_router
from app.routes.playlist_routes import router as playlist_router
from app.routes.song_routes import router as song_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    print("Database connected")
    yield
    print("Application shutdown")


app = FastAPI(title="Vibe Backend", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(song_router)
app.include_router(playlist_router)


@app.get("/")
def root():
    return {"message": "Vibe backend running"}
