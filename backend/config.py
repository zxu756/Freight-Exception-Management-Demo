"""
Application configuration settings.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # Application
    app_name: str = "Freight Exception Management Demo"
    app_version: str = "1.0.0"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./freight_demo.db"

    # API
    api_prefix: str = "/api"
    cors_origins: list = ["http://localhost:5173", "http://localhost:3000"]

    # Demo Settings
    demo_auto_play_speed: float = 1.0  # Speed multiplier for auto-play mode
    demo_step_delay_ms: int = 500  # Delay between steps in ms

    # AI Decision Engine
    ai_confidence_threshold: float = 0.85  # Minimum confidence for auto-resolve
    auto_resolve_max_value: float = 5000.0  # Max cargo value for auto-resolve
    high_risk_threshold: int = 60  # Risk score threshold for high risk

    # Weather API
    weather_api_key: str = "37Y5H59434B8AYDHSRRFSBBFH"  # Visual Crossing API key
    weather_api_enabled: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
