"""
LLM Client for connecting to various LLM providers and executing prompts.
"""

import os
import time
import json
import hashlib
import requests
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    MOCK = "mock"


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


class LLMClient:
    """Client for connecting to LLM services."""
    
    def __init__(self, provider: str = "mock", api_key: str = None, model: str = None, base_url: str = None):
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
        
        # Initialize provider-specific clients
        self._initialize_client()
    
    def _get_default_model(self) -> str:
        """Get default model for the provider."""
        defaults = {
            LLMProvider.OPENAI: "gpt-3.5-turbo",
            LLMProvider.ANTHROPIC: "claude-3-sonnet-20240229",
            LLMProvider.LOCAL: "llama-3-8b",
            LLMProvider.MOCK: "mock-model"
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
        elif self.provider == LLMProvider.MOCK:
            # Mock client for testing
            self.client = None
    
    def _generate_prompt_hash(self, prompt: str) -> str:
        """Generate SHA256 hash of the prompt."""
        return hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    
    def _calculate_response_metrics(self, response: Dict[str, Any]) -> Tuple[int, int, int]:
        """Calculate token usage metrics from response."""
        if self.provider == LLMProvider.OPENAI:
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
            # For local and mock providers, estimate based on content length
            input_tokens = len(response.get('prompt', '').split())
            output_tokens = len(response.get('content', '').split())
            total_tokens = input_tokens + output_tokens
        
        return input_tokens, output_tokens, total_tokens
    
    def execute_prompt(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> LLMResponse:
        """
        Execute a prompt and return the response with metrics.
        
        Args:
            prompt: The prompt to execute
            max_tokens: Maximum number of tokens in response
            temperature: Temperature for response generation
            
        Returns:
            LLMResponse containing the response and metadata
        """
        start_time = time.time()
        prompt_hash = self._generate_prompt_hash(prompt)
        
        try:
            if self.provider == LLMProvider.OPENAI:
                response = self._execute_openai_prompt(prompt, max_tokens, temperature)
            elif self.provider == LLMProvider.ANTHROPIC:
                response = self._execute_anthropic_prompt(prompt, max_tokens, temperature)
            elif self.provider == LLMProvider.LOCAL:
                response = self._execute_local_prompt(prompt, max_tokens, temperature)
            elif self.provider == LLMProvider.MOCK:
                response = self._execute_mock_prompt(prompt, max_tokens, temperature)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            response_time = time.time() - start_time
            input_tokens, output_tokens, total_tokens = self._calculate_response_metrics(response)
            
            return LLMResponse(
                content=response.get('content', ''),
                provider=self.provider.value,
                model=self.model,
                prompt_hash=prompt_hash,
                response_time=response_time,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                finish_reason=response.get('finish_reason', 'unknown'),
                timestamp=time.time(),
                raw_response=response
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return LLMResponse(
                content="",
                provider=self.provider.value,
                model=self.model,
                prompt_hash=prompt_hash,
                response_time=response_time,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                finish_reason="error",
                timestamp=time.time(),
                error=str(e)
            )
    
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
