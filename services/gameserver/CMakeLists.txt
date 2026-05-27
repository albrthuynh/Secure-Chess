# THIS FILE WAS A PAIN TO CONFIGURE
cmake_minimum_required(VERSION 3.20)
project(gameserver LANGUAGES C CXX)

SET(CMAKE_CXX_STANDARD 20)
SET(CMAKE_CXX_STANDARD_REQUIRED ON)

# Load CMake's built-in download module — not available by default, must be explicitly enabled
include(FetchContent)

# Declare where to find each library — doesn't download yet, just registers the source
FetchContent_Declare(uSockets
    GIT_REPOSITORY https://github.com/uNetworking/uSockets.git
    GIT_TAG v0.8.8
    GIT_SHALLOW TRUE  # only grab the latest commit, not the full git history — faster download
)

FetchContent_Declare(uWebSockets
    GIT_REPOSITORY https://github.com/uNetworking/uWebSockets.git
    GIT_TAG v20.68.0
    GIT_SHALLOW TRUE
)

FetchContent_Declare(nlohmann_json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
    GIT_SHALLOW TRUE
)

FetchContent_Declare(chess_library
  GIT_REPOSITORY https://github.com/Disservin/chess-library.git
  GIT_TAG 57159616358c2d4c09e0d4fb1562ca7f2d36a2fb  # HEAD of master as of 2026-05-27
)

# Download libraries that have their own CMakeLists.txt (npm install equivalent)
FetchContent_MakeAvailable(uSockets uWebSockets nlohmann_json)

# chess-library is header-only with no CMakeLists.txt (it uses Meson instead).
# FetchContent_MakeAvailable would crash trying to call add_subdirectory on it,
# so we use the lower-level Populate API: just download, don't try to build.
# CMP0169=OLD keeps the old FetchContent_Populate(name) API available.
cmake_policy(SET CMP0169 OLD)

FetchContent_GetProperties(chess_library)
if(NOT chess_library_POPULATED)
  FetchContent_Populate(chess_library)
endif()

# uSockets has no CMakeLists.txt of its own, so we manually compile it into a static library
# A static library (.a file) is a bundle of compiled code we can link into our binary
file(GLOB USOCKETS_SOURCES
    "${usockets_SOURCE_DIR}/src/*.c"
    "${usockets_SOURCE_DIR}/src/eventing/*.c"
)
add_library(uSockets_lib STATIC ${USOCKETS_SOURCES})
target_include_directories(uSockets_lib PUBLIC "${usockets_SOURCE_DIR}/src")
# Skip SSL support inside uSockets — we don't need encrypted WebSockets for local dev
target_compile_definitions(uSockets_lib PUBLIC LIBUS_NO_SSL=1)

add_executable(gameserver
  src/main.cpp
  src/config.cpp
  src/server.cpp
)

target_include_directories(gameserver PRIVATE
    src
    "${uwebsockets_SOURCE_DIR}/src"  # uWebSockets is header-only, just needs its headers on the include path
    "${chess_library_SOURCE_DIR}/include"  # chess-library: chess.hpp lives in include/
)

# Our code also needs to know SSL is disabled so it matches how uSockets was compiled
target_compile_definitions(gameserver PRIVATE LIBUS_NO_SSL=1)

target_link_libraries(gameserver PRIVATE
    uSockets_lib              # the compiled C networking layer
    nlohmann_json::nlohmann_json  # header-only JSON library
    z                         # zlib — short name for the system zlib we installed via apt
)
