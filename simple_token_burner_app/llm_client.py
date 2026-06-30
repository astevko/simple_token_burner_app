"""
LLM Client for connecting to various LLM providers and executing prompts.
"""

import os
import time
import json
import hashlib
import uuid
import requests
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    MOCK = "mock"
    ROUTER = "router"  # Drive a Fancy LLM Router API server


@dataclass
class LLMResponse:
    """Data class to store LLM response and metadata."""
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
    measurement: Optional[Dict[str, Any]] = None
    deployment: Optional[str] = None
    root_id: Optional[str] = None


class BurnerMode(Enum):
    """How the client drives the router."""
    INFER = "infer"
    BENCHMARK = "benchmark"


class LLMClient:
    """Client for connecting to LLM services."""
    
    def __init__(
        self,
        provider: str = "mock",
        api_key: str = None,
        model: str = None,
        base_url: str = None,
        burner_mode: str = "infer",
        measure_deployments: str = "all",
        benchmark_run_id: str = None,
        session_id: str = None,
    ):
        """
        Initialize the LLM client.
        
        Args:
            provider: LLM provider (openai, anthropic, local, mock)
            api_key: API key for the provider
            model: Model to use
            base_url: Base URL for local providers
        """
        self.provider = LLMProvider(provider.lower())
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY")
        self.model = model or self._get_default_model()
        self.base_url = base_url
        self.burner_mode = BurnerMode(burner_mode.lower())
        self.measure_deployments = measure_deployments or "all"
        self.benchmark_run_id = benchmark_run_id or str(uuid.uuid4())
        self.session_id = session_id or f"burner-{int(time.time())}"
        self.request_timeout = float(os.getenv("BURNER_REQUEST_TIMEOUT", "0"))
        self.benchmark_optimize = os.getenv("BURNER_BENCHMARK_OPTIMIZE", "true").lower() in (
            "1", "true", "yes",
        )
        self.benchmark_max_revisions = int(os.getenv("BURNER_BENCHMARK_MAX_REVISIONS", "1"))
        self._initialize_client()
    
    def _get_default_model(self) -> str:
        """Get default model for the provider."""
        defaults = {
            LLMProvider.OPENAI: "gpt-3.5-turbo",
            LLMProvider.ANTHROPIC: "claude-3-sonnet-20240229",
            LLMProvider.LOCAL: "llama-3-8b",
            LLMProvider.MOCK: "mock-model",
            LLMProvider.ROUTER: "auto"  # let the router decide
        }
        return defaults.get(self.provider, "unknown")
    
    def _initialize_client(self):
        """Initialize provider-specific client."""
        if self.provider == LLMProvider.OPENAI:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("Please install openai package: pip install openai")
        elif self.provider == LLMProvider.ANTHROPIC:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("Please install anthropic package: pip install anthropic")
        elif self.provider == LLMProvider.LOCAL:
            # For local providers, we'll use HTTP requests
            self.client = None
        elif self.provider == LLMProvider.ROUTER:
            # Talks to a Fancy LLM Router API server over HTTP.
            self.base_url = self.base_url or "http://localhost:8000"
            self.client = None
        elif self.provider == LLMProvider.MOCK:
            # Mock client for testing
            self.client = None
    
    def _generate_prompt_hash(self, prompt: str) -> str:
        """Generate 16-char SHA256 hash (matches router)."""
        return hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:16]

    def list_router_deployments(self) -> List[str]:
        """Fetch deployment ids from the Fancy LLM Router."""
        if self.provider != LLMProvider.ROUTER:
            return []
        url = f"{self.base_url.rstrip('/')}/api/v1/models"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data
        return []

    def _filter_deployments(self, all_deployments: List[str]) -> List[str]:
        if self.measure_deployments.strip().lower() == "all":
            return all_deployments
        wanted = {d.strip() for d in self.measure_deployments.split(",") if d.strip()}
        return [d for d in all_deployments if d in wanted]

    def execute_benchmark_prompt(
        self,
        root_id: str,
        prompt: str,
        expected_answer: Optional[str] = None,
        category: Optional[str] = None,
        max_tokens: int = 256,
        temperature: float = 0.0,
    ) -> List[LLMResponse]:
        """Measure a root prompt across selected router deployments."""
        deployments = self._filter_deployments(self.list_router_deployments())
        results: List[LLMResponse] = []
        for deployment_id in deployments:
            results.append(
                self.execute_prompt(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    root_id=root_id,
                    expected_answer=expected_answer,
                    category=category,
                    deployment_id=deployment_id,
                    intent="measure",
                )
            )
        return results

    def execute_prompt(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        root_id: Optional[str] = None,
        expected_answer: Optional[str] = None,
        category: Optional[str] = None,
        deployment_id: Optional[str] = None,
        intent: Optional[str] = None,
    ) -> LLMResponse:
        """Execute a prompt and return the response with metrics."""
        start_time = time.time()
        prompt_hash = self._generate_prompt_hash(prompt)
        effective_intent = intent or (
            "measure" if self.burner_mode == BurnerMode.BENCHMARK else "infer"
        )

        try:
            if self.provider == LLMProvider.OPENAI:
                response = self._execute_openai_prompt(prompt, max_tokens, temperature)
            elif self.provider == LLMProvider.ANTHROPIC:
                response = self._execute_anthropic_prompt(prompt, max_tokens, temperature)
            elif self.provider == LLMProvider.LOCAL:
                response = self._execute_local_prompt(prompt, max_tokens, temperature)
            elif self.provider == LLMProvider.ROUTER:
                response = self._execute_router_prompt(
                    prompt,
                    max_tokens,
                    temperature,
                    root_id=root_id,
                    expected_answer=expected_answer,
                    category=category,
                    deployment_id=deployment_id,
                    intent=effective_intent,
                    prompt_hash=prompt_hash,
                )
            elif self.provider == LLMProvider.MOCK:
                response = self._execute_mock_prompt(prompt, max_tokens, temperature)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            response_time = time.time() - start_time
            input_tokens, output_tokens, total_tokens = self._calculate_response_metrics(response)

            return LLMResponse(
                content=response.get('content', ''),
                provider=self.provider.value,
                model=response.get('model') or self.model,
                prompt_hash=prompt_hash,
                response_time=response_time,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                finish_reason=response.get('finish_reason', 'unknown'),
                timestamp=time.time(),
                raw_response=response,
                measurement=response.get('measurement'),
                deployment=response.get('deployment'),
                root_id=root_id,
            )

        except Exception as e:
            response_time = time.time() - start_time
            return LLMResponse(
                content="",
                provider=self.provider.value,
                model=deployment_id or self.model,
                prompt_hash=prompt_hash,
                response_time=response_time,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                finish_reason="error",
                timestamp=time.time(),
                error=str(e),
                deployment=deployment_id,
                root_id=root_id,
            )

    def _calculate_response_metrics(self, response: Dict[str, Any]) -> Tuple[int, int, int]:
        """Calculate token usage metrics from response."""
        if self.provider in (LLMProvider.OPENAI, LLMProvider.ROUTER):
            usage = response.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', input_tokens + output_tokens)
        elif self.provider == LLMProvider.ANTHROPIC:
            usage = response.get('usage', {})
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            total_tokens = input_tokens + output_tokens
        else:
            input_tokens = len(response.get('prompt', '').split())
            output_tokens = len(response.get('content', '').split())
            total_tokens = input_tokens + output_tokens

        return input_tokens, output_tokens, total_tokens

    def _execute_openai_prompt(self, prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Execute prompt using OpenAI API."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            n=1,
            stop=None
        )
        
        return {
            'content': response.choices[0].message.content,
            'finish_reason': response.choices[0].finish_reason,
            'usage': dict(response.usage),
            'prompt': prompt
        }
    
    def _execute_anthropic_prompt(self, prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Execute prompt using Anthropic API."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return {
            'content': response.content[0].text,
            'finish_reason': response.stop_reason,
            'usage': {
                'input_tokens': response.usage.input_tokens,
                'output_tokens': response.usage.output_tokens
            },
            'prompt': prompt
        }
    
    def _execute_local_prompt(self, prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Execute prompt using local LLM API."""
        if not self.base_url:
            raise ValueError("Base URL is required for local LLM provider")
        
        payload = {
            'prompt': prompt,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'stream': False
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(f"{self.base_url}/generate", json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        return {
            'content': result.get('generated_text', ''),
            'finish_reason': result.get('stop_reason', 'stop'),
            'usage': {
                'input_tokens': result.get('input_tokens', 0),
                'output_tokens': result.get('output_tokens', 0)
            },
            'prompt': prompt
        }
    
    def _execute_router_prompt(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        root_id: Optional[str] = None,
        expected_answer: Optional[str] = None,
        category: Optional[str] = None,
        deployment_id: Optional[str] = None,
        intent: str = "infer",
        prompt_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute via Fancy LLM Router ``/api/v1/complete``."""
        payload: Dict[str, Any] = {
            'prompt': prompt,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'intent': intent,
            'session_id': self.session_id,
            'prompt_hash': prompt_hash or self._generate_prompt_hash(prompt),
        }
        if root_id:
            payload['root_id'] = root_id
        if expected_answer:
            payload['expected_answer'] = expected_answer
        if category:
            payload['category'] = category
        if intent == "measure":
            payload['benchmark_run_id'] = self.benchmark_run_id
            payload['optimize_on_fail'] = self.benchmark_optimize
            payload['max_revisions'] = self.benchmark_max_revisions
            pin = deployment_id or (
                self.model if self.model and self.model != "auto" else None
            )
            if not pin:
                raise ValueError("benchmark measure requires deployment_id or pinned model")
            payload['model'] = pin
        elif self.model and self.model != "auto":
            payload['model'] = self.model
        if intent == "infer" and root_id:
            payload['root_id'] = root_id

        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f"Bearer {self.api_key}"

        url = f"{self.base_url.rstrip('/')}/api/v1/complete"
        if self.request_timeout > 0:
            timeout = self.request_timeout
        elif intent == "measure":
            timeout = 300.0
        else:
            timeout = 120.0
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        if not response.ok:
            detail = response.text
            try:
                detail = response.json().get("detail", detail)
            except Exception:
                pass
            raise requests.HTTPError(
                f"{response.status_code} Client Error: {detail} for url: {url}",
                response=response,
            )

        result = response.json()
        inner = result.get('response', result)
        choices = inner.get('choices', [])
        content = choices[0].get('text', '') if choices else ''
        finish_reason = choices[0].get('finish_reason', 'stop') if choices else 'stop'

        return {
            'content': content,
            'finish_reason': finish_reason,
            'usage': inner.get('usage', {}),
            'model': result.get('model') or inner.get('model'),
            'deployment': result.get('deployment'),
            'measurement': result.get('measurement'),
            'prompt': prompt,
        }

    def _execute_mock_prompt(self, prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Execute mock prompt for testing purposes."""
        # Simulate processing time
        time.sleep(0.1)
        
        # Generate a mock response based on the prompt
        mock_responses = [
            f"This is a mock response to: {prompt[:50]}...",
            "I am a mock AI assistant. In a real scenario, I would provide a detailed response to your prompt.",
            f"Mock response generated for prompt with hash: {hashlib.sha256(prompt.encode()).hexdigest()[:8]}",
            "This is a simulated response that demonstrates the functionality without actual LLM calls."
        ]
        
        import random
        content = random.choice(mock_responses)
        
        return {
            'content': content,
            'finish_reason': 'stop',
            'usage': {
                'input_tokens': len(prompt.split()),
                'output_tokens': len(content.split())
            },
            'prompt': prompt
        }
