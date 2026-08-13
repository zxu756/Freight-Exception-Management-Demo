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

    # Air Cargo Live Simulator
    # 实时空运模拟器
    air_sim_enabled: bool = True           # Start simulator on backend startup
    air_sim_speed: float = 60.0            # Simulation speed multiplier (60x = 1 real sec = 1 sim minute)
    air_sim_tick_seconds: float = 5.0      # Simulator thread tick interval (real seconds)
    air_sim_retention_hours: float = 48.0  # Data retention window (sim hours)

    # Road Freight Live Simulator
    # 实时陆运模拟器
    road_sim_enabled: bool = True          # Start simulator on backend startup
    road_sim_speed: float = 60.0           # Simulation speed multiplier
    road_sim_tick_seconds: float = 5.0     # Simulator thread tick interval (real seconds)
    road_sim_retention_hours: float = 48.0  # Data retention window (sim hours)

    # PortConnect API (real NZ port vessel schedules)
    # PortConnect 新西兰港口船舶时刻表 API
    portconnect_api_enabled: bool = True   # Fetch real schedules at startup (falls back to local JSON)
    portconnect_api_key: str = "56e067a235704e00b246de774f557d01"

    # Sea Freight Live Simulator
    # 实时海运模拟器
    sea_sim_enabled: bool = True           # Start simulator on backend startup
    sea_sim_speed: float = 60.0            # Simulation speed multiplier
    sea_sim_tick_seconds: float = 5.0      # Simulator thread tick interval (real seconds)
    sea_sim_retention_hours: float = 48.0  # Data retention window (sim hours)

    # LLM (DeepSeek) - AI 对话与诊断增强
    # 配置 DEEPSEEK_API_KEY 环境变量或 .env 后开启
    llm_enabled: bool = False              # Enable LLM features (needs api key)
    llm_api_key: str = ""                  # DeepSeek API key (sk-...)
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
