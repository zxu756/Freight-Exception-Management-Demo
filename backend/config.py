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

    # 全局订单量缩放：目标 ~18000 票级订单/月（海陆空合计 ~600/天）
    order_scale: float = 0.094
    # 异常注入缩放：目标异常率 8%-12%（最多不超过 12%）
    exception_scale: float = 1.8

    # Database
    database_url: str = "sqlite:///./freight_demo.db"

    # API
    api_prefix: str = "/api"
    cors_origins: list = ["http://localhost:5173", "http://localhost:3000"]

    # Air Cargo Live Simulator
    # 实时空运模拟器
    air_sim_enabled: bool = True           # Start simulator on backend startup
    air_sim_speed: float = 1.0             # Simulation speed multiplier (1x = real time)
    air_sim_tick_seconds: float = 5.0      # Simulator thread tick interval (real seconds)
    air_sim_retention_hours: float = 48.0  # Data retention window (sim hours)

    # Road Freight Live Simulator
    # 实时陆运模拟器
    road_sim_enabled: bool = True          # Start simulator on backend startup
    road_sim_speed: float = 1.0            # Simulation speed multiplier
    road_sim_tick_seconds: float = 5.0     # Simulator thread tick interval (real seconds)
    road_sim_retention_hours: float = 48.0  # Data retention window (sim hours)

    # Rail Freight Live Simulator
    # 实时铁路模拟器（Scenario 4: road, rail and sea）
    rail_sim_enabled: bool = True          # Start simulator on backend startup
    rail_sim_speed: float = 1.0
    rail_sim_tick_seconds: float = 5.0
    rail_sim_retention_hours: float = 48.0

    # 各方式订单量校准系数（订单总量目标 ~15-18k 票/月：陆 7k / 空 5k / 海 2.5k / 铁 2.5k）
    road_scale: float = 0.15
    air_scale: float = 0.8
    sea_scale: float = 0.6
    rail_scale: float = 1.0

    # PortConnect API (real NZ port vessel schedules)
    # PortConnect 新西兰港口船舶时刻表 API
    portconnect_api_enabled: bool = True   # Fetch real schedules at startup (falls back to local JSON)
    portconnect_api_key: str = "56e067a235704e00b246de774f557d01"

    # Sea Freight Live Simulator
    # 实时海运模拟器
    sea_sim_enabled: bool = True           # Start simulator on backend startup
    sea_sim_speed: float = 1.0             # Simulation speed multiplier
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
