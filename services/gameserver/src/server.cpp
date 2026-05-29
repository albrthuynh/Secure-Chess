#include "server.h"
#include <chrono> // C++ standard library for time — we use it to get the current timestamp in ms
#include <iostream>
#include <nlohmann/json.hpp>

static constexpr size_t MAX_MESSAGE_BYTES = 1024; // 1 KB — chess moves are tiny
static constexpr int RATE_LIMIT_MAX = 10;         // messages per window
static constexpr long long RATE_WINDOW_MS = 1000; // 1 second window
static constexpr size_t GRPC_WORKER_COUNT = 4;

Server::Server(const Config& config) : config_(config), exposer_("0.0.0.0:9002") {
  // create the registry for prometheus
  registry_ = std::make_shared<prometheus::Registry>();

  // link exposer to registry - so it knows where the metrics are scraped from
  exposer_.RegisterCollectable(registry_);

  // So we register each metric into the registry
  connected_sockets_ = &prometheus::BuildGauge()
                            .Name("chess_connected_sockets")
                            .Help("Number of currently connected WebSocket clients")
                            .Register(*registry_)
                            .Add({});

  active_games_ = &prometheus::BuildGauge()
                       .Name("chess_active_games")
                       .Help("Number of active game rooms")
                       .Register(*registry_)
                       .Add({});

  moves_total_ = &prometheus::BuildCounter()
                      .Name("chess_moves_total")
                      .Help("Total number of valid moves processed")
                      .Register(*registry_)
                      .Add({});

  move_duration_ =
      &prometheus::BuildHistogram()
           .Name("chess_move_duration_seconds")
           .Help("Time to validate and broadcast a move in seconds")
           .Register(*registry_)
           .Add({},
               prometheus::Histogram::BucketBoundaries{ 0.001, 0.005, 0.01, 0.025, 0.05, 0.1 });

  errors_family_ = &prometheus::BuildCounter()
                        .Name("chess_errors_total")
                        .Help("Total WebSocket errors by reason")
                        .Register(*registry_);

  startGrpcWorkers();
}

Server::~Server() {
  stopGrpcWorkers();
}

// Helper so we don't repeat the null-check pattern every time we want to tell
// both players something.
void Server::broadcastToRoom(MatchRoom& room, const std::string& msg) {
  if (room.white)
    room.white->send(msg, uWS::OpCode::TEXT);
  if (room.black)
    room.black->send(msg, uWS::OpCode::TEXT);
}

void Server::startGrpcWorkers() {
  for (size_t i = 0; i < GRPC_WORKER_COUNT; ++i) {
    grpc_workers_.emplace_back([this]() {
      GrpcClient grpc_client(config_.grpc_address);
      while (true) {
        std::function<void(GrpcClient&)> job;
        {
          std::unique_lock<std::mutex> lock(grpc_jobs_mutex_);
          grpc_jobs_cv_.wait(lock, [this]() {
            return stopping_grpc_workers_ || !grpc_jobs_.empty();
          });

          if (stopping_grpc_workers_ && grpc_jobs_.empty())
            return;

          job = std::move(grpc_jobs_.front());
          grpc_jobs_.pop();
        }

        job(grpc_client);
      }
    });
  }
}

void Server::stopGrpcWorkers() {
  {
    std::lock_guard<std::mutex> lock(grpc_jobs_mutex_);
    stopping_grpc_workers_ = true;
  }
  grpc_jobs_cv_.notify_all();

  for (auto& worker : grpc_workers_) {
    if (worker.joinable())
      worker.join();
  }
}

void Server::enqueueGrpcJob(std::function<void(GrpcClient&)> job) {
  {
    std::lock_guard<std::mutex> lock(grpc_jobs_mutex_);
    grpc_jobs_.push(std::move(job));
  }
  grpc_jobs_cv_.notify_one();
}

void Server::run() {
  std::cerr << "WebSocket Server running on port " << config_.port << "\n";

  uWS::App()
      .ws<PerSocketData>("/ws",
          { .open =
                  [this](auto* ws) {
                    std::cout << "client connected!" << std::endl;
                    auto* data = ws->getUserData();
                    data->socket_id = next_socket_id_++;
                    sockets_[data->socket_id] = ws;
                    connected_sockets_->Increment();
                  },
              .message =
                  [this](auto* ws, std::string_view msg, uWS::OpCode opCode) {
                    // --- message size limit ---
                    // reject before we even try to parse, so a huge payload can't
                    // burn CPU
                    if (msg.size() > MAX_MESSAGE_BYTES) {
                      errors_family_->Add({ { "reason", "message_too_large" } }).Increment();
                      ws->send(R"({"type":"error","message":"message too large"})",
                          uWS::OpCode::TEXT);
                      return;
                    }

                    // --- per-connection rate limit (fixed window) ---
                    // same idea as the HTTP rate limiter, but tracked in-memory
                    // per socket
                    auto* data = ws->getUserData();
                    long long now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                        std::chrono::steady_clock::now().time_since_epoch())
                                           .count();

                    if (now_ms - data->window_start_ms > RATE_WINDOW_MS) {
                      // we've crossed into a new 1-second window — reset the
                      // counter
                      data->window_start_ms = now_ms;
                      data->msg_count = 0;
                    }

                    data->msg_count++;
                    if (data->msg_count > RATE_LIMIT_MAX) {
                      errors_family_->Add({ { "reason", "rate_limit_exceeded" } }).Increment();
                      ws->send(R"({"type":"error","message":"rate limit exceeded"})",
                          uWS::OpCode::TEXT);
                      return;
                    }

                    auto json = nlohmann::json::parse(msg, nullptr, false);
                    if (json.is_discarded()) {
                      errors_family_->Add({ { "reason", "invalid_json" } }).Increment();
                      ws->send(R"({"type":"error","message":"invalid json"})", uWS::OpCode::TEXT);
                      return;
                    }

                    std::string type = json.value("type", "");

                    if (type == "join_match") {
                      std::string ticket = json.value("ticket", "");
                      std::string color = json.value("color", "");
                      size_t socket_id = data->socket_id;
                      auto* loop = uWS::Loop::get();

                      enqueueGrpcJob(
                          [this, loop, socket_id, ticket, color](GrpcClient& grpc_client) {
                            VerifyResult verified;
                            std::string resume_token;
                            verified = grpc_client.verifyMatchTicket(ticket);
                            if (verified.valid) {
                              resume_token = grpc_client.createResumeToken(verified.match_id,
                                  verified.player_id,
                                  color);
                            }

                            loop->defer([this, socket_id, color, verified, resume_token]() {
                              auto socket_it = sockets_.find(socket_id);
                              if (socket_it == sockets_.end())
                                return;

                              WsSocket* ws = socket_it->second;
                              auto* data = ws->getUserData();

                              if (!verified.valid) {
                                errors_family_->Add({ { "reason", "invalid_ticket" } }).Increment();
                                ws->send(R"({"type":"error","message":"invalid ticket"})",
                                    uWS::OpCode::TEXT);
                                ws->close();
                                return;
                              }

                              data->game_id = verified.match_id; // trust the server, not the client
                              data->user_id = verified.player_id;
                              data->color = color;

                              // Creates the room if it doesn't exist yet, then assigns
                              // this socket to the correct color slot. Room/socket
                              // mutation must stay on the uWS loop.
                              bool is_new_room = rooms_.count(verified.match_id) == 0;
                              auto& room = rooms_[verified.match_id];
                              if (color == "white") {
                                room.white = ws;
                              } else {
                                room.black = ws;
                              }
                              if (is_new_room)
                                active_games_->Increment();

                              nlohmann::json response = { { "type", "joined" },
                                { "color", color },
                                { "fen", room.board.getFen() },
                                { "resume_token", resume_token } };
                              ws->send(response.dump(), uWS::OpCode::TEXT);
                            });
                          });

                    } else if (type == "move") {
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
                        errors_family_->Add({ { "reason", "not_your_turn" } }).Increment();
                        ws->send(R"({"type":"error","message":"not your turn"})",
                            uWS::OpCode::TEXT);
                        return;
                      }

                      // --- move validation ---
                      // Clients send moves in UCI notation: "e2e4", "g1f3", "e1g1"
                      // (castling), etc. uciToMove() converts that string into a
                      // chess::Move object the board understands.
                      std::string move_str = json.value("move", "");
                      chess::Move move = chess::uci::uciToMove(board, move_str);

                      // Generate every legal move in the current position,
                      // then check whether the client's move is in that list.
                      // This is the "authoritative server" pattern: the server
                      // never trusts the client.
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
                        errors_family_->Add({ { "reason", "illegal_move" } }).Increment();
                        ws->send(R"({"type":"error","message":"illegal move"})", uWS::OpCode::TEXT);
                        return;
                      }

                      // --- apply and broadcast ---
                      // Only reach here if the move passed all checks. Now we
                      // commit it to the board.
                      auto move_start = std::chrono::steady_clock::now();
                      board.makeMove(move);
                      room.move_history.push_back(move_str);
                      moves_total_->Increment();

                      // After applying, getFen() returns the new position. We send
                      // this to both players so their boards stay perfectly in
                      // sync with the server's truth.
                      nlohmann::json broadcast = { { "type", "move" },
                        { "move", move_str },
                        { "fen", board.getFen() },
                        { "turn", board.sideToMove() == chess::Color::WHITE ? "white" : "black" } };
                      broadcastToRoom(room, broadcast.dump());

                      double move_elapsed = std::chrono::duration<double>(
                          std::chrono::steady_clock::now() - move_start)
                                                .count();
                      move_duration_->Observe(move_elapsed);

                      // --- game over detection ---
                      // isGameOver() returns a pair: the reason (checkmate,
                      // stalemate, etc.) and the result (win or draw). NONE means
                      // the game is still going.
                      auto [reason, result] = board.isGameOver();
                      if (result != chess::GameResult::NONE) {
                        std::string result_str;
                        if (result == chess::GameResult::LOSE) {
                          // The library reports LOSE from the perspective of the
                          // side now to move — i.e. the side that just got
                          // checkmated. So the winner is the other side.
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

                        // determine winner's user_id — empty string means draw
                        std::string winner_id = "";
                        if (result == chess::GameResult::LOSE) {
                          bool white_wins = (board.sideToMove() == chess::Color::BLACK);
                          if (white_wins && room.white)
                            winner_id = room.white->getUserData()->user_id;
                          else if (!white_wins && room.black)
                            winner_id = room.black->getUserData()->user_id;
                        }

                        std::string ended_game_id = data->game_id;
                        std::vector<std::string> ended_moves = room.move_history;
                        enqueueGrpcJob(
                            [ended_game_id, winner_id, ended_moves](GrpcClient& grpc_client) {
                              grpc_client.reportGameEnd(ended_game_id, winner_id, ended_moves);
                            });
                        rooms_.erase(data->game_id);
                        active_games_->Decrement();
                      }

                    } else if (type == "resume_match") {
                      std::string token = json.value("resume_token", "");
                      size_t socket_id = data->socket_id;
                      auto* loop = uWS::Loop::get();

                      enqueueGrpcJob([this, loop, socket_id, token](GrpcClient& grpc_client) {
                        ResolveResult resolved;
                        std::string new_token;
                        resolved = grpc_client.resolveResumeToken(token);
                        if (resolved.valid) {
                          new_token = grpc_client.createResumeToken(resolved.match_id,
                              resolved.user_id,
                              resolved.color);
                        }

                        loop->defer([this, socket_id, resolved, new_token]() {
                          auto socket_it = sockets_.find(socket_id);
                          if (socket_it == sockets_.end())
                            return;

                          WsSocket* ws = socket_it->second;
                          if (!resolved.valid) {
                            errors_family_->Add({ { "reason", "invalid_resume_token" } })
                                .Increment();
                            ws->send(R"({"type":"error","message":"invalid resume token"})",
                                uWS::OpCode::TEXT);
                            ws->close();
                            return;
                          }

                          auto it = rooms_.find(resolved.match_id);
                          if (it == rooms_.end()) {
                            errors_family_->Add({ { "reason", "game_no_longer_active" } })
                                .Increment();
                            ws->send(R"({"type":"error","message":"game no longer active"})",
                                uWS::OpCode::TEXT);
                            ws->close();
                            return;
                          }

                          auto& room = it->second;
                          auto* data = ws->getUserData();
                          data->game_id = resolved.match_id;
                          data->user_id = resolved.user_id;
                          data->color = resolved.color;

                          if (resolved.color == "white")
                            room.white = ws;
                          else
                            room.black = ws;

                          nlohmann::json response = { { "type", "resumed" },
                            { "color", resolved.color },
                            { "fen", room.board.getFen() },
                            { "moves", room.move_history },
                            { "resume_token", new_token } };
                          ws->send(response.dump(), uWS::OpCode::TEXT);

                          nlohmann::json reconnected = { { "type", "opponent_reconnected" } };
                          broadcastToRoom(room, reconnected.dump());
                        });
                      });

                    } else {
                      errors_family_->Add({ { "reason", "unknown_message_type" } }).Increment();
                      ws->send(R"({"type":"error","message":"unknown message type"})",
                          uWS::OpCode::TEXT);
                    }
                  },
              .close =
                  [this](auto* ws, int code, std::string_view) {
                    connected_sockets_->Decrement();

                    auto* data = ws->getUserData();
                    sockets_.erase(data->socket_id);
                    auto it = rooms_.find(data->game_id);
                    if (it == rooms_.end())
                      return;

                    auto& room = it->second;

                    // null out only this player's slot, butg don't destroy the
                    // room while the other player is still connected
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
                      active_games_->Decrement();
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
