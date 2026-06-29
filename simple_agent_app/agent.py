"""
Main agent class that orchestrates prompt execution and logging.
"""

import time
import random
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from .llm_client import LLMClient, LLMProvider
from .prompts import get_prompts_by_category, get_random_prompt, ALL_PROMPTS
from .logger import AgentLogger


class ExecutionMode(Enum):
    """Execution modes for the agent."""
    SEQUENTIAL = "sequential"
    RANDOM = "random"
    CATEGORICAL = "categorical"
    CUSTOM = "custom"


@dataclass
class AgentConfig:
    """Configuration for the agent."""
    provider: str = "mock"
    model: str = None
    api_key: str = None
    base_url: str = None
    execution_mode: str = "sequential"
    categories: List[str] = field(default_factory=lambda: ["small", "medium", "large", "xl"])
    max_prompts: int = None
    delay_between_prompts: float = 0.0
    max_tokens: int = 1000
    temperature: float = 0.7
    log_dir: str = "logs"
    enable_console_logging: bool = True
    enable_file_logging: bool = True
    custom_prompts: List[str] = field(default_factory=list)


class SimpleAgent:
    """
    Main agent class that repeatedly runs prompts and logs the results.
    """
    
    def __init__(self, config: AgentConfig = None):
        """
        Initialize the agent.
        
        Args:
            config: AgentConfig object with configuration settings
        """
        self.config = config or AgentConfig()
        self.logger = AgentLogger(
            log_dir=self.config.log_dir,
            enable_console=self.config.enable_console_logging,
            enable_file=self.config.enable_file_logging
        )
        
        # Initialize LLM client
        self.llm_client = LLMClient(
            provider=self.config.provider,
            api_key=self.config.api_key,
            model=self.config.model,
            base_url=self.config.base_url
        )
        
        # Track execution state
        self.prompts_executed = 0
        self.start_time = None
        self.end_time = None
        
        # Log session start
        self.logger.log_session_start(self._get_session_config_dict())
    
    def _get_session_config_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for logging."""
        config_dict = {
            'provider': self.config.provider,
            'model': self.config.model,
            'execution_mode': self.config.execution_mode,
            'categories': self.config.categories,
            'max_prompts': self.config.max_prompts,
            'delay_between_prompts': self.config.delay_between_prompts,
            'max_tokens': self.config.max_tokens,
            'temperature': self.config.temperature,
            'log_dir': self.config.log_dir
        }
        
        # Don't log API keys
        if self.config.api_key:
            config_dict['api_key'] = "***REDACTED***"
        
        return config_dict
    
    def _get_next_prompt(self) -> Optional[str]:
        """Get the next prompt based on execution mode."""
        mode = ExecutionMode(self.config.execution_mode.lower())
        
        if mode == ExecutionMode.SEQUENTIAL:
            # Get all prompts from configured categories
            all_prompts = []
            for category in self.config.categories:
                prompts = get_prompts_by_category(category)
                all_prompts.extend(prompts)
            
            if self.prompts_executed < len(all_prompts):
                prompt = all_prompts[self.prompts_executed]
                self.prompts_executed += 1
                return prompt
            else:
                return None
                
        elif mode == ExecutionMode.RANDOM:
            # Get random prompt from configured categories
            category = random.choice(self.config.categories)
            return get_random_prompt(category)
            
        elif mode == ExecutionMode.CATEGORICAL:
            # Cycle through categories, getting one prompt from each
            if self.prompts_executed < len(self.config.categories):
                category = self.config.categories[self.prompts_executed % len(self.config.categories)]
                prompts = get_prompts_by_category(category)
                if prompts:
                    # Get a random prompt from the current category
                    prompt = random.choice(prompts)
                    self.prompts_executed += 1
                    return prompt
            return None
            
        elif mode == ExecutionMode.CUSTOM:
            # Use custom prompts
            if self.prompts_executed < len(self.config.custom_prompts):
                prompt = self.config.custom_prompts[self.prompts_executed]
                self.prompts_executed += 1
                return prompt
            else:
                return None
        
        return None
    
    def _get_prompt_category(self, prompt: str) -> str:
        """Determine the category of a prompt."""
        # This is a simple implementation - could be enhanced
        if prompt in ALL_PROMPTS:
            index = ALL_PROMPTS.index(prompt)
            if index < len(get_prompts_by_category('small')):
                return 'small'
            elif index < len(get_prompts_by_category('small')) + len(get_prompts_by_category('medium')):
                return 'medium'
            elif index < len(get_prompts_by_category('small')) + len(get_prompts_by_category('medium')) + len(get_prompts_by_category('large')):
                return 'large'
            else:
                return 'xl'
        return 'custom'
    
    def execute_prompt(self, prompt: str = None, category: str = None) -> Any:
        """
        Execute a single prompt.
        
        Args:
            prompt: Specific prompt to execute (if None, gets next from queue)
            category: Category for the prompt (for logging)
            
        Returns:
            LLMResponse from the LLM client
        """
        if prompt is None:
            prompt = self._get_next_prompt()
        
        if prompt is None:
            self.logger.logger.info("No more prompts to execute.")
            return None
        
        if category is None:
            category = self._get_prompt_category(prompt)
        
        self.logger.logger.info(f"Executing prompt (category: {category}): {prompt[:100]}...")
        
        # Execute the prompt
        response = self.llm_client.execute_prompt(
            prompt=prompt,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature
        )
        
        # Log the execution
        self.logger.log_prompt_execution(response, category)
        
        # Add delay if configured
        if self.config.delay_between_prompts > 0:
            time.sleep(self.config.delay_between_prompts)
        
        return response
    
    def run(self):
        """Run the agent to execute prompts repeatedly."""
        self.start_time = time.time()
        
        try:
            while True:
                # Check if we've reached the maximum number of prompts
                if self.config.max_prompts and self.prompts_executed >= self.config.max_prompts:
                    self.logger.logger.info(f"Reached maximum prompts limit: {self.config.max_prompts}")
                    break
                
                # Get and execute the next prompt
                prompt = self._get_next_prompt()
                if prompt is None:
                    self.logger.logger.info("No more prompts available.")
                    break
                
                self.execute_prompt(prompt)
                
        except KeyboardInterrupt:
            self.logger.logger.info("Agent stopped by user.")
        except Exception as e:
            self.logger.log_error(e, "Agent execution")
        finally:
            self.end_time = time.time()
            self._finalize_session()
    
    def run_custom_prompts(self, prompts: List[str]):
        """Run a list of custom prompts."""
        self.config.custom_prompts = prompts
        self.config.execution_mode = "custom"
        self.run()
    
    def _finalize_session(self):
        """Finalize the session and log statistics."""
        duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        stats = self.logger.get_session_stats()
        stats.update({
            'session_duration': f"{duration:.2f}s",
            'prompts_per_second': self.prompts_executed / duration if duration > 0 else 0
        })
        
        self.logger.log_session_end(stats)
    
    def reset(self):
        """Reset the agent state."""
        self.prompts_executed = 0
        self.start_time = None
        self.end_time = None