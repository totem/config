#!/bin/bash -e

HOST_IP="${HOST_IP:-$(/sbin/ip route|awk '/default/ { print $3 }')}"

export ETCD_HOST="${ETCD_HOST:-${HOST_IP}"
export ETCD_PORT="${ETCD_PORT:-4001}"
export ETCD_TOTEM_BASE="${ETCD_TOTEM_BASE:-/totem}"
export API_EXECUTORS="${API_EXECUTORS:-2}"
export GITHUB_TOKEN="${GITHUB_TOKEN}"
export CLUSTER_NAME="${CLUSTER_NAME:-local}"
export TOTEM_ENV="${TOTEM_ENV:-local}"
export ENCRYPTION_PASSPHRASE="${ENCRYPTION_PASSPHRASE:-changeit}"
export ENCRYPTION_S3_BUCKET="${ENCRYPTION_S3_BUCKET:-not-set}"
export ENCRYPTION_STORE="${ENCRYPTION_PROVIDER:-s3}"
export LOG_IDENTIFIER="${LOG_IDENTIFIER:-configservice}"
export CONFIG_PROVIDER_LIST="${CONFIG_PROVIDER_LIST:-etcd,default,effective}"
export CONFIG_PROVIDER_DEFAULT="${CONFIG_PROVIDER_LIST:-etcd}"


/usr/local/bin/uwsgi \
        --master \
        --catch-exceptions \
        --processes ${API_EXECUTORS} \
        --gevent 100 \
        --http :9003 \
        --http-timeout 120 \
        --gevent-monkey-patch \
        --module configservice.server \
        --callable app \
        --logger syslog:${LOG_IDENTIFIER}[0]
