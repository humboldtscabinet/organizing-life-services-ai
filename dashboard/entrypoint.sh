#!/bin/sh
set -eu

: "${OLS_API_KEY:?OLS_API_KEY must be set for the dashboard proxy}"

envsubst '${OLS_API_KEY}' \
  < /etc/nginx/nginx.conf.template \
  > /etc/nginx/nginx.conf

exec nginx -g 'daemon off;'
