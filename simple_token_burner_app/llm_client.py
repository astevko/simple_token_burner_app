"""
LLM Client — all LLM calls go through LiteLLM.

Provider + model are supplied as a single LiteLLM model string, e.g.:
  "openai/gpt-4o-mini"
  "anthropic/claude-sonnet-4-20250514"
  "ollama/llama3"
  "mock/mock-model"   → offline stub, no credentials required

smart_llm telemetry is captured automatically via LurkLogger, which is
registered as a LiteLLM callback at client init time.
"""

from __future__ import annotations

import hashlib
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import litellm


@dataclass
class LLMResponse:
    """Structured result from a single LLM call."""

    content: str
    provider: str
    model: str
    prompt_hash: str
    response_time: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    finish_reason: str
    timestamp: float
    raw_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    root_id: Optional[str] = None


def _hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def _parse_provider(model_string: str) -> str:
    """Return provider portion of a LiteLLM model string."""
    return model_string.split("/")[0] if "/" in model_string else model_string


class LLMClient:
    """
    Thin wrapper around litellm.completion.

    All provider-specific branching is gone.  Pass any LiteLLM model string
    via the ``model`` constructor argument (e.g. ``openai/gpt-4o-mini``).

    LurkLogger is registered once at init time; every call is captured.
    """

    def __init__(
        self,
        model: str = "mock/mock-model",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        burner_mode: str = "infer",
        session_id: Optional[str] = None,
        benchmark_run_id: Optional[str] = None,
        # legacy args accepted but unused — kept for backward compat
        provider: str = "mock",
        measure_deployments: str = "all",
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.burner_mode = burner_mode
        self.session_id = session_id or f"burner-{int(time.time())}"
        self.benchmark_run_id = benchmark_run_id or str(uuid.uuid4())

        # Set LiteLLM API key / base_url if provided.
        if api_key:
            litellm.api_key = api_key
        if base_url:
            litellm.api_base = base_url

        # Silence LiteLLM's noisy success messages; keep errors.
        litellm.success_callback = []
        litellm.set_verbose = False

        # Register LurkLogger (no-op if smart_llm is not installed).
        self._register_lurk_logger()

    # ------------------------------------------------------------------
    # LurkLogger registration
    # ------------------------------------------------------------------

    def _register_lurk_logger(self) -> None:
        try:
            from smart_llm.lurk.logger import LurkLogger
            existing = [
                cb for cb in (litellm.callbacks or [])
                if isinstance(cb, LurkLogger)
            ]
            if not existing:
                litellm.callbacks = list(litellm.callbacks or []) + [LurkLogger()]
        except ImportError:
            pass  # smart_llm not installed; lurk capture is silently skipped
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Could not register LurkLogger: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_prompt(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        root_id: Optional[str] = None,
        expected_answer: Optional[str] = None,
        category: Optional[str] = None,
        system_prompt: Optional[str] = None,
        stop: Optional[List[str]] = None,
        intent: Optional[str] = None,
    ) -> LLMResponse:
        """Execute a single prompt and return a structured response."""
        start_time = time.time()
        prompt_hash = _hash_prompt(prompt)
        effective_intent = intent or (
            "measure" if self.burner_mode == "benchmark" else "infer"
        )
        provider = _parse_provider(self.model)

        # --- Mock: offline stub, no credentials needed ---
        if provider == "mock":
            return self._execute_mock_prompt(
                prompt=prompt,
                root_id=root_id,
                prompt_hash=prompt_hash,
                start_time=start_time,
            )

        # --- All other providers go through LiteLLM ---
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Build LiteLLM metadata so LurkLogger captures full identity.
        metadata: Dict[str, Any] = {
            "session_id": self.session_id,
            "intent": effective_intent,
        }
        if root_id:
            metadata["template_id"] = root_id
        if category:
            metadata["category"] = category
        if self.burner_mode == "benchmark":
            metadata["trace_id"] = self.benchmark_run_id
        if expected_answer is not None:
            metadata["expected_answer"] = expected_answer

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "metadata": metadata,
        }
        if stop:
            kwargs["stop"] = stop
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url:
            kwargs["base_url"] = self.base_url

        try:
            response = litellm.completion(**kwargs)
            response_time = time.time() - start_time

            choice = response.choices[0]
            content = choice.message.content or ""
            finish_reason = choice.finish_reason or "stop"
            usage = response.usage or {}
            input_tokens = getattr(usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(usage, "completion_tokens", 0) or 0
            total_tokens = getattr(usage, "total_tokens", input_tokens + output_tokens) or 0
            model_used = response.model or self.model

            return LLMResponse(
                content=content,
                provider=provider,
                model=model_used,
                prompt_hash=prompt_hash,
                response_time=response_time,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                finish_reason=finish_reason,
                timestamp=time.time(),
                raw_response={"prompt": prompt, "response": content},
                root_id=root_id,
            )

        except Exception as exc:
            response_time = time.time() - start_time
            return LLMResponse(
                content="",
                provider=provider,
                model=self.model,
                prompt_hash=prompt_hash,
                response_time=response_time,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                finish_reason="error",
                timestamp=time.time(),
                error=str(exc),
                root_id=root_id,
            )

    # ------------------------------------------------------------------
    # Offline mock provider
    # ------------------------------------------------------------------

    def _execute_mock_prompt(
        self,
        prompt: str,
        root_id: Optional[str] = None,
        prompt_hash: Optional[str] = None,
        start_time: Optional[float] = None,
    ) -> LLMResponse:
        if start_time is None:
            start_time = time.time()
        if prompt_hash is None:
            prompt_hash = _hash_prompt(prompt)

        time.sleep(0.1)  # simulate latency
        content = random.choice([
            f"This is a mock response to: {prompt[:50]}...",
            "Mock AI: In a real scenario, I would provide a detailed response.",
            f"[mock] prompt_hash={prompt_hash}",
            "Simulated response — no API credentials required.",
        ])
        word_count = len(prompt.split())
        return LLMResponse(
            content=content,
            provider="mock",
            model="mock-model",
            prompt_hash=prompt_hash,
            response_time=time.time() - start_time,
            input_tokens=word_count,
            output_tokens=len(content.split()),
            total_tokens=word_count + len(content.split()),
            finish_reason="stop",
            timestamp=time.time(),
            raw_response={"prompt": prompt, "response": content},
            root_id=root_id,
        )
