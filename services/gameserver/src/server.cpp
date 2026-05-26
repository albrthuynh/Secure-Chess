#include "server.h"
#include <iostream>
#include <nlohmann/json.hpp>

Server::Server(const Config &config) : config_(config) {}

void Server::run() {
  std::cerr << "WebSocket Server running on port " << config_.port << "\n";

  uWS::App()
      .ws<PerSocketData>(
          "/ws",
          {.open =
               [](auto *ws) { std::cout << "client connected!" << std::endl; },
           .message = [this](auto *ws, std::string_view msg, uWS::OpCode opCode) {
              auto json = nlohmann::json::parse(msg, nullptr, false);
              if (json.is_discarded()) {
                ws->send(R"({"type":"error","message":"invalid json"})", uWS::OpCode::TEXT);
                return;
              }

              std::string type = json.value("type", "");

              if (type == "join_match") {
                std::string game_id = json.value("game_id", "");
                std::string color = json.value("color", "");

                auto* data = ws->getUserData();
                data->game_id = game_id;
                data->color = color;

                // creates the room if it doesn't exist yet, then assigns this socket to the correct color slot
                auto& room = rooms_[game_id];
                if (color == "white") {
                  room.white = ws;
                }
                else {
                  room.black = ws;
                }

                nlohmann::json response = {{"type", "joined"}, {"color", color}};
                ws->send(response.dump(), uWS::OpCode::TEXT);

              } else if (type == "move") {
                auto* data = ws->getUserData();
                auto it = rooms_.find(data->game_id);
                if (it == rooms_.end()) return;

                // forward the move to whichever socket is the opponent
                WsSocket* opponent = (data->color == "white") ? it->second.black : it->second.white;
                if (opponent) {
                  opponent->send(msg, uWS::OpCode::TEXT);
                }

              } else {
                ws->send(R"({"type":"error","message":"unknown message type"})", uWS::OpCode::TEXT);
              }
            },
           .close =
               [this](auto *ws, int code, std::string_view) {
                  auto* data = ws->getUserData();
                  rooms_.erase(data->game_id);
                  std::cout << "Client disconnected code (" << code << ")" << std::endl;
               }})
      .listen(config_.port,
              [port = config_.port](auto *token) {
                if (token) {
                  std::cout << "Listening to on port " << port << std::endl;
                } else {
                  std::cerr << "Failed to listen on port " << port << std::endl;
                }
              })
      .run();
}

// QUESTIONS
// 1. What do they mean by return discarded json?
// 2. What is this line doing? -> auto json = nlohmann::json::parse(msg, nullptr, false);
// 3. What does this mean? -> uWS::OpCode::TEXT
// 4. What does getUserData do and mean??
