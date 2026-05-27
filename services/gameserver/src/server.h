#pragma once
#include "App.h"
#include "chess.hpp"
#include "config.h"
#include "grpc_client.h"
#include <string>
#include <unordered_map>
#include <vector>

struct PerSocketData {
  std::string user_id;
  std::string username;
  std::string game_id;
  std::string color; // "white" or "black"
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

  // sends msg to whichever players are currently connected in the room
  void broadcastToRoom(MatchRoom& room, const std::string& msg);
};
