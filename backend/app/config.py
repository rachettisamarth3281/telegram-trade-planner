from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import os

class Settings(BaseSettings):
    APP_NAME: str = "Paper Trading Signal Analysis System"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "insecure_dev_secret_key_change_in_production"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./paper_trading.db"

    # Telegram Userbot / Bot API configuration
    TELEGRAM_API_ID: Optional[int] = None
    TELEGRAM_API_HASH: Optional[str] = None
    TELEGRAM_PHONE: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_SESSION_NAME: str = "paper_trader_session"
    TELEGRAM_TARGET_CHANNELS: List[str] = []

    # Market Price Provider
    PRICE_PROVIDER: str = "simulated"  # "simulated", "twelvedata", "yfinance"
    TWELVEDATA_API_KEY: Optional[str] = None

    # Paper Trading Default Rules
    DEFAULT_ACCOUNT_BALANCE: float = 10000.0
    DEFAULT_RISK_PERCENT: float = 1.0  # 1% per trade
    DEFAULT_R_TARGET: float = 2.0      # Default 2R target if TP not supplied
    CONFIGURED_STRATEGY_SL_ENABLED: bool = False  # Strict mode: never invent SL
    DEFAULT_SL_PIPS: float = 30.0     # Only used if strategy SL is explicitly enabled

    # Standard R-multiple targets to calculate automatically
    CALCULATED_R_MULTIPLES: List[float] = [1.0, 1.5, 2.0, 3.0]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

