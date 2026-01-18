#include "config.h"

// C++ Standard Library Headers
#include <cstdlib> // Library used for grabbing environment variables, string to number conversion, and random numbers
#include <cstring> // Old school string operations, so C like strings. const char* (null terminated), we need it because our argv is char** argv
#include <stdexcept> // Provides exceptions, so essentially error handling such as "out of range" error

/*
 * params:
 *  const char* input which we are testing works for a port
 *
 * return:
 *  
 */
int parse_port(const char* input) {
  if (input == nullptr || *input == '\0') {
    throw std::invalid_argument("Port is empty or doesn't exist");
  }

  char* end = nullptr;

  // strtol = string to long
  // the end value here will be changed to point to end of the valid characters
  // e.g. "123abc" the end pointer will point to a
  long value = std::strtol(input, &end, 10); // filtering out any characters that are not "base 10 a.k.a digits 0-9"

  
  if (end == input) {
    throw std::invalid_argument("Port must start with digits");
  }
  if (*end != '\0') {
    throw std::invalid_argument("Not a valid port number");
  }
  if (value < 1 || value > 65535) {
    throw std::out_of_range("Port number not in valid range, should be integer ranging from 1 to 65535");
  }

  // convert type long to type int on purpose. Do this at compile time.
  return static_cast<int>(value);
}

Config Config::FromEnv(int argc, char** argv) {
  Config config;  
  
  // Check from the environment file first
  // If env is not nullptr and the string is not empty then assign port
  if (const char* env = std::getenv("PORT"); env && *env) {
    config.port = parse_port(env);
  }

  // Check the command line arguments first
  // Checking for --port 9001 or --port=9001
  for (int i = 1; i < argc; i++) {
    if (std::strcmp(argv[i], "--port") == 0) {
      if (i + 1 >= argc) {
        throw std::invalid_argument("Port number must be provided");
      }
      config.port = parse_port(argv[++i]);
    }
    else if (std::strncmp(argv[i], "--port=", 7) == 0) { //using strNcmp to compare n characters
      const char* cli_port = argv[i] + 7; // skip the --port= part
      config.port = parse_port(cli_port);
    }
  }

  return config;
}


