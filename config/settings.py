import os
from typing import List
from pydantic import BaseModel

class TuringSettings(BaseModel):
    # Identidad y Modo
    bot_name: str = "KuQuant TURING (The Apex Quantum General)"
    mode: str = os.getenv("MODE", "paper")  # 'paper' o 'live'
    exchange_id: str = os.getenv("EXCHANGE_ID", "kucoin")
    
    # Par Dedicado de Alta Volatilidad
    symbols: List[str] = [
        "SOL/USDT"
    ]
    timeframe: str = "1m"
    
    # Capital y Gestión Agresiva de Riesgo
    initial_virtual_balance: float = 10000.0
    risk_per_trade_pct: float = 0.025  # 2.5% base escalable hasta 5.0% según convicción
    max_daily_drawdown_pct: float = 0.12  # 12.0% Max DD diario
    
    # Apalancamiento Dinámico Autónomo (1x a 10x)
    min_leverage: float = 1.0
    max_leverage: float = 10.0
    default_leverage: float = 3.0
    
    # Ratios Asimétricos
    risk_reward_ratio: float = 4.0  # 1:4 Asimetría base
    
    # Parámetros Cuánticos y Físicos
    hurst_target: float = 0.10  # Volatilidad rugosa
    vpin_cutoff: float = 0.55   # Detección de toxicidad
    max_entropy_cutoff: float = 0.88
    ising_susceptibility_threshold: float = 1.85  # Avalancha de fase crítica
    
    # NLP y Sentimiento
    cryptopanic_api_key: str = os.getenv("CRYPTOPANIC_API_KEY", "")
    sentiment_half_life_minutes: float = 45.0
    
    # Conectividad y Web
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8005"))
    price_poll_interval_seconds: float = 0.40  # 400ms ultra-rápido

config = TuringSettings()
