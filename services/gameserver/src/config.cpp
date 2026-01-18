#include "config.h"

// C++ Standard Library Headers
#include <cstdlib> // Library used for grabbing environment variables, string to number conversion, and random numbers
#include <cstring> // Old school string operations, so C like strings. const char* (null terminated), we need it because our argv is char** argv
#include <stdexcept> // Provides exceptions, so essentially error handling such as "out of range" error

#include <string>
#include <cctype>


/*
 * params:
 *  const char* input which we are testing works for a port
 *  int& out: the actual variable which will be populated
 *
 * return:
 *  bool -> whether it was successful operation or not
 */
bool parse_int(const char* input, int& out) {
  if (input == nullptr || *input == '\0') {
    return false; 
  }

  char end* = nullptr;

  // strtol = string to long
  // the end value here will be changed to point to end of the valid characters
  // e.g. "123abc" the end pointer will point to a
  long value = std::strtol(s, &end, 10); // filtering out any characters that are not "base 10 a.k.a digits 0-9"

  if (std::isalpha(*end)) {
    throw std::invalid_argument("Not a valid port number")
    return false;
  }
}

