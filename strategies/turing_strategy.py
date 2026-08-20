import logging
import math
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from data.ws_market_stream import TuringMarketSnapshot

logger = logging.getLogger("TuringStrategy")

@dataclass
class TuringTradeSignal:
    symbol: str
    action: str  # "BUY", "SELL", "HOLD"
    operation_type: str  # "QUANTUM_AVALANCHE", "SNIPER_PULLBACK", "LEAD_LAG_SURGE", "LÉVY_BREAKOUT"
    conviction: float  # -1.0 a +1.0
    leverage: float    # 1.0x a 10.0x
    entry_price: float
    stop_loss: float
    take_profit: float
    atr: float
    vpin: float
    hurst: float
    entropy: float
    ising_chi: float
    reason: str

class TuringStrategy:
    def __init__(
        self,
        lookback_window: int = 20,
        atr_window: int = 14,
        signal_threshold: float = 0.28,
        vpin_cutoff: float = 0.55,
        max_entropy_cutoff: float = 0.88
    ):
        self.lookback_window = lookback_window
        self.atr_window = atr_window
        self.signal_threshold = signal_threshold
        self.vpin_cutoff = vpin_cutoff
        self.max_entropy_cutoff = max_entropy_cutoff

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if len(df) < self.lookback_window:
            return df

        # 1. ATR Cuántico
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr_14'] = tr.rolling(window=self.atr_window).mean()

        # 2. EMAs Multiescala (EMA 9, 20, 50)
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

        # 3. Zero-Lag DEMA
        lag = int((5 - 1) / 2)
        zlema_fast = df['close'] + (df['close'] - df['close'].shift(lag))
        df['zlema_fast'] = zlema_fast.ewm(span=5, adjust=False).mean()

        # 4. RSI Instantáneo (7 períodos para alta velocidad)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
        rs = gain / (loss.replace(0, 0.0001))
        df['rsi_7'] = 100 - (100 / (1 + rs))

        return df

    def generate_signal(
        self,
        snapshot: TuringMarketSnapshot,
        ohlcv_df: Optional[pd.DataFrame],
        decayed_sentiment: float,
        dynamic_weights: Optional[Dict[str, float]] = None,
        dynamic_threshold: Optional[float] = None,
        leverage_mult: float = 1.0,
        has_black_swan: bool = False
    ) -> TuringTradeSignal:
        atr_fallback = snapshot.last_price * 0.010

        if has_black_swan:
            return TuringTradeSignal(
                symbol=snapshot.symbol,
                action="SELL" if decayed_sentiment < 0 else "HOLD",
                operation_type="EMERGENCY_PURGE",
                conviction=-1.0,
                leverage=1.0,
                entry_price=snapshot.last_price,
                stop_loss=snapshot.last_price * 1.02,
                take_profit=snapshot.last_price * 0.90,
                atr=atr_fallback,
                vpin=snapshot.vpin,
                hurst=snapshot.hurst_exponent,
                entropy=1.0,
                ising_chi=snapshot.ising_susceptibility,
                reason="🚨 TURING EMERGENCY PURGE: Cisne Negro Detectado"
            )

        if ohlcv_df is None or len(ohlcv_df) < self.lookback_window:
            return TuringTradeSignal(
                symbol=snapshot.symbol,
                action="HOLD",
                operation_type="INITIALIZING",
                conviction=0.0,
                leverage=1.0,
                entry_price=snapshot.last_price,
                stop_loss=snapshot.last_price - (1.8 * atr_fallback),
                take_profit=snapshot.last_price + (5.0 * atr_fallback),
                atr=atr_fallback,
                vpin=snapshot.vpin,
                hurst=snapshot.hurst_exponent,
                entropy=snapshot.entropy,
                ising_chi=snapshot.ising_susceptibility,
                reason="Inicializando tensores cuánticos TURING"
            )

        # 1. Filtros de Toxicidad y Caos
        if snapshot.vpin >= self.vpin_cutoff:
            return TuringTradeSignal(
                symbol=snapshot.symbol,
                action="HOLD",
                operation_type="VPIN_BLOCK",
                conviction=0.0,
                leverage=1.0,
                entry_price=snapshot.last_price,
                stop_loss=snapshot.last_price - (1.8 * atr_fallback),
                take_profit=snapshot.last_price + (5.0 * atr_fallback),
                atr=atr_fallback,
                vpin=snapshot.vpin,
                hurst=snapshot.hurst_exponent,
                entropy=snapshot.entropy,
                ising_chi=snapshot.ising_susceptibility,
                reason=f"🛑 BLOQUEO VPIN TÓXICO ({snapshot.vpin:.2f} >= {self.vpin_cutoff:.2f})"
            )

        df = self.compute_indicators(ohlcv_df)
        latest = df.iloc[-1]
        atr = latest.get('atr_14', atr_fallback)
        atr = max(atr, snapshot.last_price * 0.005)

        ema_9 = latest.get('ema_9', snapshot.last_price)
        ema_20 = latest.get('ema_20', snapshot.last_price)
        ema_50 = latest.get('ema_50', snapshot.last_price)
        rsi_7 = latest.get('rsi_7', 50.0)

        # === 5 PILARES MATEMÁTICOS DE TURING ===
        # Pilar 1: Tendencia Fractal Multitemporal
        trend_bullish = snapshot.last_price >= ema_20 or ema_9 >= ema_20
        s_trend = 0.85 if trend_bullish else -0.85

        # Pilar 2: Modelo de Ising - Magnetización y Avalancha de Fase
        # Si Chi es alta y Magnetización está alineada con el flujo -> Avalancha institucional
        s_ising = float(snapshot.ising_magnetization * (1.0 + min(2.0, snapshot.ising_susceptibility / 2.0)))
        s_ising = float(np.tanh(s_ising))

        # Pilar 3: Pureza Cuántica L2 y Entropía de Von Neumann
        # Si Von Neumann es baja (estado puro), la señal es altamente determinista
        quantum_purity = max(0.1, 1.0 - snapshot.von_neumann_entropy)
        s_quantum = float(np.tanh((snapshot.order_book_imbalance * 1.8) + (snapshot.volume_delta * 1.2))) * quantum_purity

        # Pilar 4: Lead-Lag Alpha (Jane Street)
        s_lead_lag = float(snapshot.lead_lag_btc_correlation * (1.0 if trend_bullish else -1.0))

        # Pilar 5: Sentimiento NLP
        s_nlp = float(decayed_sentiment)

        # Pesos Dinámicos
        w = dynamic_weights or {
            "w_trend": 0.35,
            "w_ising": 0.25,
            "w_quantum": 0.20,
            "w_lead_lag": 0.10,
            "w_nlp": 0.10
        }
        threshold = dynamic_threshold or self.signal_threshold

        # Ecuación Maestra TURING
        linear_combo = (
            (w.get("w_trend", 0.35) * s_trend) +
            (w.get("w_ising", 0.25) * s_ising) +
            (w.get("w_quantum", 0.20) * s_quantum) +
            (w.get("w_lead_lag", 0.10) * s_lead_lag) +
            (w.get("w_nlp", 0.10) * s_nlp)
        )
        phi_turing = math.tanh(linear_combo * 2.0)
        conviction = float(np.clip(phi_turing, -1.0, 1.0))

        # === SELECCIÓN AUTÓNOMA DE ARQUETIPO DE OPERACIÓN Y APALANCAMIENTO ===
        # Cálculo de Apalancamiento Dinámico (1.0x a 10.0x)
        raw_leverage = 2.0 + (8.0 * abs(conviction) * quantum_purity * leverage_mult)
        optimal_leverage = float(np.clip(round(raw_leverage, 1), 1.0, 10.0))

        # Arquetipo de Operación
        dist_to_ema20 = (snapshot.last_price - ema_20) / max(0.001, atr)

        if snapshot.ising_susceptibility >= 1.6 and abs(snapshot.order_book_imbalance) > 0.50:
            operation_type = "QUANTUM_AVALANCHE_SURGE"  # Máxima agresividad
            optimal_leverage = min(10.0, optimal_leverage * 1.25)
        elif trend_bullish and -1.0 <= dist_to_ema20 <= 0.8 and rsi_7 < 55:
            operation_type = "SNIPER_PULLBACK"
        elif abs(snapshot.lead_lag_btc_correlation) > 0.85 and snapshot.symbol != "BTC/USDT":
            operation_type = "LEAD_LAG_ARBITRAGE"
        else:
            operation_type = "MOMENTUM_BREAKOUT"

        # Disparadores Asimétricos (1:4.0 a 1:5.0)
        if conviction >= threshold:
            action = "BUY"
            sl = snapshot.last_price - (1.6 * atr)
            tp = snapshot.last_price + (4.8 * atr)
            reason = f"👑 TURING LONG [{operation_type}] | Lev: {optimal_leverage:.1f}x | Ising: {s_ising:+.2f} | Quantum: {s_quantum:+.2f} | Conv: {conviction:+.2f}"
        elif conviction <= -threshold:
            action = "SELL"
            sl = snapshot.last_price + (1.6 * atr)
            tp = snapshot.last_price - (4.8 * atr)
            reason = f"🔻 TURING SHORT [{operation_type}] | Lev: {optimal_leverage:.1f}x | Ising: {s_ising:+.2f} | Quantum: {s_quantum:+.2f} | Conv: {conviction:+.2f}"
        else:
            action = "HOLD"
            sl = snapshot.last_price - (1.6 * atr)
            tp = snapshot.last_price + (4.8 * atr)
            reason = f"⏸️ TURING Escaneando Campo Cuántico (Conv: {conviction:+.2f} vs Umbral: {threshold:.2f})"

        return TuringTradeSignal(
            symbol=snapshot.symbol,
            action=action,
            operation_type=operation_type,
            conviction=conviction,
            leverage=optimal_leverage,
            entry_price=snapshot.last_price,
            stop_loss=sl,
            take_profit=tp,
            atr=atr,
            vpin=snapshot.vpin,
            hurst=snapshot.hurst_exponent,
            entropy=snapshot.entropy,
            ising_chi=snapshot.ising_susceptibility,
            reason=reason
        )
