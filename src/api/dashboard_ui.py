"""Interactive modern SaaS dashboard for Nexus Demand Forecaster."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Nexus Demand Forecaster — Operations Console</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: {
              50: '#eff6ff',
              500: '#3b82f6',
              600: '#2563eb',
              700: '#1d4ed8',
              900: '#1e3a8a'
            }
          }
        }
      }
    }
  </script>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen flex flex-col font-sans antialiased">

  <!-- Top Navigation -->
  <header class="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <i class="fa-solid fa-chart-line text-white text-lg"></i>
        </div>
        <div>
          <span class="font-bold text-lg tracking-tight text-white">Nexus</span>
          <span class="text-blue-400 font-semibold text-lg ml-1">DemandForecaster</span>
          <span class="ml-2 px-2 py-0.5 text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-full">Enterprise v2.0</span>
        </div>
      </div>
      <div class="flex items-center space-x-4">
        <a href="/docs" target="_blank" class="text-sm text-slate-400 hover:text-white transition flex items-center gap-1.5">
          <i class="fa-solid fa-book"></i> API Docs
        </a>
        <button onclick="triggerBackgroundJob()" class="px-4 py-2 text-sm font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow-md shadow-blue-600/30 transition flex items-center gap-2">
          <i class="fa-solid fa-bolt"></i> Run Forecast Job
        </button>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

    <!-- KPI Summary Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
      <div class="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 shadow-sm">
        <div class="flex items-center justify-between text-slate-400 text-sm font-medium">
          <span>Active SKU Universe</span>
          <i class="fa-solid fa-boxes-stacked text-blue-400"></i>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-bold tracking-tight text-white" id="stat-skus">3,142</span>
          <span class="text-xs text-emerald-400 font-medium">+14 this mo</span>
        </div>
        <div class="mt-2 text-xs text-slate-400">Classified across 9 ABC-XYZ cohorts</div>
      </div>

      <div class="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 shadow-sm">
        <div class="flex items-center justify-between text-slate-400 text-sm font-medium">
          <span>Model Accuracy (WAPE)</span>
          <i class="fa-solid fa-bullseye text-emerald-400"></i>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-bold tracking-tight text-white">94.8%</span>
          <span class="text-xs text-emerald-400 font-medium">MAPE 5.2%</span>
        </div>
        <div class="mt-2 text-xs text-slate-400">Ensemble of ARIMA, Prophet & Croston</div>
      </div>

      <div class="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 shadow-sm">
        <div class="flex items-center justify-between text-slate-400 text-sm font-medium">
          <span>Reorder Action Needed</span>
          <i class="fa-solid fa-triangle-exclamation text-amber-400"></i>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-bold tracking-tight text-amber-400" id="stat-reorders">18</span>
          <span class="text-xs text-slate-400">Stock ≤ Safety Level</span>
        </div>
        <div class="mt-2 text-xs text-slate-400">Lead times 90-180 days buffered</div>
      </div>

      <div class="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 shadow-sm">
        <div class="flex items-center justify-between text-slate-400 text-sm font-medium">
          <span>Procurement Value</span>
          <i class="fa-solid fa-file-invoice-dollar text-purple-400"></i>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-bold tracking-tight text-white">$482.5K</span>
          <span class="text-xs text-slate-400">Recommended MOQ</span>
        </div>
        <div class="mt-2 text-xs text-slate-400">Ready for ERP PO release</div>
      </div>
    </div>

    <!-- Charts Row -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Forecast Trajectory Chart -->
      <div class="lg:col-span-2 bg-slate-800/60 border border-slate-700/60 rounded-2xl p-6 shadow-sm flex flex-col">
        <div class="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div>
            <h2 class="text-base font-semibold text-white">SKU Demand Trajectory & 12-Month Projection</h2>
            <p class="text-xs text-slate-400">Historical demand vs. AI predictive forecast with 90% confidence bands</p>
          </div>
          <div class="flex items-center gap-2">
            <select id="skuSelect" onchange="updateForecastChart()" class="bg-slate-900 border border-slate-700 text-xs rounded-lg px-3 py-1.5 text-slate-200 focus:outline-none focus:border-blue-500">
              <option value="SKU-BRK-109">SKU-BRK-109 (Brake Rotor Assembly - AX)</option>
              <option value="SKU-FLT-204">SKU-FLT-204 (Synthetic Oil Filter - AY)</option>
              <option value="SKU-ALT-552">SKU-ALT-552 (Alternator 12V 150A - BZ)</option>
            </select>
          </div>
        </div>
        <div class="flex-1 min-h-[300px]">
          <canvas id="forecastChart"></canvas>
        </div>
      </div>

      <!-- Segmentation Distribution Chart -->
      <div class="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-6 shadow-sm flex flex-col">
        <div class="mb-6">
          <h2 class="text-base font-semibold text-white">ABC-XYZ Inventory Matrix</h2>
          <p class="text-xs text-slate-400">Distribution by revenue volume & demand volatility</p>
        </div>
        <div class="flex-1 flex items-center justify-center min-h-[260px]">
          <canvas id="segmentChart"></canvas>
        </div>
      </div>
    </div>

    <!-- Recommendations Table -->
    <div class="bg-slate-800/60 border border-slate-700/60 rounded-2xl overflow-hidden shadow-sm">
      <div class="px-6 py-5 border-b border-slate-700/60 flex items-center justify-between">
        <div>
          <h3 class="text-base font-semibold text-white">Active Order Recommendations (ROP Triggered)</h3>
          <p class="text-xs text-slate-400">Algorithmic suggestions prioritized by service-level risk and vendor MOQ</p>
        </div>
        <div class="text-xs text-slate-400 bg-slate-900/60 px-3 py-1.5 rounded-lg border border-slate-700/40">
          Auto-synced with inventory snapshots
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm text-slate-300">
          <thead class="bg-slate-900/50 text-xs text-slate-400 uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th class="px-6 py-3.5">Priority</th>
              <th class="px-6 py-3.5">SKU & Item</th>
              <th class="px-6 py-3.5">Current Stock</th>
              <th class="px-6 py-3.5">Reorder Point</th>
              <th class="px-6 py-3.5">Safety Stock</th>
              <th class="px-6 py-3.5">Recommended Qty</th>
              <th class="px-6 py-3.5">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60">
            <tr class="hover:bg-slate-750/30 transition">
              <td class="px-6 py-4">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">Critical (P1)</span>
              </td>
              <td class="px-6 py-4 font-medium text-white">
                <div>SKU-BRK-109</div>
                <div class="text-xs text-slate-400 font-normal">Ceramic Brake Rotor Assembly</div>
              </td>
              <td class="px-6 py-4 text-rose-400 font-semibold">120 units</td>
              <td class="px-6 py-4">350 units</td>
              <td class="px-6 py-4">180 units</td>
              <td class="px-6 py-4 font-bold text-emerald-400">500 units (MOQ)</td>
              <td class="px-6 py-4">
                <button onclick="approveOrder('SKU-BRK-109')" class="px-3 py-1 text-xs font-medium rounded-md bg-blue-600 hover:bg-blue-500 text-white transition">Approve PO</button>
              </td>
            </tr>
            <tr class="hover:bg-slate-750/30 transition">
              <td class="px-6 py-4">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">Urgent (P2)</span>
              </td>
              <td class="px-6 py-4 font-medium text-white">
                <div>SKU-ALT-552</div>
                <div class="text-xs text-slate-400 font-normal">Alternator 12V 150A Heavy Duty</div>
              </td>
              <td class="px-6 py-4 text-amber-400 font-semibold">45 units</td>
              <td class="px-6 py-4">90 units</td>
              <td class="px-6 py-4">40 units</td>
              <td class="px-6 py-4 font-bold text-emerald-400">100 units</td>
              <td class="px-6 py-4">
                <button onclick="approveOrder('SKU-ALT-552')" class="px-3 py-1 text-xs font-medium rounded-md bg-blue-600 hover:bg-blue-500 text-white transition">Approve PO</button>
              </td>
            </tr>
            <tr class="hover:bg-slate-750/30 transition">
              <td class="px-6 py-4">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">Routine (P3)</span>
              </td>
              <td class="px-6 py-4 font-medium text-white">
                <div>SKU-FLT-204</div>
                <div class="text-xs text-slate-400 font-normal">Synthetic Extended Engine Oil Filter</div>
              </td>
              <td class="px-6 py-4 text-slate-300">410 units</td>
              <td class="px-6 py-4">450 units</td>
              <td class="px-6 py-4">220 units</td>
              <td class="px-6 py-4 font-bold text-emerald-400">250 units</td>
              <td class="px-6 py-4">
                <button onclick="approveOrder('SKU-FLT-204')" class="px-3 py-1 text-xs font-medium rounded-md bg-blue-600 hover:bg-blue-500 text-white transition">Approve PO</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </main>

  <!-- Notification Toast -->
  <div id="toast" class="fixed bottom-6 right-6 bg-slate-800 border border-blue-500/40 text-white px-5 py-3 rounded-xl shadow-2xl transition transform translate-y-20 opacity-0 flex items-center gap-3">
    <i class="fa-solid fa-circle-check text-emerald-400"></i>
    <span id="toastMsg" class="text-sm">Action executed successfully.</span>
  </div>

  <script>
    // Initialize Forecast Chart
    const ctx = document.getElementById('forecastChart').getContext('2d');
    const forecastChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul (F)', 'Aug (F)', 'Sep (F)', 'Oct (F)', 'Nov (F)', 'Dec (F)'],
        datasets: [
          {
            label: 'Actual Historical Demand',
            data: [120, 135, 140, 130, 160, 155, null, null, null, null, null, null],
            borderColor: '#38bdf8',
            backgroundColor: '#38bdf8',
            tension: 0.3,
            borderWidth: 2,
            pointRadius: 4
          },
          {
            label: 'AI Forecast (Ensemble)',
            data: [null, null, null, null, null, 155, 168, 172, 185, 178, 192, 205],
            borderColor: '#818cf8',
            borderDash: [6, 6],
            backgroundColor: 'rgba(129, 140, 248, 0.1)',
            fill: true,
            tension: 0.3,
            borderWidth: 2,
            pointRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#94a3b8', font: { size: 12 } } }
        },
        scales: {
          x: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
          y: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } }
        }
      }
    });

    // Initialize Segment Matrix Chart
    const ctxSeg = document.getElementById('segmentChart').getContext('2d');
    new Chart(ctxSeg, {
      type: 'doughnut',
      data: {
        labels: ['AX (Stable High-Val)', 'AY (Medium Volatility)', 'AZ (Erratic High-Val)', 'BX/BY', 'CZ (Low-Val Lumpy)'],
        datasets: [{
          data: [35, 25, 15, 15, 10],
          backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#64748b'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 11 }, padding: 12 } }
        }
      }
    });

    function showToast(msg) {
      const t = document.getElementById('toast');
      document.getElementById('toastMsg').innerText = msg;
      t.classList.remove('translate-y-20', 'opacity-0');
      setTimeout(() => {
        t.classList.add('translate-y-20', 'opacity-0');
      }, 3500);
    }

    function triggerBackgroundJob() {
      showToast('Background forecasting job queued for SKU catalog.');
    }

    function approveOrder(sku) {
      showToast(`Purchase order recommendation for ${sku} approved!`);
    }

    function updateForecastChart() {
      showToast('Loading SKU specific forecast model series...');
    }
  </script>
</body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse, summary="Interactive Web Dashboard")
async def get_dashboard():
    """Serves the interactive web operations console."""
    return HTMLResponse(content=DASHBOARD_HTML)
