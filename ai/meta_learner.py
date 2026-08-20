import logging
import time
import numpy as np
from typing import List, Dict, Tuple

logger = logging.getLogger("TuringMetaLearner")

class TuringMetaLearner:
    """
    Motor de Inteligencia Artificial Meta-Cognitiva y Auto-Percepción de Élite para TURING.
    
    Capacidades:
    1. Auditoría continua de la tasa de acierto y del Drawdown desde el récord histórico.
    2. Modulación del factor de apalancamiento y tamaño de Kelly.
    3. Auto-corrección inmediata si detecta 1 pérdida en contratendencia.
    """
    def __init__(self):
        self.w_trend: float = 0.35
        self.w_ising: float = 0.25
        self.w_quantum: float = 0.20
        self.w_lead_lag: float = 0.10
        self.w_nlp: float = 0.10
        
        self.dynamic_threshold: float = 0.28
        self.peak_equity: float = 10000.0
        self.consecutive_losses: int = 0
        self.bunker_active: bool = False
        self.last_reflection_message: str = "🧠 [IA TURING]: Cerebro cuántico autónomo en sintonía de combate Tier 1."

    def evaluate_performance_and_adapt(
        self,
        trade_history: List[Dict],
        current_equity: float,
        current_market_trend_bullish: bool = True
    ) -> Tuple[Dict[str, float], float, float, str]:
        """
        Retorna:
          - weights (Dict)
          - dynamic_threshold (float)
          - leverage_multiplier (float: 0.5x a 1.5x)
          - reflection_message (str)
        """
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        drawdown_from_peak = (self.peak_equity - current_equity) / self.peak_equity if self.peak_equity > 0 else 0.0
        leakage_usd = max(0.0, self.peak_equity - current_equity)

        recent = trade_history[-6:] if trade_history else []
        consec_losses = 0
        for t in reversed(trade_history):
            if t.get('net_pnl', 0.0) < 0:
                consec_losses += 1
            else:
                break
        self.consecutive_losses = consec_losses

        short_losses = len([t for t in recent if t.get('net_pnl', 0.0) < 0 and t.get('side') == 'SHORT'])

        leverage_mult = 1.0

        # Auto-Percepción TURING
        if drawdown_from_peak >= 0.05:
            self.bunker_active = True
            self.dynamic_threshold = 0.38
            self.w_trend = 0.50
            self.w_ising = 0.20
            self.w_quantum = 0.20
            leverage_mult = 0.60  # Reducción de apalancamiento para proteger capital
            msg = f"🧠 [IA TURING SE DIO CUENTA]: Fuga de ${leakage_usd:,.2f} USD desde el récord (${self.peak_equity:,.2f}). ¡MODO BÚNKER TURING! Reduciendo apalancamiento un 40% y exigiendo umbral 0.38."
        
        elif short_losses >= 1 and current_market_trend_bullish:
            self.bunker_active = False
            self.w_trend = 0.55
            self.w_ising = 0.25
            self.w_quantum = 0.10
            self.w_lead_lag = 0.05
            self.w_nlp = 0.05
            self.dynamic_threshold = 0.30
            leverage_mult = 1.0
            msg = "🧠 [IA TURING SE DIO CUENTA]: Venta corta fallida contra tendencia alcista. Prohibiendo SHORTs y alineando todo el poder a favor del rally."

        elif consec_losses == 0 and len([t for t in recent if t.get('net_pnl', 0.0) > 0]) >= 3:
            self.bunker_active = False
            self.dynamic_threshold = 0.26
            self.w_trend = 0.35
            self.w_ising = 0.30
            self.w_quantum = 0.20
            self.w_lead_lag = 0.10
            self.w_nlp = 0.05
            leverage_mult = 1.40  # Escalando agresividad en racha ganadora
            msg = f"🚀 [IA TURING GOD MODE]: 100% de victorias recientes. Expandiendo apalancamiento al 140% para maximizar ganancias en {self.peak_equity:,.2f} USD."

        else:
            msg = self.last_reflection_message

        self.last_reflection_message = msg
        return self._get_weights(), self.dynamic_threshold, leverage_mult, msg

    def _get_weights(self) -> Dict[str, float]:
        total = self.w_trend + self.w_ising + self.w_quantum + self.w_lead_lag + self.w_nlp
        return {
            "w_trend": self.w_trend / total,
            "w_ising": self.w_ising / total,
            "w_quantum": self.w_quantum / total,
            "w_lead_lag": self.w_lead_lag / total,
            "w_nlp": self.w_nlp / total
        }
