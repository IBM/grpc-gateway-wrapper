#!/usr/bin/env bash

set -e
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

FAIL_THRESH=100.0
python3 -m pytest \
    --cov-config=.coveragerc \
    --cov=grpc_gateway_wrapper \
    --cov-report=term \
    --cov-report=html \
    --cov-fail-under=$FAIL_THRESH \
    -W error "$@"
