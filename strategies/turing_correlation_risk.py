"""
TURING v2 — Riesgo cross-asset ponderado por correlación
===========================================================
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

@dataclass
class PairShockEvent:
    pair: str
    move_magnitude: float
    direction: int
    timestamp: Optional[str] = None

@dataclass
class ExternalMarketAlert:
    is_active: bool = False
    events: List[PairShockEvent] = field(default_factory=list)
    source: str = ""
    note: str = ""

def compute_correlation_weighted_shock(
    alert: ExternalMarketAlert,
    correlation_map: Dict[str, float],
    shock_reference: float = 3.0,
) -> Tuple[float, int]:
    if not alert.is_active or not alert.events:
        return 0.0, 0

    residual_survival = 1.0
    dir_weighted_sum = 0.0
    dir_weight_total = 0.0

    for ev in alert.events:
        corr = correlation_map.get(ev.pair, 0.0)
        abs_corr = min(1.0, abs(corr))
        magnitude = float(np.clip(ev.move_magnitude / shock_reference, 0.0, 1.0))
        contribution = abs_corr * magnitude
        residual_survival *= (1.0 - contribution)

        implied_dir = ev.direction * (1 if corr >= 0 else -1)
        dir_weighted_sum += implied_dir * contribution
        dir_weight_total += contribution

    severity = float(np.clip(1.0 - residual_survival, 0.0, 1.0))

    dominant_direction = 0
    if dir_weight_total > 1e-9:
        avg_dir = dir_weighted_sum / dir_weight_total
        if avg_dir > 0.15:
            dominant_direction = 1
        elif avg_dir < -0.15:
            dominant_direction = -1

    return severity, dominant_direction

def apply_correlation_shock_damping(
    conviction: float,
    leverage: float,
    severity: float,
    dominant_direction: int,
    signal_action: str,
    confirming_shock_discount: float = 0.5,
) -> Tuple[float, float, float]:
    if severity <= 0:
        return conviction, leverage, 1.0

    signal_dir = 1 if signal_action == "BUY" else (-1 if signal_action == "SELL" else 0)

    if dominant_direction != 0 and signal_dir != 0 and dominant_direction == signal_dir:
        effective_severity = severity * confirming_shock_discount
    else:
        effective_severity = severity

    damp = max(0.0, 1.0 - effective_severity)
    return conviction * damp, leverage * damp, damp
