#pragma once
#include "config.h"
#include "App.h" // the websocket file
#include <unordered_map>
#include <string>

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
};

class Server {
    public: 
        // explicit keyword prevents type conversions when making an object
        explicit Server(const Config& config);
        void run();
    
    private:
        Config config_;
        std::unordered_map<std::string, MatchRoom> rooms_; // matchid -> rooms
};

