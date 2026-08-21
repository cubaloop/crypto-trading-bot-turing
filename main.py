import asyncio
import logging
import time
import sys
import os

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("KuQuantTuringMain")

from config.settings import config
from data.ws_market_stream import TuringMarketStream
from data.keep_alive import KeepAliveMesh
from sentiment.cryptopanic_streamer import TuringNewsStreamer
from sentiment.nlp_analyzer import TuringSentimentAnalyzer
from strategies.turing_strategy import TuringStrategy
from ai.meta_learner import TuringMetaLearner
from ai.episodic_memory import EpisodicMemoryEngine, MarketVector
from risk.risk_manager import TuringRiskManager
from execution.executor import PaperExecutor
from execution.binance_testnet_executor import BinanceTestnetExecutorTuring
from web.server import TuringDashboardServer

class TuringTradingEngine:
    def __init__(self):
        self.market_stream = TuringMarketStream(exchange_id=config.exchange_id, symbols=config.symbols)
        self.news_streamer = TuringNewsStreamer(api_key=config.cryptopanic_api_key)
        self.sentiment_analyzer = TuringSentimentAnalyzer(half_life_minutes=config.sentiment_half_life_minutes)
        self.strategy = TuringStrategy(
            signal_threshold=0.28,
            vpin_cutoff=config.vpin_cutoff,
            max_entropy_cutoff=config.max_entropy_cutoff
        )
        self.meta_learner = TuringMetaLearner()
        self.memory_engine = EpisodicMemoryEngine()
        self.risk_manager = TuringRiskManager(
            initial_balance=config.initial_virtual_balance,
            risk_per_trade_pct=config.risk_per_trade_pct,
            max_daily_drawdown_pct=config.max_daily_drawdown_pct
        )
        
        binance_key = os.getenv("BINANCE_TESTNET_API_KEY", "LyS7ZwuG771PRgZSD7T2AoidqJ8FIGnHUrOElsphYMTZg7BQtgkvt8PTEO95zFXX")
        binance_secret = os.getenv("BINANCE_TESTNET_API_SECRET", "EVWlkCZIJAYRe8bgw7Xu7hRamRqjyWxgEms0zzKTPkHwKTU0ALJxUKSJwUhb7gy6")
        logger.info("👑 Conectando KuQuant TURING a Binance Futures Testnet Oficial (testnet.binancefuture.com)")
        self.executor = BinanceTestnetExecutorTuring(api_key=binance_key, secret=binance_secret, default_leverage=3)
            
        self.web_server = TuringDashboardServer(
            host=config.host,
            port=config.port,
            on_reset_circuit_breaker=self.risk_manager.reset_circuit_breaker
        )
        self.keep_alive = KeepAliveMesh(interval_seconds=120)

        self.news_history = []
        self.iteration = 0
        self.is_running = False
        self._last_known_trade_count = 0
        self.last_optimal_leverage = 3.0

    async def initialize(self):
        logger.info("=================================================================")
        logger.info("👑 INICIANDO BOT AUTÓNOMO KUQUANT TURING • TIER 1 QUANTUM GENERAL")
        logger.info(f"Modo: [{config.mode.upper()}] (Capital Virtual: ${config.initial_virtual_balance:,.2f})")
        logger.info(f"Pares Monitoreados: {', '.join(config.symbols)}")
        logger.info(f"Riesgo Agresivo: {config.risk_per_trade_pct:.1%} | Apalancamiento Dinámico: {config.min_leverage}x a {config.max_leverage}x")
        logger.info("Física: Teoría de Cuerdas + Ising Magnetization + Von Neumann Entropy + Memoria Episódica")
        logger.info("=================================================================")

        await self.market_stream.initialize()
        if hasattr(self.executor, 'initialize'):
            await self.executor.initialize()
            if hasattr(self.executor, 'initial_balance') and self.executor.initial_balance > 0:
                self.risk_manager.initial_balance = self.executor.initial_balance
                self.risk_manager.peak_equity = self.executor.initial_balance
                self.meta_learner.peak_equity = self.executor.initial_balance
        await self.web_server.start()
        self.keep_alive.start()

    async def run(self, max_iterations: int = None):
        self.is_running = True
        await self.initialize()

        try:
            while self.is_running:
                self.iteration += 1
                cycle_start = time.time()

                # 1. Ingesta de Noticias y NLP
                if self.iteration % 10 == 1:
                    new_articles = await self.news_streamer.fetch_latest_news()
                    if new_articles:
                        self.news_history.extend(new_articles)
                        for a in new_articles:
                            logger.info(f"📰 [TURING NLP]: '{a.title[:55]}...' (Score: {a.sentiment_score:+.2f})")

                decayed_score, avg_conf, has_black_swan = self.sentiment_analyzer.calculate_decayed_sentiment(self.news_history)

                current_prices = dict(self.market_stream.last_prices)

                # 2. Auto-Reflexión Meta-Cognitiva y Modulación de Apalancamiento
                current_equity_est = self.executor.get_equity(current_prices) if current_prices else self.executor.balance_usd
                dynamic_weights, dynamic_threshold, leverage_mult, reflection_msg = self.meta_learner.evaluate_performance_and_adapt(
                    trade_history=self.executor.trade_history,
                    current_equity=current_equity_est,
                    current_market_trend_bullish=True
                )
                if self.iteration % 20 == 1:
                    logger.info(reflection_msg)

                # 3. Evaluación de Señales Cuánticas en Pares de Alta Volatilidad
                for symbol in config.symbols:
                    snapshot = await self.market_stream.fetch_snapshot(symbol)
                    if not snapshot:
                        continue
                    current_prices[symbol] = snapshot.last_price
                    ohlcv_df = await self.market_stream.fetch_ohlcv(symbol, timeframe=config.timeframe, limit=50)

                    signal = self.strategy.generate_signal(
                        snapshot=snapshot,
                        ohlcv_df=ohlcv_df,
                        decayed_sentiment=decayed_score,
                        dynamic_weights=dynamic_weights,
                        dynamic_threshold=dynamic_threshold,
                        leverage_mult=leverage_mult,
                        has_black_swan=has_black_swan
                    )

                    self.last_optimal_leverage = signal.leverage

                    trade_allowed, reason = self.risk_manager.check_auto_reactivation(
                        signal_conviction=signal.conviction
                    )

                    # CONSULTA AL BANCO DE MEMORIA EPISÓDICA VECTORIAL
                    if trade_allowed and signal.action in ["BUY", "SELL"] and symbol not in self.executor.positions:
                        m_vec = MarketVector(
                            symbol=symbol,
                            action=signal.action,
                            trend_direction=1.0 if signal.action == "BUY" else -1.0,
                            volatility_atr_pct=signal.atr / max(1.0, signal.entry_price),
                            order_book_imbalance=snapshot.order_book_imbalance if snapshot else 0.0,
                            volume_delta=snapshot.volume_delta if snapshot else 0.0,
                            entropy=signal.entropy,
                            ising_magnetization=snapshot.ising_magnetization if snapshot else 0.0,
                            sentiment_score=decayed_score,
                            conviction=signal.conviction
                        )
                        mem_mult, win_rate, mem_insight = self.memory_engine.query_past_experience(m_vec)
                        if mem_mult < 0.50:
                            logger.warning(f"🛑 [MEMORIA TURING VETÓ ORDEN] en {symbol}: {mem_insight}")
                            trade_allowed = False
                        else:
                            if mem_mult > 1.0:
                                logger.info(f"💎 [MEMORIA TURING POTENCIA ORDEN] en {symbol}: {mem_insight}")

                        if trade_allowed:
                            units = self.risk_manager.compute_position_size(
                                entry_price=signal.entry_price,
                                stop_loss_price=signal.stop_loss,
                                leverage=signal.leverage,
                                conviction=signal.conviction
                            )
                            if units > 0:
                                logger.info(
                                    f"👑 [SEÑAL TURING APROBADA] en {symbol}: {signal.action} "
                                    f"({signal.leverage:.1f}x LEV | {signal.operation_type}) | {signal.reason}"
                                )
                                if asyncio.iscoroutinefunction(self.executor.execute_signal):
                                    await self.executor.execute_signal(signal, units)
                                else:
                                    self.executor.execute_signal(signal, units)

                # 4. Trailing Ratchet Milimétrico y Cierre de Órdenes
                if asyncio.iscoroutinefunction(self.executor.update_and_check_exits):
                    await self.executor.update_and_check_exits(current_prices)
                else:
                    self.executor.update_and_check_exits(current_prices)

                # 5. Consolidación de Experiencia en Disco
                if len(self.executor.trade_history) > self._last_known_trade_count:
                    new_trades = self.executor.trade_history[self._last_known_trade_count:]
                    for t in new_trades:
                        t_vec = MarketVector(
                            symbol=t.get('symbol', 'SOL/USDT'),
                            action="BUY" if t.get('side') == "LONG" else "SELL",
                            trend_direction=1.0 if t.get('side') == "LONG" else -1.0,
                            volatility_atr_pct=0.015,
                            order_book_imbalance=0.0,
                            volume_delta=0.0,
                            entropy=0.30,
                            ising_magnetization=0.0,
                            sentiment_score=0.0,
                            conviction=0.6
                        )
                        self.memory_engine.record_completed_trade(
                            pos_id=t.get('id', 'trade'),
                            vector=t_vec,
                            entry_price=t.get('entry_price', 0.0),
                            exit_price=t.get('exit_price', 0.0),
                            net_pnl=t.get('net_pnl', 0.0),
                            opened_at=t.get('opened_at', time.time())
                        )
                    self._last_known_trade_count = len(self.executor.trade_history)

                # 6. Actualizar Balance y Equity
                current_equity = self.executor.get_equity(current_prices)
                self.risk_manager.update_equity(current_equity)

                # 7. Transmisión de Estado al Dashboard Web
                positions_dict = {
                    s: {
                        "id": p.id,
                        "symbol": p.symbol,
                        "side": p.side,
                        "operation_type": p.operation_type,
                        "leverage": p.leverage,
                        "entry_price": p.entry_price,
                        "units": p.units,
                        "stop_loss": p.stop_loss,
                        "take_profit": p.take_profit,
                        "highest_price": p.highest_price,
                        "lowest_price": p.lowest_price,
                        "profit_lock_stage": getattr(p, 'profit_lock_stage', 0),
                        "opened_at": p.opened_at,
                        "notional_usd": p.notional_usd
                    } for s, p in self.executor.positions.items()
                }

                state_payload = {
                    "iteration": self.iteration,
                    "balance": self.executor.balance_usd,
                    "equity": current_equity,
                    "current_prices": current_prices,
                    "circuit_breaker_active": self.risk_manager.circuit_breaker_triggered,
                    "decayed_sentiment": decayed_score,
                    "active_leverage": self.last_optimal_leverage,
                    "reflection_message": reflection_msg,
                    "positions": positions_dict,
                    "trade_history": self.executor.trade_history
                }
                await self.web_server.broadcast_state(state_payload)

                if max_iterations and self.iteration >= max_iterations:
                    break

                elapsed = time.time() - cycle_start
                sleep_time = max(0.1, config.price_poll_interval_seconds - elapsed)
                await asyncio.sleep(sleep_time)

        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info("Cerrando motor TURING...")
        finally:
            await self.shutdown()

    async def shutdown(self):
        self.is_running = False
        await self.market_stream.close()
        await self.web_server.stop()
        logger.info("KuQuant TURING finalizado correctamente.")

async def main():
    bot = TuringTradingEngine()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
