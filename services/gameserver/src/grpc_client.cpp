#include "grpc_client.h"
#include "generated/gamecontrol.grpc.pb.h"
#include <grpcpp/grpcpp.h>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

GrpcClient::GrpcClient(const std::string& address) {
  auto channel = grpc::CreateChannel(address, grpc::InsecureChannelCredentials());
  stub_ = gamecontrol::GameControl::NewStub(channel);
};

VerifyResult GrpcClient::verifyMatchTicket(const std::string& ticket_id) {
  gamecontrol::VerifyTicketRequest request;
  request.set_ticket(ticket_id);

  gamecontrol::VerifyTicketResponse response;
  grpc::ClientContext context;
  grpc::Status status = stub_->VerifyMatchTicket(&context, request, &response);

  if (!status.ok() || !response.valid()) {
    return { false, "", "" };
  }
  return { true, response.match_id(), response.player_id() };
}

bool GrpcClient::reportGameEnd(const std::string& match_id,
    const std::string& winner_id,
    const std::vector<std::string>& moves) {

  gamecontrol::GameEndRequest request;
  request.set_match_id(match_id);
  request.set_winner_id(winner_id);
  for (const auto& move : moves) {
    request.add_moves(move);
  }

  gamecontrol::GameEndResponse response;
  grpc::ClientContext context;
  grpc::Status status = stub_->ReportGameEnd(&context, request, &response);

  if (!status.ok()) {
    return false;
  }
  return response.acknowledged();
}
