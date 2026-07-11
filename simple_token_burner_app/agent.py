"""
Main agent class that orchestrates prompt execution and logging.
"""

import time
import random
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from .llm_client import LLMClient, LLMResponse
from .prompts import (
    ALL_PROMPTS,
    PROMPT_CATALOG,
    get_prompts_by_category,
    get_random_prompt,
    get_prompt_catalog,
    get_response_budget,
    get_system_prompt,
    get_token_cap,
    get_stop_sequences,
)
from .logger import AgentLogger


class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    RANDOM = "random"
    CATEGORICAL = "categorical"
    CUSTOM = "custom"


@dataclass
class AgentConfig:
    """Configuration for the agent."""

    # LiteLLM model string, e.g. "openai/gpt-4o-mini", "anthropic/claude-sonnet-4-20250514"
    model: str = "openai/mock-model"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    execution_mode: str = "sequential"
    categories: List[str] = field(default_factory=lambda: ["small", "medium", "large", "xl"])
    max_prompts: Optional[int] = None
    delay_between_prompts: float = 0.0
    # None = use per-category response_budget from catalog
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    log_dir: str = "logs"
    enable_console_logging: bool = True
    enable_file_logging: bool = True
    custom_prompts: List[str] = field(default_factory=list)
    burner_mode: str = "infer"
    benchmark_run_id: Optional[str] = None
    # legacy — kept for backward compat with CLI callers that still pass provider=
    provider: str = "mock"
    measure_deployments: str = "all"


class SimpleAgent:
    """Orchestrates prompt execution using a LiteLLM-backed LLMClient."""

    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self.logger = AgentLogger(
            log_dir=self.config.log_dir,
            enable_console=self.config.enable_console_logging,
            enable_file=self.config.enable_file_logging,
        )

        self.llm_client = LLMClient(
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            burner_mode=self.config.burner_mode,
            benchmark_run_id=self.config.benchmark_run_id,
        )

        self.prompts_executed = 0
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        self.logger.log_session_start(self._session_config_dict())

    # ------------------------------------------------------------------
    # Config / prompt helpers
    # ------------------------------------------------------------------

    def _session_config_dict(self) -> Dict[str, Any]:
        d = {
            "model": self.config.model,
            "burner_mode": self.config.burner_mode,
            "execution_mode": self.config.execution_mode,
            "categories": self.config.categories,
            "max_prompts": self.config.max_prompts,
            "delay_between_prompts": self.config.delay_between_prompts,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "log_dir": self.config.log_dir,
        }
        if self.config.api_key:
            d["api_key"] = "***REDACTED***"
        return d

    def _get_next_prompt(self) -> Optional[str]:
        mode = ExecutionMode(self.config.execution_mode.lower())

        if mode == ExecutionMode.SEQUENTIAL:
            all_prompts: List[str] = []
            for cat in self.config.categories:
                all_prompts.extend(get_prompts_by_category(cat))
            if self.prompts_executed < len(all_prompts):
                prompt = all_prompts[self.prompts_executed]
                self.prompts_executed += 1
                return prompt
            return None

        elif mode == ExecutionMode.RANDOM:
            category = random.choice(self.config.categories)
            return get_random_prompt(category)

        elif mode == ExecutionMode.CATEGORICAL:
            category = self.config.categories[self.prompts_executed % len(self.config.categories)]
            prompts = get_prompts_by_category(category)
            if prompts:
                self.prompts_executed += 1
                return random.choice(prompts)
            return None

        elif mode == ExecutionMode.CUSTOM:
            if self.prompts_executed < len(self.config.custom_prompts):
                prompt = self.config.custom_prompts[self.prompts_executed]
                self.prompts_executed += 1
                return prompt
            return None

        return None

    def _get_prompt_category(self, prompt: str) -> str:
        from .prompts import PROMPT_CATEGORIES
        for cat, texts in PROMPT_CATEGORIES.items():
            if prompt in texts or prompt.strip() in [t.strip() for t in texts]:
                return cat
        return "custom"

    def _lookup_catalog_entry(self, prompt: str) -> Dict[str, Any]:
        stripped = prompt.strip()
        for entry in PROMPT_CATALOG:
            if entry["text"] == stripped:
                return entry
        return {}

    # ------------------------------------------------------------------
    # Single-prompt execution
    # ------------------------------------------------------------------

    def execute_prompt(
        self,
        prompt: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Optional[LLMResponse]:
        if prompt is None:
            prompt = self._get_next_prompt()
        if prompt is None:
            self.logger.logger.info("No more prompts to execute.")
            return None

        if category is None:
            category = self._get_prompt_category(prompt)

        entry = self._lookup_catalog_entry(prompt)
        root_id = entry.get("root_id")
        expected_answer = entry.get("expected_answer")

        is_benchmark = self.config.burner_mode == "benchmark"

        # System prompt: always applied (infer + benchmark).
        system_prompt = get_system_prompt(category)

        # Token budget.
        base_budget = (
            self.config.max_tokens
            if self.config.max_tokens is not None
            else get_response_budget(category, entry or None)
        )
        if is_benchmark:
            max_tokens = get_token_cap(category, base_budget)
            stop = get_stop_sequences()
        else:
            max_tokens = base_budget
            stop = None

        self.logger.logger.info(
            f"Executing prompt (cat={category}, mode={self.config.burner_mode}): {prompt[:80]}..."
        )

        response = self.llm_client.execute_prompt(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=self.config.temperature if not is_benchmark else 0.0,
            root_id=root_id,
            expected_answer=expected_answer,
            category=category,
            system_prompt=system_prompt,
            stop=stop,
            intent="measure" if is_benchmark else "infer",
        )

        self.logger.log_prompt_execution(response, category)

        if self.config.delay_between_prompts > 0:
            time.sleep(self.config.delay_between_prompts)

        return response

    # ------------------------------------------------------------------
    # Run modes
    # ------------------------------------------------------------------

    def run(self):
        """Run the agent; dispatches to run_benchmark for benchmark mode."""
        if self.config.burner_mode == "benchmark":
            self.run_benchmark()
            return

        self.start_time = time.time()
        try:
            while True:
                if self.config.max_prompts and self.prompts_executed >= self.config.max_prompts:
                    self.logger.logger.info(f"Reached max_prompts={self.config.max_prompts}")
                    break
                prompt = self._get_next_prompt()
                if prompt is None:
                    self.logger.logger.info("No more prompts available.")
                    break
                self.execute_prompt(prompt)
        except KeyboardInterrupt:
            self.logger.logger.info("Agent stopped by user.")
        except Exception as exc:
            self.logger.log_error(exc, "Agent execution")
        finally:
            self.end_time = time.time()
            self._finalize_session()

    def run_benchmark(self):
        """
        Iterate over the catalog and execute each prompt in benchmark mode.

        Each entry is executed once with:
          - temperature=0.0
          - benchmark token cap from get_token_cap()
          - stop sequences from get_stop_sequences()
          - system prompt from get_system_prompt()
        Results are logged via AgentLogger; pass/fail is printed to stdout.
        """
        self.start_time = time.time()
        catalog: List[Dict[str, Any]] = []
        for cat in self.config.categories:
            catalog.extend(get_prompt_catalog(cat))
        if self.config.max_prompts:
            catalog = catalog[: self.config.max_prompts]

        print(
            f"Benchmark run {self.llm_client.benchmark_run_id}: "
            f"{len(catalog)} prompt(s) via model={self.config.model}"
        )

        try:
            for entry in catalog:
                base_budget = (
                    self.config.max_tokens
                    if self.config.max_tokens is not None
                    else get_response_budget(entry["category"], entry)
                )
                max_tokens = get_token_cap(entry["category"], base_budget)

                response = self.llm_client.execute_prompt(
                    prompt=entry["text"],
                    max_tokens=max_tokens,
                    temperature=0.0,
                    root_id=entry["root_id"],
                    expected_answer=entry.get("expected_answer"),
                    category=entry["category"],
                    system_prompt=get_system_prompt(entry["category"]),
                    stop=get_stop_sequences(),
                    intent="measure",
                )
                self.prompts_executed += 1
                self.logger.log_prompt_execution(response, entry["category"])

                # Simple pass/fail check against expected answer.
                expected = entry.get("expected_answer")
                if expected and response.content:
                    passed = expected.lower() in response.content.lower()
                    status = "PASS" if passed else "FAIL"
                elif response.error:
                    status = "ERROR"
                else:
                    status = "OK"
                print(f"  [{entry['root_id']}] {self.config.model}: {status}")
                if response.error:
                    print(f"      {response.error}")

                if self.config.delay_between_prompts > 0:
                    time.sleep(self.config.delay_between_prompts)

        except KeyboardInterrupt:
            self.logger.logger.info("Benchmark stopped by user.")
        except Exception as exc:
            self.logger.log_error(exc, "Benchmark execution")
        finally:
            self.end_time = time.time()
            self._finalize_session()

    def run_custom_prompts(self, prompts: List[str]):
        self.config.custom_prompts = prompts
        self.config.execution_mode = "custom"
        self.run()

    def _finalize_session(self):
        duration = (self.end_time - self.start_time) if self.start_time and self.end_time else 0
        stats = self.logger.get_session_stats()
        stats.update(
            {
                "session_duration": f"{duration:.2f}s",
                "prompts_per_second": self.prompts_executed / duration if duration > 0 else 0,
            }
        )
        self.logger.log_session_end(stats)

    def reset(self):
        self.prompts_executed = 0
        self.start_time = None
        self.end_time = None
