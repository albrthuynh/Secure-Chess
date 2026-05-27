#include "server.h"
#include <iostream>
#include <nlohmann/json.hpp>

Server::Server(const Config& config) : config_(config) {
}

// Helper so we don't repeat the null-check pattern every time we want to tell both players
// something.
void Server::broadcastToRoom(MatchRoom& room, const std::string& msg) {
  if (room.white)
    room.white->send(msg, uWS::OpCode::TEXT);
  if (room.black)
    room.black->send(msg, uWS::OpCode::TEXT);
}

void Server::run() {
  std::cerr << "WebSocket Server running on port " << config_.port << "\n";

  uWS::App()
      .ws<PerSocketData>("/ws",
          { .open =
                  [](auto* ws) {
                    std::cout << "client connected!" << std::endl;
                  },
              .message =
                  [this](auto* ws, std::string_view msg, uWS::OpCode opCode) {
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

                      // creates the room if it doesn't exist yet, then assigns this socket to the
                      // correct color slot
                      auto& room = rooms_[game_id];
                      if (color == "white") {
                        room.white = ws;
                      } else {
                        room.black = ws;
                      }

                      // send back the starting FEN so the client can render the initial board state
                      nlohmann::json response = { { "type", "joined" },
                        { "color", color },
                        { "fen", room.board.getFen() } };
                      ws->send(response.dump(), uWS::OpCode::TEXT);

                    } else if (type == "move") {
                      auto* data = ws->getUserData();
                      auto it = rooms_.find(data->game_id);
                      if (it == rooms_.end())
                        return;

                      auto& room = it->second;
                      chess::Board& board = room.board;

                      // --- turn enforcement ---
                      // sideToMove() tells us whose turn the board thinks it is.
                      // We compare that against which color this socket is.
                      bool white_to_move = (board.sideToMove() == chess::Color::WHITE);
                      bool sender_is_white = (data->color == "white");
                      if (white_to_move != sender_is_white) {
                        ws->send(R"({"type":"error","message":"not your turn"})",
                            uWS::OpCode::TEXT);
                        return;
                      }

                      // --- move validation ---
                      // Clients send moves in UCI notation: "e2e4", "g1f3", "e1g1" (castling), etc.
                      // uciToMove() converts that string into a chess::Move object the board
                      // understands.
                      std::string move_str = json.value("move", "");
                      chess::Move move = chess::uci::uciToMove(board, move_str);

                      // Generate every legal move in the current position,
                      // then check whether the client's move is in that list.
                      // This is the "authoritative server" pattern: the server never trusts the
                      // client.
                      chess::Movelist legal_moves;
                      chess::movegen::legalmoves(legal_moves, board);

                      bool is_legal = false;
                      for (const auto& m : legal_moves) {
                        if (m == move) {
                          is_legal = true;
                          break;
                        }
                      }

                      if (!is_legal) {
                        ws->send(R"({"type":"error","message":"illegal move"})", uWS::OpCode::TEXT);
                        return;
                      }

                      // --- apply and broadcast ---
                      // Only reach here if the move passed all checks. Now we commit it to the
                      // board.
                      board.makeMove(move);

                      // After applying, getFen() returns the new position. We send this to both
                      // players so their boards stay perfectly in sync with the server's truth.
                      nlohmann::json broadcast = { { "type", "move" },
                        { "move", move_str },
                        { "fen", board.getFen() },
                        { "turn", board.sideToMove() == chess::Color::WHITE ? "white" : "black" } };
                      broadcastToRoom(room, broadcast.dump());

                      // --- game over detection ---
                      // isGameOver() returns a pair: the reason (checkmate, stalemate, etc.)
                      // and the result (win or draw). NONE means the game is still going.
                      auto [reason, result] = board.isGameOver();
                      if (result != chess::GameResult::NONE) {
                        std::string result_str;
                        if (result == chess::GameResult::LOSE) {
                          // The library reports LOSE from the perspective of the side now to move —
                          // i.e. the side that just got checkmated. So the winner is the other side.
                          bool white_wins = (board.sideToMove() == chess::Color::BLACK);
                          result_str = white_wins ? "white_wins" : "black_wins";
                        } else {
                          result_str = "draw";
                        }

                        std::string reason_str;
                        switch (reason) {
                        case chess::GameResultReason::CHECKMATE:
                          reason_str = "checkmate";
                          break;
                        case chess::GameResultReason::STALEMATE:
                          reason_str = "stalemate";
                          break;
                        case chess::GameResultReason::INSUFFICIENT_MATERIAL:
                          reason_str = "insufficient_material";
                          break;
                        case chess::GameResultReason::FIFTY_MOVE_RULE:
                          reason_str = "fifty_move_rule";
                          break;
                        case chess::GameResultReason::THREEFOLD_REPETITION:
                          reason_str = "threefold_repetition";
                          break;
                        default:
                          reason_str = "unknown";
                          break;
                        }

                        nlohmann::json game_over = { { "type", "game_over" },
                          { "result", result_str },
                          { "reason", reason_str } };
                        broadcastToRoom(room, game_over.dump());
                        rooms_.erase(data->game_id);
                      }

                    } else {
                      ws->send(R"({"type":"error","message":"unknown message type"})",
                          uWS::OpCode::TEXT);
                    }
                  },
              .close =
                  [this](auto* ws, int code, std::string_view) {
                    auto* data = ws->getUserData();
                    auto it = rooms_.find(data->game_id);
                    if (it == rooms_.end())
                      return;

                    auto& room = it->second;

                    // null out only this player's slot, butg don't destroy the room while the
                    // other player is still connected
                    if (data->color == "white")
                      room.white = nullptr;
                    else
                      room.black = nullptr;

                    // tell the surviving player their opponent left
                    nlohmann::json disconnect_msg = { { "type", "opponent_disconnected" } };
                    broadcastToRoom(room, disconnect_msg.dump());

                    // clean up once both sockets are gone
                    if (!room.white && !room.black) {
                      rooms_.erase(it);
                    }

                    std::cout << "Client disconnected (" << code << ")" << std::endl;
                  } })
      .listen(config_.port,
          [port = config_.port](auto* token) {
            if (token) {
              std::cout << "Listening on port " << port << std::endl;
            } else {
              std::cerr << "Failed to listen on port " << port << std::endl;
            }
          })
      .run();
}
