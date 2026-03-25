from auth.jwt_routes import router as auth_router
from fastapi import FastAPI

app = FastAPI()
app.include_router(auth_router)


@app.get("/")
async def root():
    return {"message": "Application Running"}

