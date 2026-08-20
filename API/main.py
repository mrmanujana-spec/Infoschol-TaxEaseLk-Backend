from fastapi import FastAPI

from database import engine
from models import Base
from routers.auth import router as auth_router


app = FastAPI(
    title="TaxEaseLK API"
)


Base.metadata.create_all(bind=engine)


app.include_router(auth_router)


@app.get("/")
def read_root():
    return {
        "message": "TaxEaseLK API is working!"
    }