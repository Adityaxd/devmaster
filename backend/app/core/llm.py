"""
LLM Provider Configuration

This module handles the configuration and initialization of LLM providers
for the DevMaster platform.
"""

import os
from enum import Enum
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field


class LLMProvider(str, Enum):
    """Available LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"  # For testing


class LLMConfig(BaseSettings):
    """Configuration for LLM providers."""
    
    # Provider selection
    provider: LLMProvider = Field(
        default=LLMProvider.MOCK,
        description="The LLM provider to use"
    )
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(
        default=None,
        env="OPENAI_API_KEY",
        description="OpenAI API key"
    )
    openai_model: str = Field(
        default="gpt-4-turbo-preview",
        description="OpenAI model to use"
    )
    openai_temperature: float = Field(
        default=0.7,
        description="Temperature for OpenAI responses"
    )
    
    # Anthropic Configuration
    anthropic_api_key: Optional[str] = Field(
        default=None,
        env="ANTHROPIC_API_KEY",
        description="Anthropic API key"
    )
    anthropic_model: str = Field(
        default="claude-3-opus-20240229",
        description="Anthropic model to use"
    )
    anthropic_max_tokens: int = Field(
        default=4096,
        description="Max tokens for Anthropic responses"
    )
    
    # General Configuration
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for LLM calls"
    )
    timeout: int = Field(
        default=60,
        description="Timeout in seconds for LLM calls"
    )
    
    # Cost optimization
    use_cheap_model_for_classification: bool = Field(
        default=True,
        description="Use cheaper models for simple classification tasks"
    )
    cheap_openai_model: str = Field(
        default="gpt-3.5-turbo",
        description="Cheaper OpenAI model for simple tasks"
    )
    cheap_anthropic_model: str = Field(
        default="claude-3-haiku-20240307",
        description="Cheaper Anthropic model for simple tasks"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra environment variables


# Global instance
llm_config = LLMConfig()


class LLMClient:
    """
    Unified interface for interacting with LLM providers.
    
    This class provides a consistent API regardless of the underlying provider.
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize the LLM client with the given configuration."""
        self.config = config or llm_config
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the appropriate LLM client based on configuration."""
        if self.config.provider == LLMProvider.OPENAI:
            if not self.config.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.config.openai_api_key)
            except ImportError:
                raise ImportError("OpenAI package not installed. Run: pip install openai")
            
        elif self.config.provider == LLMProvider.ANTHROPIC:
            if not self.config.anthropic_api_key:
                raise ValueError("Anthropic API key not configured")
            
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)
            except ImportError:
                raise ImportError("Anthropic package not installed. Run: pip install anthropic")
            
        elif self.config.provider == LLMProvider.MOCK:
            self._client = MockLLMClient()
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_cheap_model: bool = False
    ) -> str:
        """
        Generate a completion from the LLM.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens
            use_cheap_model: Use cheaper model for simple tasks
            
        Returns:
            The LLM response as a string
        """
        if self.config.provider == LLMProvider.OPENAI:
            return await self._complete_openai(
                prompt, system_prompt, temperature, max_tokens, use_cheap_model
            )
        elif self.config.provider == LLMProvider.ANTHROPIC:
            return await self._complete_anthropic(
                prompt, system_prompt, temperature, max_tokens, use_cheap_model
            )
        elif self.config.provider == LLMProvider.MOCK:
            return await self._complete_mock(prompt, system_prompt)
        
        raise ValueError(f"Unknown provider: {self.config.provider}")
    
    async def _complete_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        use_cheap_model: bool
    ) -> str:
        """Complete using OpenAI."""
        model = (
            self.config.cheap_openai_model 
            if use_cheap_model and self.config.use_cheap_model_for_classification
            else self.config.openai_model
        )
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature or self.config.openai_temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    async def _complete_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        use_cheap_model: bool
    ) -> str:
        """Complete using Anthropic."""
        model = (
            self.config.cheap_anthropic_model 
            if use_cheap_model and self.config.use_cheap_model_for_classification
            else self.config.anthropic_model
        )
        
        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens or self.config.anthropic_max_tokens,
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        if temperature is not None:
            kwargs["temperature"] = temperature
        
        response = await self._client.messages.create(**kwargs)
        
        return response.content[0].text
    
    async def _complete_mock(self, prompt: str, system_prompt: Optional[str]) -> str:
        """Mock completion for testing."""
        return self._client.complete(prompt, system_prompt)


class MockLLMClient:
    """Mock LLM client for testing without API calls."""
    
    def complete(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate mock responses based on the prompt."""
        prompt_lower = prompt.lower()
        
        # Intent classification mocks
        if "intent" in prompt_lower or "classify" in prompt_lower:
            if "blog" in prompt_lower or "post" in prompt_lower:
                return "CODE_GENERATION"
            elif "hello" in prompt_lower or "help" in prompt_lower:
                return "CHAT"
            return "UNKNOWN"
        
        # Code generation mocks
        if "generate" in prompt_lower and "sql" in prompt_lower:
            return """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
        
        # Default response
        return "This is a mock response for testing purposes."


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the singleton LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def configure_llm(
    provider: Optional[LLMProvider] = None,
    **kwargs
) -> None:
    """
    Configure the LLM client with new settings.
    
    Args:
        provider: The LLM provider to use
        **kwargs: Additional configuration options
    """
    global _llm_client
    
    # Update configuration
    if provider:
        llm_config.provider = provider
    
    for key, value in kwargs.items():
        if hasattr(llm_config, key):
            setattr(llm_config, key, value)
    
    # Reinitialize client
    _llm_client = LLMClient(llm_config)
