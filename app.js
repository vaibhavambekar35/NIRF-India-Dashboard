// NIRF INSIGHT: Enterprise Dashboard Controller (v2.1)
// Robust ECharts India Map Integration, State Drill-Down & Relational Analytics

let currentYear = 2025;
let currentCategorySlug = 'overall';
let currentCategoryName = 'Overall';
let currentScope = 'top_100';
let currentOwnership = 'all';
let activeView = 'distribution';

let chartRadarModalInstance = null;
let compareStateAId = 16; // Karnataka
let compareStateBId = 21; // Maharashtra
let allStatesList = [];

let echartsInstance = null;
let geoJsonData = null;
let currentDistributionData = null;
let currentSelectedStateId = null;
let currentSelectedStateName = null;

let chartCatBarInstance = null;
let chartYoyInstance = null;
let chartCompareRadarInstance = null;
let chartCompareDisciplineInstance = null;

document.addEventListener('DOMContentLoaded', async () => {
  if (window.lucide) lucide.createIcons();
  setupNavigation();
  setupEventListeners();

  await loadMetadata();
  await initializeEChartsMap();
  await loadCurrentView();
});

// 1. Navigation Between 5 Views
function setupNavigation() {
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetView = btn.getAttribute('data-view');
      switchView(targetView);
    });
  });
}

async function switchView(viewName) {
  activeView = viewName;

  document.querySelectorAll('.nav-btn').forEach(btn => {
    const v = btn.getAttribute('data-view');
    if (v === viewName) {
      btn.className = 'nav-btn w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs font-bold text-white bg-[#c2410c] shadow-md shadow-orange-600/20 transition';
    } else {
      btn.className = 'nav-btn w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold text-slate-700 hover:bg-orange-50/70 hover:text-orange-950 transition';
    }
  });

  document.querySelectorAll('.dashboard-view').forEach(container => container.classList.add('hidden'));

  const viewHeadingMap = {
    'distribution': 'India – State-wise NIRF Distribution',
    'overview': 'National Ranking Intelligence Overview',
    'comparison': 'State vs State Comparative Intelligence & Benchmarking',
    'explorer': 'Institutional Ranking Explorer'
  };

  const headingEl = document.getElementById('viewHeading');
  if (headingEl) headingEl.textContent = viewHeadingMap[viewName] || 'NIRF Insight';

  if (viewName === 'distribution') {
    document.getElementById('viewDistribution').classList.remove('hidden');
    await loadDistributionData();
    if (echartsInstance) {
      setTimeout(() => echartsInstance.resize(), 50);
    }
  } else if (viewName === 'overview') {
    document.getElementById('viewOverview').classList.remove('hidden');
    await loadOverviewData();
  } else if (viewName === 'comparison') {
    document.getElementById('viewComparison').classList.remove('hidden');
    await loadComparisonData();
  } else if (viewName === 'explorer') {
    document.getElementById('viewExplorer').classList.remove('hidden');
    await loadExplorerTable();
  }

  if (window.lucide) lucide.createIcons();
}

// 2. Load Years and Categories from Database API
async function loadMetadata() {
  try {
    const yRes = await fetch('/v1/years');
    const years = await yRes.json();
    const selectY = document.getElementById('selectYear');
    if (selectY && years.length > 0) {
      selectY.innerHTML = '';
      years.forEach(y => {
        const opt = document.createElement('option');
        opt.value = y.year;
        opt.textContent = y.year;
        if (y.is_default) {
          currentYear = y.year;
          opt.selected = true;
        }
        selectY.appendChild(opt);
      });
    }

    const cRes = await fetch('/v1/categories');
    const categories = await cRes.json();
    const selectC = document.getElementById('selectCategory');
    if (selectC && categories.length > 0) {
      selectC.innerHTML = '';

      categories.forEach((cat, idx) => {
        const opt = document.createElement('option');
        opt.value = cat.slug;
        opt.textContent = cat.name;
        if (idx === 0) {
          currentCategorySlug = cat.slug;
          currentCategoryName = cat.name;
          opt.selected = true;
        }
        selectC.appendChild(opt);
      });
    }
  } catch (err) {
    console.error('Error loading metadata:', err);
  }
}

// 3. Initialize Apache ECharts India Map
async function initializeEChartsMap() {
  const chartDom = document.getElementById('echartsMap');
  if (!chartDom) return;

  echartsInstance = echarts.init(chartDom);

  try {
    const res = await fetch('/india_states.geojson');
    geoJsonData = await res.json();

    // Ensure ECharts can match by state name property
    if (geoJsonData && geoJsonData.features) {
      geoJsonData.features.forEach(f => {
        if (f.properties && f.properties.ST_NM) {
          f.properties.name = f.properties.ST_NM;
        }
      });
    }

    echarts.registerMap('India', geoJsonData);
    const spinner = document.getElementById('mapSpinner');
    if (spinner) spinner.classList.add('hidden');
  } catch (err) {
    console.error('Failed to load India GeoJSON:', err);
    const spinner = document.getElementById('mapSpinner');
    if (spinner) {
      spinner.innerHTML = `<span class="text-rose-600 text-xs font-semibold">Failed to load boundary data</span>`;
    }
  }

  window.addEventListener('resize', () => {
    if (echartsInstance) echartsInstance.resize();
  });
}

// Render ECharts Choropleth
function renderEChartsChoropleth(stateCounts) {
  if (!echartsInstance || !geoJsonData) return;

  const dataMap = {};
  let maxCount = 1;

  stateCounts.forEach(st => {
    dataMap[st.state_name] = st;
    if (st.institution_count > maxCount) maxCount = st.institution_count;
  });

  const seriesData = geoJsonData.features.map(f => {
    const stName = f.properties.name || f.properties.ST_NM;
    const stInfo = dataMap[stName];
    return {
      name: stName,
      value: stInfo ? stInfo.institution_count : 0,
      bestRank: stInfo ? (stInfo.best_rank_display || stInfo.best_rank || 'N/A') : 'N/A',
      topInst: stInfo ? stInfo.top_institution : 'None',
      stateId: stInfo ? stInfo.state_id : null
    };
  });

  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: '#334155',
      borderWidth: 1,
      padding: [8, 12],
      textStyle: { color: '#ffffff', fontSize: 12 },
      formatter: params => {
        const d = params.data;
        if (!d || d.value === undefined) return params.name;
        const scopeLabel = currentScope === 'top_100' ? 'Top 100 Institutions' : 'Ranked Institutions';
        return `
          <div style="font-weight: 700; font-size: 13px; margin-bottom: 3px; color: #60a5fa;">${d.name}</div>
          <div style="font-size: 12px; margin-bottom: 2px;">${scopeLabel}: <strong>${d.value}</strong></div>
          <div style="font-size: 11px; color: #cbd5e1;">Best Rank: <strong>${d.bestRank || 'N/A'}</strong></div>
          ${d.topInst && d.topInst !== 'None' ? `<div style="font-size: 10px; color: #94a3b8; margin-top: 3px; max-width: 190px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">Top: ${d.topInst}</div>` : ''}
          <div style="font-size: 9px; color: #ea580c; margin-top: 4px; font-style: italic;">Click to inspect ranked institutions</div>
        `;
      }
    },
    visualMap: {
      min: 0,
      max: Math.max(maxCount, 10),
      left: 24,
      bottom: 24,
      text: ['High Concentration', '0 Institutions'],
      textGap: 8,
      itemWidth: 12,
      itemHeight: 120,
      calculable: true,
      inRange: {
        color: ['#fff7ed', '#ffedd5', '#fed7aa', '#fb923c', '#ea580c', '#c2410c', '#7c2d12']
      },
      textStyle: { color: '#64748b', fontSize: 10, fontWeight: 500 }
    },
    series: [
      {
        name: 'NIRF Institutions',
        type: 'map',
        map: 'India',
        roam: true,
        scaleLimit: { min: 0.9, max: 5 },
        aspectScale: 0.9,
        zoom: 1.15,
        center: [83.0, 22.5],
        selectedMode: 'single',
        select: {
          disabled: false,
          label: {
            show: true,
            color: '#78350f',
            fontWeight: 'bold',
            fontSize: 11
          },
          itemStyle: {
            areaColor: '#f59e0b',
            borderColor: '#b45309',
            borderWidth: 2,
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.3)'
          }
        },
        emphasis: {
          label: { show: false },
          itemStyle: {
            areaColor: '#f59e0b',
            borderColor: '#b45309',
            borderWidth: 1.5,
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.3)'
          }
        },
        itemStyle: {
          borderColor: '#cbd5e1',
          borderWidth: 0.8,
          areaColor: '#fbf9f6'
        },
        data: seriesData
      }
    ]
  };

  echartsInstance.setOption(option, true);

  if (currentSelectedStateName) {
    highlightStateOnMap(currentSelectedStateName);
  }

  echartsInstance.off('click');
  echartsInstance.on('click', params => {
    if (params.data && params.data.stateId) {
      openStateDetail(params.data.stateId, params.data.name);
    }
  });
}

// Map & Leaderboard Bidirectional Selection Helpers
let previousSelectedStateName = null;

function highlightStateOnMap(stateName) {
  if (!echartsInstance) return;

  try {
    // 1. Get all currently selected data indices from the series model and unselect/downplay them
    const seriesModel = echartsInstance.getModel()?.getSeriesByIndex(0);
    if (seriesModel && seriesModel.getSelectedDataIndices) {
      const selectedIndices = seriesModel.getSelectedDataIndices() || [];
      selectedIndices.forEach(idx => {
        echartsInstance.dispatchAction({
          type: 'unselect',
          seriesIndex: 0,
          dataIndex: idx
        });
        echartsInstance.dispatchAction({
          type: 'downplay',
          seriesIndex: 0,
          dataIndex: idx
        });
      });
    }
  } catch (e) {
    console.warn('Error clearing selected indices:', e);
  }

  // 2. Also explicitly unselect and downplay previously tracked state by name
  if (previousSelectedStateName && previousSelectedStateName !== stateName) {
    echartsInstance.dispatchAction({
      type: 'unselect',
      seriesIndex: 0,
      name: previousSelectedStateName
    });
    echartsInstance.dispatchAction({
      type: 'downplay',
      seriesIndex: 0,
      name: previousSelectedStateName
    });
  }

  // 3. Downplay entire series
  echartsInstance.dispatchAction({
    type: 'downplay',
    seriesIndex: 0
  });

  // 4. If a target stateName is specified, select and highlight it
  if (stateName) {
    echartsInstance.dispatchAction({
      type: 'select',
      seriesIndex: 0,
      name: stateName
    });
    echartsInstance.dispatchAction({
      type: 'highlight',
      seriesIndex: 0,
      name: stateName
    });
    previousSelectedStateName = stateName;
  } else {
    previousSelectedStateName = null;
  }
}

function highlightStateOnLeaderboard(stateId) {
  document.querySelectorAll('#tableLeaderboardBody tr').forEach(row => {
    const rowId = row.getAttribute('data-state-id');
    if (stateId && rowId && parseInt(rowId) === parseInt(stateId)) {
      row.classList.add('active', 'bg-amber-100', 'border-l-4', 'border-amber-500', 'font-semibold');
      row.style.backgroundColor = '#fff7ed';
      row.style.borderLeft = '4px solid #ea580c';
      row.querySelectorAll('td').forEach(td => {
        td.style.backgroundColor = '#fff7ed';
      });
      row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
      row.classList.remove('active', 'bg-amber-100', 'border-l-4', 'border-amber-500', 'font-semibold');
      row.style.backgroundColor = '';
      row.style.borderLeft = '';
      row.querySelectorAll('td').forEach(td => {
        td.style.backgroundColor = '';
      });
    }
  });
}

// 4. Load Current View Data
async function loadCurrentView() {
  if (activeView === 'distribution') {
    await loadDistributionData();
  } else if (activeView === 'overview') {
    await loadOverviewData();
  } else if (activeView === 'comparison') {
    await loadComparisonData();
  } else if (activeView === 'explorer') {
    await loadExplorerTable();
  }
}

// 5. Load Distribution Data (Main Map & Leaderboard)
async function loadDistributionData() {
  try {
    const res = await fetch(`/v1/distribution?year=${currentYear}&category=${currentCategorySlug}&scope=${currentScope}&ownership=${currentOwnership}`);
    const data = await res.json();
    currentDistributionData = data;

    const banner = document.getElementById('bannerDataNotAvailable');
    const badge = document.getElementById('coverageBadge');

    // Sync MahaSAMARTH Executive Dossier Banner
    const activeCatEl = document.getElementById('bannerActiveCategoryText');
    if (activeCatEl) activeCatEl.textContent = `NIRF Category: ${currentCategoryName}`;
    const bannerTotalEl = document.getElementById('bannerTotalCount');
    if (bannerTotalEl) bannerTotalEl.textContent = data.total_institutions || (data.top_100_count || 100);

    if (data.data_status === 'not_available') {
      if (banner) {
        banner.classList.remove('hidden');
        document.getElementById('bannerNote').textContent = data.note || 'The selected category is not available for this ranking year.';
      }
      if (badge) {
        badge.textContent = 'Data Not Available';
        badge.className = 'text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-300';
      }

      document.getElementById('kpiTotalInsts').textContent = '—';
      document.getElementById('kpiTotalSub').textContent = 'Category Not Available';
      document.getElementById('kpiStatesRep').textContent = '—';
      document.getElementById('kpiLeadingState').textContent = '—';
      document.getElementById('kpiLeadingCount').textContent = '—';
      document.getElementById('kpiTopInst').textContent = '—';
      document.getElementById('kpiTopScore').textContent = 'Rank #1 • Score: —';

      renderEChartsChoropleth([]);
      renderLeaderboardTable([], 0);
      return;
    } else {
      if (banner) banner.classList.add('hidden');
      if (badge) {
        badge.textContent = 'Verified Dataset';
        badge.className = 'text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300';
      }
    }

    // Populate KPI Cards
    const isTop100 = currentScope === 'top_100';
    const totalLabel = document.getElementById('kpiTotalLabel');
    if (totalLabel) totalLabel.textContent = isTop100 ? 'Top 100 Ranked Institutions' : 'Total Ranked Institutions';
    document.getElementById('kpiTotalInsts').textContent = (data.ranked_institutions || 0).toLocaleString();
    document.getElementById('kpiTotalSub').textContent = `NIRF ${currentYear} • ${data.category}${isTop100 ? ' (Top 100)' : ''}`;
    document.getElementById('kpiStatesRep').textContent = data.states_represented || 0;
    document.getElementById('kpiLeadingState').textContent = data.leading_state || 'N/A';
    document.getElementById('kpiLeadingState').title = data.leading_state || '';
    document.getElementById('kpiLeadingCount').textContent = `${data.leading_state_count || 0} ${isTop100 ? 'top 100 ' : ''}institutions`;
    document.getElementById('kpiTopInst').textContent = data.highest_ranked_institution || 'N/A';
    document.getElementById('kpiTopInst').title = data.highest_ranked_institution || '';
    document.getElementById('kpiTopScore').textContent = data.highest_score ? `Rank #1 • Score: ${data.highest_score.toFixed(2)}` : 'Rank #1 • Score: N/A';

    const thInst = document.getElementById('thInstCol');
    if (thInst) thInst.textContent = isTop100 ? 'Top 100' : 'Institutions';
    const lbSub = document.getElementById('leaderboardSub');
    if (lbSub) lbSub.textContent = isTop100 ? 'Sorted by Top 100 concentration' : 'Sorted by institution concentration';

    // Render Map & Leaderboard
    renderEChartsChoropleth(data.state_counts || []);
    renderLeaderboardTable(data.state_counts || [], data.ranked_institutions || 1);

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Failed to load distribution data:', err);
  }
}

// 6. Render Leaderboard Table
function renderLeaderboardTable(stateCounts, totalInstitutions) {
  const tbody = document.getElementById('tableLeaderboardBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  const badge = document.getElementById('stateCountBadge');
  if (badge) badge.textContent = `${stateCounts.length} States`;

  if (!stateCounts || stateCounts.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-slate-400 text-xs">No records available</td></tr>`;
    return;
  }

  const tot = totalInstitutions || 1;

  stateCounts.forEach((st, idx) => {
    const tr = document.createElement('tr');
    const isSelected = currentSelectedStateId && (parseInt(currentSelectedStateId) === parseInt(st.state_id));
    tr.className = `leaderboard-row ${isSelected ? 'active bg-amber-100 border-l-4 border-amber-500 font-semibold' : ''}`;
    if (isSelected) {
      tr.style.backgroundColor = '#fff7ed';
      tr.style.borderLeft = '4px solid #ea580c';
    }
    tr.setAttribute('data-state-id', st.state_id);
    tr.setAttribute('data-state-name', st.state_name);
    const rankNum = idx + 1;
    const sharePct = ((st.institution_count / tot) * 100).toFixed(1);

    let rankPill = `<span class="inline-block w-5 h-5 rounded-full bg-slate-100 text-slate-600 font-bold text-center leading-5 text-[10px]">${rankNum}</span>`;
    if (rankNum === 1) rankPill = `<span class="inline-block w-5 h-5 rounded-full badge-gold font-bold text-center leading-5 text-[10px]">1</span>`;
    else if (rankNum === 2) rankPill = `<span class="inline-block w-5 h-5 rounded-full badge-silver font-bold text-center leading-5 text-[10px]">2</span>`;
    else if (rankNum === 3) rankPill = `<span class="inline-block w-5 h-5 rounded-full badge-bronze font-bold text-center leading-5 text-[10px]">3</span>`;

    tr.innerHTML = `
      <td class="py-2.5 px-3 text-center">${rankPill}</td>
      <td class="py-2.5 px-3">
        <div class="font-semibold text-slate-800">${st.state_name}</div>
        <div class="text-[10px] text-slate-500 break-words leading-tight max-w-[260px]" title="Top: ${st.top_institution || 'None'}">Top: ${st.top_institution || 'None'}</div>
      </td>
      <td class="py-2.5 px-3 text-right font-bold text-slate-900">${st.institution_count}</td>
      <td class="py-2.5 px-3 text-center">
        <span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-orange-50 text-orange-800 border border-orange-200">${st.best_rank_display || 'N/A'}</span>
      </td>
      <td class="py-2.5 px-3 text-right">
        <span class="font-bold text-[#c2410c] text-xs">${sharePct}%</span>
        <div class="w-10 bg-slate-100 h-1.5 rounded-full overflow-hidden mt-1 ml-auto">
          <div class="bg-[#c2410c] h-full rounded-full" style="width: ${Math.min(sharePct * 3, 100)}%"></div>
        </div>
      </td>
    `;

    tr.addEventListener('click', () => {
      openStateDetail(st.state_id, st.state_name);
    });

    tbody.appendChild(tr);
  });
}

// 7. State Drill-down Information Panel
async function openStateDetail(stateId, stateName) {
  currentSelectedStateId = stateId;
  currentSelectedStateName = stateName;

  highlightStateOnMap(stateName);
  highlightStateOnLeaderboard(stateId);

  const panel = document.getElementById('panelStateDetail');
  if (!panel) return;
  panel.classList.remove('hidden');

  document.getElementById('panelStateName').textContent = stateName;
  
  // Dynamically update the PDF button label to "[State Name] Ranking Report (PDF)"
  const btnStateBrief = document.getElementById('btnStateBrief');
  if (btnStateBrief) {
    const span = btnStateBrief.querySelector('span');
    if (span) {
      span.textContent = `${stateName} Ranking Report (PDF)`;
    } else {
      btnStateBrief.innerHTML = `<i data-lucide="file-text" class="w-3.5 h-3.5 text-emerald-600"></i><span id="btnStateBriefText">${stateName} Ranking Report (PDF)</span>`;
      if (window.lucide && lucide.createIcons) lucide.createIcons();
    }
  }

  try {
    const res = await fetch(`/v1/distribution/states/${stateId}?year=${currentYear}&category=${currentCategorySlug}&scope=${currentScope}&ownership=${currentOwnership}`);
    const data = await res.json();

    const scopeBadgeLabel = currentScope === 'top_100' ? 'Top 100' : 'All Ranked';
    document.getElementById('panelStateCountBadge').textContent = `${data.institution_count} ${scopeBadgeLabel} in ${currentCategoryName} (Best Rank: ${data.best_rank || 'N/A'})`;
    const subEl = document.querySelector('#panelStateDetail p.text-xs');
    if (subEl) subEl.textContent = `Ranked institutions in ${currentCategoryName} (${currentYear} • ${scopeBadgeLabel}) sorted by NIRF rank`;

    const tbody = document.getElementById('panelStateTableBody');
    tbody.innerHTML = '';

    if (!data.institutions || data.institutions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="py-4 text-center text-slate-400 text-xs">No ranked institutions found for this state</td></tr>`;
      return;
    }

    data.institutions.forEach(inst => {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-50 cursor-pointer';

      const rankBadge = inst.is_rank_band
        ? `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600">${inst.rank}</span>`
        : `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-50 text-orange-800 border border-orange-200">#${inst.rank}</span>`;

      const scoreText = inst.score ? `<span class="font-bold text-slate-900">${inst.score.toFixed(2)}</span>` : `<span class="text-slate-300">—</span>`;
      const pdfBtn = (inst.source_url && inst.source_url.startsWith('http'))
        ? `<a href="${inst.source_url}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation();" class="p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded inline-flex items-center" title="Download Official NIRF DCS Report (PDF)"><i data-lucide="file-text" class="w-4 h-4"></i></a>`
        : `<span class="text-slate-300 font-mono">—</span>`;

      tr.innerHTML = `
        <td class="py-2 px-3 text-center">${rankBadge}</td>
        <td class="py-2 px-3 font-semibold text-slate-900">${inst.institution_name}</td>
        <td class="py-2 px-3 text-slate-600">${inst.city || '—'}</td>
        <td class="py-2 px-3 text-right">${scoreText}</td>
        <td class="py-2 px-3 text-center">${pdfBtn}</td>
      `;

      tr.addEventListener('click', () => {
        openInstitutionModalByName(inst.institution_name);
      });

      tbody.appendChild(tr);
    });

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Error fetching state details:', err);
  }
}

// 8. Overview View Data
async function loadOverviewData() {
  try {
    const res = await fetch('/v1/availability');
    const editions = await res.json();
    const tbody = document.getElementById('overviewCoverageBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    editions.forEach(ed => {
      const tr = document.createElement('tr');
      const badge = ed.is_available 
        ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">Verified</span>`
        : `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">Data Not Available</span>`;

      tr.innerHTML = `
        <td class="py-2.5 px-3 font-bold text-slate-900">${ed.year}</td>
        <td class="py-2.5 px-3 font-semibold text-slate-800">${ed.category}</td>
        <td class="py-2.5 px-3 text-center">${badge}</td>
        <td class="py-2.5 px-3 text-right font-bold">${ed.total_records.toLocaleString()}</td>
        <td class="py-2.5 px-3 text-slate-700">${ed.rank_1_institution || '—'}</td>
        <td class="py-2.5 px-3 text-right font-semibold text-emerald-700">${ed.top_score ? ed.top_score.toFixed(2) : '—'}</td>
        <td class="py-2.5 px-3 text-slate-400 text-[11px]">${ed.note || '—'}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading overview:', err);
  }
}

// 9. Comparison View Data (State vs State Benchmarking)
async function loadComparisonData() {
  try {
    await initCompareSelectors();
    await renderStateComparison();
    await renderMoversTracker();
  } catch (err) {
    console.error('Error loading comparison data:', err);
  }
}

// 10. Institution Explorer Table
let explorerSearch = '';
let explorerTier = 'all';

async function loadExplorerTable() {
  let url = `/v1/institutions?year=${currentYear}&category=${currentCategorySlug}&rank_type=${explorerTier}&ownership=${currentOwnership}`;
  if (explorerSearch) url += `&search=${encodeURIComponent(explorerSearch)}`;

  try {
    const res = await fetch(url);
    const insts = await res.json();

    document.getElementById('explorerCountText').textContent = `Showing ${insts.length} institutions`;
    const tbody = document.getElementById('explorerTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!insts || insts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="12" class="py-8 text-center text-slate-400 text-xs">No matching institutions found</td></tr>`;
      return;
    }

    insts.forEach(inst => {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-50 cursor-pointer';

      const rankPill = inst.is_rank_band
        ? `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600">${inst.rank}</span>`
        : `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-50 text-orange-800 border border-orange-200">#${inst.rank}</span>`;

      const scoreCell = inst.score ? `<span class="font-bold text-slate-900">${inst.score.toFixed(2)}</span>` : `<span class="text-slate-300">—</span>`;
      const pdfCell = (inst.source_url && inst.source_url.startsWith('http'))
        ? `<a href="${inst.source_url}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation();" class="p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded inline-flex items-center" title="Download Official NIRF DCS Report (PDF)"><i data-lucide="file-text" class="w-4 h-4"></i></a>`
        : `<span class="text-slate-300 font-mono">—</span>`;

      tr.innerHTML = `
        <td class="py-2 px-3 text-center">${rankPill}</td>
        <td class="py-2 px-3 font-semibold text-slate-900">${inst.institution_name}</td>
        <td class="py-2 px-3 font-mono text-[10px] text-slate-400">${inst.institute_id || '—'}</td>
        <td class="py-2 px-3 text-slate-600">${inst.city || '—'}</td>
        <td class="py-2 px-3 text-slate-600">${inst.state_name}</td>
        <td class="py-2 px-3 text-right">${scoreCell}</td>
        <td class="py-2 px-3 text-right text-slate-500">${inst.tlr ? inst.tlr.toFixed(1) : '—'}</td>
        <td class="py-2 px-3 text-right text-slate-500">${inst.rpc ? inst.rpc.toFixed(1) : '—'}</td>
        <td class="py-2 px-3 text-right text-slate-500">${inst.go ? inst.go.toFixed(1) : '—'}</td>
        <td class="py-2 px-3 text-right text-slate-500">${inst.oi ? inst.oi.toFixed(1) : '—'}</td>
        <td class="py-2 px-3 text-right text-slate-500">${inst.perception ? inst.perception.toFixed(1) : '—'}</td>
        <td class="py-2 px-3 text-center">${pdfCell}</td>
      `;

      tr.addEventListener('click', () => {
        openInstitutionModal(inst.id);
      });

      tbody.appendChild(tr);
    });

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Error loading explorer:', err);
  }
}

// 11. Institution Scorecard Modal
async function openInstitutionModal(instId) {
  try {
    const res = await fetch(`/v1/institutions/${instId}?category=${currentCategorySlug}&year=${currentYear}`);
    const data = await res.json();

    document.getElementById('mInstName').textContent = data.institution_name;
    document.getElementById('mInstLocation').textContent = `${data.city ? data.city + ', ' : ''}${data.state_name} • ${currentCategoryName} (${currentYear})`;
    document.getElementById('mInstIdBadge').textContent = data.nirf_institute_id ? `ID: ${data.nirf_institute_id}` : 'ID: N/A';

    // Prioritize the ranking record for the currently selected category & year
    const matchedRanking = data.rankings_history.find(h => 
      (h.category_slug === currentCategorySlug || (h.category && h.category.toLowerCase() === currentCategoryName.toLowerCase())) && 
      h.year === currentYear
    ) || data.rankings_history[0];

    const latest = matchedRanking;
    const barsContainer = document.getElementById('mScoreBars');
    barsContainer.innerHTML = '';

    if (latest && latest.tlr !== null) {
      const params = [
        { label: 'Teaching, Learning & Resources (TLR)', value: latest.tlr, color: 'bg-blue-600' },
        { label: 'Research and Professional Practice (RPC)', value: latest.rpc, color: 'bg-emerald-600' },
        { label: 'Graduation Outcomes (GO)', value: latest.go, color: 'bg-amber-600' },
        { label: 'Outreach and Inclusivity (OI)', value: latest.oi, color: 'bg-purple-600' },
        { label: 'Peer Perception (PR)', value: latest.perception, color: 'bg-pink-600' },
      ];

      params.forEach(p => {
        barsContainer.innerHTML += `
          <div>
            <div class="flex justify-between text-xs font-medium text-slate-700 mb-1">
              <span>${p.label}</span>
              <span class="font-bold">${p.value !== null ? p.value.toFixed(2) : 'N/A'}</span>
            </div>
            <div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
              <div class="${p.color} h-full rounded-full" style="width: ${p.value || 0}%"></div>
            </div>
          </div>
        `;
      });
    } else {
      barsContainer.innerHTML = `<p class="text-xs text-slate-400 italic">Individual parameter scores are published for Top Ranked institutions (Rank 1–100/50).</p>`;
    }

    const histBody = document.getElementById('mHistoryBody');
    histBody.innerHTML = '';
    data.rankings_history.forEach(h => {
      const pdf = (h.source_url && h.source_url.startsWith('http'))
        ? `<a href="${h.source_url}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center space-x-1 text-blue-600 hover:text-blue-800 hover:underline font-semibold text-xs" title="Download Official NIRF DCS Report (PDF)"><i data-lucide="file-text" class="w-3.5 h-3.5"></i><span>PDF</span></a>`
        : `<span class="text-slate-300 font-mono">—</span>`;
      histBody.innerHTML += `
        <tr>
          <td class="py-2 px-3 font-bold">${h.year}</td>
          <td class="py-2 px-3 text-slate-600">${h.category}</td>
          <td class="py-2 px-3 text-center"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700">${h.rank}</span></td>
          <td class="py-2 px-3 text-right font-semibold">${h.score ? h.score.toFixed(2) : '—'}</td>
          <td class="py-2 px-3 text-center">${pdf}</td>
        </tr>
      `;
    });

    // Render 5-Pillar Spider / Radar Chart
    const radarCanvas = document.getElementById('chartRadarModal');
    if (chartRadarModalInstance) {
      chartRadarModalInstance.destroy();
      chartRadarModalInstance = null;
    }
    if (radarCanvas && data.radar && data.radar.labels && data.radar.institution_scores) {
      const ctx = radarCanvas.getContext('2d');
      chartRadarModalInstance = new Chart(ctx, {
        type: 'radar',
        data: {
          labels: data.radar.labels,
          datasets: [
            {
              label: data.institution_name,
              data: data.radar.institution_scores,
              backgroundColor: 'rgba(194, 65, 12, 0.25)',
              borderColor: '#c2410c',
              pointBackgroundColor: '#c2410c',
              pointBorderColor: '#fff',
              borderWidth: 2
            },
            {
              label: 'Top 10 Benchmark',
              data: data.radar.top10_benchmarks,
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              borderColor: '#10b981',
              borderDash: [4, 4],
              pointBackgroundColor: '#10b981',
              borderWidth: 1.5
            },
            {
              label: 'Category Average',
              data: data.radar.category_averages,
              backgroundColor: 'rgba(148, 163, 184, 0.15)',
              borderColor: '#94a3b8',
              borderDash: [2, 2],
              pointBackgroundColor: '#94a3b8',
              borderWidth: 1
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            r: {
              min: 0,
              max: 100,
              ticks: { stepSize: 25, font: { size: 9 }, backdropColor: 'transparent' },
              pointLabels: { font: { size: 10, weight: '600' }, color: '#334155' }
            }
          },
          plugins: {
            legend: {
              position: 'bottom',
              labels: { boxWidth: 10, font: { size: 10, weight: '600' }, padding: 8 }
            }
          }
        }
      });
    }

    document.getElementById('modalInstDetail').classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Error opening institution detail:', err);
  }
}

async function openInstitutionModalByName(instName) {
  const res = await fetch(`/v1/institutions?search=${encodeURIComponent(instName)}`);
  const list = await res.json();
  if (list && list.length > 0) {
    openInstitutionModal(list[0].id);
  }
}

// 12. Event Listeners Setup
function setupEventListeners() {
  document.getElementById('selectYear').addEventListener('change', e => {
    currentYear = parseInt(e.target.value);
    const panel = document.getElementById('panelStateDetail');
    if (panel) panel.classList.add('hidden');
    currentSelectedStateId = null;
    currentSelectedStateName = null;
    highlightStateOnMap(null);
    highlightStateOnLeaderboard(null);
    const mainEl = document.querySelector('main');
    if (mainEl) mainEl.scrollTo({ top: 0, behavior: 'smooth' });
    loadCurrentView();
  });

  document.getElementById('selectCategory').addEventListener('change', e => {
    currentCategorySlug = e.target.value;
    const opt = e.target.options[e.target.selectedIndex];
    currentCategoryName = opt.textContent;
    const panel = document.getElementById('panelStateDetail');
    if (panel) panel.classList.add('hidden');
    currentSelectedStateId = null;
    currentSelectedStateName = null;
    highlightStateOnMap(null);
    highlightStateOnLeaderboard(null);
    const mainEl = document.querySelector('main');
    if (mainEl) mainEl.scrollTo({ top: 0, behavior: 'smooth' });
    loadCurrentView();
  });

  const selectScopeEl = document.getElementById('selectScope');
  if (selectScopeEl) {
    selectScopeEl.addEventListener('change', e => {
      currentScope = e.target.value;
      const panel = document.getElementById('panelStateDetail');
      if (panel) panel.classList.add('hidden');
      currentSelectedStateId = null;
      currentSelectedStateName = null;
      highlightStateOnMap(null);
      highlightStateOnLeaderboard(null);
      const mainEl = document.querySelector('main');
      if (mainEl) mainEl.scrollTo({ top: 0, behavior: 'smooth' });
      loadCurrentView();
    });
  }

  document.getElementById('btnMapReset').addEventListener('click', () => {
    if (echartsInstance) {
      echartsInstance.dispatchAction({ type: 'restore' });
    }
    const panel = document.getElementById('panelStateDetail');
    if (panel) panel.classList.add('hidden');
    currentSelectedStateId = null;
    currentSelectedStateName = null;
    highlightStateOnMap(null);
    highlightStateOnLeaderboard(null);
  });

  document.getElementById('btnCloseStatePanel').addEventListener('click', () => {
    document.getElementById('panelStateDetail').classList.add('hidden');
    currentSelectedStateId = null;
    currentSelectedStateName = null;
    const btnStateBrief = document.getElementById('btnStateBrief');
    if (btnStateBrief) {
      const span = btnStateBrief.querySelector('span');
      if (span) span.textContent = 'State Ranking Report (PDF)';
    }
    highlightStateOnMap(null);
    highlightStateOnLeaderboard(null);
  });

  document.getElementById('btnExportStateData').addEventListener('click', () => {
    if (currentSelectedStateId) {
      window.open(`/v1/export?format=csv&year=${currentYear}&category=${currentCategorySlug}&state_id=${currentSelectedStateId}&scope=${currentScope}&ownership=${currentOwnership}`, '_blank');
    }
  });

  // Ownership Filter Listener
  const selectOwnershipEl = document.getElementById('selectOwnership');
  if (selectOwnershipEl) {
    selectOwnershipEl.addEventListener('change', e => {
      currentOwnership = e.target.value;
      const panel = document.getElementById('panelStateDetail');
      if (panel) panel.classList.add('hidden');
      currentSelectedStateId = null;
      currentSelectedStateName = null;
      highlightStateOnMap(null);
      highlightStateOnLeaderboard(null);
      const mainEl = document.querySelector('main');
      if (mainEl) mainEl.scrollTo({ top: 0, behavior: 'smooth' });
      loadCurrentView();
    });
  }

  // Presentation / Kiosk Mode Listener
  const btnKioskMode = document.getElementById('btnKioskMode');
  if (btnKioskMode) {
    btnKioskMode.addEventListener('click', () => {
      const isKiosk = document.body.classList.toggle('kiosk-mode');
      if (isKiosk) {
        btnKioskMode.innerHTML = `<i data-lucide="minimize" class="w-3.5 h-3.5 text-blue-600"></i><span class="hidden md:inline">Exit Kiosk</span>`;
        if (document.documentElement.requestFullscreen) {
          document.documentElement.requestFullscreen().catch(() => {});
        }
      } else {
        btnKioskMode.innerHTML = `<i data-lucide="maximize" class="w-3.5 h-3.5 text-blue-600"></i><span class="hidden md:inline">Presentation Mode</span>`;
        if (document.fullscreenElement && document.exitFullscreen) {
          document.exitFullscreen().catch(() => {});
        }
      }
      if (window.lucide) lucide.createIcons();
      if (echartsInstance) setTimeout(() => echartsInstance.resize(), 100);
    });
  }

  document.addEventListener('fullscreenchange', () => {
    if (!document.fullscreenElement && document.body.classList.contains('kiosk-mode')) {
      document.body.classList.remove('kiosk-mode');
      if (btnKioskMode) {
        btnKioskMode.innerHTML = `<i data-lucide="maximize" class="w-3.5 h-3.5 text-blue-600"></i><span class="hidden md:inline">Presentation Mode</span>`;
        if (window.lucide) lucide.createIcons();
      }
      if (echartsInstance) setTimeout(() => echartsInstance.resize(), 100);
    }
  });

  // State Policy Brief Generator Button
  const btnStateBrief = document.getElementById('btnStateBrief');
  if (btnStateBrief) {
    btnStateBrief.addEventListener('click', () => {
      if (currentSelectedStateId) {
        generateStateBrief(currentSelectedStateId);
      }
    });
  }

  // Print Factsheet PDF Button
  const btnPrintStateBrief = document.getElementById('btnPrintStateBrief');
  if (btnPrintStateBrief) {
    btnPrintStateBrief.addEventListener('click', () => {
      window.print();
    });
  }

  // Close Factsheet Modal Button
  const btnCloseStateBrief = document.getElementById('btnCloseStateBrief');
  if (btnCloseStateBrief) {
    btnCloseStateBrief.addEventListener('click', () => {
      document.getElementById('modalStateBrief').classList.add('hidden');
    });
  }

  document.getElementById('btnExportCSV').addEventListener('click', e => {
    e.preventDefault();
    window.open(`/v1/export?format=csv&year=${currentYear}&category=${currentCategorySlug}&scope=${currentScope}`, '_blank');
  });

  document.getElementById('btnExportXLSX').addEventListener('click', e => {
    e.preventDefault();
    window.open(`/v1/export?format=xlsx&year=${currentYear}&category=${currentCategorySlug}&scope=${currentScope}`, '_blank');
  });

  document.getElementById('btnModalClose').addEventListener('click', () => {
    document.getElementById('modalInstDetail').classList.add('hidden');
  });
  document.getElementById('btnModalCloseBottom').addEventListener('click', () => {
    document.getElementById('modalInstDetail').classList.add('hidden');
  });

  let searchTimer = null;
  const expSearchInput = document.getElementById('explorerSearchInput');
  if (expSearchInput) {
    expSearchInput.addEventListener('input', e => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        explorerSearch = e.target.value;
        loadExplorerTable();
      }, 250);
    });
  }

  document.querySelectorAll('.exp-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.exp-tab').forEach(t => {
        t.className = 'exp-tab px-3 py-1 rounded-md text-slate-600 hover:text-slate-900';
      });
      tab.className = 'exp-tab px-3 py-1 rounded-md text-blue-700 bg-white shadow-sm font-bold';
      explorerTier = tab.getAttribute('data-type');
      loadExplorerTable();
    });
  });
}


// 13. State vs State Head-to-Head Comparison & Movers Logic
async function initCompareSelectors() {
  const selA = document.getElementById('selectCompareStateA');
  const selB = document.getElementById('selectCompareStateB');
  if (!selA || !selB) return;

  if (selA.children.length === 0 || allStatesList.length === 0) {
    try {
      const res = await fetch('/v1/states');
      allStatesList = await res.json();
      
      selA.innerHTML = '';
      selB.innerHTML = '';
      allStatesList.forEach(st => {
        const optA = document.createElement('option');
        optA.value = st.id;
        optA.textContent = st.name;
        if (st.id === compareStateAId) optA.selected = true;
        selA.appendChild(optA);

        const optB = document.createElement('option');
        optB.value = st.id;
        optB.textContent = st.name;
        if (st.id === compareStateBId) optB.selected = true;
        selB.appendChild(optB);
      });

      selA.addEventListener('change', e => {
        compareStateAId = parseInt(e.target.value);
        renderStateComparison();
      });
      selB.addEventListener('change', e => {
        compareStateBId = parseInt(e.target.value);
        renderStateComparison();
      });
    } catch (e) {
      console.error('Failed to load states list for comparison:', e);
    }
  }
}

async function renderStateComparison() {
  const container = document.getElementById('compareStateContent');
  if (!container) return;

  try {
    const res = await fetch(`/v1/benchmarking/compare-states?state_a_id=${compareStateAId}&state_b_id=${compareStateBId}&year=${currentYear}&category=${currentCategorySlug}&scope=${currentScope}&ownership=${currentOwnership}`);
    const data = await res.json();
    const a = data.state_a;
    const b = data.state_b;
    const catName = data.category_name || currentCategoryName;
    const scopeLabel = currentScope === 'top_100' ? 'Top 100' : 'Ranked';

    // Update Radar badge & description
    const badgeRadar = document.getElementById('badgeCompareRadarStates');
    if (badgeRadar) badgeRadar.textContent = `${a.state_name} vs ${b.state_name} • ${catName}`;
    const descRadar = document.getElementById('descCompareRadar');
    if (descRadar) descRadar.textContent = `Comparative state average across 5 evaluation pillars in ${catName}`;

    // Update Discipline Bar Chart badge
    const badgeSeats = document.getElementById('badgeCompareDisciplineSeats');
    if (badgeSeats) badgeSeats.textContent = `All 6 Streams • Active: ${catName}`;

    // 1. Render Dynamic 5-Pillar Spider / Radar Chart
    const ctxRadar = document.getElementById('chartCompareRadar');
    if (ctxRadar) {
      if (chartCompareRadarInstance) {
        chartCompareRadarInstance.destroy();
        chartCompareRadarInstance = null;
      }
      chartCompareRadarInstance = new Chart(ctxRadar.getContext('2d'), {
        type: 'radar',
        data: {
          labels: data.radar_labels || ["Teaching (TLR)", "Research (RPC)", "Graduation (GO)", "Outreach (OI)", "Perception (PR)"],
          datasets: [
            {
              label: a.state_name,
              data: a.radar_scores || [a.avg_tlr, a.avg_rpc, a.avg_go, a.avg_oi, a.avg_pr],
              backgroundColor: 'rgba(37, 99, 235, 0.25)',
              borderColor: '#2563eb',
              pointBackgroundColor: '#2563eb',
              pointBorderColor: '#fff',
              borderWidth: 2.5
            },
            {
              label: b.state_name,
              data: b.radar_scores || [b.avg_tlr, b.avg_rpc, b.avg_go, b.avg_oi, b.avg_pr],
              backgroundColor: 'rgba(234, 88, 12, 0.22)',
              borderColor: '#ea580c',
              pointBackgroundColor: '#ea580c',
              pointBorderColor: '#fff',
              borderWidth: 2.5
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            r: {
              min: 0,
              max: 100,
              ticks: { stepSize: 25, font: { size: 9 }, backdropColor: 'transparent' },
              pointLabels: { font: { size: 10, weight: '700' }, color: '#334155' }
            }
          },
          plugins: {
            legend: {
              position: 'bottom',
              labels: { boxWidth: 12, font: { size: 10, weight: '700' }, padding: 8 }
            }
          }
        }
      });
    }

    // 2. Render Dynamic Grouped Bar Chart (Discipline Distribution)
    const ctxDisc = document.getElementById('chartCompareDiscipline');
    if (ctxDisc) {
      if (chartCompareDisciplineInstance) {
        chartCompareDisciplineInstance.destroy();
        chartCompareDisciplineInstance = null;
      }

      const discLabels = ['Overall', 'Universities', 'Engineering', 'Management', 'Medical', 'State Public'];
      const discKeys = ['overall', 'universities', 'engineering', 'management', 'medical', 'state_public_university'];
      const countsA = discKeys.map(k => a.category_distribution[k] || 0);
      const countsB = discKeys.map(k => b.category_distribution[k] || 0);

      chartCompareDisciplineInstance = new Chart(ctxDisc.getContext('2d'), {
        type: 'bar',
        data: {
          labels: discLabels,
          datasets: [
            {
              label: a.state_name,
              data: countsA,
              backgroundColor: discKeys.map(k => k === currentCategorySlug ? '#1d4ed8' : '#3b82f6'),
              borderColor: discKeys.map(k => k === currentCategorySlug ? '#1e3a8a' : 'transparent'),
              borderWidth: discKeys.map(k => k === currentCategorySlug ? 2.5 : 0),
              borderRadius: 6,
              barPercentage: 0.7,
              categoryPercentage: 0.7
            },
            {
              label: b.state_name,
              data: countsB,
              backgroundColor: discKeys.map(k => k === currentCategorySlug ? '#c2410c' : '#f97316'),
              borderColor: discKeys.map(k => k === currentCategorySlug ? '#7c2d12' : 'transparent'),
              borderWidth: discKeys.map(k => k === currentCategorySlug ? 2.5 : 0),
              borderRadius: 6,
              barPercentage: 0.7,
              categoryPercentage: 0.7
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: { boxWidth: 12, font: { size: 10, weight: '700' }, padding: 8 }
            }
          },
          scales: {
            x: { ticks: { font: { size: 10, weight: '600' } }, grid: { display: false } },
            y: { ticks: { font: { size: 10 }, stepSize: 2 }, grid: { color: '#f1f5f9' }, beginAtZero: true }
          }
        }
      });
    }

    // Dynamic advantage insights
    let rpcAdvantage = '';
    if (a.avg_rpc !== null && b.avg_rpc !== null && (a.avg_rpc > 0 || b.avg_rpc > 0)) {
      const diff = (a.avg_rpc - b.avg_rpc).toFixed(1);
      if (diff > 0) {
        rpcAdvantage = `<span class="text-xs font-semibold px-3 py-1 rounded-full bg-blue-100 text-blue-900 border border-blue-300 font-bold">★ ${a.state_name} leads Research (RPC) in ${catName} by +${diff} pts</span>`;
      } else if (diff < 0) {
        rpcAdvantage = `<span class="text-xs font-semibold px-3 py-1 rounded-full bg-amber-100 text-amber-900 border border-amber-300 font-bold">★ ${b.state_name} leads Research (RPC) in ${catName} by +${Math.abs(diff)} pts</span>`;
      }
    }

    let seatAdvantage = '';
    const seatDiff = a.total_placements - b.total_placements;
    if (seatDiff > 0) {
      seatAdvantage = `<span class="text-xs font-semibold px-3 py-1 rounded-full bg-blue-100 text-blue-900 border border-blue-300 font-bold">★ ${a.state_name} has +${seatDiff} more ${catName} ${scopeLabel} seats</span>`;
    } else if (seatDiff < 0) {
      seatAdvantage = `<span class="text-xs font-semibold px-3 py-1 rounded-full bg-amber-100 text-amber-900 border border-amber-300 font-bold">★ ${b.state_name} has +${Math.abs(seatDiff)} more ${catName} ${scopeLabel} seats</span>`;
    }

    const ownA = a.ownership_breakdown || { Central: 0, 'State Public': 0, 'Private / Deemed': 0 };
    const ownB = b.ownership_breakdown || { Central: 0, 'State Public': 0, 'Private / Deemed': 0 };

    container.innerHTML = `
      <!-- Head-to-Head Header Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- State A Card -->
        <div class="bg-blue-50/70 border-2 border-blue-200 rounded-xl p-4 shadow-sm">
          <div class="flex items-center justify-between">
            <div>
              <span class="text-[10px] font-bold tracking-wider text-blue-600 uppercase">State A (Selected)</span>
              <h3 class="text-xl font-black text-blue-950 mt-0.5">${a.state_name}</h3>
            </div>
            <div class="text-right">
              <span class="text-2xl font-black text-blue-700">${a.total_placements}</span>
              <p class="text-[10px] text-blue-600 font-bold uppercase">${scopeLabel} in ${catName}</p>
            </div>
          </div>
          <div class="mt-3 pt-3 border-t border-blue-200/80 flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1 text-xs">
            <span class="text-slate-600 flex-shrink-0">Top in ${catName}:</span>
            <span class="font-bold text-slate-900 break-words text-left sm:text-right" title="${a.top_institution || '—'}">${a.top_institution || '—'}</span>
          </div>
        </div>

        <!-- State B Card (High Contrast Amber/Orange) -->
        <div class="bg-amber-50/80 border-2 border-amber-300 rounded-xl p-4 shadow-sm">
          <div class="flex items-center justify-between">
            <div>
              <span class="text-[10px] font-bold tracking-wider text-amber-700 uppercase">State B (Benchmark)</span>
              <h3 class="text-xl font-black text-amber-950 mt-0.5">${b.state_name}</h3>
            </div>
            <div class="text-right">
              <span class="text-2xl font-black text-amber-600">${b.total_placements}</span>
              <p class="text-[10px] text-amber-700 font-bold uppercase">${scopeLabel} in ${catName}</p>
            </div>
          </div>
          <div class="mt-3 pt-3 border-t border-amber-200 flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1 text-xs">
            <span class="text-slate-600 flex-shrink-0">Top in ${catName}:</span>
            <span class="font-bold text-slate-900 break-words text-left sm:text-right" title="${b.top_institution || '—'}">${b.top_institution || '—'}</span>
          </div>
        </div>
      </div>

      <!-- Key Insights Banner -->
      <div class="flex flex-wrap items-center justify-center gap-3 py-1">
        ${seatAdvantage}
        ${rpcAdvantage}
      </div>

      <!-- Side-by-side Comparative Metrics -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Metric 1: Avg Score -->
        <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm text-center">
          <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Average NIRF Score</span>
          <div class="flex items-center justify-center space-x-4 mt-2">
            <span class="text-xl font-black text-blue-700">${a.avg_score ? a.avg_score.toFixed(1) : '—'}</span>
            <span class="text-xs text-slate-300 font-bold">vs</span>
            <span class="text-xl font-black text-amber-600">${b.avg_score ? b.avg_score.toFixed(1) : '—'}</span>
          </div>
          <p class="text-[10px] text-slate-400 mt-1">${catName} Score Average</p>
        </div>

        <!-- Metric 2: Research Strength (RPC) -->
        <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm text-center">
          <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Research Strength (RPC)</span>
          <div class="flex items-center justify-center space-x-4 mt-2">
            <span class="text-xl font-black text-blue-700">${a.avg_rpc ? a.avg_rpc.toFixed(1) : '—'}</span>
            <span class="text-xs text-slate-300 font-bold">vs</span>
            <span class="text-xl font-black text-amber-600">${b.avg_rpc ? b.avg_rpc.toFixed(1) : '—'}</span>
          </div>
          <p class="text-[10px] text-slate-400 mt-1">Mean RPC in ${catName}</p>
        </div>

        <!-- Metric 3: Teaching Quality (TLR) -->
        <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm text-center">
          <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Teaching & Learning (TLR)</span>
          <div class="flex items-center justify-center space-x-4 mt-2">
            <span class="text-xl font-black text-blue-700">${a.avg_tlr ? a.avg_tlr.toFixed(1) : '—'}</span>
            <span class="text-xs text-slate-300 font-bold">vs</span>
            <span class="text-xl font-black text-amber-600">${b.avg_tlr ? b.avg_tlr.toFixed(1) : '—'}</span>
          </div>
          <p class="text-[10px] text-slate-400 mt-1">Mean TLR in ${catName}</p>
        </div>
      </div>

      <!-- Governance Structure Mix Comparison -->
      <div class="bg-slate-50/60 rounded-xl border border-slate-200 p-5">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h4 class="text-xs font-bold text-slate-800 uppercase tracking-wider">Governance Structure Footprint</h4>
            <p class="text-[11px] text-slate-500 mt-0.5">Central Government vs State Public vs Private / Deemed in ${catName}</p>
          </div>
          <div class="flex items-center space-x-3 text-[10px] font-semibold">
            <span class="text-blue-700 font-bold">■ ${a.state_name}</span>
            <span class="text-amber-600 font-bold">■ ${b.state_name}</span>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <!-- Central -->
          <div class="bg-white p-3 rounded-lg border border-slate-200">
            <span class="text-slate-500 block text-[11px] font-medium">Central Institutes</span>
            <div class="flex justify-between items-center mt-1">
              <span class="text-blue-700 font-black text-lg">${ownA['Central']}</span>
              <span class="text-slate-300 font-bold text-xs">vs</span>
              <span class="text-amber-600 font-black text-lg">${ownB['Central']}</span>
            </div>
            <span class="text-[10px] text-slate-400 block mt-0.5">IITs, NITs, AIIMS, IISc</span>
          </div>

          <!-- State Public -->
          <div class="bg-white p-3 rounded-lg border border-slate-200">
            <span class="text-slate-500 block text-[11px] font-medium">State Public Universities</span>
            <div class="flex justify-between items-center mt-1">
              <span class="text-blue-700 font-black text-lg">${ownA['State Public']}</span>
              <span class="text-slate-300 font-bold text-xs">vs</span>
              <span class="text-amber-600 font-black text-lg">${ownB['State Public']}</span>
            </div>
            <span class="text-[10px] text-slate-400 block mt-0.5">State Government Funded</span>
          </div>

          <!-- Private / Deemed -->
          <div class="bg-white p-3 rounded-lg border border-slate-200">
            <span class="text-slate-500 block text-[11px] font-medium">Private / Deemed Universities</span>
            <div class="flex justify-between items-center mt-1">
              <span class="text-blue-700 font-black text-lg">${ownA['Private / Deemed']}</span>
              <span class="text-slate-300 font-bold text-xs">vs</span>
              <span class="text-amber-600 font-black text-lg">${ownB['Private / Deemed']}</span>
            </div>
            <span class="text-[10px] text-slate-400 block mt-0.5">Self-Financed / Deemed</span>
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    console.error('Failed to render state comparison:', err);
  }
}

async function renderMoversTracker() {
  const tbody = document.getElementById('tableMoversBody');
  const risersContainer = document.getElementById('containerFastestRisers');
  if (!tbody || !risersContainer) return;

  try {
    const res = await fetch(`/v1/benchmarking/movers?category=${currentCategorySlug}&scope=${currentScope}`);
    const data = await res.json();

    // 1. State changes table
    tbody.innerHTML = '';
    (data.state_changes || []).forEach(st => {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-50';

      let changePill = '';
      if (st.net_change > 0) {
        changePill = `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">+${st.net_change}</span>`;
      } else if (st.net_change < 0) {
        changePill = `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-rose-100 text-rose-800 border border-rose-300">${st.net_change}</span>`;
      } else {
        changePill = `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-600">0</span>`;
      }

      tr.innerHTML = `
        <td class="py-2 px-3 font-semibold text-slate-800">${st.state_name}</td>
        <td class="py-2 px-3 text-center text-slate-600 font-mono">${st.base_count}</td>
        <td class="py-2 px-3 text-center text-slate-900 font-bold font-mono">${st.target_count}</td>
        <td class="py-2 px-3 text-right">${changePill}</td>
      `;
      tbody.appendChild(tr);
    });

    // 2. Fastest risers cards
    risersContainer.innerHTML = '';
    (data.fastest_risers || []).slice(0, 6).forEach(r => {
      risersContainer.innerHTML += `
        <div class="bg-slate-50/80 border border-slate-200 rounded-lg p-3 hover:bg-slate-100 transition">
          <div class="flex items-start justify-between gap-2">
            <div class="flex-1 min-w-0">
              <h5 class="text-xs font-bold text-slate-900 break-words leading-snug" title="${r.institution_name}">${r.institution_name}</h5>
              <p class="text-[11px] text-slate-500">${r.state_name} • <span class="font-medium text-blue-700">${r.category}</span></p>
            </div>
            <div class="text-right flex-shrink-0">
              <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                ▲ +${r.jump} spots
              </span>
              <p class="text-[10px] text-slate-400 mt-0.5 font-mono">#${r.base_rank} → #${r.target_rank}</p>
            </div>
          </div>
        </div>
      `;
    });

  } catch (err) {
    console.error('Failed to load movers tracker:', err);
  }
}

// 14. One-Click State Policy Brief (Factsheet Generator)
async function generateStateBrief(stateId) {
  try {
    const res = await fetch(`/v1/export/state-brief?state_id=${stateId}&year=${currentYear}&scope=${currentScope}`);
    const data = await res.json();

    const container = document.getElementById('stateBriefPrintableContent');
    if (!container) return;

    const s = data.summary;
    const catKeys = Object.keys(data.category_breakdown || {});
    const own = data.ownership_breakdown || { Central: 0, 'State Public': 0, 'Private / Deemed': 0 };

    let catBadgesHtml = catKeys.map(k => `
      <div class="bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-center">
        <span class="text-[11px] text-slate-500 font-semibold block">${k}</span>
        <span class="text-base font-black text-slate-900">${data.category_breakdown[k]}</span>
      </div>
    `).join('');

    const rankedInsts = (data.institutions || []).filter(inst => {
      if (inst.is_rank_band) return false;
      const r = String(inst.rank || '');
      if (r.includes('-') || !inst.score) return false;
      return true;
    });

    let instRowsHtml = rankedInsts.map(inst => {
      const pdf = (inst.source_url && inst.source_url.startsWith('http'))
        ? `<a href="${inst.source_url}" target="_blank" class="text-blue-600 font-bold hover:underline">PDF</a>`
        : `<span class="text-slate-300">—</span>`;
      return `
        <tr class="hover:bg-slate-50">
          <td class="py-1.5 px-2.5 text-center font-bold text-blue-700 whitespace-nowrap">#${inst.rank}</td>
          <td class="py-1.5 px-2.5 font-semibold text-slate-900">${inst.institution_name}</td>
          <td class="py-1.5 px-2.5 text-slate-600 whitespace-nowrap">${inst.category}</td>
          <td class="py-1.5 px-2.5 text-slate-500 text-[11px] whitespace-nowrap">${inst.institution_type}</td>
          <td class="py-1.5 px-2.5 text-right font-bold text-slate-900 whitespace-nowrap">${inst.score ? inst.score.toFixed(2) : '—'}</td>
          <td class="py-1.5 px-2.5 text-right text-slate-600 whitespace-nowrap">${inst.tlr ? inst.tlr.toFixed(1) : '—'}</td>
          <td class="py-1.5 px-2.5 text-right text-slate-600 whitespace-nowrap">${inst.rpc ? inst.rpc.toFixed(1) : '—'}</td>
          <td class="py-1.5 px-2.5 text-right text-slate-600 whitespace-nowrap">${inst.go ? inst.go.toFixed(1) : '—'}</td>
          <td class="py-1.5 px-2.5 text-right text-slate-600 whitespace-nowrap">${inst.oi ? inst.oi.toFixed(1) : '—'}</td>
          <td class="py-1.5 px-2.5 text-right text-slate-600 whitespace-nowrap">${inst.perception ? inst.perception.toFixed(1) : '—'}</td>
          <td class="py-1.5 px-2.5 text-center whitespace-nowrap">${pdf}</td>
        </tr>
      `;
    }).join('');

    container.innerHTML = `
      <!-- Briefing Header -->
      <div class="border-b-2 border-slate-900 pb-4">
        <div class="flex items-center justify-between">
          <div>
            <span class="text-[10px] font-bold tracking-widest text-blue-700 uppercase">Government of India • Ministry of Education</span>
            <h2 class="text-2xl font-black text-slate-900 tracking-tight mt-0.5">${data.state_name} – Higher Education Ranking Report</h2>
            <p class="text-xs text-slate-500 mt-0.5">National Institutional Ranking Framework (NIRF ${data.year}) • Scope: ${data.scope === 'top_100' ? 'Top 100 Institutions' : 'All Ranked'}</p>
          </div>
          <div class="text-right">
            <span class="inline-block px-3 py-1 bg-emerald-50 text-emerald-800 border border-emerald-300 rounded-lg text-xs font-bold font-mono">
              OFFICIAL RANKING REPORT
            </span>
            <p class="text-[10px] text-slate-400 mt-1">Generated: ${new Date().toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' })}</p>
          </div>
        </div>
      </div>

      <!-- Key Metrics Row -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div class="bg-emerald-50/60 border border-emerald-200 rounded-xl p-3">
          <span class="text-[10px] font-bold text-emerald-700 uppercase tracking-wider">Best National Rank</span>
          <p class="text-2xl font-black text-emerald-900 mt-1">#${s.best_rank || 'N/A'}</p>
          <span class="text-[10px] text-emerald-700 break-words block font-medium leading-tight mt-0.5" title="${s.top_institution || ''}">${s.top_institution || 'N/A'}</span>
        </div>
        <div class="bg-amber-50/60 border border-amber-200 rounded-xl p-3">
          <span class="text-[10px] font-bold text-amber-700 uppercase tracking-wider">Avg NIRF Score</span>
          <p class="text-2xl font-black text-amber-900 mt-1">${s.avg_score ? s.avg_score.toFixed(2) : '—'}</p>
          <span class="text-[10px] text-amber-700">Top institutions mean</span>
        </div>
        <div class="bg-purple-50/60 border border-purple-200 rounded-xl p-3">
          <span class="text-[10px] font-bold text-purple-700 uppercase tracking-wider">Research vs Teaching</span>
          <p class="text-sm font-black text-purple-900 mt-2">RPC: ${s.avg_rpc ? s.avg_rpc.toFixed(1) : '—'} <span class="text-slate-400 font-normal">|</span> TLR: ${s.avg_tlr ? s.avg_tlr.toFixed(1) : '—'}</p>
          <span class="text-[10px] text-purple-700">State diagnostic average</span>
        </div>
      </div>

      <!-- Discipline Footprint -->
      <div class="bg-white rounded-xl border border-slate-200 p-4">
        <h4 class="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2.5">Discipline & Category Footprint</h4>
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
          ${catBadgesHtml}
        </div>
      </div>

      <!-- Ranked Institutions Table -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <h4 class="text-xs font-bold text-slate-800 uppercase tracking-wider">Ranked Institutions (${data.state_name})</h4>
          <span class="text-[10px] text-slate-400">Official Parameter Scores</span>
        </div>
        <div class="overflow-x-auto rounded-lg border border-slate-200">
          <table class="min-w-full text-xs divide-y divide-slate-200">
            <thead class="bg-slate-50 font-semibold text-slate-600">
              <tr>
                <th class="py-1.5 px-2.5 text-center">Rank</th>
                <th class="py-1.5 px-2.5 text-left">Institution Name</th>
                <th class="py-1.5 px-2.5 text-left">Category</th>
                <th class="py-1.5 px-2.5 text-left">Governance</th>
                <th class="py-1.5 px-2.5 text-right font-bold text-slate-800">NIRF Score</th>
                <th class="py-1.5 px-2.5 text-right" title="Teaching, Learning & Resources">TLR</th>
                <th class="py-1.5 px-2.5 text-right" title="Research & Professional Practice">RPC</th>
                <th class="py-1.5 px-2.5 text-right" title="Graduation Outcomes">GO</th>
                <th class="py-1.5 px-2.5 text-right" title="Outreach & Inclusivity">OI</th>
                <th class="py-1.5 px-2.5 text-right" title="Peer Perception">PR</th>
                <th class="py-1.5 px-2.5 text-center">Report</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 bg-white">
              ${instRowsHtml}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Briefing Footer Note -->
      <div class="text-[10px] text-slate-400 border-t border-slate-200 pt-3 flex items-center justify-between">
        <span>Confidential & Executive Factsheet • Powered by NIRF Insight • Managed by ICARE under MITRA Project</span>
        <span>Page 1 of 1</span>
      </div>
    `;

    document.getElementById('modalStateBrief').classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Failed to generate state policy brief:', err);
  }
}
