import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from strategies.turing_strategy import TuringTradeSignal
from data.persistence import StatePersistence

logger = logging.getLogger("PaperExecutorTuring")

@dataclass
class TuringPosition:
    id: str
    symbol: str
    side: str  # "LONG" o "SHORT"
    operation_type: str
    leverage: float
    entry_price: float
    units: float
    stop_loss: float
    take_profit: float
    highest_price: float
    lowest_price: float
    profit_lock_stage: int
    opened_at: float
    notional_usd: float

class PaperExecutor:
    def __init__(
        self,
        initial_balance_usd: float = 10000.0,
        taker_fee_pct: float = 0.0004,
        slippage_bps: float = 1.5
    ):
        self.balance_usd = initial_balance_usd
        self.initial_balance = initial_balance_usd
        self.taker_fee_pct = taker_fee_pct
        self.slippage_bps = slippage_bps
        self.positions: Dict[str, TuringPosition] = {}
        self.trade_history: List[Dict] = []
        self._order_counter = 0

        saved_state = StatePersistence.load_state()
        if saved_state:
            self.balance_usd = saved_state.get("balance_usd", initial_balance_usd)
            self.initial_balance = saved_state.get("initial_balance", initial_balance_usd)
            self._order_counter = saved_state.get("order_counter", 0)
            self.trade_history = saved_state.get("trade_history", [])
            for sym, pdata in saved_state.get("positions", {}).items():
                self.positions[sym] = TuringPosition(
                    id=pdata.get("id", ""),
                    symbol=pdata.get("symbol", sym),
                    side=pdata.get("side", "LONG"),
                    operation_type=pdata.get("operation_type", "MOMENTUM_BREAKOUT"),
                    leverage=pdata.get("leverage", 3.0),
                    entry_price=pdata.get("entry_price", 0.0),
                    units=pdata.get("units", 0.0),
                    stop_loss=pdata.get("stop_loss", 0.0),
                    take_profit=pdata.get("take_profit", 0.0),
                    highest_price=pdata.get("highest_price", pdata.get("entry_price", 0.0)),
                    lowest_price=pdata.get("lowest_price", pdata.get("entry_price", 0.0)),
                    profit_lock_stage=pdata.get("profit_lock_stage", 0),
                    opened_at=pdata.get("opened_at", time.time()),
                    notional_usd=pdata.get("notional_usd", 0.0)
                )

    def _persist(self):
        StatePersistence.save_state(
            balance_usd=self.balance_usd,
            initial_balance=self.initial_balance,
            positions=self.positions,
            trade_history=self.trade_history,
            order_counter=self._order_counter
        )

    def get_equity(self, current_prices: Dict[str, float]) -> float:
        unrealized_pnl = 0.0
        for symbol, pos in self.positions.items():
            curr_p = current_prices.get(symbol, pos.entry_price)
            if pos.side == "LONG":
                unrealized_pnl += (curr_p - pos.entry_price) * pos.units
            else:
                unrealized_pnl += (pos.entry_price - curr_p) * pos.units
        return self.balance_usd + unrealized_pnl

    def execute_signal(self, signal: TuringTradeSignal, units: float) -> Optional[TuringPosition]:
        if signal.action not in ["BUY", "SELL"] or units <= 0:
            return None

        self._order_counter += 1
        pos_id = f"TURING-{int(time.time())}-{self._order_counter}"
        side = "LONG" if signal.action == "BUY" else "SHORT"

        # Simulación de Slippage de Mercado
        slip = signal.entry_price * (self.slippage_bps / 10000.0)
        fill_price = signal.entry_price + slip if side == "LONG" else signal.entry_price - slip

        notional = fill_price * units
        entry_fee = notional * self.taker_fee_pct
        self.balance_usd -= entry_fee

        pos = TuringPosition(
            id=pos_id,
            symbol=signal.symbol,
            side=side,
            operation_type=signal.operation_type,
            leverage=signal.leverage,
            entry_price=fill_price,
            units=units,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            highest_price=fill_price,
            lowest_price=fill_price,
            profit_lock_stage=0,
            opened_at=time.time(),
            notional_usd=notional
        )
        self.positions[signal.symbol] = pos
        self._persist()

        logger.info(
            f"👑 [ORDEN TURING EJECUTADA]: {side} {units:.4f} {signal.symbol} @ ${fill_price:,.2f} "
            f"({signal.leverage:.1f}x LEVERAGE | {signal.operation_type}) | Notional: ${notional:,.2f}"
        )
        return pos

    def update_and_check_exits(self, current_prices: Dict[str, float]):
        symbols_to_close = []

        for symbol, pos in self.positions.items():
            curr_p = current_prices.get(symbol)
            if not curr_p:
                continue

            if curr_p > pos.highest_price:
                pos.highest_price = curr_p
            if curr_p < pos.lowest_price:
                pos.lowest_price = curr_p

            hit_tp = False
            hit_sl = False
            reason = "NONE"

            # === TURING HYPER-CHANDELIER PROFIT LOCK MILIMÉTRICO ===
            if pos.side == "LONG":
                peak_gain_pct = (pos.highest_price - pos.entry_price) / pos.entry_price

                # Escalón 1: Micro Break-Even (+0.35% -> SL a entrada + comisiones)
                if peak_gain_pct >= 0.0035 and pos.profit_lock_stage < 1:
                    pos.stop_loss = max(pos.stop_loss, pos.entry_price * 1.001)
                    pos.profit_lock_stage = 1
                    logger.info(f"🛡️ [TURING BREAK-EVEN] {symbol}: SL a ${pos.stop_loss:,.2f} (Riesgo Cero)")

                # Escalón 2: Lock 50% Profit (+0.70% -> SL asegura +0.45% neto)
                if peak_gain_pct >= 0.0070 and pos.profit_lock_stage < 2:
                    pos.stop_loss = max(pos.stop_loss, pos.entry_price * 1.0045)
                    pos.profit_lock_stage = 2
                    logger.info(f"💰 [TURING PROFIT LOCK 1] {symbol}: Ganancia asegurada en ${pos.stop_loss:,.2f}")

                # Escalón 3: Hyper-Chandelier Trailing Ratchet (> +1.2%)
                if peak_gain_pct >= 0.035:
                    trailing_sl = pos.highest_price * 0.998  # Solo 0.20% de retroceso
                elif peak_gain_pct >= 0.018:
                    trailing_sl = pos.highest_price * 0.997  # Solo 0.30% de retroceso
                elif peak_gain_pct >= 0.010:
                    trailing_sl = pos.highest_price * 0.996  # Solo 0.40% de retroceso
                else:
                    trailing_sl = pos.stop_loss

                if trailing_sl > pos.stop_loss:
                    pos.stop_loss = trailing_sl
                    pos.profit_lock_stage = 3

                if curr_p >= pos.take_profit and pos.take_profit > pos.entry_price:
                    hit_tp = True
                    reason = f"TAKE_PROFIT ({pos.operation_type} 1:4.8 WIN)"
                elif curr_p <= pos.stop_loss:
                    hit_sl = True
                    reason = "PROFIT_LOCK_EXIT" if pos.stop_loss > pos.entry_price else "STOP_LOSS"

            elif pos.side == "SHORT":
                peak_gain_pct = (pos.entry_price - pos.lowest_price) / pos.entry_price

                # Escalón 1: Micro Break-Even (+0.35%)
                if peak_gain_pct >= 0.0035 and pos.profit_lock_stage < 1:
                    pos.stop_loss = min(pos.stop_loss, pos.entry_price * 0.999)
                    pos.profit_lock_stage = 1
                    logger.info(f"🛡️ [TURING BREAK-EVEN] {symbol}: SL a ${pos.stop_loss:,.2f} (Riesgo Cero)")

                # Escalón 2: Lock 50% Profit (+0.70%)
                if peak_gain_pct >= 0.0070 and pos.profit_lock_stage < 2:
                    pos.stop_loss = min(pos.stop_loss, pos.entry_price * 0.9955)
                    pos.profit_lock_stage = 2
                    logger.info(f"💰 [TURING PROFIT LOCK 1] {symbol}: Ganancia asegurada en ${pos.stop_loss:,.2f}")

                # Escalón 3: Hyper-Chandelier Trailing Ratchet (> +1.2%)
                if peak_gain_pct >= 0.035:
                    trailing_sl = pos.lowest_price * 1.002
                elif peak_gain_pct >= 0.018:
                    trailing_sl = pos.lowest_price * 1.003
                elif peak_gain_pct >= 0.010:
                    trailing_sl = pos.lowest_price * 1.004
                else:
                    trailing_sl = pos.stop_loss

                if trailing_sl < pos.stop_loss:
                    pos.stop_loss = trailing_sl
                    pos.profit_lock_stage = 3

                if curr_p <= pos.take_profit and pos.take_profit < pos.entry_price:
                    hit_tp = True
                    reason = f"TAKE_PROFIT ({pos.operation_type} 1:4.8 WIN)"
                elif curr_p >= pos.stop_loss:
                    hit_sl = True
                    reason = "PROFIT_LOCK_EXIT" if pos.stop_loss < pos.entry_price else "STOP_LOSS"

            if hit_tp or hit_sl:
                pnl = ((curr_p - pos.entry_price) * pos.units) if pos.side == "LONG" else ((pos.entry_price - curr_p) * pos.units)
                exit_fee = (curr_p * pos.units) * self.taker_fee_pct
                net_pnl = pnl - exit_fee

                if net_pnl < 0 and ("TAKE_PROFIT" in reason or "PROFIT_LOCK" in reason):
                    reason = "STOP_LOSS"

                self.balance_usd += net_pnl
                closed_trade = {
                    "id": pos.id,
                    "symbol": symbol,
                    "side": pos.side,
                    "operation_type": pos.operation_type,
                    "leverage": pos.leverage,
                    "entry_price": pos.entry_price,
                    "exit_price": curr_p,
                    "units": pos.units,
                    "gross_pnl": pnl,
                    "net_pnl": net_pnl,
                    "return_pct": (net_pnl / (pos.entry_price * pos.units / pos.leverage)) if pos.units > 0 else 0.0,
                    "reason": reason,
                    "opened_at": pos.opened_at,
                    "closed_at": time.time()
                }
                self.trade_history.append(closed_trade)
                symbols_to_close.append(symbol)

                emoji = "🏆" if net_pnl > 0 else "🛑"
                logger.info(
                    f"{emoji} [TURING TRADE CERRADO] {pos.side} {symbol} | "
                    f"PnL Neto: ${net_pnl:+,.2f} | Motivo: {reason} | Lev: {pos.leverage:.1f}x"
                )

        for sym in symbols_to_close:
            del self.positions[sym]

        if symbols_to_close:
            self._persist()
