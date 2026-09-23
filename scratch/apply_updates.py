import os
import re

with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Title and Subtitle
content = content.replace(
    "<title>TT Multi-Monitor — Setka Cup, TT Cup, League Pro & Sport-Liga Pro</title>",
    "<title>TT Multi-Monitor — Setka Cup, TT Cup, League Pro & Liga Pro</title>"
)
content = content.replace(
    'id="app-main-subtitle">Setka Cup • TT Cup • League Pro • Sport-Liga Pro</p>',
    'id="app-main-subtitle">Setka Cup • TT Cup • League Pro • Liga Pro</p>'
)

# 2. Update Nav Tab Button for Sport-Liga Pro
content = re.sub(
    r'<button\s+id="tab-btn-sportliga"[^>]*>.*?<span>Sport-Liga Pro</span>\s*</button>',
    '''<button
              id="tab-btn-sportliga"
              onclick="switchPlatform('sportliga')"
              class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-medium text-xs transition-all duration-200 text-slate-400 hover:text-white"
            >
              <i data-lucide="target" class="w-3.5 h-3.5 text-rose-400"></i>
              <span>Liga Pro</span>
            </button>''',
    content,
    flags=re.DOTALL
)

# 3. Update Unified stats bar
content = content.replace(
    '<span>Sport-Liga:</span>',
    '<span>Liga Pro:</span>'
)

# 4. Update Unified platform filter select option
content = content.replace(
    '<option value="sport_liga">🎯 Sport-Liga Pro</option>',
    '<option value="sport_liga">🎯 Liga Pro</option>'
)
content = content.replace(
    '<option value="sport_liga">🎯 Sport-Liga</option>',
    '<option value="sport_liga">🎯 Liga Pro</option>'
)

# 5. Update Sport-Liga Banner Header & Subtitle
content = re.sub(
    r'<!-- Sport-Liga Banner -->.*?<section id="sportliga-kpi-bar"',
    '''<!-- Liga Pro Banner -->
      <div class="bg-gradient-to-r from-rose-950/60 via-slate-900 to-indigo-950/60 border border-rose-800/40 rounded-3xl p-5 shadow-2xl relative overflow-hidden">
        <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 relative z-10">
          <div>
            <div class="flex items-center gap-2">
              <span class="px-2.5 py-1 rounded-lg bg-rose-500/20 text-rose-300 border border-rose-500/40 text-xs font-bold uppercase tracking-wider flex items-center gap-1.5">
                <i data-lucide="target" class="w-3.5 h-3.5"></i> sport-liga.pro
              </span>
              <span class="text-xs text-slate-400">Турниры Liga Pro Table Tennis</span>
            </div>
            <h2 class="text-xl sm:text-2xl font-bold text-white mt-1.5">Liga Pro Table Tennis</h2>
            <p class="text-xs text-slate-400 mt-1 max-w-2xl">
              Прямые трансляции, расписание и результаты матчей турниров Liga Pro (Россия, Беларусь, Молдова) с автоматическим обновлением.
            </p>
          </div>

          <div class="flex items-center gap-2">
            <span class="px-3 py-1.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-mono">
              Турниров: <strong id="stat-sportliga-tournaments" class="text-white font-bold">0</strong>
            </span>
          </div>
        </div>
      </div>

      <!-- KPI STATS BAR -->
      <section id="sportliga-kpi-bar"''',
    content,
    flags=re.DOTALL
)

# 6. Update Platform badge in JS helper
content = re.sub(
    r"if \(platform === 'sport_liga' \|\| platform === 'sportliga'\) \{.*?return `<span class=\"inline-flex items-center gap-1 px-2 py-0\.5 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-300 font-semibold text-\[11px\] font-mono\">\s*<span class=\"w-1\.5 h-1\.5 rounded-full bg-rose-400\"></span> Sport-Liga\s*</span>`;\s*\}",
    """if (platform === 'sport_liga' || platform === 'sportliga' || platform === 'liga_pro' || platform === 'ligapro') {
        return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-300 font-semibold text-[11px] font-mono">
          <span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span> Liga Pro
        </span>`;
      }""",
    content,
    flags=re.DOTALL
)

# 7. Update getCountryBadgeHtml function to support Russia, Belarus, Moldova, Czech, Poland, Ukraine with clean SVG flags & city tags
new_get_country_badge = """function getCountryBadgeHtml(country, countryCode, city) {
      const code = (countryCode || '').toLowerCase();
      const cName = (country || '').toLowerCase();
      const cityName = (city || '').trim();

      // Russia (ru)
      if (code === 'ru' || cName.includes('russia') || cName.includes('россия')) {
        const cityLabel = cityName ? `<span class="text-[10px] text-blue-200/70 border-l border-blue-500/30 pl-1.5 ml-0.5">${cityName}</span>` : '';
        return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-blue-500/10 border border-blue-500/30 text-blue-300 font-medium text-xs shadow-sm" title="Russia${cityName ? ' • ' + cityName : ''}">
          <svg class="w-3.5 h-2.5 rounded-sm overflow-hidden flex-shrink-0 shadow-xs" viewBox="0 0 640 480">
            <path fill="#fff" d="M0 0h640v160H0z"/>
            <path fill="#0039a6" d="M0 160h640v160H0z"/>
            <path fill="#d52b1e" d="M0 320h640v160H0z"/>
          </svg>
          <span>Россия</span>${cityLabel}
        </span>`;
      }

      // Belarus (by)
      if (code === 'by' || cName.includes('belarus') || cName.includes('беларусь') || cName.includes('minsk') || cName.includes('минск')) {
        const cityLabel = cityName ? `<span class="text-[10px] text-emerald-200/70 border-l border-emerald-500/30 pl-1.5 ml-0.5">${cityName}</span>` : '<span class="text-[10px] text-emerald-200/70 border-l border-emerald-500/30 pl-1.5 ml-0.5">Минск</span>';
        return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 font-medium text-xs shadow-sm" title="Belarus${cityName ? ' • ' + cityName : ''}">
          <svg class="w-3.5 h-2.5 rounded-sm overflow-hidden flex-shrink-0 shadow-xs" viewBox="0 0 640 480">
            <path fill="#c8313e" d="M0 0h640v320H0z"/>
            <path fill="#4aa657" d="M0 320h640v160H0z"/>
            <path fill="#fff" d="M0 0h110v480H0z"/>
            <path fill="#c8313e" d="M10 20l40 40-40 40 40 40-40 40 40 40-40 40 40 40-40 40 40 40-40 40 40 40-40 40M90 20l-40 40 40 40-40 40 40 40-40 40 40 40-40 40 40 40-40 40 40 40-40 40 40 40-40 40"/>
          </svg>
          <span>Беларусь</span>${cityLabel}
        </span>`;
      }

      // Moldova (md)
      if (code === 'md' || cName.includes('moldova') || cName.includes('молдова') || cName.includes('chisinau') || cName.includes('кишинев')) {
        const cityLabel = cityName ? `<span class="text-[10px] text-amber-200/70 border-l border-amber-500/30 pl-1.5 ml-0.5">${cityName}</span>` : '<span class="text-[10px] text-amber-200/70 border-l border-amber-500/30 pl-1.5 ml-0.5">Кишинев</span>';
        return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-300 font-medium text-xs shadow-sm" title="Moldova${cityName ? ' • ' + cityName : ''}">
          <svg class="w-3.5 h-2.5 rounded-sm overflow-hidden flex-shrink-0 shadow-xs" viewBox="0 0 640 480">
            <path fill="#003da5" d="M0 0h213.3v480H0z"/>
            <path fill="#ffd100" d="M213.3 0h213.4v480H213.3z"/>
            <path fill="#c8102e" d="M426.7 0h213.3v480H426.7z"/>
            <path fill="#8b5a2b" d="M280 200h80v80h-80z"/>
            <path fill="#c8102e" d="M300 215h40v50h-40z"/>
            <circle cx="320" cy="240" r="10" fill="#ffd100"/>
          </svg>
          <span>Молдова</span>${cityLabel}
        </span>`;
      }

      // Czech Republic (cz)
      if (code === 'cz' || cName.includes('czech')) {
        return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-blue-500/10 border border-blue-500/30 text-blue-300 font-medium text-xs shadow-sm" title="Czech Republic">
          <svg class="w-3.5 h-2.5 rounded-sm overflow-hidden flex-shrink-0 shadow-xs" viewBox="0 0 640 480">
            <path fill="#d7141a" d="M0 0h640v480H0z"/>
            <path fill="#fff" d="M0 0h640v240H0z"/>
            <path fill="#11457e" d="M0 0l360 240L0 480z"/>
          </svg>
          <span>Чехия</span>
        </span>`;
      }

      // Poland (pl)
      if (code === 'pl' || cName.includes('poland')) {
        return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-300 font-medium text-xs shadow-sm" title="Poland">
          <svg class="w-3.5 h-2.5 rounded-sm overflow-hidden flex-shrink-0 shadow-xs" viewBox="0 0 640 480">
            <path fill="#dc143c" d="M0 240h640v240H0z"/>
            <path fill="#fff" d="M0 0h640v240H0z"/>
          </svg>
          <span>Польша</span>
        </span>`;
      }

      // Ukraine (ua)
      if (code === 'ua' || cName.includes('ukraine')) {
        return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-300 font-medium text-xs shadow-sm" title="Ukraine">
          <svg class="w-3.5 h-2.5 rounded-sm overflow-hidden flex-shrink-0 shadow-xs" viewBox="0 0 640 480">
            <path fill="#ffd500" d="M0 240h640v240H0z"/>
            <path fill="#005bbb" d="M0 0h640v240H0z"/>
          </svg>
          <span>Украина</span>
        </span>`;
      }

      return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800 border border-slate-700 text-slate-300 font-medium text-xs">
        <span>🌐</span> <span>${country || 'Intl'}</span>
      </span>`;
    }"""

content = re.sub(
    r"function getCountryBadgeHtml\(country, countryCode\) \{.*?\n    \}",
    new_get_country_badge,
    content,
    flags=re.DOTALL
)

# 8. Ensure renderUnifiedMatches passes city: getCountryBadgeHtml(m.country, m.country_code, m.city)
content = content.replace(
    "const countryBadge = getCountryBadgeHtml(m.country, m.country_code);",
    "const countryBadge = getCountryBadgeHtml(m.country, m.country_code, m.city);"
)

# 9. In renderSportLigaMatches, render proper country/city badge instead of hardcoded text
old_sl_card_header = """<div class="flex items-center justify-between border-b border-slate-800/80 pb-2.5 mb-3">
                <div class="flex items-center gap-2">
                  <span class="font-mono text-sm font-bold text-white bg-slate-800/80 px-2 py-0.5 rounded-lg">${timeDisplay}</span>
                  <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 text-xs">
                    🎯 Liga Pro
                  </span>
                </div>
                ${statusBadge}
              </div>"""

new_sl_card_header = """<div class="flex items-center justify-between border-b border-slate-800/80 pb-2.5 mb-3">
                <div class="flex items-center gap-2">
                  <span class="font-mono text-sm font-bold text-white bg-slate-800/80 px-2 py-0.5 rounded-lg">${timeDisplay}</span>
                  ${countryBadge}
                </div>
                ${statusBadge}
              </div>"""

content = re.sub(
    r'<div class="flex items-center justify-between border-b border-slate-800/80 pb-2\.5 mb-3">\s*<div class="flex items-center gap-2">\s*<span class="font-mono text-sm font-bold text-white bg-slate-800/80 px-2 py-0\.5 rounded-lg">\$\{timeDisplay\}</span>\s*<span class="inline-flex items-center gap-1 px-1\.5 py-0\.5 rounded bg-slate-800 border border-slate-700 text-slate-300 text-xs">.*?</span>\s*</div>\s*\$\{statusBadge\}\s*</div>',
    new_sl_card_header,
    content,
    flags=re.DOTALL
)

# Also ensure renderSportLigaMatches defines countryBadge
content = re.sub(
    r"(function renderSportLigaMatches\(\) \{\s*const cardsWrapper = document\.getElementById\('sportliga-cards-wrapper'\);\s*const tableBody = document\.getElementById\('sportliga-matches-table-body'\);\s*cardsWrapper\.innerHTML = sportLigaState\.matches\.map\(m => \{\s*const timeDisplay = formatMatchTime\(m\.start_date, m\.time\);\s*const statusBadge = getStatusBadgeHtml\(m\.status\);)",
    r"\1\n        const countryBadge = getCountryBadgeHtml(m.country, m.country_code, m.city);",
    content
)

# And in the table view of Liga Pro matches, add countryBadge column
old_table_header = """<thead>
                <tr class="text-left text-xs font-semibold text-slate-400 border-b border-slate-800 bg-slate-950/40">
                  <th class="p-3.5">Время</th>
                  <th class="p-3.5">Турнир</th>
                  <th class="p-3.5">Стадия</th>
                  <th class="p-3.5">Игроки</th>
                  <th class="p-3.5 text-center">Счет</th>
                  <th class="p-3.5">Сеты</th>
                  <th class="p-3.5 text-right">Статус</th>
                </tr>
              </thead>"""

new_table_header = """<thead>
                <tr class="text-left text-xs font-semibold text-slate-400 border-b border-slate-800 bg-slate-950/40">
                  <th class="p-3.5">Время</th>
                  <th class="p-3.5">Страна / Город</th>
                  <th class="p-3.5">Турнир</th>
                  <th class="p-3.5">Стадия</th>
                  <th class="p-3.5">Игроки</th>
                  <th class="p-3.5 text-center">Счет</th>
                  <th class="p-3.5">Сеты</th>
                  <th class="p-3.5 text-right">Статус</th>
                </tr>
              </thead>"""

content = content.replace(old_table_header, new_table_header)

old_table_row = """<tr class="hover:bg-slate-900/50 transition-colors">
            <td class="p-3.5 font-mono text-xs text-white font-semibold">${timeDisplay}</td>
            <td class="p-3.5 text-xs text-rose-300 font-medium">${m.tournament_name}</td>"""

new_table_row = """<tr class="hover:bg-slate-900/50 transition-colors">
            <td class="p-3.5 font-mono text-xs text-white font-semibold">${timeDisplay}</td>
            <td class="p-3.5">${countryBadge}</td>
            <td class="p-3.5 text-xs text-rose-300 font-medium">${m.tournament_name}</td>"""

content = content.replace(old_table_row, new_table_row)

# 10. Update tournament selector options to include country / city flag
old_tourn_map = "sportLigaState.tournaments.map(t => `<option value=\"${t.id}\">${t.name}</option>`).join('')"
new_tourn_map = "sportLigaState.tournaments.map(t => { const f = t.country_code === 'by' ? '🇧🇾' : (t.country_code === 'md' ? '🇲🇩' : '🇷🇺'); const c = t.city ? ` [${f} ${t.city}]` : ` [${f}]`; return `<option value=\"${t.id}\">${t.name}${c}</option>`; }).join('')"
content = content.replace(old_tourn_map, new_tourn_map)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated static/index.html successfully!")
