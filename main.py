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
from simple_token_burner_app.llm_client import LLMProvider


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Simple Token Burner App - Run LLM prompts with comprehensive logging"
    )
    
    # Provider arguments
    parser.add_argument(
        '--provider',
        type=str,
        default='mock',
        choices=[p.value for p in LLMProvider],
        help='LLM provider to use (default: mock)'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help='Model to use (default: provider-specific default)'
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
        default=None,
        help='Base URL for local LLM providers'
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
        default=None,
        help='Maximum number of prompts to execute (default: all available)'
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
        default=1000,
        help='Maximum tokens in response (default: 1000)'
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
    """Interactive configuration to set up provider information."""
    print("Simple Token Burner App - Configuration")
    print("=" * 40)
    
    # Get current configuration from .env if it exists
    env_file = ".env"
    current_config = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    current_config[key.strip()] = value.strip()
    
    # Ask for provider
    providers = [p.value for p in LLMProvider if p.value != 'mock']
    print("Available LLM Providers:")
    for i, provider in enumerate(providers, 1):
        print(f"  {i}. {provider}")
    
    while True:
        try:
            choice = input(f"Select provider (1-{len(providers)}): ")
            if choice.isdigit() and 1 <= int(choice) <= len(providers):
                selected_provider = providers[int(choice) - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(providers)}")
        except (ValueError, IndexError):
            print("Invalid input. Please try again.")
    
    # Ask for API key
    api_key_var = f"{selected_provider.upper()}_API_KEY"
    current_api_key = current_config.get(api_key_var, "")
    
    if current_api_key:
        use_existing = input(f"Use existing API key for {selected_provider}? (y/n): ").lower()
        if use_existing == 'y':
            api_key = current_api_key
        else:
            api_key = input(f"Enter API key for {selected_provider}: ").strip()
    else:
        api_key = input(f"Enter API key for {selected_provider}: ").strip()
    
    # Ask for model (optional)
    model_var = f"{selected_provider.upper()}_MODEL"
    current_model = current_config.get(model_var, "")
    
    if current_model:
        use_existing = input(f"Use existing model for {selected_provider}? (y/n): ").lower()
        if use_existing == 'y':
            model = current_model
        else:
            model = input(f"Enter model for {selected_provider} (leave empty for default): ").strip()
    else:
        model = input(f"Enter model for {selected_provider} (leave empty for default): ").strip()
    
    # Ask for base URL (for local providers)
    base_url = ""
    if selected_provider == 'local':
        current_base_url = current_config.get("LOCAL_BASE_URL", "")
        if current_base_url:
            use_existing = input("Use existing base URL? (y/n): ").lower()
            if use_existing == 'y':
                base_url = current_base_url
            else:
                base_url = input("Enter base URL for local LLM: ").strip()
        else:
            base_url = input("Enter base URL for local LLM: ").strip()
    
    # Save configuration to .env file
    with open(env_file, 'w') as f:
        f.write("# Simple Token Burner App Configuration\n")
        f.write(f"# Generated on: {__import__('datetime').datetime.now().isoformat()}\n")
        f.write("\n")
        f.write("# LLM Provider Configuration\n")
        f.write(f"PROVIDER={selected_provider}\n")
        
        if api_key:
            f.write(f"{api_key_var}={api_key}\n")
        
        if model:
            f.write(f"{model_var}={model}\n")
        
        if base_url:
            f.write(f"LOCAL_BASE_URL={base_url}\n")
    
    print(f"\nConfiguration saved to {env_file}")
    print(f"Provider: {selected_provider}")
    if model:
        print(f"Model: {model}")
    if base_url:
        print(f"Base URL: {base_url}")


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
    
    # Load configuration from .env file
    env_config = load_env_config()
    
    # Override with command line arguments if provided
    provider = args.provider
    if 'PROVIDER' in env_config and args.provider == 'mock':
        provider = env_config['PROVIDER']
    
    api_key = args.api_key
    if api_key is None and f"{provider.upper()}_API_KEY" in env_config:
        api_key = env_config[f"{provider.upper()}_API_KEY"]
    
    model = args.model
    if model is None and f"{provider.upper()}_MODEL" in env_config:
        model = env_config[f"{provider.upper()}_MODEL"]
    
    base_url = args.base_url
    if base_url is None and 'LOCAL_BASE_URL' in env_config:
        base_url = env_config['LOCAL_BASE_URL']
    
    # Handle information requests
    if args.list_prompts:
        list_prompts()
        return
    
    if args.list_categories:
        list_categories()
        return
    
    # Create configuration
    config = AgentConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        execution_mode=args.mode,
        categories=args.categories,
        max_prompts=args.max_prompts,
        delay_between_prompts=args.delay,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        log_dir=args.log_dir,
        enable_console_logging=not args.no_console,
        enable_file_logging=not args.no_file,
        custom_prompts=args.custom_prompts or []
    )
    
    # Create and run agent
    agent = SimpleAgent(config)
    
    if args.custom_prompts:
        print(f"Running {len(args.custom_prompts)} custom prompts...")
        agent.run_custom_prompts(args.custom_prompts)
    else:
        print("Starting Simple Token Burner App...")
        print(f"Provider: {provider}")
        print(f"Model: {model or 'default'}")
        print(f"Mode: {args.mode}")
        print(f"Categories: {', '.join(args.categories)}")
        
        if args.max_prompts:
            print(f"Max prompts: {args.max_prompts}")
        else:
            print(f"Max prompts: all available ({len(ALL_PROMPTS)})")
        
        print(f"Delay between prompts: {args.delay}s")
        print(f"Log directory: {args.log_dir}")
        print("-" * 50)
        
        agent.run()


if __name__ == "__main__":
    main()