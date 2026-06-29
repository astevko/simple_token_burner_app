#!/usr/bin/env bash

# Simple Token Burner App - Interactive Runner
# Uses gum for a nice interactive experience

set -euo pipefail

# Check if gum is installed
if ! command -v gum &> /dev/null; then
    echo "Error: gum is not installed. Please install it first:"
    echo "  brew install gum        # macOS (Homebrew)"
    echo "  sudo apt install gum    # Debian/Ubuntu"
    echo "  sudo dnf install gum    # Fedora"
    echo "  cargo install gum       # Cargo"
    exit 1
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
show_header() {
    gum style --foreground 21 "\n╔══════════════════════════════════════════════════════════════╗"
    gum style --foreground 21 "║     Simple Token Burner App                              ║"
    gum style --foreground 21 "╚══════════════════════════════════════════════════════════════╝"
    echo
}

show_menu() {
    gum style --foreground 3 "What would you like to do?\n"
    
    OPTION=$(gum choose \
        "Run with default settings (mock provider)" \
        "Configure provider settings" \
        "List available prompts" \
        "List prompt categories" \
        "Run custom prompts" \
        "Run with specific settings" \
        "Exit")
    
    case "$OPTION" in
        "Run with default settings (mock provider)")
            run_default
            ;;
        "Configure provider settings")
            configure_provider
            ;;
        "List available prompts")
            python main.py --list-prompts
            ;;
        "List prompt categories")
            python main.py --list-categories
            ;;
        "Run custom prompts")
            run_custom_prompts
            ;;
        "Run with specific settings")
            run_with_settings
            ;;
        "Exit")
            gum style --foreground 1 "Goodbye! 👋"
            exit 0
            ;;
    esac
}

run_default() {
    gum style --foreground 2 "Running with default settings...\n"
    gum spin --spinner dot --title "Executing prompts..." -- python main.py
    gum style --foreground 2 "\nDone! ✅\n"
}

configure_provider() {
    gum style --foreground 3 "Configuring provider settings...\n"
    python main.py --configure
    gum style --foreground 2 "\nConfiguration complete! ✅\n"
}

run_custom_prompts() {
    gum style --foreground 3 "Enter your custom prompts (one per line, empty line to finish):\n"
    
    # Use gum write for multi-line input
    CUSTOM_PROMPTS=$(gum write --placeholder "Enter prompts here, one per line..." --width 80 --height 10)
    
    if [ -z "$CUSTOM_PROMPTS" ]; then
        gum style --foreground 1 "No prompts entered.\n"
        return
    fi
    
    # Convert to array and run
    gum style --foreground 2 "Running custom prompts...\n"
    gum spin --spinner dot --title "Executing custom prompts..." -- python main.py --custom-prompts $CUSTOM_PROMPTS
    gum style --foreground 2 "\nDone! ✅\n"
}

run_with_settings() {
    gum style --foreground 3 "Let's configure your run settings:\n"
    
    # Select provider
    PROVIDER=$(gum choose "openai" "anthropic" "local" "mock" --header "Select LLM Provider")
    
    # Select mode
    MODE=$(gum choose "sequential" "random" "categorical" "custom" --header "Select Execution Mode")
    
    # Select categories
    CATEGORIES=$(gum choose --no-limit "small" "medium" "large" "xl" --header "Select Prompt Categories (press space to select, enter to confirm)")
    
    # Max prompts
    MAX_PROMPTS=$(gum input --placeholder "Maximum prompts (leave empty for all)" --header "Max Prompts")
    
    # Delay
    DELAY=$(gum input --placeholder "0" --header "Delay between prompts (seconds)")
    
    # Build command
    CMD="python main.py --provider $PROVIDER --mode $MODE"
    
    if [ -n "$CATEGORIES" ]; then
        CMD="$CMD --categories $CATEGORIES"
    fi
    
    if [ -n "$MAX_PROMPTS" ]; then
        CMD="$CMD --max-prompts $MAX_PROMPTS"
    fi
    
    if [ -n "$DELAY" ]; then
        CMD="$CMD --delay $DELAY"
    fi
    
    gum style --foreground 2 "Running with custom settings...\n"
    gum style --foreground 21 "Command: $CMD\n\n"
    gum spin --spinner dot --title "Executing prompts..." -- $CMD
    gum style --foreground 2 "\nDone! ✅\n"
}

# Main execution
show_header

while true; do
    show_menu
done