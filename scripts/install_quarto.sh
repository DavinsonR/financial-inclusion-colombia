#!/usr/bin/env bash
# Instala Quarto desde el tarball de GitHub Releases en ~/.local/opt (idempotente).
# La API de GitHub puede estar bloqueada por el proxy; el tarball no.
set -euo pipefail
QUARTO_VERSION="${QUARTO_VERSION:-1.7.32}"
OPT="${HOME}/.local/opt"
BIN="${HOME}/.local/bin"
mkdir -p "$OPT" "$BIN"
if [ -x "$OPT/quarto-${QUARTO_VERSION}/bin/quarto" ]; then
  echo "quarto ${QUARTO_VERSION} ya instalado"
else
  TGZ="${TMPDIR:-/tmp}/quarto-${QUARTO_VERSION}.tgz"
  if [ ! -s "$TGZ" ]; then
    curl -fL --retry 3 -o "$TGZ" \
      "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-amd64.tar.gz"
  fi
  tar -xzf "$TGZ" -C "$OPT"
fi
ln -sf "$OPT/quarto-${QUARTO_VERSION}/bin/quarto" "$BIN/quarto"
"$BIN/quarto" --version
