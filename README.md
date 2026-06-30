# Simple Token Burner App

A standalone Python application that repeatedly runs prompts against an LLM and logs comprehensive metrics including prompt hashing, response times, token usage, and more.

## Features

- **Multiple LLM Providers**: Support for OpenAI, Anthropic, local LLMs, a mock provider for testing, and a `router` provider that drives a [Fancy LLM Router](../fancy_llm_router) server
- **Comprehensive Logging**: Logs all request/response metrics, including prompt hashing
- **Prompt Library**: Includes computer-generated prompts of various sizes (small, medium, large, XL) that exercise different reasoning capabilities
- **Flexible Execution**: Multiple execution modes (sequential, random, categorical, custom)
- **Detailed Metrics**: Tracks response times, token usage, finish reasons, and errors
- **Structured Output**: Logs to both console and files (CSV for metrics, JSONL for detailed responses)

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency and environment management.

```bash
# Clone the repository
git clone https://github.com/astevko/simple_token_burner_app.git
cd simple_token_burner_app

# Create the virtual environment and install dependencies
uv sync

# For specific providers, install the optional extras:
uv sync --extra openai      # For OpenAI
uv sync --extra anthropic   # For Anthropic
```

### Environment file (`.env`)

Copy `.env.example` to `.env` and set defaults so you do not need to pass flags every run:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `BURNER_PROVIDER` | LLM provider (`mock`, `router`, `openai`, `anthropic`, `local`) |
| `BURNER_BASE_URL` | Base URL for `router` or `local` providers |
| `BURNER_MODEL` | Model name (`auto`, logical model, or deployment id for router) |
| `BURNER_MAX_PROMPTS` | Maximum prompts to run (omit for all) |
| `BURNER_MODE` | `infer` (production) or `benchmark` (measure all deployments) |
| `BURNER_MEASURE_DEPLOYMENTS` | `all` or comma-separated deployment ids |

CLI flags override `.env` values. The interactive `./run.sh` launcher also reads `.env` to pre-fill prompts.

Example for driving the Fancy LLM Router:

```env
BURNER_PROVIDER=router
BURNER_BASE_URL=http://localhost:8000
BURNER_MODEL=auto
BURNER_MAX_PROMPTS=10
```

Then simply:

```bash
uv run main.py
```

## Usage

### Interactive Launcher

For a guided, menu-driven way to run the app, use the [gum](https://github.com/charmbracelet/gum)-powered launcher:

```bash
./run.sh
```

It prompts you for the provider, mode, categories, and other options, then runs the app via `uv`.

### Driving the Fancy LLM Router

The token burner can send its prompts through a running [Fancy LLM Router](../fancy_llm_router)
server, which routes each prompt to the best configured model and records its own
metrics. This is handy for load-testing the router or comparing routing strategies.

```bash
# 1) In the fancy_llm_router project, start a router (mock models = offline, no API key):
#    uv run fancy-llm -c configs/mock.yaml serve

# 2) Point the token burner at it:
uv run main.py --provider router --base-url http://localhost:8000 --max-prompts 10
```

Notes:
- `--base-url` defaults to `http://localhost:8000` if omitted.
- The burner stays **decoupled from connection details**: it never holds API keys,
  base URLs, protocols, or hosting info. It only names a model (or `auto`); the
  router resolves that to a concrete deployment (source + protocol + wire id).
- Leave `--model` unset (default `auto`) to let the router choose across everything
  by its active strategy. Pass a **logical model name** (e.g. `--model "Qwen/Qwen3-32B"`)
  to route among all sources serving that model, or pin a single source by its
  **deployment id** (e.g. `--model "qwen3-32b@nebius"`). The deployment the router
  actually selected is recorded in the logs.
- The burner posts to the router's `POST /api/v1/complete` endpoint and reads token
  usage from the response.

### Benchmark mode (measure + specialize prompts)

Each catalog prompt has a stable `root_id` (e.g. `small-01`). In **benchmark** mode
the client fetches `GET /api/v1/models`, then sends `intent=measure` with a pinned
deployment per request. The router judges responses, stores baselines in SQLite, and
refactors failing prompts into per-deployment variants.

```bash
# Terminal 1: router
cd ../fancy_llm_router && uv run fancy-llm -c configs/mock.yaml serve

# Terminal 2: benchmark one category across all deployments
uv run main.py --provider router --burner-mode benchmark \
  --categories small --max-prompts 1
```

After benchmark passes, switch to production **infer** mode. Send the same generic
prompt with `root_id`; the router substitutes the specialized variant for the
selected deployment:

```bash
uv run main.py --provider router --burner-mode infer --model auto
```

### Basic Usage

```bash
# Run with mock provider (default)
uv run main.py

# Run with OpenAI
uv run main.py --provider openai --api-key YOUR_API_KEY

# Run with Anthropic
uv run main.py --provider anthropic --api-key YOUR_API_KEY
```

### Command Line Options

```bash
# List available prompts
uv run main.py --list-prompts

# List prompt categories
uv run main.py --list-categories

# Run specific categories
uv run main.py --categories small medium

# Run in random mode
uv run main.py --mode random

# Limit number of prompts
uv run main.py --max-prompts 10

# Add delay between prompts
uv run main.py --delay 1.0

# Use custom prompts
uv run main.py --custom-prompts "What is AI?" "Explain machine learning"

# Disable console logging
uv run main.py --no-console

# Change log directory
uv run main.py --log-dir my_logs
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
simple_token_burner_app/
├── main.py                      # Main entry point
├── pyproject.toml               # Project metadata and dependencies
├── uv.lock                      # Locked dependency versions
├── README.md                    # This file
└── simple_token_burner_app/
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
uv run main.py
```

### Run 5 random medium prompts with OpenAI
```bash
uv run main.py --provider openai --api-key YOUR_KEY --mode random --categories medium --max-prompts 5
```

### Run large prompts with 2-second delay between them
```bash
uv run main.py --categories large --delay 2.0
```

### Run custom prompts
```bash
uv run main.py --custom-prompts "Explain quantum computing" "What is the meaning of life?"
```

## Development

Install the development dependencies (included by default with `uv sync`), then run the tools via `uv run`:

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Format code
uv run black .

# Lint code
uv run flake8 .

# Type checking
uv run mypy .
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
