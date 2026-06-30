#!/usr/bin/env bash
#
# Interactive launcher for the Simple Token Burner App.
# Uses `gum` to prompt for run options and executes via `uv run`.

set -euo pipefail

cd "$(dirname "$0")"

# Load defaults from .env (e.g. BURNER_PROVIDER, BURNER_BASE_URL, BURNER_MODEL, BURNER_MAX_PROMPTS).
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
      - Run prompts          (choose provider, burner mode, categories, limits, delay)
      - Run benchmark        (router: measure prompts across all deployments)
      - Run custom prompts   (enter your own prompts, one per line)
      - List available prompts
      - List prompt categories

OPTIONS:
    -h, --help    Show this help message and exit.

REQUIREMENTS:
    gum   https://github.com/charmbracelet/gum   (brew install gum)
    uv    https://docs.astral.sh/uv/             (brew install uv)

ENVIRONMENT:
    Optional .env in the project root (see .env.example):
      BURNER_PROVIDER, BURNER_BASE_URL, BURNER_MODEL, BURNER_MAX_PROMPTS,
      BURNER_MODE, BURNER_MEASURE_DEPLOYMENTS
    Loaded by main.py and this script; CLI flags override .env values.
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
    echo "See https://github.com/charmbracelet/gum for other platforms."
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: 'uv' is not installed."
    echo "Install it with: brew install uv"
    echo "See https://docs.astral.sh/uv/ for other platforms."
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

# Shared helper: prompt for router benchmark / infer run options.
# Sets globals: PROVIDER, BURNER_MODE, BASE_URL, MODEL, MEASURE_DEPLOYMENTS,
# MODE, CATEGORIES, MAX_PROMPTS, DELAY, API_KEY
prompt_run_options() {
    local default_burner_mode="${1:-infer}"

    PROVIDER=$(gum choose --header "Select an LLM provider" mock router openai anthropic local \
        --selected "${BURNER_PROVIDER:-router}")
    cmd+=(--provider "$PROVIDER")

    BURNER_MODE=$(gum choose --header "Burner mode" infer benchmark \
        --selected "${default_burner_mode:-${BURNER_MODE:-infer}}")
    cmd+=(--burner-mode "$BURNER_MODE")

    if [ "$BURNER_MODE" = "benchmark" ] && [ "$PROVIDER" != "router" ]; then
        gum style --foreground 1 "Benchmark mode requires the router provider."
        exit 1
    fi

    if [ "$PROVIDER" != "mock" ]; then
        API_KEY=$(gum input --password --header "API key (leave blank to skip)" --placeholder "sk-...")
        [ -n "$API_KEY" ] && cmd+=(--api-key "$API_KEY")
    fi

    if [ "$PROVIDER" = "local" ]; then
        BASE_URL=$(gum input --header "Base URL for the local provider" \
            --value "${BURNER_BASE_URL:-http://localhost:11434}")
        [ -n "$BASE_URL" ] && cmd+=(--base-url "$BASE_URL")
    fi

    if [ "$PROVIDER" = "router" ]; then
        BASE_URL=$(gum input --header "Fancy LLM Router API base URL" \
            --value "${BURNER_BASE_URL:-http://localhost:8000}")
        [ -n "$BASE_URL" ] && cmd+=(--base-url "$BASE_URL")
    fi

    if [ "$BURNER_MODE" = "benchmark" ]; then
        gum style --foreground 212 \
            "Benchmark: fetches deployments from the router and measures each prompt with intent=measure."
        MEASURE_DEPLOYMENTS=$(gum input --header "Deployments to measure (all, or comma-separated ids)" \
            --placeholder "all" --value "${BURNER_MEASURE_DEPLOYMENTS:-all}")
        [ -n "$MEASURE_DEPLOYMENTS" ] && cmd+=(--measure-deployments "$MEASURE_DEPLOYMENTS")
        cmd+=(--temperature 0)
    else
        MODEL=$(gum input --header "Model (leave blank for provider/router default)" \
            --placeholder "auto" --value "${BURNER_MODEL:-}")
        [ -n "$MODEL" ] && cmd+=(--model "$MODEL")
    fi

    MODE=$(gum choose --header "Prompt execution mode" sequential random categorical custom)
    cmd+=(--mode "$MODE")

    CATEGORIES=$(gum choose --no-limit --header "Prompt categories (space to select, enter to confirm; none = all)" \
        small medium large xl)
    if [ -n "$CATEGORIES" ]; then
        cmd+=(--categories)
        while IFS= read -r cat; do
            [ -n "$cat" ] && cmd+=("$cat")
        done <<< "$CATEGORIES"
    fi

    MAX_PROMPTS=$(gum input --header "Max prompts (leave blank for all)" \
        --placeholder "10" --value "${BURNER_MAX_PROMPTS:-}")
    [ -n "$MAX_PROMPTS" ] && cmd+=(--max-prompts "$MAX_PROMPTS")

    DELAY=$(gum input --header "Delay between prompts in seconds" --value "0")
    [ -n "$DELAY" ] && cmd+=(--delay "$DELAY")

    if gum confirm "Disable console logging?"; then
        cmd+=(--no-console)
    fi
}

case "$ACTION" in
    "List available prompts")
        cmd+=(--list-prompts)
        ;;

    "List prompt categories")
        cmd+=(--list-categories)
        ;;

    "Run custom prompts")
        PROMPTS=$(gum write --header "Enter one prompt per line" --placeholder "What is AI?")
        if [ -z "$PROMPTS" ]; then
            echo "No prompts entered. Aborting."
            exit 1
        fi
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
