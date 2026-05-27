#pragma once
#include <string>

struct Config {
  int port = 9001;
  std::string grpc_address = "localhost:50051";

  static Config FromEnv(int argc, char** argv);
};
