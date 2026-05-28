#pragma once
#include "generated/gamecontrol.grpc.pb.h"
#include <grpcpp/grpcpp.h>
#include <memory>
#include <string>
#include <vector>

// Defining the return types
struct VerifyResult {
  bool valid;
  std::string match_id;
  std::string player_id;
};

struct ResolveResult {
  bool valid;
  std::string match_id;
  std::string user_id;
  std::string color;
};

class GrpcClient {
public:
  explicit GrpcClient(const std::string& address);
  VerifyResult verifyMatchTicket(const std::string& ticket_id);
  // passing by reference bc we are only reading the values not modifying
  bool reportGameEnd(const std::string& match_id,
      const std::string& winner_id,
      const std::vector<std::string>& moves);
  std::string createResumeToken(const std::string& match_id,
      const std::string& user_id,
      const std::string& color);
  ResolveResult resolveResumeToken(const std::string& token);

private:
  // The stub is the generated gRPC object that knows how to serialize requests and send them over
  // the network to the Python server. You need one stub per service you're calling, if we ever
  // added a second .proto service, we'd have a second stub alongside this one.
  std::unique_ptr<gamecontrol::GameControl::Stub> stub_;
};
