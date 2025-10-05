"""
Metrics tracking for code reviews
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional


class ReviewMetrics:
    """Track review metrics including cost and token usage"""
    
    def __init__(self):
        self.start_time = time.time()
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.api_calls = 0
        self.estimated_cost = 0.0
        self.input_cost = 0.0
        self.output_cost = 0.0
        self.model_name: Optional[str] = None
        self.pricing_info: Optional[Dict[str, float]] = None
        
    def add_api_call(self, usage_metadata: Any, model_pricing: Optional[Dict[str, float]] = None):
        """
        Add metrics from an AI API call
        
        Args:
            usage_metadata: Usage metadata from AI provider
            model_pricing: Dict with 'input_per_million' and 'output_per_million' costs
        """
        self.api_calls += 1
        
        # Store pricing info for reference
        if model_pricing:
            self.pricing_info = model_pricing
        
        # Extract token usage (works for Gemini, Claude, OpenAI with minor variations)
        if hasattr(usage_metadata, 'prompt_token_count'):
            # Gemini format - use API's token counts directly
            input_tokens = usage_metadata.prompt_token_count
            output_tokens = getattr(usage_metadata, 'candidates_token_count', 0)
            total_tokens = usage_metadata.total_token_count  # Trust API's total
            
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.total_tokens += total_tokens
            
            # Debug logging
            print(f"DEBUG: Gemini tokens - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
            
        elif hasattr(usage_metadata, 'input_tokens'):
            # Claude/Anthropic format - use API's token counts directly
            input_tokens = usage_metadata.input_tokens
            output_tokens = usage_metadata.output_tokens
            # Claude doesn't provide total_tokens, calculate it
            total_tokens = input_tokens + output_tokens

            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.total_tokens += total_tokens

            # Debug logging
            print(f"DEBUG: Claude tokens - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
            
        elif hasattr(usage_metadata, 'prompt_tokens'):
            # OpenAI format - use API's token counts directly
            input_tokens = usage_metadata.prompt_tokens
            output_tokens = usage_metadata.completion_tokens
            total_tokens = usage_metadata.total_tokens  # Trust API's total
            
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.total_tokens += total_tokens
        
        # Calculate cost if pricing provided
        if model_pricing:
            self.input_cost = (self.input_tokens / 1_000_000) * model_pricing.get('input_per_million', 0)
            self.output_cost = (self.output_tokens / 1_000_000) * model_pricing.get('output_per_million', 0)
            self.estimated_cost = self.input_cost + self.output_cost
            
            # Debug cost calculation
            print(f"DEBUG: Cost calculation - Input cost: ${self.input_cost:.6f}, Output cost: ${self.output_cost:.6f}, Total: ${self.estimated_cost:.6f}")
    
    def get_duration(self) -> float:
        """Get review duration in seconds"""
        return round(time.time() - self.start_time, 2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        result = {
            'duration_seconds': self.get_duration(),
            'api_calls': self.api_calls,
            'model': self.model_name,
            'tokens': {
                'input': self.input_tokens,
                'output': self.output_tokens,
                'total': self.total_tokens
            },
            'cost': {
                'input_cost_usd': round(self.input_cost, 6),
                'output_cost_usd': round(self.output_cost, 6),
                'total_cost_usd': round(self.estimated_cost, 6)
            },
            'estimated_cost_usd': round(self.estimated_cost, 6),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add pricing info if available
        if self.pricing_info:
            result['pricing'] = {
                'input_per_million_tokens': self.pricing_info.get('input_per_million', 0),
                'output_per_million_tokens': self.pricing_info.get('output_per_million', 0)
            }
        
        return result
    
    def log(self):
        """Log metrics to console"""
        print(f"\n{'='*60}")
        print(f"📊 REVIEW METRICS")
        print(f"{'='*60}")
        print(f"Model: {self.model_name or 'Unknown'}")
        print(f"Duration: {self.get_duration()}s")
        print(f"API Calls: {self.api_calls}")
        print(f"Tokens Used: {self.total_tokens:,} (Input: {self.input_tokens:,}, Output: {self.output_tokens:,})")
        
        # Show detailed cost breakdown
        if self.pricing_info:
            print(f"\nPricing:")
            print(f"  Input: ${self.pricing_info.get('input_per_million', 0):.3f} per 1M tokens")
            print(f"  Output: ${self.pricing_info.get('output_per_million', 0):.3f} per 1M tokens")
            print(f"\nCost Breakdown:")
            print(f"  Input cost:  ${self.input_cost:.6f} USD ({self.input_tokens:,} tokens)")
            print(f"  Output cost: ${self.output_cost:.6f} USD ({self.output_tokens:,} tokens)")
            print(f"  Total cost:  ${self.estimated_cost:.6f} USD")
        else:
            print(f"Estimated Cost: ${self.estimated_cost:.4f} USD")
        
        print(f"{'='*60}\n")