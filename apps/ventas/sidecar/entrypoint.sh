#!/bin/sh
set -e

# Upstream defaults â€” override per environment:
#   docker-compose  â†’ inventario:3002
#   ECS same-task   â†’ localhost:3002
#   ECS cross-task  â†’ <ALB or Cloud Map DNS>:3002
INVENTARIO_UPSTREAM_HOST="${INVENTARIO_UPSTREAM_HOST:-inventario}"
INVENTARIO_UPSTREAM_PORT="${INVENTARIO_UPSTREAM_PORT:-3002}"

export INVENTARIO_UPSTREAM_HOST INVENTARIO_UPSTREAM_PORT

# Substitute placeholders and write the final Envoy config
envsubst < /etc/envoy/envoy.yaml.tmpl > /etc/envoy/envoy.yaml

echo "[sidecar] upstream: ${INVENTARIO_UPSTREAM_HOST}:${INVENTARIO_UPSTREAM_PORT}"

exec envoy -c /etc/envoy/envoy.yaml --log-level info "$@"
