#!/bin/sh
DIR=$(dirname "$(readlink -f "$0")")
. $DIR/transform_vars.sh
mkdir -p /tmp/workspace/
docker build -t zensum/$ZENS_NAME:latest -t zensum/$ZENS_NAME:$TAG  .
docker save -o /tmp/workspace/latest zensum/$ZENS_NAME:$TAG
