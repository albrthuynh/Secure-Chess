#include "config.h"
#include "server.h"

#include <iostream>

int main(int argc, char** argv) {
  try {
    Config config = Config::FromEnv(argc, argv);
    Server server(config);
    server.run();
  } catch (const std::exception& e) {
    std::cerr << "Fatal Error: " << e.what() << std::endl;
    return 1;
  }

  return 0;
}
