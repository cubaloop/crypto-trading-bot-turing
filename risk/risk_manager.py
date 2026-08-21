import logging
import time
import math
from typing import Tuple

logger = logging.getLogger("RiskManagerTuring")

class TuringRiskManager:
    def __init__(
        self,
        initial_balance: float = 10000.0,
        risk_per_trade_pct: float = 0.08,
        max_daily_drawdown_pct: float = 0.12
    ):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.peak_equity = initial_balance
        self.risk_per_trade_pct = 0.08
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        self.circuit_breaker_triggered = False
        self.triggered_at = 0.0

    def update_equity(self, current_equity: float):
        self.current_balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        drawdown = (self.peak_equity - current_equity) / self.peak_equity if self.peak_equity > 0 else 0.0

        if drawdown >= self.max_daily_drawdown_pct and not self.circuit_breaker_triggered:
            self.circuit_breaker_triggered = True
            self.triggered_at = time.time()
            logger.critical(f"🚨 [TURING CIRCUIT BREAKER]: Drawdown crítico de {drawdown:.1%}. Modo de protección activado.")

    def check_auto_reactivation(self, signal_conviction: float) -> Tuple[bool, str]:
        if not self.circuit_breaker_triggered:
            return True, "Operativa Normal 24/7"

        # Auto-reactivación con señal ultra-convincente
        if abs(signal_conviction) >= 0.65:
            self.circuit_breaker_triggered = False
            logger.info("⚡ [TURING AUTO-REACTIVACIÓN]: Señal de Máxima Convicción Cuántica (>0.65). Reactivando motor.")
            return True, "Reactivación por Alta Convicción"

        return False, "Circuit Breaker Activo (Búnker de Protección)"

    def compute_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        leverage: float = 3.0,
        conviction: float = 0.50
    ) -> float:
        if entry_price <= 0:
            return 0.0

        risk_dist = abs(entry_price - stop_loss_price)
        if risk_dist <= 0:
            return 0.0

        # Criterio de Kelly Fraccionario Adaptativo
        conviction_mult = min(2.0, 0.8 + (1.2 * abs(conviction)))
        adjusted_risk_pct = self.risk_per_trade_pct * conviction_mult
        risk_capital = self.current_balance * adjusted_risk_pct

        # Unidades base
        base_units = risk_capital / risk_dist
        # Aplicación de apalancamiento seguro
        leveraged_units = base_units * (leverage / 3.0)

        # Límite de no sobrepasar el capital disponible x apalancamiento
        max_notional = self.current_balance * leverage
        max_units = max_notional / entry_price

        final_units = min(leveraged_units, max_units)
        return float(max(0.0, final_units))

    def reset_circuit_breaker(self):
        self.circuit_breaker_triggered = False
        self.peak_equity = self.current_balance
        logger.info("⚡ [TURING]: Circuit breaker reiniciado manualmente.")
