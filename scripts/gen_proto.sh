#!/usr/bin/env bash
# Run from the repo root: ./scripts/gen_proto.sh

set -e  # exit immediately if any command fails

PROTO_FILE="proto/gamecontrol.proto"
PROTO_DIR="proto"

PYTHON_OUT="services/api/grpc_generated"
CPP_OUT="services/gameserver/src/generated"

mkdir -p "$PYTHON_OUT"
mkdir -p "$CPP_OUT"

echo "Generating Python stubs..."
python -m grpc_tools.protoc \
  -I "$PROTO_DIR" \
  --python_out="$PYTHON_OUT" \
  --grpc_python_out="$PYTHON_OUT" \
  "$PROTO_FILE"

echo "Generating C++ stubs..."
GRPC_CPP_PLUGIN="$(brew --prefix grpc)/bin/grpc_cpp_plugin"
protoc \
  -I "$PROTO_DIR" \
  --cpp_out="$CPP_OUT" \
  --grpc_out="$CPP_OUT" \
  --plugin=protoc-gen-grpc="$GRPC_CPP_PLUGIN" \
  "$PROTO_FILE"

echo "Done. Generated files:"
echo "  Python: $PYTHON_OUT"
echo "  C++:    $CPP_OUT"
