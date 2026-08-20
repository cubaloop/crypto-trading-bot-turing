import asyncio
import logging
import math
import time
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger("MarketStreamTuring")

@dataclass
class TuringMarketSnapshot:
    symbol: str
    last_price: float
    best_bid: float
    best_ask: float
    order_book_imbalance: float
    volume_delta: float
    vpin: float
    hurst_exponent: float
    entropy: float
    ising_magnetization: float  # -1.0 a +1.0 (Alineación de espines de mercado)
    ising_susceptibility: float # Susceptibilidad a avalanchas de liquidación
    von_neumann_entropy: float  # Pureza cuántica L2 (0 = Estado puro, 1 = Mezcla caótica)
    lead_lag_btc_correlation: float # Correlación instantánea de arrastre con BTC
    timestamp: float

class TuringMarketStream:
    def __init__(self, exchange_id: str = "kucoin", symbols: Optional[List[str]] = None):
        self.exchange_id = exchange_id
        self.symbols = symbols or ["SOL/USDT", "DOGE/USDT", "BTC/USDT", "ETH/USDT", "NEAR/USDT"]
        self.exchange = None
        self.last_prices: Dict[str, float] = {}
        self.snapshots: Dict[str, TuringMarketSnapshot] = {}
        self._price_history: Dict[str, List[float]] = {s: [] for s in self.symbols}
        self._volume_history: Dict[str, List[float]] = {s: [] for s in self.symbols}

    async def initialize(self):
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            self.exchange = exchange_class({
                'enableRateLimit': True,
                'timeout': 10000
            })
            logger.info(f"⚡ [TURING STREAM]: Conectado exitosamente a exchange: {self.exchange_id.upper()}")
        except Exception as e:
            logger.error(f"Error inicializando CCXT en TURING: {e}")

    async def fetch_snapshot(self, symbol: str) -> Optional[TuringMarketSnapshot]:
        if not self.exchange:
            await self.initialize()

        try:
            order_book = await self.exchange.fetch_order_book(symbol, limit=20)
            ticker = await self.exchange.fetch_ticker(symbol)

            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])

            best_bid = bids[0][0] if bids else ticker.get('bid', 0.0)
            best_ask = asks[0][0] if asks else ticker.get('ask', 0.0)
            last_price = ticker.get('last', (best_bid + best_ask) / 2.0 if best_bid and best_ask else 0.0)

            if not last_price or last_price <= 0:
                return None

            self.last_prices[symbol] = last_price
            self._price_history[symbol].append(last_price)
            if len(self._price_history[symbol]) > 200:
                self._price_history[symbol].pop(0)

            # 1. Order Book Imbalance (OBI) L2
            bid_vol = sum([b[1] for b in bids[:10]])
            ask_vol = sum([a[1] for a in asks[:10]])
            total_vol = bid_vol + ask_vol
            obi = (bid_vol - ask_vol) / total_vol if total_vol > 0 else 0.0

            # 2. Modelo de Ising: Magnetización (M) y Susceptibilidad (Chi)
            # Cada nivel del libro actúa como un micro-espín ponderado por volumen
            bid_spins = [+1.0 * (b[1] / (total_vol or 1.0)) for b in bids[:10]]
            ask_spins = [-1.0 * (a[1] / (total_vol or 1.0)) for a in asks[:10]]
            ising_m = float(np.clip(np.sum(bid_spins) + np.sum(ask_spins), -1.0, 1.0))
            variance_spins = np.var(bid_spins + ask_spins) if (bid_spins + ask_spins) else 0.01
            ising_chi = float(variance_spins * 100.0)  # Susceptibilidad de avalancha

            # 3. Entropía Cuántica de Von Neumann L2
            all_vols = [b[1] for b in bids[:10]] + [a[1] for a in asks[:10]]
            p_probs = np.array(all_vols) / max(1e-6, sum(all_vols))
            von_neumann_entropy = float(-np.sum(p_probs * np.log2(p_probs + 1e-9)) / np.log2(len(p_probs) or 1))

            # 4. Exponente de Hurst Rugoso (H ~ 0.10)
            prices = self._price_history[symbol]
            if len(prices) >= 20:
                lags = [2, 4, 8, 16]
                tau = [np.std(np.subtract(prices[lag:], prices[:-lag])) for lag in lags]
                poly = np.polyfit(np.log(lags), np.log(tau + np.finfo(float).eps), 1)
                hurst = float(np.clip(poly[0] * 2.0, 0.05, 0.95))
            else:
                hurst = 0.12  # Valor fractal rugoso por defecto

            # 5. Lead-Lag Correlation con Bitcoin
            btc_prices = self._price_history.get("BTC/USDT", [])
            if symbol != "BTC/USDT" and len(prices) >= 15 and len(btc_prices) >= 15:
                min_len = min(len(prices), len(btc_prices))
                r_corr = np.corrcoef(prices[-min_len:], btc_prices[-min_len:])[0, 1]
                lead_lag_corr = float(r_corr) if not math.isnan(r_corr) else 0.85
            else:
                lead_lag_corr = 1.0

            # 6. VPIN y Volumen Delta
            vol_delta = (bid_vol - ask_vol) / max(1.0, total_vol)
            vpin = float(np.clip(abs(vol_delta) * 0.8 + (1.0 - hurst) * 0.2, 0.05, 0.95))
            entropy = float(np.clip(von_neumann_entropy * 0.7 + (1.0 - abs(obi)) * 0.3, 0.1, 0.95))

            snap = TuringMarketSnapshot(
                symbol=symbol,
                last_price=last_price,
                best_bid=best_bid,
                best_ask=best_ask,
                order_book_imbalance=obi,
                volume_delta=vol_delta,
                vpin=vpin,
                hurst_exponent=hurst,
                entropy=entropy,
                ising_magnetization=ising_m,
                ising_susceptibility=ising_chi,
                von_neumann_entropy=von_neumann_entropy,
                lead_lag_btc_correlation=lead_lag_corr,
                timestamp=time.time()
            )
            self.snapshots[symbol] = snap
            return snap

        except Exception as e:
            logger.error(f"Error obteniendo snapshot en TURING para {symbol}: {e}")
            return None

    async def fetch_ohlcv(self, symbol: str, timeframe: str = "1m", limit: int = 50) -> Optional[pd.DataFrame]:
        if not self.exchange:
            await self.initialize()

        try:
            candles = await self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if not candles:
                return None

            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Error obteniendo OHLCV en TURING para {symbol}: {e}")
            return None

    async def close(self):
        if self.exchange:
            await self.exchange.close()
