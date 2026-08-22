"""
TURING v2 — Motor de backtest y calibración walk-forward
==========================================================
"""
import sys
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

# Añadir rutas de importación local
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from strategies.turing_strategy_v2 import TuringStrategyV2, REGIME_WEIGHTS, PillarWeights
from execution.turing_exit_manager_v2 import update_trailing_stop

@dataclass
class SimPosition:
    direction: int
    entry_price: float
    entry_bar: int
    leverage: float
    atr: float
    regime: str
    stop_loss: float
    initial_stop_loss: float
    take_profit: float
    highest_price: float
    lowest_price: float
    profit_lock_stage: int = 0
    opened_at_bar: int = 0
    force_close: bool = False

@dataclass
class Trade:
    direction: int
    entry_bar: int
    exit_bar: int
    entry_price: float
    exit_price: float
    leverage: float
    regime: str
    pnl_pct: float
    r_multiple: float
    exit_reason: str

@dataclass
class BacktestResult:
    trades: List[Trade]
    equity_curve: List[float]
    sharpe: float
    sortino: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    total_return_pct: float
    n_trades: int
    avg_r_multiple: float

class SnapshotRow:
    __slots__ = (
        "symbol", "last_price", "vpin", "hurst", "ising_magnetization",
        "ising_susceptibility", "von_neumann_entropy", "order_book_imbalance",
        "volume_delta", "lead_lag_btc_correlation",
    )

    def __init__(self, row: pd.Series, symbol: str):
        self.symbol = symbol
        self.last_price = float(row["close"])
        self.vpin = float(row.get("vpin", 0.20))
        self.hurst = float(row.get("hurst", 0.52))
        self.ising_magnetization = float(row.get("ising_magnetization", 0.0))
        self.ising_susceptibility = float(row.get("ising_susceptibility", 0.50))
        self.von_neumann_entropy = float(row.get("von_neumann_entropy", 0.30))
        self.order_book_imbalance = float(row.get("order_book_imbalance", 0.0))
        self.volume_delta = float(row.get("volume_delta", 0.0))
        self.lead_lag_btc_correlation = float(row.get("lead_lag_btc_correlation", 0.0))

def run_backtest(
    df: pd.DataFrame,
    strategy: TuringStrategyV2,
    symbol: str = "SOLUSDT",
    initial_equity: float = 10_000.0,
    fee_pct_per_side: float = 0.0004,
    slippage_pct_per_side: float = 0.0003,
    max_holding_bars: Optional[int] = 288,
    min_bars_warmup: int = 60,
) -> BacktestResult:
    equity = initial_equity
    equity_curve = [equity]
    trades: List[Trade] = []
    position: Optional[SimPosition] = None

    n = len(df)
    for i in range(min_bars_warmup, n):
        row = df.iloc[i]

        if position is not None:
            position.highest_price = max(position.highest_price, float(row["high"]))
            position.lowest_price = min(position.lowest_price, float(row["low"]))

            update_trailing_stop(position, position.regime, max_holding_bars, i)

            exit_price, exit_reason = _check_exit(position, row)
            if exit_price is not None:
                trade = _close_position(position, exit_price, i, exit_reason,
                                         fee_pct_per_side, slippage_pct_per_side)
                trades.append(trade)
                equity *= max(0.0, (1.0 + trade.pnl_pct))
                position = None

        if position is None and equity > 0:
            window = df.iloc[max(0, i - 200): i + 1]
            snap = SnapshotRow(row, symbol)
            signal = strategy.generate_signal(snap, window, decayed_sentiment=0.0, external_alert=None)
            if signal.action in ("BUY", "SELL"):
                direction = 1 if signal.action == "BUY" else -1
                position = SimPosition(
                    direction=direction, entry_price=signal.entry_price, entry_bar=i,
                    leverage=signal.leverage, atr=signal.atr, regime=signal.regime,
                    stop_loss=signal.stop_loss, initial_stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    highest_price=signal.entry_price, lowest_price=signal.entry_price,
                    opened_at_bar=i,
                )

        equity_curve.append(equity)

    return _compute_metrics(trades, equity_curve, initial_equity)

def _check_exit(position: SimPosition, row) -> Tuple[Optional[float], str]:
    high, low = float(row["high"]), float(row["low"])
    if position.force_close:
        return float(row["close"]), "TIME_STOP"
    if position.direction == 1:
        if low <= position.stop_loss:
            reason = "STOP_LOSS" if position.profit_lock_stage == 0 else "TRAIL_STOP"
            return position.stop_loss, reason
        if high >= position.take_profit:
            return position.take_profit, "TAKE_PROFIT"
    else:
        if high >= position.stop_loss:
            reason = "STOP_LOSS" if position.profit_lock_stage == 0 else "TRAIL_STOP"
            return position.stop_loss, reason
        if low <= position.take_profit:
            return position.take_profit, "TAKE_PROFIT"
    return None, ""

def _close_position(position: SimPosition, exit_price: float, exit_bar: int, reason: str,
                     fee_pct: float, slippage_pct: float) -> Trade:
    slip = exit_price * slippage_pct
    filled_price = exit_price - slip if position.direction == 1 else exit_price + slip

    gross_move_pct = (filled_price - position.entry_price) / position.entry_price * position.direction
    pnl_pct_on_equity = gross_move_pct * position.leverage
    pnl_pct_on_equity -= (fee_pct * 2) * position.leverage

    risk_per_unit_pct = abs(position.entry_price - position.initial_stop_loss) / position.entry_price
    r_multiple = gross_move_pct / risk_per_unit_pct if risk_per_unit_pct > 1e-9 else 0.0

    return Trade(
        direction=position.direction, entry_bar=position.entry_bar, exit_bar=exit_bar,
        entry_price=position.entry_price, exit_price=filled_price, leverage=position.leverage,
        regime=position.regime, pnl_pct=pnl_pct_on_equity, r_multiple=r_multiple, exit_reason=reason,
    )

def _compute_metrics(trades: List[Trade], equity_curve: List[float], initial_equity: float) -> BacktestResult:
    if not trades:
        return BacktestResult([], equity_curve, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0.0)

    returns = np.array([t.pnl_pct for t in trades])
    wins = returns[returns > 0]
    losses = returns[returns <= 0]

    win_rate = len(wins) / len(returns)
    profit_factor = float(wins.sum() / abs(losses.sum())) if losses.sum() != 0 else float("inf")

    mean_r = returns.mean()
    std_r = returns.std(ddof=1) if len(returns) > 1 else 0.0
    sharpe = float(mean_r / std_r * np.sqrt(len(returns))) if std_r > 1e-12 else 0.0

    downside = returns[returns < 0]
    downside_std = downside.std(ddof=1) if len(downside) > 1 else 0.0
    sortino = float(mean_r / downside_std * np.sqrt(len(returns))) if downside_std > 1e-12 else 0.0

    eq = np.array(equity_curve)
    running_max = np.maximum.accumulate(eq)
    drawdowns = np.where(running_max > 0, (eq - running_max) / running_max, 0.0)
    max_dd = float(drawdowns.min()) * 100

    total_return_pct = float((eq[-1] / initial_equity - 1.0) * 100)
    avg_r = float(np.mean([t.r_multiple for t in trades]))

    return BacktestResult(
        trades=trades, equity_curve=equity_curve, sharpe=sharpe, sortino=sortino,
        max_drawdown_pct=max_dd, win_rate=float(win_rate), profit_factor=profit_factor,
        total_return_pct=total_return_pct, n_trades=len(trades), avg_r_multiple=avg_r,
    )

def generate_weight_candidates(base: PillarWeights, perturbations=(-0.10, 0.0, 0.10)) -> List[PillarWeights]:
    candidates = []
    for d_trend in perturbations:
        for d_ising in perturbations:
            trend = float(np.clip(base.trend + d_trend, 0.05, 0.6))
            ising = float(np.clip(base.ising + d_ising, 0.05, 0.5))
            remaining = max(0.05, 1.0 - trend - ising)
            other_sum = base.quantum + base.lead_lag + base.nlp
            ratio = remaining / other_sum if other_sum > 1e-9 else 0.0
            candidates.append(PillarWeights(
                trend=trend, ising=ising,
                quantum=base.quantum * ratio, lead_lag=base.lead_lag * ratio, nlp=base.nlp * ratio,
            ))
    return candidates

def walk_forward_optimize(
    df: pd.DataFrame,
    train_bars: int = 2000,
    test_bars: int = 500,
    step_bars: int = 500,
    regimes_to_tune: Tuple[str, ...] = ("trend", "mean_revert"),
    min_trades_in_sample: int = 10,
) -> Dict:
    results_oos = []
    start = 0
    n = len(df)
    window_id = 0

    while start + train_bars + test_bars <= n:
        train_df = df.iloc[start: start + train_bars]
        test_df = df.iloc[start + train_bars: start + train_bars + test_bars]

        best_weights: Dict[str, PillarWeights] = {}
        for regime in regimes_to_tune:
            base = REGIME_WEIGHTS[regime]
            candidates = generate_weight_candidates(base)
            best_sharpe, best_w = -np.inf, base
            original = REGIME_WEIGHTS[regime]
            for cand in candidates:
                REGIME_WEIGHTS[regime] = cand
                try:
                    res = run_backtest(train_df, TuringStrategyV2())
                finally:
                    REGIME_WEIGHTS[regime] = original
                if res.n_trades >= min_trades_in_sample and res.sharpe > best_sharpe:
                    best_sharpe, best_w = res.sharpe, cand
            best_weights[regime] = best_w

        originals = {r: REGIME_WEIGHTS[r] for r in regimes_to_tune}
        for r in regimes_to_tune:
            REGIME_WEIGHTS[r] = best_weights[r]
        try:
            oos_result = run_backtest(test_df, TuringStrategyV2())
        finally:
            for r in regimes_to_tune:
                REGIME_WEIGHTS[r] = originals[r]

        results_oos.append({
            "window": window_id,
            "test_start_bar": start + train_bars,
            "sharpe_oos": oos_result.sharpe,
            "max_dd_oos": oos_result.max_drawdown_pct,
            "n_trades_oos": oos_result.n_trades,
            "weights_used": {r: best_weights[r] for r in regimes_to_tune},
        })
        window_id += 1
        start += step_bars

    avg_sharpe_oos = float(np.mean([w["sharpe_oos"] for w in results_oos])) if results_oos else 0.0
    return {"windows": results_oos, "avg_sharpe_oos": avg_sharpe_oos, "n_windows": len(results_oos)}

if __name__ == "__main__":
    print("✅ TURING v2 Backtest & Walk-Forward Engine cargado con éxito.")
