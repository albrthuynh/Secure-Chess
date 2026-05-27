from contextlib import asynccontextmanager
from auth.jwt_routes import router as auth_router
from matchmaking.routes import router as matchmaking_router
from utils.redis_client import close_redis_connection, get_redis_client
from rpc.server import start_grpc_server
from fastapi import FastAPI


# lifespan context manager for startup/shutdown events (handling the redis lifecycle)
@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_redis_client()
    print("Redis Client Connected!")

    grpc_server = await start_grpc_server()

    # pause here while the app is running, then continue when shutting down.
    yield

    await grpc_server.stop(grace=5)
    print("gRPC server stopped")

    await close_redis_connection()
    print("Redis Client Disconnected")


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
app.include_router(matchmaking_router)


@app.get("/")
async def root():
    return {"message": "Application Running"}
