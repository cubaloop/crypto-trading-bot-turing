"""
TURING v2 — Gestor de salida / trailing stop
=============================================
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class ExitRegimeParams:
    hurdle_be_floor: float      # piso absoluto del hurdle de break-even
    hurdle_be_atr_mult: float   # multiplicador de ATR% para el hurdle
    be_lock_pct: float          # % de ganancia asegurada en Etapa 1 (sobre entry)
    stage2_hurdle_mult: float   # múltiplo del hurdle para Etapa 2
    stage2_lock_pct: float      # % de ganancia asegurada en Etapa 2
    stage3_hurdle_mult: float   # múltiplo del hurdle para activar Etapa 3
    stage3_atr_trail_mult: float  # ancho del trailing en Etapa 3 (x ATR%)
    micro_tp_floor: float
    micro_tp_atr_mult: float
    stage4_trigger_pct_of_tp: float  # % del micro-TP para activar Etapa 4
    stage4_lock_pct_of_peak: float   # % del pico que se asegura en Etapa 4

EXIT_PARAMS = {
    "trend": ExitRegimeParams(
        hurdle_be_floor=0.0060, hurdle_be_atr_mult=1.10, be_lock_pct=1.0010,
        stage2_hurdle_mult=1.6, stage2_lock_pct=1.0030,
        stage3_hurdle_mult=2.2, stage3_atr_trail_mult=0.55,
        micro_tp_floor=0.020, micro_tp_atr_mult=3.4,
        stage4_trigger_pct_of_tp=0.80, stage4_lock_pct_of_peak=0.60,
    ),
    "mean_revert": ExitRegimeParams(
        hurdle_be_floor=0.0040, hurdle_be_atr_mult=0.90, be_lock_pct=1.0015,
        stage2_hurdle_mult=1.4, stage2_lock_pct=1.0040,
        stage3_hurdle_mult=2.0, stage3_atr_trail_mult=0.35,
        micro_tp_floor=0.0075, micro_tp_atr_mult=1.8,
        stage4_trigger_pct_of_tp=0.75, stage4_lock_pct_of_peak=0.85,
    ),
    "mixed": ExitRegimeParams(
        hurdle_be_floor=0.0050, hurdle_be_atr_mult=1.00, be_lock_pct=1.0020,
        stage2_hurdle_mult=1.5, stage2_lock_pct=1.0035,
        stage3_hurdle_mult=2.1, stage3_atr_trail_mult=0.45,
        micro_tp_floor=0.012, micro_tp_atr_mult=2.5,
        stage4_trigger_pct_of_tp=0.78, stage4_lock_pct_of_peak=0.72,
    ),
}

def update_trailing_stop(pos, regime: str, max_holding_bars: Optional[int] = None, current_bar: Optional[int] = None):
    params = EXIT_PARAMS.get(regime, EXIT_PARAMS["mixed"])
    direction = getattr(pos, "direction", 1)
    atr_pct = (pos.atr / pos.entry_price) if pos.entry_price > 0 else 0.008

    if direction == 1:
        peak_gain = (pos.highest_price - pos.entry_price) / pos.entry_price
    else:
        peak_gain = (pos.entry_price - pos.lowest_price) / pos.entry_price

    hurdle_be = max(params.hurdle_be_floor, params.hurdle_be_atr_mult * atr_pct)
    micro_tp_gain = max(params.micro_tp_floor, params.micro_tp_atr_mult * atr_pct)

    def _mirror_pct(pct_above_entry_for_long: float) -> float:
        return pct_above_entry_for_long if direction == 1 else (2.0 - pct_above_entry_for_long)

    def _tighten(new_sl: float) -> bool:
        if direction == 1:
            if new_sl > pos.stop_loss:
                pos.stop_loss = new_sl
                return True
        else:
            if new_sl < pos.stop_loss:
                pos.stop_loss = new_sl
                return True
        return False

    # Etapa 1: Break-even garantizado
    if peak_gain >= hurdle_be and pos.profit_lock_stage < 1:
        if _tighten(pos.entry_price * _mirror_pct(params.be_lock_pct)):
            pos.profit_lock_stage = 1

    # Etapa 2: ganancia moderada asegurada
    if peak_gain >= (hurdle_be * params.stage2_hurdle_mult) and pos.profit_lock_stage < 2:
        if _tighten(pos.entry_price * _mirror_pct(params.stage2_lock_pct)):
            pos.profit_lock_stage = 2

    # Etapa 3: trailing ratchet por volatilidad
    if peak_gain >= (hurdle_be * params.stage3_hurdle_mult):
        if direction == 1:
            trailing_sl = pos.highest_price * (1.0 - (params.stage3_atr_trail_mult * atr_pct))
        else:
            trailing_sl = pos.lowest_price * (1.0 + (params.stage3_atr_trail_mult * atr_pct))
        if _tighten(trailing_sl):
            pos.profit_lock_stage = 3

    # Etapa 4: ultra-ceñido cerca del TP
    if peak_gain >= (params.stage4_trigger_pct_of_tp * micro_tp_gain):
        if direction == 1:
            ultra_sl = pos.entry_price + (params.stage4_lock_pct_of_peak * (pos.highest_price - pos.entry_price))
        else:
            ultra_sl = pos.entry_price - (params.stage4_lock_pct_of_peak * (pos.entry_price - pos.lowest_price))
        if _tighten(ultra_sl):
            pos.profit_lock_stage = 4

    if max_holding_bars is not None and current_bar is not None and hasattr(pos, "opened_at_bar"):
        if (current_bar - pos.opened_at_bar) >= max_holding_bars and pos.profit_lock_stage == 0:
            pos.force_close = True

    return pos
