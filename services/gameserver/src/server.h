#pragma once
#include "App.h"
#include "chess.hpp"
#include "config.h"
#include "grpc_client.h"
#include <memory>
#include <prometheus/counter.h>
#include <prometheus/exposer.h>
#include <prometheus/family.h>
#include <prometheus/gauge.h>
#include <prometheus/histogram.h>
#include <prometheus/registry.h>
#include <string>
#include <unordered_map>
#include <vector>

struct PerSocketData {
  std::string user_id;
  std::string username;
  std::string game_id;
  std::string color; // "white" or "black"

  // rate limiting: fixed window per connection
  int msg_count = 0;
  long long window_start_ms = 0; // epoch milliseconds when the current window opened
};

// Type alias so we don't have to write this mouthful everywhere.
// false = no SSL, true = server-side, PerSocketData = our per-connection struct
using WsSocket = uWS::WebSocket<false, true, PerSocketData>;

struct MatchRoom {
  WsSocket* white = nullptr;
  WsSocket* black = nullptr;
  chess::Board board; // tracks live game state; default-constructed = starting position
  std::vector<std::string> move_history; // accumulates moves to send to Python on game end
};

class Server {
public:
  explicit Server(const Config& config);
  void run();

private:
  Config config_;
  GrpcClient grpc_client_;
  std::unordered_map<std::string, MatchRoom> rooms_;

  // observability — exposer serves /metrics on port 9002, registry owns all metric objects
  prometheus::Exposer exposer_;
  std::shared_ptr<prometheus::Registry> registry_;

  // raw pointers into the registry — the registry owns the memory, we just hold references
  prometheus::Gauge* connected_sockets_; // goes up/down as players connect/disconnect
  prometheus::Gauge* active_games_;      // goes up/down as rooms are created/destroyed
  prometheus::Counter* moves_total_;     // only ever increases — total valid moves processed
  prometheus::Histogram* move_duration_; // records how long each move takes — gives us p50/p95/p99
  // Family lets us use one counter with a "reason" label instead of 9 separate counters
  prometheus::Family<prometheus::Counter>* errors_family_;

  // sends msg to whichever players are currently connected in the room
  void broadcastToRoom(MatchRoom& room, const std::string& msg);
};
