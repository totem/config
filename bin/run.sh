#!/bin/bash -c

export ETCD_HOST='${ETCD_HOST:-172.17.42.1}'
export ETCD_PORT='${ETCD_PORT:-4001}'
export ETCD_TOTEM_BASE='${ETCD_TOTEM_BASE:-/totem}'
export API_EXECUTORS='${API_EXECUTORS:-2}'
export GITHUB_TOKEN='${GITHUB_TOKEN}'
export CLUSTER_NAME='${CLUSTER_NAME:-local}'
export TOTEM_ENV='${TOTEM_ENV:-local}'
export ENCRYPTION_PASSPHRASE='${ENCRYPTION_PASSPHRASE:-changeit}'
export ENCRYPTION_S3_BUCKET='${ENCRYPTION_S3_BUCKET:-not-set}'
export ENCRYPTION_STORE='${ENCRYPTION_PROVIDER:-s3}'
export LOG_IDENTIFIER='${LOG_IDENTIFIER:-configservice}'

/usr/local/bin/uwsgi \
        --master \
        --catch-exceptions \
        --processes ${API_EXECUTORS} \
        --gevent 100 \
        --http :9003 \
        --http-timeout 120 \
        --gevent-monkey-patch \
        --module configservice.server \
        --callable app