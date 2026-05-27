"""
Starts the gRPC server on a separate port alongside FastAPI
"""

import os
import sys
import grpc
import grpc.aio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "grpc_generated"))

import gamecontrol_pb2_grpc
from rpc.servicer import GameControlServicer

GRPC_PORT = os.getenv("GRPC_PORT", "50051")


async def start_grpc_server():
    server = grpc.aio.server()
    gamecontrol_pb2_grpc.add_GameControlServicer_to_server(
        GameControlServicer(), server
    )
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    await server.start()
    print(f"gRPC server listening on port {GRPC_PORT}")
    return server
