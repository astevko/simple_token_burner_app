"""
Comprehensive logging module for the Simple Agent App.
"""

import os
import json
import logging
import csv
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


class AgentLogger:
    """Handles all logging for the agent application."""
    
    def __init__(self, log_dir: str = "logs", enable_console: bool = True, enable_file: bool = True):
        """
        Initialize the logger.
        
        Args:
            log_dir: Directory to store log files
            enable_console: Enable console logging
            enable_file: Enable file logging
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.enable_console = enable_console
        self.enable_file = enable_file
        
        # Create logger
        self.logger = logging.getLogger("simple_token_burner_app")
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Add console handler
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # Add file handler
        if enable_file:
            log_file = self.log_dir / f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # CSV file for structured metrics
        self.metrics_file = self.log_dir / "metrics.csv"
        self._initialize_metrics_file()
        
        # JSON file for detailed response logging
        self.responses_file = self.log_dir / "responses.jsonl"
    
    def _initialize_metrics_file(self):
        """Initialize the metrics CSV file with headers."""
        if not self.metrics_file.exists():
            headers = [
                'timestamp', 'prompt_hash', 'provider', 'model', 'prompt_length',
                'response_length', 'response_time', 'input_tokens', 'output_tokens',
                'total_tokens', 'finish_reason', 'error', 'category'
            ]
            with open(self.metrics_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
    
    def log_prompt_execution(self, response: Any, category: str = None):
        """
        Log a prompt execution with all available metrics.
        
        Args:
            response: LLMResponse object from llm_client
            category: Optional category for the prompt
        """
        # Log to console/file
        self.logger.info(f"Prompt executed - Hash: {response.prompt_hash[:8]}... ")
        self.logger.info(f"Provider: {response.provider}, Model: {response.model}")
        self.logger.info(f"Response time: {response.response_time:.2f}s")
        self.logger.info(f"Tokens: {response.input_tokens} in, {response.output_tokens} out, {response.total_tokens} total")
        self.logger.info(f"Finish reason: {response.finish_reason}")
        
        if response.error:
            self.logger.error(f"Error: {response.error}")
        
        # Log metrics to CSV
        metrics = {
            'timestamp': datetime.fromtimestamp(response.timestamp).isoformat(),
            'prompt_hash': response.prompt_hash,
            'provider': response.provider,
            'model': response.model,
            'prompt_length': len(response.raw_response.get('prompt', '') if response.raw_response else ''),
            'response_length': len(response.content),
            'response_time': f"{response.response_time:.4f}",
            'input_tokens': response.input_tokens,
            'output_tokens': response.output_tokens,
            'total_tokens': response.total_tokens,
            'finish_reason': response.finish_reason,
            'error': response.error or '',
            'category': category or ''
        }
        
        with open(self.metrics_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=metrics.keys())
            writer.writerow(metrics)
        
        # Log detailed response to JSONL file
        response_data = {
            'timestamp': datetime.fromtimestamp(response.timestamp).isoformat(),
            'prompt_hash': response.prompt_hash,
            'provider': response.provider,
            'model': response.model,
            'prompt': response.raw_response.get('prompt', '') if response.raw_response else '',
            'response': response.content,
            'metrics': {
                'response_time': response.response_time,
                'input_tokens': response.input_tokens,
                'output_tokens': response.output_tokens,
                'total_tokens': response.total_tokens,
                'finish_reason': response.finish_reason
            },
            'error': response.error,
            'category': category
        }
        
        with open(self.responses_file, 'a') as f:
            f.write(json.dumps(response_data) + '\n')
    
    def log_session_start(self, config: Dict[str, Any]):
        """Log the start of a new session."""
        self.logger.info("=" * 50)
        self.logger.info("NEW SESSION STARTED")
        self.logger.info("=" * 50)
        self.logger.info(f"Configuration: {json.dumps(config, indent=2)}")
        self.logger.info("-" * 50)
    
    def log_session_end(self, stats: Dict[str, Any]):
        """Log the end of a session with statistics."""
        self.logger.info("-" * 50)
        self.logger.info("SESSION ENDED")
        self.logger.info("=" * 50)
        self.logger.info(f"Statistics: {json.dumps(stats, indent=2)}")
        self.logger.info("=" * 50)
    
    def log_error(self, error: Exception, context: str = ""):
        """Log an error with context."""
        self.logger.error(f"Error in {context}: {str(error)}", exc_info=True)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics for the current session from the metrics file."""
        if not self.metrics_file.exists():
            return {}
        
        stats = {
            'total_prompts': 0,
            'successful_prompts': 0,
            'failed_prompts': 0,
            'total_tokens': 0,
            'total_response_time': 0,
            'providers': {},
            'models': {},
            'categories': {}
        }
        
        with open(self.metrics_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats['total_prompts'] += 1
                
                if row.get('error'):
                    stats['failed_prompts'] += 1
                else:
                    stats['successful_prompts'] += 1
                
                stats['total_tokens'] += int(row.get('total_tokens', 0))
                stats['total_response_time'] += float(row.get('response_time', 0))
                
                # Track providers
                provider = row.get('provider', 'unknown')
                stats['providers'][provider] = stats['providers'].get(provider, 0) + 1
                
                # Track models
                model = row.get('model', 'unknown')
                stats['models'][model] = stats['models'].get(model, 0) + 1
                
                # Track categories
                category = row.get('category', 'unknown')
                stats['categories'][category] = stats['categories'].get(category, 0) + 1
        
        # Calculate averages
        if stats['successful_prompts'] > 0:
            stats['avg_tokens_per_prompt'] = stats['total_tokens'] / stats['successful_prompts']
            stats['avg_response_time'] = stats['total_response_time'] / stats['successful_prompts']
        else:
            stats['avg_tokens_per_prompt'] = 0
            stats['avg_response_time'] = 0
        
        return stats
