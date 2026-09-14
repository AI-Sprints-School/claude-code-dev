#!/usr/bin/env sh
# Обновить статику Swagger UI в static/docs/.
# Версия пришпилена: /docs не должен меняться посреди работы.
set -eu
VERSION="${1:-5.18.2}"
DIR="$(dirname "$0")/../static/docs"
curl -sSL -o "$DIR/swagger-ui.css" "https://unpkg.com/swagger-ui-dist@$VERSION/swagger-ui.css"
curl -sSL -o "$DIR/swagger-ui-bundle.js" "https://unpkg.com/swagger-ui-dist@$VERSION/swagger-ui-bundle.js"
echo "swagger-ui-dist@$VERSION → $DIR"
