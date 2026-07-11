#!/usr/bin/env python3
"""
Simple Token Burner App - Main entry point

This application repeatedly runs prompts against an LLM and logs comprehensive metrics
including prompt hashing, response times, token usage, and more.
"""

import argparse
import os
import sys
from typing import List

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simple_token_burner_app.agent import SimpleAgent, AgentConfig, ExecutionMode
from simple_token_burner_app.prompts import ALL_PROMPTS
from simple_token_burner_app.env import load_dotenv_file, getenv_int, getenv_str


def parse_arguments():
    """Parse command line arguments."""
    load_dotenv_file()

    parser = argparse.ArgumentParser(
        description="Simple Token Burner App - Run LLM prompts with comprehensive logging"
    )
    
    # Provider arguments
    parser.add_argument(
        '--model',
        type=str,
        default=os.environ.get('BURNER_MODEL', 'mock-model'),
        help=(
            'LiteLLM model string or bare model name, e.g. "openai/gpt-4o-mini", '
            '"anthropic/claude-sonnet-4-20250514", "ollama/llama3", "auto" '
            '(default: BURNER_MODEL from .env, else "mock-model")'
        ),
    )

    # --provider is prepended to --model when --model contains no slash:
    #   --provider openai --model gpt-4o  →  "openai/gpt-4o"
    #   BURNER_PROVIDER=router BURNER_MODEL=auto  →  "router/auto"
    # If --model already includes a slash (full model string), --provider is ignored.
    parser.add_argument(
        '--provider',
        type=str,
        default=os.environ.get('BURNER_PROVIDER', 'mock'),
        help='Provider prefix prepended to --model when --model has no slash (default: BURNER_PROVIDER from .env, else "mock")',
    )
    
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='API key for the provider (can also use environment variables)'
    )
    
    parser.add_argument(
        '--base-url',
        type=str,
        default=os.environ.get('BURNER_BASE_URL'),
        help='Base URL for the local or router provider '
             '(default: BURNER_BASE_URL from .env; router fallback: http://localhost:8000)'
    )
    
    parser.add_argument(
        '--burner-mode',
        type=str,
        default=getenv_str('BURNER_MODE', 'infer'),
        choices=['infer', 'benchmark'],
        help='infer = normal routing; benchmark = measure all deployments (default: BURNER_MODE)'
    )

    parser.add_argument(
        '--measure-deployments',
        type=str,
        default=getenv_str('BURNER_MEASURE_DEPLOYMENTS', 'all'),
        help='Comma-separated deployment ids or "all" (default: BURNER_MEASURE_DEPLOYMENTS)'
    )

    # Execution mode arguments
    parser.add_argument(
        '--mode',
        type=str,
        default='sequential',
        choices=[m.value for m in ExecutionMode],
        help='Execution mode: sequential, random, categorical, custom (default: sequential)'
    )
    
    parser.add_argument(
        '--categories',
        type=str,
        nargs='+',
        default=['small', 'medium', 'large', 'xl'],
        choices=['small', 'medium', 'large', 'xl'],
        help='Categories of prompts to use (default: all)'
    )
    
    parser.add_argument(
        '--max-prompts',
        type=int,
        default=getenv_int('BURNER_MAX_PROMPTS'),
        help='Maximum number of prompts to execute '
             '(default: BURNER_MAX_PROMPTS from .env, else all available)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=0.0,
        help='Delay between prompts in seconds (default: 0)'
    )
    
    # LLM parameters
    parser.add_argument(
        '--max-tokens',
        type=int,
        default=None,
        help='Override response token budget for all prompts (default: infer=1000; '
             'benchmark=per-category budget from catalog: small 256, medium 512, '
             'large 1024, xl 2048)'
    )
    
    parser.add_argument(
        '--temperature',
        type=float,
        default=0.7,
        help='Temperature for response generation (default: 0.7)'
    )
    
    # Logging arguments
    parser.add_argument(
        '--log-dir',
        type=str,
        default='logs',
        help='Directory for log files (default: logs)'
    )
    
    parser.add_argument(
        '--no-console',
        action='store_true',
        help='Disable console logging'
    )
    
    parser.add_argument(
        '--no-file',
        action='store_true',
        help='Disable file logging'
    )
    
    # Custom prompts
    parser.add_argument(
        '--custom-prompts',
        type=str,
        nargs='+',
        default=None,
        help='Custom prompts to execute'
    )
    
    # Configuration
    parser.add_argument(
        '--configure',
        action='store_true',
        help='Interactive configuration to set up provider information'
    )
    
    # Information
    parser.add_argument(
        '--list-prompts',
        action='store_true',
        help='List all available prompts and exit'
    )
    
    parser.add_argument(
        '--list-categories',
        action='store_true',
        help='List prompt categories and exit'
    )
    
    return parser.parse_args()


def list_prompts():
    """List all available prompts."""
    print("Available Prompts:")
    print("=" * 50)
    
    from simple_token_burner_app.prompts import PROMPT_CATEGORIES
    
    for category, prompts in PROMPT_CATEGORIES.items():
        print(f"\n{category.upper()} PROMPTS ({len(prompts)}):")
        print("-" * 30)
        for i, prompt in enumerate(prompts, 1):
            # Show first 100 characters of each prompt
            preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
            print(f"  {i}. {preview}")
    
    print(f"\nTotal prompts: {len(ALL_PROMPTS)}")


def list_categories():
    """List prompt categories."""
    print("Available Prompt Categories:")
    print("=" * 40)
    
    from simple_token_burner_app.prompts import PROMPT_CATEGORIES
    
    for category, prompts in PROMPT_CATEGORIES.items():
        print(f"  {category}: {len(prompts)} prompts")
    
    print(f"\nTotal: {len(ALL_PROMPTS)} prompts across all categories")


def configure_provider():
    """Interactive configuration: write BURNER_MODEL and optional API key to .env."""
    print("Simple Token Burner App - Configuration")
    print("=" * 40)
    print(
        "Use LiteLLM model strings, e.g.:\n"
        "  openai/gpt-4o-mini\n"
        "  anthropic/claude-sonnet-4-20250514\n"
        "  ollama/llama3\n"
    )

    env_file = ".env"
    current_config: dict = {}
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    current_config[k.strip()] = v.strip()

    current_model = current_config.get("BURNER_MODEL", "")
    model_input = input(
        f"Enter LiteLLM model string [{current_model or 'mock-model'}]: "
    ).strip()
    model = model_input or current_model or "mock-model"

    api_key = input("API key (leave blank to skip / use env var): ").strip()
    base_url = input("Base URL (leave blank if not needed): ").strip()

    with open(env_file, "w") as f:
        f.write("# Simple Token Burner App Configuration\n")
        f.write(f"# Generated on: {__import__('datetime').datetime.now().isoformat()}\n\n")
        f.write(f"BURNER_MODEL={model}\n")
        if api_key:
            provider = model.split("/")[0].upper()
            f.write(f"{provider}_API_KEY={api_key}\n")
        if base_url:
            f.write(f"BURNER_BASE_URL={base_url}\n")

    print(f"\nConfiguration saved to {env_file}")
    print(f"Model: {model}")


def load_env_config():
    """Load configuration from .env file."""
    env_file = ".env"
    config = {}
    
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    
    return config


def main():
    """Main function."""
    args = parse_arguments()
    
    # Handle configuration
    if args.configure:
        configure_provider()
        return
    
    env_config = load_env_config()

    # Build the LiteLLM model string.
    # If --model already contains a "/" use it as-is.
    # If --provider was also given, prepend it: "openai/gpt-4o"
    model = args.model
    if args.provider and "/" not in model:
        model = f"{args.provider}/{model}"

    # Resolve API key: explicit arg > env var keyed by provider prefix > generic.
    api_key = args.api_key
    if api_key is None:
        provider_prefix = model.split("/")[0].upper()
        api_key = (
            env_config.get(f"{provider_prefix}_API_KEY")
            or env_config.get("BURNER_API_KEY")
            or os.environ.get(f"{provider_prefix}_API_KEY")
        )

    base_url = args.base_url
    
    # Handle information requests
    if args.list_prompts:
        list_prompts()
        return
    
    if args.list_categories:
        list_categories()
        return

    max_tokens = args.max_tokens
    if max_tokens is None and args.burner_mode != "benchmark":
        max_tokens = 1000
    
    config = AgentConfig(
        model=model,
        api_key=api_key,
        base_url=base_url,
        execution_mode=args.mode,
        categories=args.categories,
        max_prompts=args.max_prompts,
        delay_between_prompts=args.delay,
        max_tokens=max_tokens,
        temperature=args.temperature,
        log_dir=args.log_dir,
        enable_console_logging=not args.no_console,
        enable_file_logging=not args.no_file,
        custom_prompts=args.custom_prompts or [],
        burner_mode=args.burner_mode,
        measure_deployments=args.measure_deployments,
    )
    
    # Create and run agent
    agent = SimpleAgent(config)
    
    if args.custom_prompts:
        print(f"Running {len(args.custom_prompts)} custom prompts...")
        agent.run_custom_prompts(args.custom_prompts)
    else:
        print("Starting Simple Token Burner App...")
        print(f"Model: {model}")
        print(f"Burner mode: {args.burner_mode}")
        print(f"Mode: {args.mode}")
        print(f"Categories: {', '.join(args.categories)}")
        
        if args.max_prompts:
            print(f"Max prompts: {args.max_prompts}")
        else:
            print(f"Max prompts: all available ({len(ALL_PROMPTS)})")
        
        print(f"Delay between prompts: {args.delay}s", end="")
        if args.burner_mode == "benchmark":
            print(" (between catalog prompts, not deployments)")
        else:
            print()
        print(f"Log directory: {args.log_dir}")
        print("-" * 50)
        
        agent.run()


if __name__ == "__main__":
    main()