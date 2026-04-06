#!/usr/bin/env bash
# Build bozemanpass/test-database-client
source ${STACK_CONTAINER_BASE_DIR}/build-base.sh
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
docker build -t bozemanpass/test-database-client:stack -f ${SCRIPT_DIR}/Containerfile ${build_command_args} $SCRIPT_DIR
