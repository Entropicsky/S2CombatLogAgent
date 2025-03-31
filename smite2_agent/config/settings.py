"""
Global settings and configuration for the application.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional


class Settings:
    """
    Global application settings.
    """
    
    def __init__(self):
        """Initialize default settings."""
        # API Keys
        self.openai_api_key: Optional[str] = os.getenv('OPENAI_API_KEY')
        
        # Paths
        self.temp_dir: Path = Path(os.getenv('TEMP_DIR', '/tmp/smite2_agent'))
        self.data_dir: Path = Path(os.getenv('DATA_DIR', 'data'))
        
        # Ensure directories exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Database
        self.db_uri_template: str = "file:{path}?mode=ro"
        
        # Agents
        self.model_name: str = os.getenv('OPENAI_MODEL', 'gpt-4')
        self.orchestrator_instructions: str = """
        You are an AI assistant that answers questions about SMITE 2 match logs by coordinating specialized agents and tools.
        You break queries into parts, use the appropriate data tool or agent, and compile a clear, helpful answer with evidence (tables/charts) as needed.
        """
        
        # Tool Settings
        self.max_sql_rows: int = 1000
        self.chart_dpi: int = 300
        self.default_chart_size: tuple = (10, 6)
        
        # Logging
        self.log_level: str = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file: Optional[str] = os.getenv('LOG_FILE')
        
        # Security
        self.enable_read_only_mode: bool = True
        self.query_validation: bool = True
        
        # UI
        self.streamlit_page_title: str = "SMITE 2 Combat Log Analyzer"
        self.streamlit_page_icon: str = "📊"
        self.max_history_length: int = 50  # Number of messages to keep in chat history
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all settings as a dictionary.
        
        Returns:
            Dictionary of all settings
        """
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    def update(self, **kwargs):
        """
        Update settings from keyword arguments.
        
        Args:
            **kwargs: Settings to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"Unknown setting: {key}")
    
    def load_from_env(self):
        """Load settings from environment variables."""
        for key in self.__dict__.keys():
            if key.startswith('_'):
                continue
            
            env_key = f"SMITE2_AGENT_{key.upper()}"
            value = os.getenv(env_key)
            
            if value is not None:
                # Convert to the appropriate type
                current_value = getattr(self, key)
                if isinstance(current_value, bool):
                    setattr(self, key, value.lower() in ('true', 'yes', '1', 'y'))
                elif isinstance(current_value, int):
                    setattr(self, key, int(value))
                elif isinstance(current_value, float):
                    setattr(self, key, float(value))
                elif isinstance(current_value, Path):
                    setattr(self, key, Path(value))
                else:
                    setattr(self, key, value)


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get the global settings instance.
    
    Returns:
        Settings instance
    """
    return settings


def update_settings(**kwargs):
    """
    Update global settings.
    
    Args:
        **kwargs: Settings to update
    """
    settings.update(**kwargs) 