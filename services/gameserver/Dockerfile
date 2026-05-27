# ---------- build stage ----------
FROM gcc:14 AS build
WORKDIR /src

# Install build tools (cmake + make)
RUN apt-get update \
 && apt-get install -y --no-install-recommends cmake make git zlib1g-dev \
    libgrpc++-dev libprotobuf-dev protobuf-compiler protobuf-compiler-grpc \
 && rm -rf /var/lib/apt/lists/*

# Copy source and proto file (build context is repo root)
COPY services/gameserver/ .
COPY proto/ /proto/

# Regenerate proto stubs using this container's protoc so the generated
# files match the installed protobuf version (avoids local/Docker version mismatch)
RUN mkdir -p src/generated && \
    protoc -I /proto \
        --cpp_out=src/generated \
        --grpc_out=src/generated \
        --plugin=protoc-gen-grpc=/usr/bin/grpc_cpp_plugin \
        /proto/gamecontrol.proto

# Configure + compile (Release = optimized)
# Remove any stale local build directory before configuring
RUN rm -rf build && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build -j

# ---------- runtime stage ----------
FROM debian:trixie-slim AS runtime
WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    libgrpc++1.51 libprotobuf32 libre2-11 libssl3 libcares2 \
 && rm -rf /var/lib/apt/lists/*

# Copy ONLY the compiled binary into the runtime image
COPY --from=build /src/build/gameserver /app/gameserver

# Export PORT
ENV PORT=9001
EXPOSE 9001

# Create a new user within the container
RUN useradd -m gameserver

RUN chown -R gameserver:gameserver /app

USER gameserver

CMD ["/app/gameserver"]
