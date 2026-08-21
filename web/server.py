import asyncio
import json
import logging
from aiohttp import web
from typing import Dict, Set

logger = logging.getLogger("WebServerTuring")

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KuQuant TURING (The Apex Quantum General) • Tier 1 Neural Engine 24/7</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root[data-theme="dark"] {
            --bg-base: #06090e;
            --bg-card: #0d121d;
            --bg-hover: #151d2e;
            --border: #1f293d;
            --border-light: #2c3b57;
            --text-primary: #ffffff;
            --text-secondary: #9aa8bd;
            --text-muted: #62718a;
            --accent: #00f0ff; /* Turing Cyan */
            --accent-glow: rgba(0, 240, 255, 0.25);
            --gold: #ffd700;
            --purple: #bf00ff;
            --green: #00ff88;
            --green-bright: #39ff14; /* Verde Claro Ultra-Brillante para Locked Profit */
            --green-glow: rgba(57, 255, 20, 0.25);
            --red: #ff3366;
            --red-glow: rgba(255, 51, 102, 0.20);
        }

        :root[data-theme="light"] {
            --bg-base: #f0f4f8;
            --bg-card: #ffffff;
            --bg-hover: #e8eef5;
            --border: #d4e0ed;
            --border-light: #b9cde3;
            --text-primary: #0a111a;
            --text-secondary: #4a5d73;
            --text-muted: #7e94ac;
            --accent: #0088cc;
            --accent-glow: rgba(0, 136, 204, 0.15);
            --gold: #d4a017;
            --purple: #8a00cc;
            --green: #059669;
            --green-bright: #10b981;
            --green-glow: rgba(16, 185, 129, 0.20);
            --red: #dc2626;
            --red-glow: rgba(220, 38, 38, 0.15);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            transition: background-color 0.25s ease, border-color 0.25s ease, color 0.25s ease;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-base);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        .mono { font-family: 'JetBrains Mono', monospace; }

        header {
            background-color: var(--bg-card);
            border-bottom: 1px solid var(--border);
            padding: 14px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 50;
        }

        .brand { display: flex; align-items: center; gap: 14px; }
        .logo-icon {
            width: 42px;
            height: 42px;
            background: linear-gradient(135deg, var(--accent), var(--purple));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            box-shadow: 0 0 20px var(--accent-glow);
        }

        .brand h1 { font-size: 18px; font-weight: 800; }
        .brand span { font-size: 11px; color: var(--accent); letter-spacing: 0.5px; }

        .cluster-nav {
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--bg-base);
            padding: 6px;
            border-radius: 10px;
            border: 1px solid var(--border);
        }

        .cluster-link {
            padding: 5px 10px;
            font-size: 11px;
            font-weight: 700;
            border-radius: 6px;
            text-decoration: none;
            color: var(--text-secondary);
        }

        .cluster-link:hover {
            color: var(--text-primary);
            background: var(--bg-hover);
        }

        .cluster-link.active {
            background: var(--accent);
            color: #000;
            box-shadow: 0 0 12px var(--accent-glow);
        }

        .header-actions { display: flex; align-items: center; gap: 12px; }

        .theme-btn {
            background: var(--bg-hover);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 7px 12px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .theme-btn:hover { border-color: var(--accent); }

        .btn-reset {
            background: rgba(255, 215, 0, 0.15);
            border: 1px solid var(--gold);
            color: var(--gold);
            padding: 7px 14px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 11px;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
        }
        .btn-reset:hover { background: var(--gold); color: #000; }

        main {
            padding: 24px;
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .neural-banner {
            background: linear-gradient(180deg, var(--bg-card), var(--bg-base));
            border: 1px solid var(--accent);
            border-radius: 14px;
            padding: 18px 22px;
            box-shadow: 0 0 25px rgba(0, 240, 255, 0.08);
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .neural-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            font-weight: 700;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }

        .neural-thought {
            font-size: 14px;
            line-height: 1.5;
            color: var(--text-primary);
            font-family: 'JetBrains Mono', monospace;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 16px;
        }

        .metric-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .metric-title {
            font-size: 12px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }

        .metric-value {
            font-size: 26px;
            font-weight: 800;
        }

        .metric-sub {
            font-size: 11px;
            color: var(--text-muted);
        }

        .table-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 20px;
            overflow-x: auto;
        }

        .table-card h3 {
            font-size: 15px;
            font-weight: 700;
            margin-bottom: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }

        th {
            text-align: left;
            padding: 10px 12px;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border);
            font-size: 11px;
            text-transform: uppercase;
        }

        td {
            padding: 14px 12px;
            border-bottom: 1px solid var(--border);
        }

        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
        }
        .badge-buy { background: var(--green-glow); color: var(--green); border: 1px solid var(--green); }
        .badge-sell { background: var(--red-glow); color: var(--red); border: 1px solid var(--red); }
        .badge-lev { background: rgba(255, 215, 0, 0.15); color: var(--gold); border: 1px solid var(--gold); }
        
        /* ESTILOS DE GANANCIA BLOQUEADA (LOCKED PROFIT) EN VERDE CLARO BRILLANTE */
        .badge-locked {
            background: rgba(57, 255, 20, 0.18);
            color: var(--green-bright);
            border: 1px solid var(--green-bright);
            font-weight: 800;
            box-shadow: 0 0 10px var(--green-glow);
            text-shadow: 0 0 6px rgba(57, 255, 20, 0.4);
        }
        .badge-be {
            background: rgba(0, 240, 255, 0.15);
            color: var(--accent);
            border: 1px solid var(--accent);
            font-weight: 700;
        }
        .badge-open {
            background: var(--bg-hover);
            color: var(--text-muted);
            border: 1px solid var(--border);
        }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <div class="logo-icon">👑</div>
            <div>
                <h1>KuQuant TURING <span style="font-size: 12px; color: var(--accent); font-weight: 600;">(Tier 1 Apex General)</span></h1>
                <div class="mono" style="font-size: 11px; color: var(--text-muted);">FÍSICA TEÓRICA + ISING SPIN GLASS + APALANCAMIENTO 1X A 10X</div>
            </div>
        </div>

        <div class="cluster-nav mono">
            <a href="https://crypto-trading-bot-1-iz21.onrender.com" class="cluster-link" target="_blank">🟢 CLASSIC</a>
            <a href="https://crypto-trading-bot-turbo.onrender.com" class="cluster-link" target="_blank">⚡ TURBO</a>
            <a href="https://crypto-trading-bot-apex.onrender.com" class="cluster-link" target="_blank">🩸 APEX</a>
            <a href="https://crypto-trading-bot-bare.onrender.com" class="cluster-link" target="_blank">⚛️ BARE</a>
            <a href="https://crypto-trading-bot-nexus.onrender.com" class="cluster-link" target="_blank">🌌 NEXUS</a>
            <a href="#" class="cluster-link active">👑 TURING</a>
        </div>

        <div class="header-actions">
            <button class="btn-reset" onclick="resetCircuitBreaker()">⚡ RESET CB</button>
            <button class="theme-btn" id="theme-toggle-btn" onclick="toggleTheme()">☀️ Claro</button>
        </div>
    </header>

    <main>
        <div class="neural-banner">
            <div class="neural-header">
                <span>🧠 Auto-Conciencia & Stream Neuronal Introspectivo</span>
                <span class="mono" id="turing-cycle" style="font-size: 11px; color: var(--text-muted);">Ciclo #0</span>
            </div>
            <div class="neural-thought" id="turing-thought">Cargando matrices de física cuántica y banco de memoria...</div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-title">Balance / Equity Total</div>
                <div class="metric-value mono" id="val-equity">$10,000.00</div>
                <div class="metric-sub mono" id="val-pnl">+0.00% PnL Global</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Ganancia Asegurada (Locked Profit)</div>
                <div class="metric-value mono" style="color: var(--green-bright); text-shadow: 0 0 12px var(--green-glow);" id="val-locked">$0.00</div>
                <div class="metric-sub mono" style="color: var(--green-bright);" id="val-locked-sub">0 Posiciones Blindadas</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Apalancamiento Óptimo</div>
                <div class="metric-value mono" style="color: var(--gold);" id="val-leverage">3.0x</div>
                <div class="metric-sub">Dinámico Autónomo (1x a 10x)</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Modelo de Ising (Magnetización)</div>
                <div class="metric-value mono" style="color: var(--accent);" id="val-ising">0.00 M</div>
                <div class="metric-sub mono" id="val-chi">Susceptibilidad Chi: 0.00</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Entropía Cuántica L2</div>
                <div class="metric-value mono" style="color: var(--purple);" id="val-entropy">0.30 S</div>
                <div class="metric-sub mono" id="val-hurst">Hurst Rugoso: H ~ 0.10</div>
            </div>
        </div>

        <div class="table-card">
            <h3>
                <span>Posiciones Abiertas en Tiempo Real (Detalle Milimétrico & Trailing)</span>
                <span class="mono" style="font-size: 12px; color: var(--green-bright);" id="pos-count-badge">0 Activas</span>
            </h3>
            <table>
                <thead>
                    <tr class="mono">
                        <th>Par</th>
                        <th>Lado</th>
                        <th>Tipo Operación</th>
                        <th>Apalancamiento</th>
                        <th>Precio Entrada</th>
                        <th>Precio Actual</th>
                        <th>PnL Flotante</th>
                        <th>Stop Loss / Trailing</th>
                        <th>Take Profit (1:4.8)</th>
                        <th>Estado / Blindaje</th>
                    </tr>
                </thead>
                <tbody id="positions-body" class="mono">
                    <tr><td colspan="10" style="text-align: center; color: var(--text-muted);">Escaneando pares de alta volatilidad...</td></tr>
                </tbody>
            </table>
        </div>

        <div class="table-card">
            <h3>Historial de Órdenes y Experiencia Consolidada</h3>
            <table>
                <thead>
                    <tr class="mono">
                        <th>ID</th>
                        <th>Par</th>
                        <th>Lado</th>
                        <th>Apalancamiento</th>
                        <th>Precio Entrada</th>
                        <th>Precio Salida</th>
                        <th>PnL Neto</th>
                        <th>Retorno %</th>
                        <th>Motivo de Cierre</th>
                    </tr>
                </thead>
                <tbody id="history-body" class="mono">
                    <tr><td colspan="9" style="text-align: center; color: var(--text-muted);">Sin órdenes cerradas aún.</td></tr>
                </tbody>
            </table>
        </div>
    </main>

    <script>
        function setTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('kuquant_theme', theme);
            const btn = document.getElementById('theme-toggle-btn');
            btn.innerHTML = theme === 'dark' ? '☀️ Claro' : '🌙 Oscuro';
        }

        function toggleTheme() {
            const curr = document.documentElement.getAttribute('data-theme') || 'dark';
            setTheme(curr === 'dark' ? 'light' : 'dark');
        }

        const savedTheme = localStorage.getItem('kuquant_theme') || 'dark';
        setTheme(savedTheme);

        async function resetCircuitBreaker() {
            try {
                const res = await fetch('/api/reset-cb', { method: 'POST' });
                const d = await res.json();
                alert(d.message || 'Circuit breaker reiniciado');
            } catch (e) {
                alert('Error al reiniciar');
            }
        }

        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                if (!res.ok) return;
                const data = await res.json();

                const eq = parseFloat(data.equity || 10000.0);
                const pnl = ((eq - (parseFloat(data.initial_balance) || eq)) / (parseFloat(data.initial_balance) || eq)) * 100;
                document.getElementById('val-equity').innerText = '$' + eq.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                document.getElementById('val-pnl').innerText = (pnl >= 0 ? '+' : '') + pnl.toFixed(2) + '% PnL Global';
                document.getElementById('val-pnl').style.color = pnl >= 0 ? 'var(--green)' : 'var(--red)';

                document.getElementById('turing-cycle').innerText = 'Ciclo #' + (data.iteration || 0);
                if (data.reflection_message) {
                    document.getElementById('turing-thought').innerText = data.reflection_message;
                }

                if (data.active_leverage) {
                    document.getElementById('val-leverage').innerText = data.active_leverage.toFixed(1) + 'x';
                }

                const currentPrices = data.current_prices || {};

                // Renderizar Posiciones Detalladas
                const posBody = document.getElementById('positions-body');
                const posKeys = Object.keys(data.positions || {});
                document.getElementById('pos-count-badge').innerText = posKeys.length + ' Activas';

                let totalLockedUsd = 0.0;
                let lockedCount = 0;

                if (posKeys.length > 0) {
                    posBody.innerHTML = posKeys.map(k => {
                        const p = data.positions[k];
                        const currP = currentPrices[p.symbol] || p.entry_price;
                        
                        let unRealizedPnl = 0.0;
                        let unRealizedPct = 0.0;
                        if (p.side === 'LONG') {
                            unRealizedPnl = (currP - p.entry_price) * p.units;
                            unRealizedPct = ((currP - p.entry_price) / p.entry_price) * (p.leverage || 1.0) * 100;
                        } else {
                            unRealizedPnl = (p.entry_price - currP) * p.units;
                            unRealizedPct = ((p.entry_price - currP) / p.entry_price) * (p.leverage || 1.0) * 100;
                        }

                        // Cálculo de Locked Profit
                        let lockedBadge = '<span class="badge badge-open">⏳ ABIERTA</span>';
                        if (p.profit_lock_stage === 1) {
                            lockedBadge = '<span class="badge badge-be">🛡️ BREAK-EVEN</span>';
                        } else if (p.profit_lock_stage === 2) {
                            const lockedUsd = (p.side === 'LONG' ? (p.stop_loss - p.entry_price) : (p.entry_price - p.stop_loss)) * p.units;
                            totalLockedUsd += Math.max(0, lockedUsd);
                            lockedCount++;
                            lockedBadge = `<span class="badge badge-locked">💎 LOCKED +$${Math.max(0, lockedUsd).toFixed(2)}</span>`;
                        } else if (p.profit_lock_stage >= 3) {
                            const lockedUsd = (p.side === 'LONG' ? (p.stop_loss - p.entry_price) : (p.entry_price - p.stop_loss)) * p.units;
                            totalLockedUsd += Math.max(0, lockedUsd);
                            lockedCount++;
                            lockedBadge = `<span class="badge badge-locked">⚡ TRAILING +$${Math.max(0, lockedUsd).toFixed(2)}</span>`;
                        }

                        const pnlColor = unRealizedPnl >= 0 ? 'var(--green-bright)' : 'var(--red)';
                        const bClass = p.side === 'LONG' ? 'badge-buy' : 'badge-sell';

                        return `<tr>
                            <td><strong>${p.symbol}</strong></td>
                            <td><span class="badge ${bClass}">${p.side}</span></td>
                            <td><span style="color: var(--accent); font-weight: 700;">${p.operation_type || 'BREAKOUT'}</span></td>
                            <td><span class="badge badge-lev">${(p.leverage || 3.0).toFixed(1)}x</span></td>
                            <td>$${p.entry_price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 4})}</td>
                            <td style="font-weight: 700;">$${currP.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 4})}</td>
                            <td style="color: ${pnlColor}; font-weight: 800;">${unRealizedPnl >= 0 ? '+' : ''}$${unRealizedPnl.toFixed(2)} (${unRealizedPct >= 0 ? '+' : ''}${unRealizedPct.toFixed(2)}%)</td>
                            <td style="color: var(--red);">$${p.stop_loss.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 4})}</td>
                            <td style="color: var(--green);">$${p.take_profit.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 4})}</td>
                            <td>${lockedBadge}</td>
                        </tr>`;
                    }).join('');
                } else {
                    posBody.innerHTML = '<tr><td colspan="10" style="text-align: center; color: var(--text-muted);">Sin posiciones abiertas. Buscando confluencia cuántica...</td></tr>';
                }

                // Actualizar Métrica de Locked Profit en Verde Brillante
                document.getElementById('val-locked').innerText = '+$' + totalLockedUsd.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                document.getElementById('val-locked-sub').innerText = lockedCount + ' Posiciones con Ganancia Blindada';

                // Historial Detallado
                const histBody = document.getElementById('history-body');
                const trades = data.trade_history || [];
                if (trades.length > 0) {
                    histBody.innerHTML = trades.slice(-12).reverse().map(t => {
                        const bClass = t.side === 'LONG' ? 'badge-buy' : 'badge-sell';
                        const pnlVal = parseFloat(t.net_pnl || 0);
                        const pnlCol = pnlVal >= 0 ? 'var(--green-bright)' : 'var(--red)';
                        return `<tr>
                            <td>${t.id}</td>
                            <td><strong>${t.symbol}</strong></td>
                            <td><span class="badge ${bClass}">${t.side}</span></td>
                            <td><span class="badge badge-lev">${(t.leverage || 3.0).toFixed(1)}x</span></td>
                            <td>$${(t.entry_price || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                            <td>$${(t.exit_price || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                            <td style="color: ${pnlCol}; font-weight: 800;">${pnlVal >= 0 ? '+' : ''}$${pnlVal.toFixed(2)}</td>
                            <td style="color: ${pnlCol}; font-weight: 700;">${((t.return_pct || 0) * 100).toFixed(2)}%</td>
                            <td>${t.reason || 'EXIT'}</td>
                        </tr>`;
                    }).join('');
                }
            } catch (e) {
                console.error(e);
            }
        }

        setInterval(fetchStatus, 1000);
        fetchStatus();
    </script>
</body>
</html>
"""

class TuringDashboardServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8000, on_reset_circuit_breaker=None):
        self.host = host
        self.port = port
        self.on_reset_circuit_breaker = on_reset_circuit_breaker
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.latest_state = {}

        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_post('/api/reset-cb', self.handle_reset_cb)
        self.app.router.add_post('/api/sentinel-push', self.handle_sentinel_push)

    async def handle_index(self, request):
        return web.Response(text=DASHBOARD_HTML, content_type='text/html')

    async def handle_status(self, request):
        return web.json_response(self.latest_state)

    async def handle_reset_cb(self, request):
        if self.on_reset_circuit_breaker:
            self.on_reset_circuit_breaker()
        return web.json_response({"status": "success", "message": "Circuit breaker TURING reiniciado"})

    async def handle_sentinel_push(self, request):
        try:
            alert = await request.json()
            if hasattr(self, 'on_sentinel_push') and self.on_sentinel_push:
                await self.on_sentinel_push(alert)
            return web.json_response({"status": "received", "timestamp": alert.get("timestamp")})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=400)

    async def broadcast_state(self, state: Dict):
        self.latest_state = state

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        logger.info(f"👑 [DASHBOARD TURING DISPONIBLE EN]: http://localhost:{self.port}")

    async def stop(self):
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
