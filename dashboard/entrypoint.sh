#!/bin/sh
set -eu

: "${OLS_API_KEY:?OLS_API_KEY must be set for the dashboard proxy}"

# Optional HTTP Basic Auth in front of the SPA and the key-injecting /api/
# proxy. The proxy is safe unauthenticated only on localhost; requiring a
# credential is what makes it safe to reach from off-localhost (e.g. a
# Cloudflare tunnel). With no credentials set the proxy stays open, as before,
# for localhost-only use.
DASHBOARD_AUTH_DIRECTIVES=""
if [ -n "${OLS_DASHBOARD_BASIC_AUTH_USER:-}" ] && [ -n "${OLS_DASHBOARD_BASIC_AUTH_PASSWORD:-}" ]; then
  htpasswd -cbB /etc/nginx/.htpasswd \
    "${OLS_DASHBOARD_BASIC_AUTH_USER}" "${OLS_DASHBOARD_BASIC_AUTH_PASSWORD}" >/dev/null
  DASHBOARD_AUTH_DIRECTIVES='auth_basic "OLS Dashboard"; auth_basic_user_file /etc/nginx/.htpasswd;'
fi
export DASHBOARD_AUTH_DIRECTIVES

envsubst '${OLS_API_KEY} ${DASHBOARD_AUTH_DIRECTIVES}' \
  < /etc/nginx/nginx.conf.template \
  > /etc/nginx/nginx.conf

exec nginx -g 'daemon off;'
