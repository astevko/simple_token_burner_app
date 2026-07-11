#!/usr/bin/env bash
#
# Interactive launcher for the Simple Token Burner App.
# Uses `gum` to prompt for run options and executes via `uv run`.

set -euo pipefail

cd "$(dirname "$0")"

# Load defaults from .env
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

usage() {
    cat <<'EOF'
Simple Token Burner App - interactive launcher

USAGE:
    ./run.sh [-h|--help]

DESCRIPTION:
    A gum-powered, menu-driven launcher that prompts you for run options and
    executes the app via `uv run main.py`.

    Running with no arguments starts the interactive menu, which lets you:
      - Run prompts          (infer mode, any LiteLLM model)
      - Run benchmark        (measure prompts, temperature=0, capped tokens)
      - Run custom prompts   (enter your own prompts, one per line)
      - List available prompts
      - List prompt categories

OPTIONS:
    -h, --help    Show this help message and exit.

REQUIREMENTS:
    gum   https://github.com/charmbracelet/gum   (brew install gum)
    uv    https://docs.astral.sh/uv/             (brew install uv)

ENVIRONMENT (.env in project root):
    BURNER_MODEL        LiteLLM model string, e.g. "openai/Qwen/Qwen3-32B"
    BURNER_BASE_URL     Custom API base URL (Nebius, Ollama, etc.)
    OPENAI_API_KEY      API key (used when model prefix is "openai/")
    BURNER_MODE         Default burner mode (infer | benchmark)
    BURNER_MAX_PROMPTS  Default max prompts
EOF
}

case "${1:-}" in
    -h|--help)
        usage
        exit 0
        ;;
esac

if ! command -v gum >/dev/null 2>&1; then
    echo "Error: 'gum' is not installed."
    echo "Install it with: brew install gum"
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: 'uv' is not installed."
    echo "Install it with: brew install uv"
    exit 1
fi

gum style --border normal --margin "1" --padding "1 2" --border-foreground 212 \
    "Simple Token Burner App"

ACTION=$(gum choose --header "What would you like to do?" \
    "Run prompts" \
    "Run benchmark" \
    "Run custom prompts" \
    "List available prompts" \
    "List prompt categories")

cmd=(uv run main.py)

# ---------------------------------------------------------------------------
# Shared helper: prompt for model + common run options.
# Sets global cmd array.
# ---------------------------------------------------------------------------
prompt_run_options() {
    local default_burner_mode="${1:-infer}"

    # ── Model string ────────────────────────────────────────────────────────
    MODEL=$(gum input \
        --header "LiteLLM model string  (e.g. openai/Qwen/Qwen3-32B, ollama/llama3)" \
        --placeholder "openai/..." \
        --value "${BURNER_MODEL:-}")
    [ -n "$MODEL" ] && cmd+=(--model "$MODEL")

    # ── API key ─────────────────────────────────────────────────────────────
    API_KEY=$(gum input --password \
        --header "API key (leave blank to use env var)" \
        --placeholder "sk-... or leave blank")
    [ -n "$API_KEY" ] && cmd+=(--api-key "$API_KEY")

    # ── Base URL (Nebius, Ollama, proxy, etc.) ───────────────────────────────
    BASE_URL=$(gum input \
        --header "Base URL (leave blank for default / already in .env)" \
        --value "${BURNER_BASE_URL:-}")
    [ -n "$BASE_URL" ] && cmd+=(--base-url "$BASE_URL")

    # ── Burner mode ──────────────────────────────────────────────────────────
    BURNER_MODE_SEL=$(gum choose --header "Burner mode" infer benchmark \
        --selected "${default_burner_mode:-${BURNER_MODE:-infer}}")
    cmd+=(--burner-mode "$BURNER_MODE_SEL")

    if [ "$BURNER_MODE_SEL" = "benchmark" ]; then
        gum style --foreground 212 \
            "Benchmark: temperature=0, per-category token caps, stop sequences."
        cmd+=(--temperature 0)
    fi

    # ── Execution mode ───────────────────────────────────────────────────────
    MODE=$(gum choose --header "Prompt execution mode" sequential random categorical)
    cmd+=(--mode "$MODE")

    # ── Categories ───────────────────────────────────────────────────────────
    CATEGORIES=$(gum choose --no-limit \
        --header "Prompt categories (space to select, enter to confirm; none = all)" \
        small medium large xl)
    if [ -n "$CATEGORIES" ]; then
        cmd+=(--categories)
        while IFS= read -r cat; do
            [ -n "$cat" ] && cmd+=("$cat")
        done <<< "$CATEGORIES"
    fi

    # ── Limits ───────────────────────────────────────────────────────────────
    MAX_PROMPTS=$(gum input --header "Max prompts (leave blank for all)" \
        --placeholder "10" --value "${BURNER_MAX_PROMPTS:-}")
    [ -n "$MAX_PROMPTS" ] && cmd+=(--max-prompts "$MAX_PROMPTS")

    DELAY=$(gum input --header "Delay between prompts in seconds" --value "0")
    [ -n "$DELAY" ] && cmd+=(--delay "$DELAY")

    if gum confirm "Disable console logging?"; then
        cmd+=(--no-console)
    fi
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
case "$ACTION" in
    "List available prompts")
        cmd+=(--list-prompts)
        ;;

    "List prompt categories")
        cmd+=(--list-categories)
        ;;

    "Run custom prompts")
        PROMPTS=$(gum write --header "Enter one prompt per line" \
            --placeholder "What is AI?")
        if [ -z "$PROMPTS" ]; then
            echo "No prompts entered. Aborting."
            exit 1
        fi
        # Still ask for model + key so the call can actually go through.
        MODEL=$(gum input \
            --header "LiteLLM model string" \
            --placeholder "openai/..." \
            --value "${BURNER_MODEL:-}")
        [ -n "$MODEL" ] && cmd+=(--model "$MODEL")

        API_KEY=$(gum input --password \
            --header "API key (leave blank to use env var)" \
            --placeholder "leave blank")
        [ -n "$API_KEY" ] && cmd+=(--api-key "$API_KEY")

        BASE_URL=$(gum input \
            --header "Base URL (leave blank for default)" \
            --value "${BURNER_BASE_URL:-}")
        [ -n "$BASE_URL" ] && cmd+=(--base-url "$BASE_URL")

        cmd+=(--custom-prompts)
        while IFS= read -r line; do
            [ -n "$line" ] && cmd+=("$line")
        done <<< "$PROMPTS"
        ;;

    "Run prompts")
        prompt_run_options "${BURNER_MODE:-infer}"
        ;;

    "Run benchmark")
        prompt_run_options benchmark
        ;;
esac

echo
gum style --foreground 212 "Running: ${cmd[*]}"
echo

exec "${cmd[@]}"
