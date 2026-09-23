import os
import re

with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Header Container & Tabs
# Replace header container classes to use max-w-[1720px] and compact padding
content = content.replace(
    '<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">',
    '<div class="w-full max-w-[1720px] mx-auto px-2 sm:px-4 lg:px-6">'
)
content = content.replace(
    '<main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">',
    '<main class="flex-1 w-full max-w-[1720px] mx-auto px-2 sm:px-4 lg:px-6 py-4 space-y-6">'
)

# Replace the tabs container to remove overflow-x-auto and make it compact
old_tabs_container = '<div class="flex items-center p-1 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-inner mx-1 overflow-x-auto">'
new_tabs_container = '<div class="flex items-center p-1 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-inner mx-0.5 flex-nowrap shrink-0">'
content = content.replace(old_tabs_container, new_tabs_container)

# 2. Update Timezone Select options to pure UTC (no cities!)
old_tz_select = """<select id="timezone-select" onchange="changeTimezone(this.value)" class="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer">
              <option value="local" class="bg-slate-900">PC Локальное (Auto)</option>
              <option value="UTC" class="bg-slate-900">UTC (+00:00)</option>
              <option value="Europe/Prague" class="bg-slate-900">Прага / Варшава (UTC+1/+2)</option>
              <option value="Europe/Kyiv" class="bg-slate-900">Киев / Афины (UTC+2/+3)</option>
              <option value="Europe/Moscow" class="bg-slate-900">Москва / Минск (UTC+3)</option>
              <option value="Asia/Yerevan" class="bg-slate-900">Ереван / Баку (UTC+4)</option>
              <option value="Asia/Tashkent" class="bg-slate-900">Ташкент (UTC+5)</option>
              <option value="America/New_York" class="bg-slate-900">Нью-Йорк (EST)</option>
            </select>"""

new_tz_select = """<select id="timezone-select" onchange="changeTimezone(this.value)" class="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer font-mono text-xs">
              <option value="local" class="bg-slate-900">Local (Auto)</option>
              <option value="UTC-10" class="bg-slate-900">UTC-10</option>
              <option value="UTC-8" class="bg-slate-900">UTC-8</option>
              <option value="UTC-5" class="bg-slate-900">UTC-5</option>
              <option value="UTC-4" class="bg-slate-900">UTC-4</option>
              <option value="UTC-3" class="bg-slate-900">UTC-3</option>
              <option value="UTC" class="bg-slate-900">UTC+0</option>
              <option value="UTC+1" class="bg-slate-900">UTC+1</option>
              <option value="UTC+2" class="bg-slate-900">UTC+2</option>
              <option value="UTC+3" class="bg-slate-900" selected>UTC+3</option>
              <option value="UTC+4" class="bg-slate-900">UTC+4</option>
              <option value="UTC+5" class="bg-slate-900">UTC+5</option>
              <option value="UTC+6" class="bg-slate-900">UTC+6</option>
              <option value="UTC+7" class="bg-slate-900">UTC+7</option>
              <option value="UTC+8" class="bg-slate-900">UTC+8</option>
              <option value="UTC+9" class="bg-slate-900">UTC+9</option>
              <option value="UTC+10" class="bg-slate-900">UTC+10</option>
              <option value="UTC+12" class="bg-slate-900">UTC+12</option>
            </select>"""

content = content.replace(old_tz_select, new_tz_select)

# Also update the Timezone label text
content = content.replace(
    '<span class="text-slate-400 hidden lg:inline">Часовой пояс:</span>',
    '<span class="text-slate-400 hidden xl:inline">UTC:</span>'
)

# 3. Add TT Cup Cookie Button in Header right next to refresh button
old_header_controls = """<!-- Manual Refresh Button -->
          <button 
            id="refresh-btn" 
            onclick="triggerManualRefresh()" 
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 text-xs font-medium transition-colors"
            title="Обновить данные"
          >
            <i data-lucide="rotate-cw" id="refresh-icon" class="w-3.5 h-3.5 text-emerald-400"></i>
            <span class="hidden md:inline">Обновить</span>
          </button>"""

new_header_controls = """<!-- Cookie TT Cup Button -->
          <button
            id="header-cookie-btn"
            onclick="openTTCupCookieModal()"
            class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-medium transition-colors"
            title="Настройка Cookie TT Cup для обхода защиты"
          >
            <i data-lucide="cookie" class="w-3.5 h-3.5 text-amber-400"></i>
            <span class="hidden lg:inline">Cookie TT Cup</span>
            <span id="header-cookie-dot" class="w-2 h-2 rounded-full bg-slate-500" title="Статус Cookie"></span>
          </button>

          <!-- Manual Refresh Button -->
          <button 
            id="refresh-btn" 
            onclick="triggerManualRefresh()" 
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 text-xs font-medium transition-colors"
            title="Обновить данные"
          >
            <i data-lucide="rotate-cw" id="refresh-icon" class="w-3.5 h-3.5 text-emerald-400"></i>
            <span class="hidden md:inline">Обновить</span>
          </button>"""

content = content.replace(old_header_controls, new_header_controls)

# 4. Remove the big redundant banner div in Unified Section and keep compact Platform pills
old_unified_banner = re.search(
    r'<div id="section-unified"[^>]*>(\s*<!-- Unified Header Banner & Platform Breakdown -->.*?)(<!-- KPI STATS BAR -->)',
    content,
    flags=re.DOTALL
)

if old_unified_banner:
    compact_platform_bar = """<!-- Compact Platform Breakdown & Quick Links -->
      <div class="flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 border border-slate-800/80 rounded-2xl p-3">
        <div class="flex items-center gap-2">
          <span class="px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[11px] font-bold uppercase tracking-wider flex items-center gap-1">
            <i data-lucide="layers" class="w-3 h-3"></i> 4 Платформы
          </span>
          <span class="text-xs text-slate-400 font-medium">Агрегатор турниров и матчей в реальном времени</span>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <div class="px-2.5 py-1 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-1.5 font-mono whitespace-nowrap">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0"></span>
            <span>Setka:</span>
            <strong id="stat-unified-setka" class="text-white font-bold">0</strong>
          </div>
          <div class="px-2.5 py-1 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-300 text-xs flex items-center gap-1.5 font-mono whitespace-nowrap">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0"></span>
            <span>TT Cup:</span>
            <strong id="stat-unified-ttcup" class="text-white font-bold">0</strong>
          </div>
          <div class="px-2.5 py-1 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs flex items-center gap-1.5 font-mono whitespace-nowrap">
            <span class="w-1.5 h-1.5 rounded-full bg-purple-400 flex-shrink-0"></span>
            <span>League Pro:</span>
            <strong id="stat-unified-leaguepro" class="text-white font-bold">0</strong>
          </div>
          <div class="px-2.5 py-1 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-1.5 font-mono whitespace-nowrap">
            <span class="w-1.5 h-1.5 rounded-full bg-rose-400 flex-shrink-0"></span>
            <span>Liga Pro:</span>
            <strong id="stat-unified-sportliga" class="text-white font-bold">0</strong>
          </div>
        </div>
      </div>\n\n      """
    
    content = content[:old_unified_banner.start(1)] + compact_platform_bar + content[old_unified_banner.start(2):]

# 5. Add "⚡ Завершены ≤10 мин" tab to Unified Status Switcher
old_status_tabs = """<button onclick="setUnifiedStatus('finished')" id="unified-status-tab-finished" class="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-white">
              Завершенные (<span id="unified-tab-count-finished">0</span>)
            </button>"""

new_status_tabs = """<button onclick="setUnifiedStatus('finished')" id="unified-status-tab-finished" class="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-white whitespace-nowrap flex-shrink-0">
              Завершенные (<span id="unified-tab-count-finished">0</span>)
            </button>
            <button onclick="setUnifiedStatus('just_finished')" id="unified-status-tab-just_finished" class="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-amber-300 hover:bg-slate-800/80 whitespace-nowrap flex-shrink-0 flex items-center gap-1 transition-all">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0 animate-pulse"></span>
              <span>Завершены ≤10 мин</span> (<span id="unified-tab-count-just-finished">0</span>)
            </button>"""

content = content.replace(old_status_tabs, new_status_tabs)

# Also add Just Finished to KPI Grid in Unified view
old_kpi_grid = """<section class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">"""
new_kpi_grid = """<section class="grid grid-cols-2 sm:grid-cols-5 gap-2.5 sm:gap-3">"""
content = content.replace(old_kpi_grid, new_kpi_grid)

old_kpi_finished = """<div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 flex items-center justify-between">
          <div>
            <p class="text-xs uppercase font-semibold text-slate-400 tracking-wider">Завершенные</p>
            <h3 id="stat-unified-finished" class="text-2xl font-bold text-slate-300 mt-1 font-mono">0</h3>
          </div>
          <div class="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400">
            <i data-lucide="check-circle-2" class="w-5 h-5"></i>
          </div>
        </div>
      </section>"""

new_kpi_finished = """<div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 flex items-center justify-between">
          <div>
            <p class="text-xs uppercase font-semibold text-slate-400 tracking-wider">Завершенные</p>
            <h3 id="stat-unified-finished" class="text-2xl font-bold text-slate-300 mt-1 font-mono">0</h3>
          </div>
          <div class="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400">
            <i data-lucide="check-circle-2" class="w-5 h-5"></i>
          </div>
        </div>

        <div class="bg-slate-900/70 border border-amber-500/30 rounded-2xl p-4 flex items-center justify-between">
          <div>
            <p class="text-xs uppercase font-semibold text-amber-300/80 tracking-wider">Завершены ≤10м</p>
            <h3 id="stat-unified-just-finished" class="text-2xl font-bold text-amber-400 mt-1 font-mono">0</h3>
          </div>
          <div class="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <i data-lucide="zap" class="w-5 h-5"></i>
          </div>
        </div>
      </section>"""

content = content.replace(old_kpi_finished, new_kpi_finished)

# 6. Fix "two strokes" label wrapping in getPlatformBadgeHtml, getCountryBadgeHtml, getStatusBadgeHtml
new_platform_badge = """function getPlatformBadgeHtml(platform) {
      if (platform === 'setka') {
        return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-semibold text-[11px] font-mono whitespace-nowrap flex-shrink-0">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0"></span> Setka Cup
        </span>`;
      }
      if (platform === 'ttcup') {
        return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-500/10 border border-blue-500/30 text-blue-400 font-semibold text-[11px] font-mono whitespace-nowrap flex-shrink-0">
          <span class="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0"></span> TT Cup
        </span>`;
      }
      if (platform === 'league_pro' || platform === 'leaguepro') {
        return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-purple-500/10 border border-purple-500/30 text-purple-300 font-semibold text-[11px] font-mono whitespace-nowrap flex-shrink-0">
          <span class="w-1.5 h-1.5 rounded-full bg-purple-400 flex-shrink-0"></span> League Pro
        </span>`;
      }
      if (platform === 'sport_liga' || platform === 'sportliga' || platform === 'liga_pro' || platform === 'ligapro') {
        return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-300 font-semibold text-[11px] font-mono whitespace-nowrap flex-shrink-0">
          <span class="w-1.5 h-1.5 rounded-full bg-rose-400 flex-shrink-0"></span> Liga Pro
        </span>`;
      }
      return '';
    }"""

content = re.sub(
    r"function getPlatformBadgeHtml\(platform\) \{.*?\n    \}",
    new_platform_badge,
    content,
    flags=re.DOTALL
)

# In getCountryBadgeHtml, ensure every span has whitespace-nowrap flex-shrink-0
content = content.replace(
    'class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-blue-500/10 border border-blue-500/30 text-blue-300 font-medium text-xs shadow-sm"',
    'class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-blue-500/10 border border-blue-500/30 text-blue-300 font-medium text-xs shadow-sm whitespace-nowrap flex-shrink-0"'
)
content = content.replace(
    'class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 font-medium text-xs shadow-sm"',
    'class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 font-medium text-xs shadow-sm whitespace-nowrap flex-shrink-0"'
)
content = content.replace(
    'class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-300 font-medium text-xs shadow-sm"',
    'class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-300 font-medium text-xs shadow-sm whitespace-nowrap flex-shrink-0"'
)
content = content.replace(
    'class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-300 font-medium text-xs shadow-sm"',
    'class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-300 font-medium text-xs shadow-sm whitespace-nowrap flex-shrink-0"'
)

# In getStatusBadgeHtml, ensure whitespace-nowrap flex-shrink-0
new_status_badge = """function getStatusBadgeHtml(status) {
      if (status === 'live') {
        return `<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 text-xs font-bold tracking-wide animate-pulse shadow-sm whitespace-nowrap flex-shrink-0">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> LIVE
        </span>`;
      }
      if (status === 'upcoming') {
        return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-medium whitespace-nowrap flex-shrink-0">
          <i data-lucide="clock" class="w-3 h-3"></i> Ожидается
        </span>`;
      }
      return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-400 text-xs whitespace-nowrap flex-shrink-0">
        <i data-lucide="check" class="w-3 h-3"></i> Завершен
      </span>`;
    }"""

content = re.sub(
    r"function getStatusBadgeHtml\(status\) \{.*?\n    \}",
    new_status_badge,
    content,
    flags=re.DOTALL
)

# Update formatMatchTime to support pure UTC offsets
new_fmt_time = """function formatMatchTime(isoStr, fallbackTime = '--:--') {
      if (isoStr) {
        try {
          const dt = new Date(isoStr);
          if (!isNaN(dt.getTime())) {
            const tz = (state.timeZone || 'local').trim();
            if (tz === 'local') {
              return new Intl.DateTimeFormat('en-GB', {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false,
              }).format(dt);
            }
            // Pure UTC offset mode
            let offsetHours = 0;
            const upperTz = tz.toUpperCase();
            if (upperTz === 'UTC' || upperTz === 'UTC+0' || upperTz === 'UTC-0') {
              offsetHours = 0;
            } else if (upperTz.startsWith('UTC+')) {
              offsetHours = parseFloat(upperTz.replace('UTC+', '')) || 0;
            } else if (upperTz.startsWith('UTC-')) {
              offsetHours = -(parseFloat(upperTz.replace('UTC-', '')) || 0);
            } else {
              try {
                return new Intl.DateTimeFormat('en-GB', {
                  hour: '2-digit',
                  minute: '2-digit',
                  hour12: false,
                  timeZone: tz,
                }).format(dt);
              } catch (e) {}
            }
            const shiftedMs = dt.getTime() + offsetHours * 3600 * 1000;
            const shiftedDate = new Date(shiftedMs);
            const hh = String(shiftedDate.getUTCHours()).padStart(2, '0');
            const mm = String(shiftedDate.getUTCMinutes()).padStart(2, '0');
            return `${hh}:${mm}`;
          }
        } catch (e) {}
      }
      return fallbackTime || '--:--';
    }"""

content = re.sub(
    r"function formatMatchTime\(isoStr, fallbackTime = '--:--'\) \{.*?\n    \}",
    new_fmt_time,
    content,
    flags=re.DOTALL
)

# 7. Helper isJustFinished and renderUnifiedMatches updates
new_is_just_finished_js = """function isJustFinishedMatch(m) {
      if (m.status !== 'finished') return false;
      if (m.start_date) {
        try {
          const st = new Date(m.start_date).getTime();
          if (!isNaN(st)) {
            const endEst = st + 18 * 60 * 1000;
            const now = Date.now();
            const diffSec = (now - endEst) / 1000;
            return (-300 <= diffSec && diffSec <= 720) || (600 <= (now - st) / 1000 && (now - st) / 1000 <= 2100);
          }
        } catch (e) {}
      }
      return false;
    }"""

# Insert isJustFinishedMatch before renderUnifiedMatches
content = content.replace("function renderUnifiedMatches() {", f"{new_is_just_finished_js}\n\n    function renderUnifiedMatches() {{")

# Update renderUnifiedMatches filtering
old_render_filter = """let matches = unifiedState.matches;

      // Status tab filter
      if (unifiedState.statusTab !== 'all') {
        matches = matches.filter(m => m.status === unifiedState.statusTab);
      }"""

new_render_filter = """let matches = unifiedState.matches;

      // Calculate just finished count
      const justFinishedCount = matches.filter(m => isJustFinishedMatch(m)).length;
      const justFinTab = document.getElementById('unified-tab-count-just-finished');
      if (justFinTab) justFinTab.textContent = justFinishedCount;
      const justFinStat = document.getElementById('stat-unified-just-finished');
      if (justFinStat) justFinStat.textContent = justFinishedCount;

      // Status tab filter
      if (unifiedState.statusTab === 'just_finished') {
        matches = matches.filter(m => isJustFinishedMatch(m));
      } else if (unifiedState.statusTab !== 'all') {
        matches = matches.filter(m => m.status === unifiedState.statusTab);
      }"""

content = content.replace(old_render_filter, new_render_filter)

# Update setUnifiedStatus tab highlighting
old_set_unified_status = """function setUnifiedStatus(status) {
      unifiedState.statusTab = status;
      ['all', 'live', 'upcoming', 'finished'].forEach(s => {
        const btn = document.getElementById(`unified-status-tab-${s}`);
        if (btn) {
          if (s === status) {
            btn.className = 'px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40';
          } else {
            btn.className = 'px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-white';
          }
        }
      });
      renderUnifiedMatches();
    }"""

new_set_unified_status = """function setUnifiedStatus(status) {
      unifiedState.statusTab = status;
      ['all', 'live', 'upcoming', 'finished', 'just_finished'].forEach(s => {
        const btn = document.getElementById(`unified-status-tab-${s}`);
        if (btn) {
          if (s === status) {
            btn.className = 'px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40 whitespace-nowrap flex-shrink-0';
          } else {
            btn.className = 'px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-white whitespace-nowrap flex-shrink-0';
          }
        }
      });
      renderUnifiedMatches();
    }"""

content = content.replace(old_set_unified_status, new_set_unified_status)

# 8. Add TT Cup Cookie Modal HTML right before </body>
cookie_modal_html = """
  <!-- TT CUP COOKIE CONFIG MODAL -->
  <div id="ttcup-cookie-modal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
    <div class="glass-panel w-full max-w-lg rounded-3xl p-6 border border-slate-700 shadow-2xl relative">
      <div class="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <i data-lucide="cookie" class="w-4 h-4"></i>
          </div>
          <div>
            <h3 class="text-sm font-bold text-white">Настройка Cookie TT Cup (ttcup.com)</h3>
            <p class="text-[11px] text-slate-400">Обход проверки Cloudflare и reCAPTCHA</p>
          </div>
        </div>
        <button onclick="closeTTCupCookieModal()" class="w-8 h-8 rounded-xl bg-slate-800/80 hover:bg-slate-700 flex items-center justify-center text-slate-400 hover:text-white transition-colors">
          <i data-lucide="x" class="w-4 h-4"></i>
        </button>
      </div>

      <div class="space-y-4 text-xs">
        <div class="bg-slate-950/70 rounded-xl p-3 border border-slate-800/80 space-y-1 text-slate-300">
          <div class="flex items-center justify-between">
            <span class="text-slate-400">Текущий статус:</span>
            <span id="ttcup-cookie-modal-status" class="font-mono font-semibold text-slate-300 flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-slate-500"></span> Проверка...
            </span>
          </div>
          <div id="ttcup-cookie-modal-snippet" class="text-[11px] text-slate-500 font-mono truncate hidden"></div>
        </div>

        <div class="space-y-1.5">
          <label class="font-medium text-slate-300 flex items-center justify-between">
            <span>Вставьте значение Cookie:</span>
            <span class="text-[10px] text-slate-500">PHPSESSID=...; cf_clearance=...</span>
          </label>
          <textarea
            id="ttcup-cookie-modal-input"
            rows="3"
            placeholder="Вставьте сюда заголовок Cookie из браузера (например: PHPSESSID=abc123xyz; cf_clearance=...)"
            class="w-full bg-slate-950 border border-slate-800 focus:border-amber-500 rounded-xl p-3 text-xs text-white font-mono focus:outline-none placeholder-slate-600"
          ></textarea>
        </div>

        <div class="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 text-[11px] text-amber-300/90 leading-relaxed">
          💡 <strong>Как получить:</strong> Откройте <a href="https://ttcup.com/schedule/" target="_blank" class="underline text-amber-200">ttcup.com/schedule</a> в браузере. Нажмите <code>F12</code> &rarr; вкладка <code>Network</code> (или <code>Application &rarr; Cookies</code>), скопируйте заголовок Cookie и вставьте выше.
        </div>

        <div class="flex items-center justify-between gap-2 pt-2 border-t border-slate-800">
          <button
            onclick="clearTTCupCookie()"
            class="px-3 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 font-medium text-xs transition-colors"
          >
            Сбросить Cookie
          </button>
          <div class="flex items-center gap-2">
            <button
              onclick="closeTTCupCookieModal()"
              class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs transition-colors"
            >
              Отмена
            </button>
            <button
              onclick="saveTTCupCookie()"
              class="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-semibold text-xs shadow-md shadow-amber-900/30 transition-all flex items-center gap-1.5"
            >
              <i data-lucide="check" class="w-3.5 h-3.5"></i>
              Сохранить и активировать
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
"""

content = content.replace("</body>", f"{cookie_modal_html}\n</body>")

# 9. Add Cookie Management JS functions
cookie_js_functions = """
    // TT Cup Cookie Modal & State Management
    async function checkTTCupCookieStatus() {
      try {
        const res = await fetch('/api/ttcup/config');
        if (!res.ok) return;
        const data = await res.json();
        const dot = document.getElementById('header-cookie-dot');
        const modalStatus = document.getElementById('ttcup-cookie-modal-status');
        const modalSnippet = document.getElementById('ttcup-cookie-modal-snippet');

        if (data.cookie_set) {
          if (dot) dot.className = 'w-2 h-2 rounded-full bg-emerald-400';
          if (modalStatus) modalStatus.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-400"></span> Активен';
          if (modalSnippet) {
            modalSnippet.textContent = data.cookie_snippet || 'Cookie сохранен';
            modalSnippet.classList.remove('hidden');
          }
        } else if (data.captcha_required) {
          if (dot) dot.className = 'w-2 h-2 rounded-full bg-amber-400 animate-pulse';
          if (modalStatus) modalStatus.innerHTML = '<span class="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span> Требуется капча';
          if (modalSnippet) modalSnippet.classList.add('hidden');
        } else {
          if (dot) dot.className = 'w-2 h-2 rounded-full bg-slate-500';
          if (modalStatus) modalStatus.innerHTML = '<span class="w-2 h-2 rounded-full bg-slate-500"></span> Не настроен';
          if (modalSnippet) modalSnippet.classList.add('hidden');
        }
      } catch (e) {
        console.error('Failed to check TT Cup cookie status:', e);
      }
    }

    function openTTCupCookieModal() {
      const modal = document.getElementById('ttcup-cookie-modal');
      if (modal) {
        modal.classList.remove('hidden');
        lucide.createIcons();
        checkTTCupCookieStatus();
      }
    }

    function closeTTCupCookieModal() {
      const modal = document.getElementById('ttcup-cookie-modal');
      if (modal) modal.classList.add('hidden');
    }

    async function saveTTCupCookie() {
      const input = document.getElementById('ttcup-cookie-modal-input');
      const cookieVal = input ? input.value.trim() : '';
      if (!cookieVal) {
        alert('Пожалуйста, вставьте значение Cookie');
        return;
      }

      try {
        const res = await fetch('/api/ttcup/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cookie: cookieVal })
        });
        if (res.ok) {
          closeTTCupCookieModal();
          checkTTCupCookieStatus();
          // Trigger immediate refresh of TT Cup & Unified view
          fetchUnifiedMatches();
          fetchTTCupMatches();
        } else {
          alert('Ошибка при сохранении Cookie');
        }
      } catch (err) {
        console.error('Error saving cookie:', err);
        alert('Сетевая ошибка при отправке Cookie');
      }
    }

    async function clearTTCupCookie() {
      try {
        const res = await fetch('/api/ttcup/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cookie: '' })
        });
        if (res.ok) {
          const input = document.getElementById('ttcup-cookie-modal-input');
          if (input) input.value = '';
          checkTTCupCookieStatus();
          closeTTCupCookieModal();
          fetchUnifiedMatches();
          fetchTTCupMatches();
        }
      } catch (e) {
        console.error('Error clearing cookie:', e);
      }
    }
"""

content = content.replace("fetchMetadata();", "checkTTCupCookieStatus();\n      fetchMetadata();")
content = content.replace("// Platform Switcher", f"{cookie_js_functions}\n\n    // Platform Switcher")

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("static/index.html successfully updated with all v3 requirements!")
