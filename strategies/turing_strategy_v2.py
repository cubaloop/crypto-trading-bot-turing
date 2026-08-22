"""
TURING v2 — Motor de señales (SOL/USDT)
========================================
"""
import math
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict
import numpy as np
import pandas as pd

from strategies.turing_correlation_risk import (
    ExternalMarketAlert, PairShockEvent,
    compute_correlation_weighted_shock, apply_correlation_shock_damping,
)

@dataclass
class PillarWeights:
    trend: float
    ising: float
    quantum: float
    lead_lag: float
    nlp: float

    def as_tuple(self) -> Tuple[float, float, float, float, float]:
        return (self.trend, self.ising, self.quantum, self.lead_lag, self.nlp)

REGIME_WEIGHTS = {
    "trend":       PillarWeights(trend=0.40, ising=0.20, quantum=0.15, lead_lag=0.15, nlp=0.10),
    "mean_revert": PillarWeights(trend=0.15, ising=0.30, quantum=0.30, lead_lag=0.15, nlp=0.10),
    "mixed":       PillarWeights(trend=0.30, ising=0.25, quantum=0.20, lead_lag=0.15, nlp=0.10),
}

@dataclass
class TuringTradeSignal:
    symbol: str
    action: str                    # "BUY", "SELL", "HOLD"
    regime: str                    # "trend" | "mean_revert" | "mixed"
    conviction: float
    conviction_raw: float          # antes de damping por shock externo
    leverage: float
    entry_price: float
    stop_loss: float
    take_profit: float
    atr: float
    vpin: float
    hurst: float
    entropy: float
    vpin_penalty: float
    external_damping: float
    reason: str

def classify_regime(hurst: float, trend_band: float = 0.55, revert_band: float = 0.45) -> str:
    if hurst >= trend_band:
        return "trend"
    if hurst <= revert_band:
        return "mean_revert"
    return "mixed"

def normalize_flow_feature(value: float, scale: float, clip: float = 3.0) -> float:
    if scale is None or scale <= 1e-9:
        return 0.0
    return float(np.clip(value / scale, -clip, clip))

def soft_penalty(value: float, soft_cutoff: float, hard_cutoff: float) -> float:
    if value <= soft_cutoff:
        return 1.0
    if value >= hard_cutoff:
        return 0.0
    return float(1.0 - (value - soft_cutoff) / (hard_cutoff - soft_cutoff))

class TuringStrategyV2:
    def __init__(
        self,
        lookback_window: int = 20,
        atr_window: int = 14,
        signal_threshold: float = 0.26,
        vpin_soft_cutoff: float = 0.40,
        vpin_hard_cutoff: float = 0.65,
        entropy_soft_cutoff: float = 0.70,
        entropy_hard_cutoff: float = 0.92,
        target_risk_pct: float = 0.008,
        min_leverage: float = 1.0,
        max_leverage: float = 10.0,
        correlation_map: Optional[Dict[str, float]] = None,
    ):
        self.lookback_window = lookback_window
        self.atr_window = atr_window
        self.signal_threshold = signal_threshold
        self.vpin_soft_cutoff = vpin_soft_cutoff
        self.vpin_hard_cutoff = vpin_hard_cutoff
        self.entropy_soft_cutoff = entropy_soft_cutoff
        self.entropy_hard_cutoff = entropy_hard_cutoff
        self.target_risk_pct = target_risk_pct
        self.min_leverage = min_leverage
        self.max_leverage = max_leverage
        self.correlation_map = correlation_map or {
            "BTC/USDT": 0.85,
            "ETH/USDT": 0.78,
            "NEAR/USDT": 0.65,
            "DOGE/USDT": 0.55
        }

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if len(df) < self.lookback_window:
            return df

        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr_14'] = tr.rolling(window=self.atr_window).mean()

        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

        if 'volume_delta' in df.columns:
            df['volume_delta_std'] = df['volume_delta'].rolling(window=self.lookback_window).std()

        return df

    def compute_leverage(self, conviction: float, quantum_purity: float, atr_pct: float) -> float:
        if atr_pct <= 1e-9:
            return self.min_leverage
        vol_scaled = self.target_risk_pct / atr_pct
        raw = vol_scaled * abs(conviction) * quantum_purity * 10.0
        return float(np.clip(round(raw, 1), self.min_leverage, self.max_leverage))

    def generate_signal(
        self,
        snapshot,
        ohlcv_df: pd.DataFrame,
        decayed_sentiment: float = 0.0,
        external_alert: Optional[ExternalMarketAlert] = None,
        dynamic_weights: Optional[Dict[str, float]] = None,
        dynamic_threshold: Optional[float] = None,
        leverage_mult: float = 1.0,
        has_black_swan: bool = False
    ) -> TuringTradeSignal:

        df = self.compute_indicators(ohlcv_df)
        latest = df.iloc[-1]
        atr = max(latest.get('atr_14', snapshot.last_price * 0.01), snapshot.last_price * 0.005)
        atr_pct = atr / snapshot.last_price

        hurst_val = getattr(snapshot, 'hurst_exponent', getattr(snapshot, 'hurst', 0.50))
        regime = classify_regime(hurst_val)
        weights = REGIME_WEIGHTS[regime]

        trend_dist = (snapshot.last_price - latest['ema_20']) / atr if atr > 0 else 0.0
        s_trend = float(np.tanh(trend_dist * 0.6))

        ising_mag = getattr(snapshot, 'ising_magnetization', 0.0)
        ising_chi = getattr(snapshot, 'ising_susceptibility', 0.5)
        s_ising = float(np.tanh(ising_mag * (1.0 + min(2.0, ising_chi / 2.0))))

        entropy_val = getattr(snapshot, 'von_neumann_entropy', getattr(snapshot, 'entropy', 0.30))
        quantum_purity_raw = max(0.1, 1.0 - entropy_val)
        entropy_penalty = soft_penalty(entropy_val, self.entropy_soft_cutoff, self.entropy_hard_cutoff)
        quantum_purity = quantum_purity_raw * entropy_penalty

        vd_scale = latest.get('volume_delta_std', None)
        obi_val = getattr(snapshot, 'order_book_imbalance', 0.0)
        vol_delta_val = getattr(snapshot, 'volume_delta', 0.0)
        obi_norm = normalize_flow_feature(obi_val, 1.0)
        vd_norm = normalize_flow_feature(vol_delta_val, vd_scale)
        s_quantum = float(np.tanh(obi_norm * 0.9 + vd_norm * 0.6)) * quantum_purity

        lead_lag_corr = getattr(snapshot, 'lead_lag_btc_correlation', 0.0)
        s_lead_lag = float(np.tanh(lead_lag_corr * 1.2))

        s_nlp = float(decayed_sentiment)

        w_trend, w_ising, w_quantum, w_lead_lag, w_nlp = weights.as_tuple()
        linear_combo = (
            w_trend * s_trend + w_ising * s_ising + w_quantum * s_quantum
            + w_lead_lag * s_lead_lag + w_nlp * s_nlp
        )
        conviction_raw = float(np.clip(math.tanh(linear_combo * 1.6), -1.0, 1.0))

        vpin_val = getattr(snapshot, 'vpin', 0.20)
        vpin_pen = soft_penalty(vpin_val, self.vpin_soft_cutoff, self.vpin_hard_cutoff)
        conviction_after_vpin = conviction_raw * vpin_pen

        leverage_raw = self.compute_leverage(conviction_after_vpin, quantum_purity, atr_pct)

        provisional_action = (
            "BUY" if conviction_after_vpin >= self.signal_threshold
            else "SELL" if conviction_after_vpin <= -self.signal_threshold
            else "HOLD"
        )
        severity, dominant_direction = (0.0, 0)
        if external_alert is not None:
            severity, dominant_direction = compute_correlation_weighted_shock(
                external_alert, self.correlation_map
            )
        conviction, leverage, ext_damp = apply_correlation_shock_damping(
            conviction_after_vpin, leverage_raw, severity, dominant_direction, provisional_action
        )

        if vpin_pen <= 0.0:
            action = "HOLD"
            reason = "VPIN_HARD_BLOCK"
        elif severity >= 0.90 and dominant_direction != 0 and provisional_action != "HOLD" and \
                dominant_direction != (1 if provisional_action == "BUY" else -1):
            action = "HOLD"
            reason = f"CORRELATED_SHOCK_BLOCK:{external_alert.source if external_alert else ''}"
        elif conviction >= self.signal_threshold:
            action = "BUY"
            reason = f"regime={regime}"
        elif conviction <= -self.signal_threshold:
            action = "SELL"
            reason = f"regime={regime}"
        else:
            action = "HOLD"
            reason = f"below_threshold:regime={regime}"

        if regime == "trend":
            sl_mult, tp_mult = 1.4, 4.0
        elif regime == "mean_revert":
            sl_mult, tp_mult = 1.2, 1.8
        else:
            sl_mult, tp_mult = 1.4, 3.2

        if action == "BUY":
            sl = snapshot.last_price - (sl_mult * atr)
            tp = snapshot.last_price + (tp_mult * atr)
        elif action == "SELL":
            sl = snapshot.last_price + (sl_mult * atr)
            tp = snapshot.last_price - (tp_mult * atr)
        else:
            sl = snapshot.last_price - (sl_mult * atr)
            tp = snapshot.last_price + (tp_mult * atr)

        return TuringTradeSignal(
            symbol=snapshot.symbol,
            action=action,
            regime=regime,
            conviction=conviction,
            conviction_raw=conviction_raw,
            leverage=leverage,
            entry_price=snapshot.last_price,
            stop_loss=sl,
            take_profit=tp,
            atr=atr,
            vpin=vpin_val,
            hurst=hurst_val,
            entropy=entropy_val,
            vpin_penalty=vpin_pen,
            external_damping=ext_damp,
            reason=reason,
        )
