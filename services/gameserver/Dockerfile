# ---------- build stage ----------
FROM gcc:14 AS build
WORKDIR /src

# Install build tools (cmake + make)
RUN apt-get update \
 && apt-get install -y --no-install-recommends cmake make \
 && rm -rf /var/lib/apt/lists/*

# Copy source code into the build container
COPY . .

# Configure + compile (Release = optimized)
RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build -j

# ---------- runtime stage ----------
FROM debian:trixie-slim AS runtime
WORKDIR /app

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

