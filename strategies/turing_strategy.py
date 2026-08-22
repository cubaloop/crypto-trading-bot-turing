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
    operation_type: str
    conviction: float  # -1.0 a +1.0
    leverage: float    # 1.0x a 10.0x (Inversamente proporcional a la volatilidad)
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
        signal_threshold: float = 0.26,
        vpin_cutoff: float = 0.65,
        max_entropy_cutoff: float = 0.88,
        target_risk_pct: float = 0.035  # 3.5% de riesgo normalizado por volatilidad
    ):
        self.lookback_window = lookback_window
        self.atr_window = atr_window
        self.signal_threshold = signal_threshold
        self.vpin_cutoff = vpin_cutoff
        self.max_entropy_cutoff = max_entropy_cutoff
        self.target_risk_pct = target_risk_pct

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if len(df) < self.lookback_window:
            return df

        # 1. ATR Robusto (14 períodos)
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

        # 4. RSI Instantáneo (7 períodos)
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
        hurst_val = getattr(snapshot, 'hurst_exponent', 0.50)

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
                hurst=hurst_val,
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
                hurst=hurst_val,
                entropy=snapshot.entropy,
                ising_chi=snapshot.ising_susceptibility,
                reason="Inicializando tensores matemáticos TURING"
            )

        df = self.compute_indicators(ohlcv_df)
        latest = df.iloc[-1]
        atr = latest.get('atr_14', atr_fallback)
        atr = max(atr, snapshot.last_price * 0.005)
        atr_pct = atr / max(1.0, snapshot.last_price)

        ema_9 = latest.get('ema_9', snapshot.last_price)
        ema_20 = latest.get('ema_20', snapshot.last_price)
        ema_50 = latest.get('ema_50', snapshot.last_price)
        rsi_7 = latest.get('rsi_7', 50.0)

        # ======================================================================
        # REFACTORIZACIÓN AUDITORÍA: 5 PILARES CONTINUOS Y ORTOGONALES
        # ======================================================================
        
        # 1. Pilar 1: Tendencia Continua (Distancia normalizada por ATR)
        dist_ema20 = (snapshot.last_price - ema_20) / max(0.0001, atr)
        ema_slope = (ema_9 - ema_50) / max(0.0001, atr)
        s_trend = float(np.tanh(0.7 * dist_ema20 + 0.3 * ema_slope))

        # 2. Pilar 2: Magnetización y Susceptibilidad de Fase
        s_ising = float(np.clip(snapshot.ising_magnetization * (1.0 + min(1.5, snapshot.ising_susceptibility)), -1.0, 1.0))

        # 3. Pilar 3: Flujo de Órdenes L2 Normalizado
        quantum_purity = max(0.1, 1.0 - snapshot.von_neumann_entropy)
        obi = float(np.clip(snapshot.order_book_imbalance, -1.0, 1.0))
        vol_delta_norm = float(np.clip(snapshot.volume_delta, -1.0, 1.0))
        s_quantum = float(0.6 * obi + 0.4 * vol_delta_norm) * quantum_purity

        # 4. Pilar 4: Lead-Lag Alpha Ortogonal (Correlación cruda independiente)
        s_lead_lag = float(np.clip(snapshot.lead_lag_btc_correlation, -1.0, 1.0))

        # 5. Pilar 5: Sentimiento NLP
        s_nlp = float(np.clip(decayed_sentiment, -1.0, 1.0))

        # Penalización Continua de Toxicidad VPIN (No salto binario)
        vpin_penalty = max(0.0, 1.0 - (snapshot.vpin / self.vpin_cutoff)) if snapshot.vpin > 0 else 1.0

        # Ponderación
        w = dynamic_weights or {
            "w_trend": 0.35,
            "w_ising": 0.25,
            "w_quantum": 0.20,
            "w_lead_lag": 0.10,
            "w_nlp": 0.10
        }
        threshold = dynamic_threshold or self.signal_threshold

        # Combinación Lineal Continua con Penalización VPIN
        raw_score = (
            (w.get("w_trend", 0.35) * s_trend) +
            (w.get("w_ising", 0.25) * s_ising) +
            (w.get("w_quantum", 0.20) * s_quantum) +
            (w.get("w_lead_lag", 0.10) * s_lead_lag) +
            (w.get("w_nlp", 0.10) * s_nlp)
        ) * vpin_penalty

        conviction = float(np.clip(math.tanh(raw_score * 1.5), -1.0, 1.0))

        # ======================================================================
        # GESTIÓN DE APALANCAMIENTO: Inversamente Proporcional a Volatilidad (ATR%)
        # ======================================================================
        # Normaliza el riesgo: a mayor volatilidad, menor apalancamiento
        vol_adjusted_lev = self.target_risk_pct / max(0.005, atr_pct)
        target_lev = vol_adjusted_lev * (0.5 + 0.5 * abs(conviction)) * leverage_mult
        optimal_leverage = float(np.clip(round(target_lev, 1), 1.0, 10.0))

        # ======================================================================
        # BIFURCACIÓN DE RÉGIMEN POR EXPONENTE DE HURST (H)
        # ======================================================================
        if hurst_val >= 0.55:
            operation_type = "TREND_RUNNER"  # Dejar correr la tendencia completa
            tp_mult = 3.5
            sl_mult = 1.4
        elif hurst_val <= 0.45:
            operation_type = "MEAN_REVERSION_SNIPER"  # Scalping ceñido
            tp_mult = 2.0
            sl_mult = 1.0
        else:
            operation_type = "DYNAMIC_MOMENTUM"
            tp_mult = 2.8
            sl_mult = 1.2

        if conviction >= threshold:
            action = "BUY"
            sl = snapshot.last_price - (sl_mult * atr)
            tp = snapshot.last_price + (tp_mult * atr)
            reason = f"👑 TURING LONG [{operation_type}] | Lev: {optimal_leverage:.1f}x (Vol-Adj) | Hurst: {hurst_val:.2f} | Conv: {conviction:+.2f}"
        elif conviction <= -threshold:
            action = "SELL"
            sl = snapshot.last_price + (sl_mult * atr)
            tp = snapshot.last_price - (tp_mult * atr)
            reason = f"🔻 TURING SHORT [{operation_type}] | Lev: {optimal_leverage:.1f}x (Vol-Adj) | Hurst: {hurst_val:.2f} | Conv: {conviction:+.2f}"
        else:
            action = "HOLD"
            sl = snapshot.last_price - (sl_mult * atr)
            tp = snapshot.last_price + (tp_mult * atr)
            reason = f"⏸️ TURING Escaneando Régimen (Hurst: {hurst_val:.2f} | Conv: {conviction:+.2f} vs {threshold:.2f})"

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
            hurst=hurst_val,
            entropy=snapshot.entropy,
            ising_chi=snapshot.ising_susceptibility,
            reason=reason
        )
