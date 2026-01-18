#include "server.h"

#include <iostream>
#include <thread> // Allows us to use threads, running things in parallel
#include <chrono> // C++’s time library — durations, clocks, and timestamps.

Server::Server(const Config& config) : config_(config) {}


void Server::run() {
  std::cerr << "Server running on port " << config_.port << "\n";
  
  // temporary place holder
  while (true) {
    std::this_thread::sleep_for(std::chrono::seconds(5));
    std::cerr << "[gameserver]: heartbeat (port " << config_.port << ")\n";
  }
}
