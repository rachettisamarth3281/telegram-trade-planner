from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, List, Union
import json

class Settings(BaseSettings):
    # Application & Environment
    APP_NAME: str = "Telegram Signal Paper Trading System"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    JSON_LOGS: bool = False
    CORS_ORIGINS: List[str] = Field(default=["*"], description="Allowed CORS origins")

    # Telegram Credentials & Channel Configuration
    TELEGRAM_API_ID: Optional[int] = Field(default=None, description="Telegram API ID from my.telegram.org")
    TELEGRAM_API_HASH: Optional[str] = Field(default=None, description="Telegram API Hash from my.telegram.org")
    TELEGRAM_SESSION: str = Field(default="paper_trading_session", description="Session file name or string")
    TELEGRAM_SOURCE_CHAT_ID: Optional[str] = Field(default=None, description="Primary source chat/channel ID")
    TELEGRAM_PHONE: Optional[str] = Field(default=None, description="Phone number for userbot authentication")
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=None, description="Bot token if running as bot")
    TELEGRAM_MOCK_MODE: bool = Field(default=False, description="Enable mock mode for development without live Telegram connection")
    TELEGRAM_RETRY_ATTEMPTS: int = Field(default=5, description="Max reconnection attempts on Telegram error")
    TELEGRAM_RETRY_DELAY: float = Field(default=3.0, description="Base retry delay in seconds for backoff")

    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./paper_trading.db",
        description="Async database connection URL"
    )

    # Market Data Configuration
    MARKET_DATA_PROVIDER: str = Field(
        default="simulated",
        description="Market data provider name: 'simulated', 'mock', 'mt5', 'twelvedata'"
    )
    PRICE_SNAPSHOT_INTERVAL_SECONDS: float = Field(
        default=5.0,
        description="Minimum interval in seconds between storing price snapshots in DB to prevent excessive writes"
    )
    STALE_PRICE_THRESHOLD_SECONDS: float = Field(
        default=60.0,
        description="Threshold in seconds after which a price tick is considered stale"
    )
    CANDLE_EXECUTION_POLICY: str = Field(
        default="CONSERVATIVE",
        description="Policy when candle touches both SL and TP: 'CONSERVATIVE', 'SL_FIRST', 'TP_FIRST', 'BAR_CLOSE'"
    )
    MT5_ENABLED: bool = Field(
        default=False,
        description="Enable read-only MT5 market data feed (never executes live orders)"
    )
    MT5_PATH: Optional[str] = Field(default=None, description="Path to terminal64.exe for MT5")
    MT5_SERVER: Optional[str] = Field(default=None, description="MT5 broker server name")
    MT5_LOGIN: Optional[int] = Field(default=None, description="MT5 account login number")
    MT5_PASSWORD: Optional[str] = Field(default=None, description="MT5 account password")

    # Risk & SL/TP Rules Configuration
    DEFAULT_TP_R_MULTIPLE: float = Field(
        default=2.0,
        description="Default Take Profit R-multiple target when no provider TP is supplied"
    )
    DEFAULT_R_TARGET: float = Field(
        default=2.0,
        description="Alias for DEFAULT_TP_R_MULTIPLE"
    )
    ALTERNATIVE_TP_R_MULTIPLES: List[float] = Field(
        default=[1.0, 1.5, 2.0, 3.0],
        description="List of alternative R-multiples to compute automatically"
    )
    CALCULATED_R_MULTIPLES: List[float] = Field(
        default=[1.0, 1.5, 2.0, 3.0],
        description="Alias for ALTERNATIVE_TP_R_MULTIPLES"
    )
    MIN_RR: float = Field(
        default=1.5,
        description="Minimum acceptable Risk/Reward Ratio before flagging LOW_RR"
    )

    # Paper Trading Feature Flag (Strictly Simulation)
    PAPER_TRADING_ENABLED: bool = Field(
        default=True,
        description="Flag enabling or disabling virtual paper trade creation"
    )

    # Strategy SL settings
    CONFIGURED_STRATEGY_SL_ENABLED: bool = Field(
        default=False,
        description="Strict zero-assumption mode: false means never invent an SL"
    )
    DEFAULT_SL_PIPS: float = Field(
        default=30.0,
        description="Default pip distance if strategy SL is explicitly enabled"
    )

    # Account Risk Parameters (V1 Trade Planning Platform)
    ACCOUNT_CURRENCY: str = Field(default="INR", description="Default account currency: INR")
    INITIAL_BALANCE: float = Field(default=50000.0, description="Initial starting account balance in INR")
    CURRENT_BALANCE: float = Field(default=50000.0, description="Current account balance in INR")
    DAILY_STARTING_BALANCE: float = Field(default=50000.0, description="Daily starting account balance in INR")
    RISK_PER_TRADE_PCT: float = Field(default=1.0, description="Configured risk per trade percentage (1.0%)")
    MAX_DAILY_RISK_PCT: float = Field(default=3.0, description="Configured maximum daily risk percentage (3.0%)")
    MAX_OPEN_TRADES: int = Field(default=3, description="Maximum open/tracked manual trades")

    # Currency Conversion (V1 Manual Conversion Mode)
    USD_INR_CONVERSION_MODE: str = Field(default="MANUAL", description="Conversion mode: 'MANUAL' or 'AUTO'")
    MANUAL_USD_INR_RATE: float = Field(default=85.00, description="Configurable manual USD/INR exchange rate")

    # Legacy / Backwards-compatible aliases
    INITIAL_ACCOUNT_BALANCE: float = 50000.0
    DEFAULT_ACCOUNT_BALANCE: float = 50000.0
    DEFAULT_RISK_PERCENT: float = 1.0

    @field_validator("ALTERNATIVE_TP_R_MULTIPLES", "CALCULATED_R_MULTIPLES", mode="before")
    @classmethod
    def parse_alternative_r_multiples(cls, v: Union[str, List[float]]) -> List[float]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return [float(x) for x in json.loads(v)]
                except Exception:
                    pass
            # Comma-separated fallback
            return [float(x.strip()) for x in v.split(",") if x.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

settings = Settings()
