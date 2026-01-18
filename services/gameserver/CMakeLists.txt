cmake_minimum_required(VERSION 3.20)
project(gameserver LANGUAGES CXX)

SET(CMAKE_CXX_STANDARD 20)
SET(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(gameserver
  src/main.cpp
  src/config.cpp
  src/server.cpp
)

target_include_directories(gameserver PRIVATE src)
