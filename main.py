#!/usr/bin/env python3
"""
Simple Agent App - Main entry point

This application repeatedly runs prompts against an LLM and logs comprehensive metrics
including prompt hashing, response times, token usage, and more.
"""

import argparse
import os
import sys
from typing import List

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simple_agent_app.agent import SimpleAgent, AgentConfig, ExecutionMode
from simple_agent_app.prompts import ALL_PROMPTS
from simple_agent_app.llm_client import LLMProvider


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Simple Agent App - Run LLM prompts with comprehensive logging"
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
    
    from simple_agent_app.prompts import PROMPT_CATEGORIES
    
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
    
    from simple_agent_app.prompts import PROMPT_CATEGORIES
    
    for category, prompts in PROMPT_CATEGORIES.items():
        print(f"  {category}: {len(prompts)} prompts")
    
    print(f"\nTotal: {len(ALL_PROMPTS)} prompts across all categories")


def main():
    """Main function."""
    args = parse_arguments()
    
    # Handle information requests
    if args.list_prompts:
        list_prompts()
        return
    
    if args.list_categories:
        list_categories()
        return
    
    # Create configuration
    config = AgentConfig(
        provider=args.provider,
        model=args.model,
        api_key=args.api_key,
        base_url=args.base_url,
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
        print("Starting Simple Agent App...")
        print(f"Provider: {args.provider}")
        print(f"Model: {args.model or 'default'}")
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
