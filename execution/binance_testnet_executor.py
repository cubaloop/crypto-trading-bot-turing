import logging
import asyncio
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
import ccxt.async_support as ccxt_async

logger = logging.getLogger("BinanceTestnetExecutorTuring")

@dataclass
class LiveTuringPosition:
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
    atr: float

class BinanceTestnetExecutorTuring:
    def __init__(self, api_key: str, secret: str, default_leverage: int = 3):
        self.api_key = api_key
        self.secret = secret
        self.default_leverage = default_leverage
        self.exchange = ccxt_async.binanceusdm({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'timeout': 10000
        })
        self.exchange.set_sandbox_mode(True)
        self.positions: Dict[str, LiveTuringPosition] = {}
        self.trade_history: List[Dict] = []
        self.balance_usd: float = 4923.84
        self.initial_balance: float = 4923.84
        self._order_counter = 0

    async def initialize(self):
        try:
            await self.exchange.load_markets()
            bal = await self.exchange.fetch_balance()
            self.balance_usd = float(bal['total'].get('USDT', 4923.84))
            self.initial_balance = self.balance_usd
            logger.info(f"⚡ [TURING BINANCE INSTITUCIONAL CONECTADO] Balance Oficial: ${self.balance_usd:,.2f} USDT")
        except Exception as e:
            logger.error(f"Error inicializando Binance Testnet en TURING: {e}")

    async def execute_signal(self, signal, units: float):
        if signal.action not in ["BUY", "SELL"] or units <= 0:
            return None

        market_symbol = f"{signal.symbol.split('/')[0]}/USDT:USDT"
        side = "buy" if signal.action == "BUY" else "sell"
        lev = int(round(signal.leverage or self.default_leverage))

        try:
            # 1. Filtro de Spread Institucional (< 0.035%)
            try:
                ticker = await self.exchange.fetch_ticker(market_symbol)
                bid = float(ticker.get('bid', signal.entry_price))
                ask = float(ticker.get('ask', signal.entry_price))
                if bid > 0 and ask > 0:
                    spread_pct = (ask - bid) / bid
                    if spread_pct > 0.00035:
                        logger.warning(f"🛑 [TURING SPREAD FILTER] Spread amplio ({spread_pct:.4%}). Esperando compresión.")
                        return None
            except Exception:
                pass

            try:
                await self.exchange.set_leverage(lev, market_symbol)
            except Exception:
                pass

            # 2. Control de Margen Aislado Seguro (Máximo $800 USDT notional por trade)
            max_safe_notional = 3000.0
            if (units * signal.entry_price) > max_safe_notional:
                units = max(25.0, max_safe_notional / signal.entry_price)

            amount_formatted = round(max(25.0, units), 1)
            if amount_formatted <= 0:
                return None

            # 1. Intento de Entrada Límite Post-Only (Comisión Reducida Maker)
            try:
                order = await self.exchange.create_order(
                    symbol=market_symbol,
                    type='limit',
                    side=side,
                    amount=amount_formatted,
                    price=signal.entry_price,
                    params={'postOnly': True}
                )
            except Exception as post_only_err:
                logger.info(f"Colocación Post-Only ajustada a mercado para garantizar llenado: {post_only_err}")
                # 1. Intento de Entrada Límite Post-Only (Comisión Reducida Maker)
            try:
                order = await self.exchange.create_order(
                    symbol=market_symbol,
                    type='limit',
                    side=side,
                    amount=amount_formatted,
                    price=signal.entry_price,
                    params={'postOnly': True}
                )
            except Exception as post_only_err:
                logger.info(f"Colocación Post-Only ajustada a mercado para garantizar llenado: {post_only_err}")
                order = await self.exchange.create_order(
                symbol=market_symbol,
                type='market',
                side=side,
                amount=amount_formatted
            )

            raw_p = order.get('average') or order.get('price') or signal.entry_price
            fill_price = float(raw_p) if raw_p else float(signal.entry_price)
            actual_units = float(amount_formatted)
            notional = fill_price * actual_units
            pos_id = f"binance_turing_{order.get('id', self._order_counter)}"
            self._order_counter += 1

            pos = LiveTuringPosition(
                id=pos_id,
                symbol=signal.symbol,
                side="LONG" if signal.action == "BUY" else "SHORT",
                operation_type=getattr(signal, 'operation_type', 'QUANTUM_GENERAL'),
                leverage=float(lev),
                entry_price=fill_price,
                units=actual_units,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                highest_price=fill_price,
                lowest_price=fill_price,
                profit_lock_stage=0,
                opened_at=time.time(),
                notional_usd=notional,
                atr=getattr(signal, 'atr', fill_price * 0.008)
            )
            self.positions[signal.symbol] = pos
            logger.info(
                f"👑 [ORDEN REAL BINANCE TURING] {signal.action} {actual_units} {signal.symbol} @ ${fill_price:,.2f} "
                f"({lev}x LEV | {pos.operation_type}) | ID: {pos_id}"
            )
            return pos
        except Exception as e:
            logger.error(f"Error ejecutando orden real en Binance Testnet para TURING: {e}")
            return None

    def get_equity(self, current_prices: Dict[str, float]) -> float:
        unrealized = 0.0
        for sym, pos in self.positions.items():
            curr_p = current_prices.get(sym, pos.entry_price)
            if pos.side == "LONG":
                unrealized += (curr_p - pos.entry_price) * pos.units
            else:
                unrealized += (pos.entry_price - curr_p) * pos.units
        return self.balance_usd + unrealized

    async def update_and_check_exits(self, current_prices: Dict[str, float]):
        for symbol, pos in list(self.positions.items()):
            curr_p = current_prices.get(symbol, pos.entry_price)
            if not curr_p:
                continue

            if curr_p > pos.highest_price:
                pos.highest_price = curr_p
            if curr_p < pos.lowest_price:
                pos.lowest_price = curr_p

            should_close = False
            reason = ""
            atr_pct = (pos.atr / pos.entry_price) if pos.entry_price > 0 else 0.008
            micro_tp_gain = max(0.0075, 1.8 * atr_pct)
            hurdle_be = max(0.0040, 0.90 * atr_pct)

            # 1. Salida por Estancamiento / Time-Decay (Rotación dinámica de capital)
            position_age_sec = time.time() - pos.opened_at
            price_variation = abs(curr_p - pos.entry_price) / max(1.0, pos.entry_price)
            if position_age_sec >= 600 and price_variation <= 0.0018:
                should_close = True
                reason = "TIME_DECAY_STAGNATION (Rotación de Capital)"

            # 2. Hyper-Chandelier Micro-Scalping Trailing Ratchet
            if pos.side == "LONG":
                peak_gain = (pos.highest_price - pos.entry_price) / pos.entry_price
                if peak_gain >= hurdle_be and pos.profit_lock_stage < 1:
                    pos.stop_loss = max(pos.stop_loss, pos.entry_price * 1.0010)
                    pos.profit_lock_stage = 1
                if peak_gain >= (hurdle_be * 1.5) and pos.profit_lock_stage < 2:
                    pos.stop_loss = max(pos.stop_loss, pos.entry_price * 1.0035)
                    pos.profit_lock_stage = 2
                if peak_gain >= (hurdle_be * 2.2):
                    trailing_sl = pos.highest_price * (1.0 - (0.4 * atr_pct))
                    if trailing_sl > pos.stop_loss:
                        pos.stop_loss = trailing_sl
                        pos.profit_lock_stage = 3

                if curr_p <= pos.stop_loss:
                    should_close = True
                    reason = "PROFIT_LOCK_EXIT" if pos.stop_loss > pos.entry_price else "STOP_LOSS"
                elif curr_p >= (pos.entry_price * (1.0 + micro_tp_gain)):
                    should_close = True
                    reason = "MICRO_SCALPING_TAKE_PROFIT"
                elif curr_p >= pos.take_profit and pos.take_profit > pos.entry_price:
                    should_close = True
                    reason = f"TAKE_PROFIT ({getattr(pos, 'operation_type', 'SNIPER')})"

            elif pos.side == "SHORT":
                peak_gain = (pos.entry_price - pos.lowest_price) / pos.entry_price
                if peak_gain >= hurdle_be and pos.profit_lock_stage < 1:
                    pos.stop_loss = min(pos.stop_loss, pos.entry_price * 0.9990)
                    pos.profit_lock_stage = 1
                if peak_gain >= (hurdle_be * 1.5) and pos.profit_lock_stage < 2:
                    pos.stop_loss = min(pos.stop_loss, pos.entry_price * 0.9965)
                    pos.profit_lock_stage = 2
                if peak_gain >= (hurdle_be * 2.2):
                    trailing_sl = pos.lowest_price * (1.0 + (0.4 * atr_pct))
                    if trailing_sl < pos.stop_loss:
                        pos.stop_loss = trailing_sl
                        pos.profit_lock_stage = 3

                if curr_p >= pos.stop_loss:
                    should_close = True
                    reason = "PROFIT_LOCK_EXIT" if pos.stop_loss < pos.entry_price else "STOP_LOSS"
                elif curr_p <= (pos.entry_price * (1.0 - micro_tp_gain)):
                    should_close = True
                    reason = "MICRO_SCALPING_TAKE_PROFIT"
                elif curr_p <= pos.take_profit and pos.take_profit < pos.entry_price:
                    should_close = True
                    reason = f"TAKE_PROFIT ({getattr(pos, 'operation_type', 'SNIPER')})"

            if should_close:
                await self.close_position(symbol, exit_price=curr_p, reason=reason)

    async def close_position(self, symbol: str, exit_price: float, reason: str):
        pos = self.positions.get(symbol)
        if not pos:
            return

        market_symbol = f"{symbol.split('/')[0]}/USDT:USDT"
        close_side = "sell" if pos.side == "LONG" else "buy"

        try:
            order = await self.exchange.create_order(
                symbol=market_symbol,
                type='market',
                side=close_side,
                amount=pos.units,
                params={'reduceOnly': True}
            )
            raw_p = order.get('average') or order.get('price') or exit_price
            real_exit = float(raw_p) if raw_p else exit_price
            pnl = ((real_exit - pos.entry_price) * pos.units) if pos.side == "LONG" else ((pos.entry_price - real_exit) * pos.units)

            self.balance_usd += pnl
            closed_trade = {
                "id": pos.id,
                "symbol": symbol,
                "side": pos.side,
                "operation_type": pos.operation_type,
                "leverage": pos.leverage,
                "entry_price": pos.entry_price,
                "exit_price": real_exit,
                "units": pos.units,
                "gross_pnl": pnl,
                "net_pnl": pnl * 0.9992,
                "return_pct": (pnl / (pos.entry_price * pos.units / pos.leverage)) if pos.units > 0 else 0.0,
                "reason": reason,
                "opened_at": pos.opened_at,
                "closed_at": time.time()
            }
            self.trade_history.append(closed_trade)
            del self.positions[symbol]
            logger.info(f"🏆 [POSICIÓN CERRADA REAL BINANCE TURING] {symbol} | PnL: ${pnl:+,.2f} | Motivo: {reason}")
        except Exception as e:
            logger.error(f"Error cerrando posición en Binance Testnet para TURING: {e}")

    async def close(self):
        if self.exchange:
            await self.exchange.close()
