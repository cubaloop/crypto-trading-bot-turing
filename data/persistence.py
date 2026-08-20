import json
import os
import logging
from typing import Dict, List, Any

logger = logging.getLogger("StatePersistenceTuring")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
STATE_FILE = os.path.join(DATA_DIR, "trading_state.json")

class StatePersistence:
    @staticmethod
    def ensure_data_dir():
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)

    @staticmethod
    def save_state(balance_usd: float, initial_balance: float, positions: Dict[str, Any], trade_history: List[Dict], order_counter: int):
        StatePersistence.ensure_data_dir()
        positions_serializable = {}
        for sym, pos in positions.items():
            if hasattr(pos, '__dict__'):
                positions_serializable[sym] = dict(pos.__dict__)
            else:
                positions_serializable[sym] = pos

        state_data = {
            "balance_usd": balance_usd,
            "initial_balance": initial_balance,
            "order_counter": order_counter,
            "positions": positions_serializable,
            "trade_history": trade_history[-100:]
        }

        try:
            temp_file = STATE_FILE + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2)
            if os.path.exists(STATE_FILE):
                os.remove(STATE_FILE)
            os.rename(temp_file, STATE_FILE)
        except Exception as e:
            logger.error(f"Error guardando estado persistente: {e}")

    @staticmethod
    def load_state() -> Dict[str, Any]:
        StatePersistence.ensure_data_dir()
        if not os.path.exists(STATE_FILE):
            return {}
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error leyendo estado persistente: {e}")
            return {}
