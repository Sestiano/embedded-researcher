#!/usr/bin/env bash
# Embedded Researcher · UniTrento — Avvio rapido in 1 comando
# Uso:
#   ./run.sh          -> avvia il server locale (e costruisce i dati se mancano, oppure permette di farlo da browser)
#   ./run.sh --build  -> esegue subito tutta la pipeline (incluso download open data + IRIS) e poi apre il server
#   ./run.sh --alt    -> esegue la pipeline completa includendo anche il modello alternativo (EmbeddingGemma-2)
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "Errore: 'uv' non trovato. Installalo con: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

uv sync

if [[ "${1:-}" == "--build" ]]; then
  uv run python -m unitn_net build
elif [[ "${1:-}" == "--alt" ]]; then
  uv run python -m unitn_net build --alt
fi

echo "Avvio interfaccia su http://127.0.0.1:8000/ ..."
exec uv run python -m unitn_net serve --host 127.0.0.1 --port 8000
