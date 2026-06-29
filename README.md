# Simple Agent App

A standalone Python application that repeatedly runs prompts against an LLM and logs comprehensive metrics including prompt hashing, response times, token usage, and more.

## Features

- **Multiple LLM Providers**: Support for OpenAI, Anthropic, local LLMs, and a mock provider for testing
- **Comprehensive Logging**: Logs all request/response metrics, including prompt hashing
- **Prompt Library**: Includes computer-generated prompts of various sizes (small, medium, large, XL) that exercise different reasoning capabilities
- **Flexible Execution**: Multiple execution modes (sequential, random, categorical, custom)
- **Detailed Metrics**: Tracks response times, token usage, finish reasons, and errors
- **Structured Output**: Logs to both console and files (CSV for metrics, JSONL for detailed responses)

## Installation

```bash
# Clone the repository
git clone https://github.com/astevko/simple_agent_app.git
cd simple_agent_app

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For specific providers, install additional packages:
pip install openai      # For OpenAI
pip install anthropic   # For Anthropic
```

## Usage

### Basic Usage

```bash
# Run with mock provider (default)
python main.py

# Run with OpenAI
python main.py --provider openai --api-key YOUR_API_KEY

# Run with Anthropic
python main.py --provider anthropic --api-key YOUR_API_KEY
```

### Command Line Options

```bash
# List available prompts
python main.py --list-prompts

# List prompt categories
python main.py --list-categories

# Run specific categories
python main.py --categories small medium

# Run in random mode
python main.py --mode random

# Limit number of prompts
python main.py --max-prompts 10

# Add delay between prompts
python main.py --delay 1.0

# Use custom prompts
python main.py --custom-prompts "What is AI?" "Explain machine learning"

# Disable console logging
python main.py --no-console

# Change log directory
python main.py --log-dir my_logs
```

### All Options

```
--provider PROVIDER       LLM provider: openai, anthropic, local, mock (default: mock)
--model MODEL             Model to use (default: provider-specific default)
--api-key API_KEY         API key for the provider
--base-url BASE_URL       Base URL for local LLM providers
--mode MODE               Execution mode: sequential, random, categorical, custom (default: sequential)
--categories CATEGORIES   Categories of prompts to use: small, medium, large, xl (default: all)
--max-prompts MAX_PROMPTS Maximum number of prompts to execute
--delay DELAY             Delay between prompts in seconds (default: 0)
--max-tokens MAX_TOKENS   Maximum tokens in response (default: 1000)
--temperature TEMPERATURE Temperature for response generation (default: 0.7)
--log-dir LOG_DIR         Directory for log files (default: logs)
--no-console              Disable console logging
--no-file                 Disable file logging
--custom-prompts PROMPTS  Custom prompts to execute
--list-prompts            List all available prompts and exit
--list-categories         List prompt categories and exit
```

## Project Structure

```
simple_agent_app/
├── main.py                      # Main entry point
├── requirements.txt             # Dependencies
├── README.md                    # This file
└── simple_agent_app/
    ├── __init__.py
    ├── prompts.py               # Prompt library
    ├── llm_client.py            # LLM client for various providers
    ├── logger.py                # Comprehensive logging module
    └── agent.py                 # Main agent class
```

## Prompt Categories

The application includes prompts in four categories:

1. **Small**: Simple questions requiring basic knowledge or calculation
2. **Medium**: Moderate complexity questions requiring explanation or analysis
3. **Large**: Complex questions requiring detailed analysis and reasoning
4. **XL**: Very complex questions requiring comprehensive, multi-faceted analysis

## Logging

The application creates two main log files:

1. **metrics.csv**: Contains structured metrics for each prompt execution
   - timestamp, prompt_hash, provider, model, prompt_length, response_length
   - response_time, input_tokens, output_tokens, total_tokens, finish_reason
   - error, category

2. **responses.jsonl**: Contains detailed JSON records for each response
   - Full prompt and response text
   - All metrics and metadata
   - Error information if applicable

## Examples

### Run all prompts sequentially with mock provider
```bash
python main.py
```

### Run 5 random medium prompts with OpenAI
```bash
python main.py --provider openai --api-key YOUR_KEY --mode random --categories medium --max-prompts 5
```

### Run large prompts with 2-second delay between them
```bash
python main.py --categories large --delay 2.0
```

### Run custom prompts
```bash
python main.py --custom-prompts "Explain quantum computing" "What is the meaning of life?"
```

## Development

```bash
# Run tests
pytest

# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
