/* LocalizaVotos — Dashboard com Leaflet.js + Chart.js */

'use strict';

// ─── Configuração ─────────────────────────────────────────────────────────────
const API = '';
const TOKEN = localStorage.getItem('lv_token');

if (!TOKEN) { window.location.href = '/'; }

// ─── Estado global ────────────────────────────────────────────────────────────
let map = null;
let tileLayer = null;
let votosLayer = null;
let extraLayers = {};
let rawFeatures = [];
let currentBase = null;
let isMunicipios = false;

// Camadas extras disponíveis (carregadas uma vez da API)
let allAvailableLayers = [];
// Visibilidade da camada de votos (toggle)
let votosVisible = true;

// Prefixos/sufixos que indicam camada geográfica específica de uma cidade
const GEO_PREFIXES = ['locais_', 'lider_', 'renda_', 'popula_', 'regionais_', 'bairros_', 'zonas_', 'votos_'];
const GEO_SUFFIXES = ['_distritos', '_bairros', '_zonas'];

// Chart.js instances (para destruir antes de recriar)
const _charts = {};

// ─── Tile layers disponíveis ──────────────────────────────────────────────────
const TILES = {
  dark: {
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attr: '© <a href="https://openstreetmap.org">OpenStreetMap</a> © <a href="https://carto.com">CARTO</a>',
    subdomains: 'abcd',
  },
  light: {
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attr: '© <a href="https://openstreetmap.org">OpenStreetMap</a> © <a href="https://carto.com">CARTO</a>',
    subdomains: 'abcd',
  },
  satellite: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr: '© Esri, Maxar, Earthstar Geographics',
    subdomains: undefined,
  },
  osm: {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attr: '© <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
    subdomains: 'abc',
  },
};

// ─── Chart.js — tema escuro padrão ───────────────────────────────────────────
Chart.defaults.color = '#8b90a7';
Chart.defaults.borderColor = '#2d3040';
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size = 12;

// ─── API helper ───────────────────────────────────────────────────────────────
async function apiFetch(url, opts = {}) {
  const res = await fetch(API + url, {
    ...opts,
    headers: { 'Authorization': `Bearer ${TOKEN}`, 'Content-Type': 'application/json', ...(opts.headers || {}) },
  });
  if (res.status === 401) { localStorage.clear(); window.location.href = '/'; return null; }
  if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || `HTTP ${res.status}`); }
  return res.json();
}

// ─── Cores de votos ───────────────────────────────────────────────────────────
function voteColor(v) {
  if (!v || v <= 0) return '#6c757d';
  if (v <= 15)  return '#2dc937';
  if (v <= 40)  return '#f1c40f';
  if (v <= 80)  return '#e67e22';
  if (v <= 150) return '#e74c3c';
  return '#8e1a1a';
}

function choroplethColor(v, maxV) {
  if (!v || v <= 0 || !maxV) return '#1e2236';
  const t = Math.pow(v / maxV, 0.45);
  return `rgb(${Math.round(30 + 200 * t)},${Math.round(34 + 23 * t)},${Math.round(54 + 16 * t)})`;
}

function voteRadius(v) {
  return Math.max(5, Math.min(22, 4 + Math.sqrt(Math.max(0, v)) * 0.85));
}

// ─── Popups ───────────────────────────────────────────────────────────────────
function buildPointPopup(p) {
  const nome = p._nome || p._local || p.NM_LOCAL_VOTACAO || 'Local';
  const votos = (p._qt_votos || 0).toLocaleString('pt-BR');
  const mun = p._municipio || p.NM_MUNICIPIO || '';
  const bairro = p._bairro || '';
  return `<div class="popup-name">${nome}</div>
    <div class="popup-votes">⬤ ${votos} votos</div>
    <div class="popup-meta">${mun ? `📍 ${mun}<br>` : ''}${bairro ? `🏘 ${bairro}` : ''}</div>`;
}

function buildChoroplethPopup(p) {
  const mun = p._municipio || p.Municipio || '';
  const votos = (p._qt_votos || 0).toLocaleString('pt-BR');
  const reg = p.Região || p.Regiao || '';
  return `<div class="popup-name">${mun || 'Município'}</div>
    <div class="popup-votes">⬤ ${votos} votos</div>
    ${reg ? `<div class="popup-meta">Região: ${reg}</div>` : ''}`;
}

// ─── Renderização mapa ────────────────────────────────────────────────────────
function renderPoints(features) {
  if (votosLayer) { votosLayer.remove(); votosLayer = null; }
  if (!features.length) return;
  votosLayer = L.geoJSON({ type: 'FeatureCollection', features }, {
    pointToLayer(ft, ll) {
      const v = ft.properties._qt_votos || 0;
      return L.circleMarker(ll, {
        radius: voteRadius(v), fillColor: voteColor(v),
        color: 'rgba(255,255,255,0.3)', weight: 0.6, opacity: 0.9, fillOpacity: 0.88,
      });
    },
    onEachFeature(ft, layer) {
      layer.bindPopup(buildPointPopup(ft.properties), { className: 'lv-popup', maxWidth: 240 });
    },
  }).addTo(map);
  if (!votosVisible) { votosLayer.remove(); }
  try { map.fitBounds(votosLayer.getBounds(), { padding: [30, 30], maxZoom: 14 }); } catch (_) {}
}

function renderChoropleth(features) {
  if (votosLayer) { votosLayer.remove(); votosLayer = null; }
  if (!features.length) return;
  const maxV = Math.max(...features.map(f => f.properties._qt_votos || 0), 1);
  votosLayer = L.geoJSON({ type: 'FeatureCollection', features }, {
    style(ft) {
      return { fillColor: choroplethColor(ft.properties._qt_votos || 0, maxV), color: '#3d4156', weight: 1, opacity: 0.85, fillOpacity: 0.72 };
    },
    onEachFeature(ft, layer) {
      layer.bindPopup(buildChoroplethPopup(ft.properties), { className: 'lv-popup', maxWidth: 220 });
      layer.on('mouseover', () => layer.setStyle({ fillOpacity: 0.92, weight: 2, color: '#8b90a7' }));
      layer.on('mouseout', () => votosLayer && votosLayer.resetStyle(layer));
    },
  }).addTo(map);
  if (!votosVisible) { votosLayer.remove(); }
  try { map.fitBounds(votosLayer.getBounds(), { padding: [20, 20] }); } catch (_) {}
}

// ─── Filtros ──────────────────────────────────────────────────────────────────
function getFiltered() {
  const mun = document.getElementById('municipeFilter').value;
  const minV = parseInt(document.getElementById('minVotesRange').value) || 0;
  return rawFeatures.filter(f => {
    const p = f.properties || {};
    const fMun = p._municipio || p.NM_MUNICIPIO || '';
    return (p._qt_votos || 0) >= minV && (!mun || fMun === mun);
  });
}

function applyFilters() {
  const filtered = getFiltered();
  if (isMunicipios) { renderChoropleth(filtered); }
  else              { renderPoints(filtered); }
  updateKPIs(filtered);
  renderCharts(filtered);
  renderTable(filtered);
}

// ─── KPIs ─────────────────────────────────────────────────────────────────────
function updateKPIs(features) {
  const props = features.map(f => f.properties || {});
  const total  = props.reduce((s, p) => s + (p._qt_votos || 0), 0);
  const locais = features.length;
  const muns   = new Set(props.map(p => p._municipio || p.NM_MUNICIPIO).filter(Boolean)).size;
  const top    = features.reduce((b, f) => (!b || (f.properties._qt_votos || 0) > (b.properties._qt_votos || 0)) ? f : b, null);
  const topV   = top ? (top.properties._qt_votos || 0) : 0;
  const topN   = top ? (top.properties._nome || top.properties._local || top.properties._municipio || '—') : '—';
  document.getElementById('kpiVotos').textContent = total.toLocaleString('pt-BR');
  document.getElementById('kpiLocais').textContent = locais.toLocaleString('pt-BR');
  document.getElementById('kpiMunicipios').textContent = muns;
  document.getElementById('kpiTopVotos').textContent = topV.toLocaleString('pt-BR');
  document.getElementById('kpiTopName').textContent = topN;
}

// ─── Filtro de município ──────────────────────────────────────────────────────
function populateMunicipeFilter(features) {
  const muns = [...new Set(features.map(f => f.properties._municipio || f.properties.NM_MUNICIPIO || '').filter(Boolean))].sort();
  const sel = document.getElementById('municipeFilter');
  sel.innerHTML = '<option value="">Todos os municípios</option>';
  muns.forEach(m => { const o = document.createElement('option'); o.value = m; o.textContent = m; sel.appendChild(o); });
}

// ─── Base identifier (ex: "fortaleza", "municipios", "quixeramobim") ──────────
function getBaseIdentifier(base) {
  return (base || '').toLowerCase().replace(/_?municipios?$/, '').replace(/^votos_/, '');
}

// Retorna true se a camada extra é relevante para o base selecionado
function isLayerRelevantToBase(layerName, baseId) {
  const name = layerName.toLowerCase();
  const hasGeoPrefix = GEO_PREFIXES.some(p => name.startsWith(p));
  const hasGeoSuffix = GEO_SUFFIXES.some(s => name.includes(s));
  if (!hasGeoPrefix && !hasGeoSuffix) return true;           // camada genérica: sempre visível
  if (!baseId || baseId === 'municipios') {                   // vista estadual
    return name.includes('regionais') || name.includes('municipio');
  }
  return name.includes(baseId);                               // deve conter o nome da cidade
}

// Etiqueta amigável para o base
function baseLabel(base) {
  return (base || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// ─── Carregar base de votos ───────────────────────────────────────────────────
async function loadBase(base) {
  currentBase = base;
  isMunicipios = base.toLowerCase().includes('municipio');
  votosVisible = true;                                        // reset toggle ao trocar base
  document.getElementById('mapLegend').style.display = isMunicipios ? 'none' : '';
  document.getElementById('municipeFilter').value = '';
  document.getElementById('minVotesRange').value = 0;
  document.getElementById('minVotesLabel').textContent = '0';
  setMapLoading(true);
  try {
    const gj = await apiFetch(`/api/candidato/votos/${base}`);
    if (!gj) return;
    rawFeatures = gj.features || [];
    populateMunicipeFilter(rawFeatures);
    updateKPIs(rawFeatures);
    if (isMunicipios) { renderChoropleth(rawFeatures); }
    else              { renderPoints(rawFeatures); }
    renderCharts(rawFeatures);
    renderTable(rawFeatures);
    refreshLayerList(base);                                   // atualiza painel de camadas
  } catch (err) {
    console.error('[dashboard] loadBase:', err);
  } finally {
    setMapLoading(false);
  }
}

// ─── Tile switcher ────────────────────────────────────────────────────────────
function setTile(key) {
  const cfg = TILES[key];
  if (!cfg || !map) return;
  if (tileLayer) { tileLayer.remove(); }
  const opts = { attribution: cfg.attr, maxZoom: 19 };
  if (cfg.subdomains) opts.subdomains = cfg.subdomains;
  tileLayer = L.tileLayer(cfg.url, opts).addTo(map);
  document.querySelectorAll('.tile-btn').forEach(b => b.classList.toggle('active', b.dataset.tile === key));
}

// ─── Configurações de camadas personalizadas ─────────────────────────────────
// type: 'graduated' → escala de cor por campo numérico
// type: 'polygon'   → polígono simples com popup personalizado
//
// Matching: use 'prefix' para início do nome OU 'suffix' para fim do nome.
// Adicione novas entradas aqui para personalizar qualquer camada.

const LAYER_CONFIGS = {
  renda: {
    type: 'graduated',
    prefix: 'renda_',
    field: 'renda_media',
    // azul claro → azul escuro (renda baixa → alta)
    colors: ['#f7fbff', '#c6dbef', '#6baed6', '#2171b5', '#08306b'],
    popupFn(p) {
      const nome  = p.NM_MUN   || p.nm_mun   || p.Municipio || '';
      const sit   = p.SITUACAO || p.situacao || '—';
      const renda = parseFloat(p.renda_media ?? p.RENDA_MEDIA ?? 0);
      return `<div class="popup-name">${nome}</div>
        <div class="popup-meta">
          Situação: <strong>${sit}</strong><br>
          Renda média: <strong>R$ ${renda.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
        </div>`;
    },
  },
  popula: {
    type: 'graduated',
    prefix: 'popula_',
    field: 'v0001',
    // verde claro → verde escuro (pop baixa → alta)
    colors: ['#f7fcf5', '#c7e9c0', '#74c476', '#238b45', '#00441b'],
    popupFn(p) {
      const nome = p.NM_MUN   || p.nm_mun   || p.Municipio || '';
      const sit  = p.SITUACAO || p.situacao || '—';
      const pop  = parseInt(p.V0001 ?? p.v0001 ?? 0);
      return `<div class="popup-name">${nome}</div>
        <div class="popup-meta">
          Situação: <strong>${sit}</strong><br>
          População: <strong>${pop.toLocaleString('pt-BR')}</strong>
        </div>`;
    },
  },
  distritos: {
    type: 'polygon',
    suffix: '_distritos',
    style: { color: '#e67e22', weight: 1.2, fillColor: '#e67e22', fillOpacity: 0.06, opacity: 0.9 },
    popupFn(p) {
      const nome = p.NM_DISTRIT || p.NM_DISTR || p.NM_DIST || p.nome || p.Nome || p.LABEL || '—';
      return `<div class="popup-name">${nome}</div>`;
    },
  },
  locais: {
    type: 'polygon',
    prefix: 'locais_',
    style: { color: '#e84393', weight: 1.2, fillColor: '#e84393', fillOpacity: 0.08, opacity: 0.9 },
    popupFn(p) {
      const mun     = p.Municipio              || p.municipio              || p.MUNICIPIO              || '—';
      const bairro  = p.Bairro_ou_Localidade   || p.bairro_ou_localidade   || p.BAIRRO_OU_LOCALIDADE   || '—';
      const aptos   = p.Eleitores_aptos        || p.eleitores_aptos        || p.ELEITORES_APTOS        || '—';
      const aptosNum = parseInt(aptos);
      const aptosStr = isNaN(aptosNum) ? aptos : aptosNum.toLocaleString('pt-BR');
      return `<div class="popup-name">${bairro}</div>
        <div class="popup-meta">
          Município: <strong>${mun}</strong><br>
          Eleitores aptos: <strong>${aptosStr}</strong>
        </div>`;
    },
  },
};

// Retorna a config pelo nome da camada (prefix ou suffix), ou null se genérica
function getLayerConfig(layerName) {
  const name = (layerName || '').toLowerCase();
  return Object.values(LAYER_CONFIGS).find(cfg => {
    if (cfg.prefix) return name.startsWith(cfg.prefix);
    if (cfg.suffix) return name.endsWith(cfg.suffix) || name.includes(cfg.suffix);
    return false;
  }) || null;
}

// Quebras de classificação por quantil (5 classes)
function computeBreaks(values, nClasses) {
  const sorted = values.filter(v => v != null && !isNaN(v)).sort((a, b) => a - b);
  if (!sorted.length) return Array(nClasses + 1).fill(0);
  const breaks = [];
  for (let i = 0; i <= nClasses; i++) {
    breaks.push(sorted[Math.min(Math.floor((i / nClasses) * sorted.length), sorted.length - 1)]);
  }
  return breaks;
}

function getGraduatedColor(value, breaks, colors) {
  if (value == null || isNaN(value)) return '#aaaaaa';
  for (let i = 0; i < colors.length; i++) {
    if (value <= breaks[i + 1]) return colors[i];
  }
  return colors[colors.length - 1];
}

// Cria L.geoJSON com estilo graduado + popup personalizado
function buildGraduatedLayer(gj, cfg) {
  // Lê valores para calcular quebras (aceita nome do campo em minúsculo ou maiúsculo)
  const fieldLow = cfg.field.toLowerCase();
  const fieldUp  = cfg.field.toUpperCase();
  const getVal   = p => parseFloat(p[fieldLow] ?? p[fieldUp] ?? 0) || 0;

  const values = gj.features.map(f => getVal(f.properties || {}));
  const breaks  = computeBreaks(values, cfg.colors.length);

  let layerRef;
  layerRef = L.geoJSON(gj, {
    style(ft) {
      const v = getVal(ft.properties || {});
      return {
        fillColor: getGraduatedColor(v, breaks, cfg.colors),
        color: '#444',
        weight: 0.8,
        opacity: 0.9,
        fillOpacity: 0.72,
      };
    },
    onEachFeature(ft, lyr) {
      const p = ft.properties || {};
      lyr.bindPopup(cfg.popupFn(p), { className: 'lv-popup', maxWidth: 260 });
      lyr.on('mouseover', function () { this.setStyle({ fillOpacity: 0.92, weight: 2, color: '#aaa' }); });
      lyr.on('mouseout',  function () { layerRef.resetStyle(this); });
    },
  });
  return layerRef;
}

// ─── Camadas extras ───────────────────────────────────────────────────────────

// Busca todas as camadas disponíveis da API e guarda em memória
async function loadLayers() {
  try { allAvailableLayers = await apiFetch('/api/candidato/layers') || []; }
  catch (_) { allAvailableLayers = []; }
}

// Reconstrói o painel de camadas filtrando pelo base atual
function refreshLayerList(base) {
  // Remove todas as camadas extras do mapa ao trocar de base
  Object.values(extraLayers).forEach(l => l.remove());
  extraLayers = {};

  const section = document.getElementById('layersSection');
  const list    = document.getElementById('layerList');
  list.innerHTML = '';

  // ── Toggle da camada de votos (sempre primeiro) ──────────────────────────
  const votesBtn = document.createElement('div');
  votesBtn.className = 'layer-toggle active';
  votesBtn.id = 'votesToggle';
  votesBtn.innerHTML = `<span class="layer-dot" style="background:var(--accent)"></span>Votos — ${baseLabel(base)}`;
  votesBtn.addEventListener('click', () => {
    votosVisible = !votosVisible;
    if (votosLayer) {
      if (votosVisible) { votosLayer.addTo(map); } else { votosLayer.remove(); }
    }
    votesBtn.classList.toggle('active', votosVisible);
    const leg = document.getElementById('mapLegend');
    if (leg) leg.style.display = votosVisible ? '' : 'none';
  });
  list.appendChild(votesBtn);

  // ── Camadas extras filtradas pelo base ───────────────────────────────────
  const baseId   = getBaseIdentifier(base);
  const relevant = allAvailableLayers.filter(l => isLayerRelevantToBase(l.name, baseId));

  if (relevant.length > 0) {
    // Separador visual
    const sep = document.createElement('div');
    sep.style.cssText = 'border-top:1px solid var(--border);margin:6px 0 2px';
    list.appendChild(sep);

    relevant.forEach(layer => {
      const btn = document.createElement('div');
      btn.className = 'layer-toggle';
      btn.dataset.key = `${layer.source}:${layer.name}`;
      btn.innerHTML = `<span class="layer-dot"></span>${layer.label}`;
      btn.addEventListener('click', () => toggleLayer(btn, layer));
      list.appendChild(btn);
    });
  }

  section.style.display = '';
}

async function toggleLayer(btn, layer) {
  const key = `${layer.source}:${layer.name}`;
  if (btn.classList.contains('active')) {
    extraLayers[key]?.remove(); delete extraLayers[key];
    btn.classList.remove('active'); return;
  }
  try {
    const gj = await apiFetch(`/api/candidato/layer/${layer.source}/${layer.name}`);
    if (!gj) return;

    const cfg = getLayerConfig(layer.name);

    if (cfg && cfg.type === 'graduated') {
      // Camada com escala de cor por campo numérico
      extraLayers[key] = buildGraduatedLayer(gj, cfg).addTo(map);

    } else if (cfg && cfg.type === 'polygon') {
      // Polígono simples com popup personalizado
      const baseStyle = cfg.style || { color: '#814afd', weight: 1.2, fillOpacity: 0.08 };
      let polyLayer;
      polyLayer = L.geoJSON(gj, {
        style: () => ({ ...baseStyle }),
        onEachFeature(ft, lyr) {
          lyr.bindPopup(cfg.popupFn(ft.properties || {}), { className: 'lv-popup', maxWidth: 260 });
          lyr.on('mouseover', function () { this.setStyle({ fillOpacity: 0.22, weight: 2 }); });
          lyr.on('mouseout',  function () { polyLayer.resetStyle(this); });
        },
      }).addTo(map);
      extraLayers[key] = polyLayer;

    } else {
      // Camada genérica (sem config específica)
      extraLayers[key] = L.geoJSON(gj, {
        style: { color: '#814afd', weight: 1.5, fillOpacity: 0.12 },
        pointToLayer: (ft, ll) => L.circleMarker(ll, {
          radius: 5, fillColor: '#814afd', color: '#fff', weight: 0.5, fillOpacity: 0.8,
        }),
        onEachFeature(ft, lyr) {
          const p = ft.properties || {};
          const lbl = p.nome || p.Nome || p.LABEL || p.NM_MUNICIPIO || Object.values(p).slice(0, 2).join(' | ');
          lyr.bindPopup(`<div style="font-size:.85rem;color:#e8eaf0">${lbl}</div>`, { className: 'lv-popup' });
        },
      }).addTo(map);
    }

    btn.classList.add('active');
  } catch (err) { console.error('[dashboard] toggleLayer:', err); }
}

// ─── Chart.js helpers ─────────────────────────────────────────────────────────
function destroyChart(id) {
  if (_charts[id]) { _charts[id].destroy(); delete _charts[id]; }
}

/**
 * Define a altura no WRAPPER (não no canvas).
 * Chart.js com maintainAspectRatio:false usa a altura do parent — se definirmos
 * diretamente no canvas, ele lê o próprio tamanho no hover e cresce indefinidamente.
 */
function setChartHeight(canvasId, px) {
  const wrap = document.getElementById(`wrap-${canvasId}`);
  if (wrap) wrap.style.height = px + 'px';
}

function horizontalBar(id, labels, values, color, maxLabel = 'Votos') {
  destroyChart(id);
  const canvas = document.getElementById(id);
  if (!canvas) return;
  _charts[id] = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: color, borderRadius: 4, borderSkipped: false }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: {
        callbacks: { label: ctx => ` ${ctx.raw.toLocaleString('pt-BR')} votos` },
      }},
      scales: {
        x: { grid: { color: '#2d3040' }, ticks: { color: '#8b90a7' }, title: { display: true, text: maxLabel, color: '#8b90a7' } },
        y: { grid: { display: false }, ticks: { color: '#b0b3c8', font: { size: 11 } } },
      },
    },
  });
}

// ─── Gráficos de análise ──────────────────────────────────────────────────────
function renderCharts(features) {
  document.getElementById('chartsEmpty').style.display = features.length ? 'none' : '';
  document.getElementById('chartsLocal').style.display = (!isMunicipios && features.length) ? '' : 'none';
  document.getElementById('chartsMunicipios').style.display = (isMunicipios && features.length) ? '' : 'none';

  if (!features.length) return;

  const props = features.map(f => f.properties || {});

  if (isMunicipios) {
    renderChartsMunicipios(props);
  } else {
    renderChartsLocal(props);
  }
}

function renderChartsMunicipios(props) {
  // Agrupa por município
  const byMun = {};
  props.forEach(p => {
    const m = p._municipio || p.NM_MUNICIPIO || '';
    if (!m) return;
    byMun[m] = (byMun[m] || 0) + (p._qt_votos || 0);
  });
  const sorted = Object.entries(byMun).sort((a, b) => b[1] - a[1]);

  const top15 = sorted.slice(0, 15);
  const bot15 = sorted.slice(-15).reverse();

  setChartHeight('chartTopMun', Math.max(250, top15.length * 28));
  horizontalBar('chartTopMun', top15.map(e => e[0]), top15.map(e => e[1]), '#2dc937');

  setChartHeight('chartBottomMun', Math.max(250, bot15.length * 28));
  horizontalBar('chartBottomMun', bot15.map(e => e[0]), bot15.map(e => e[1]), '#e74c3c');
}

function renderChartsLocal(props) {
  // ── Top / Bottom locais ──
  const byLocal = {};
  props.forEach(p => {
    const l = p._nome || p._local || p.NM_LOCAL_VOTACAO || '';
    if (!l) return;
    byLocal[l] = (byLocal[l] || 0) + (p._qt_votos || 0);
  });
  const sortedLocal = Object.entries(byLocal).sort((a, b) => b[1] - a[1]);
  const top15  = sortedLocal.slice(0, 15);
  const bot15  = sortedLocal.slice(-15).reverse();

  setChartHeight('chartTopLocais', Math.max(250, top15.length * 28));
  horizontalBar('chartTopLocais', top15.map(e => e[0]), top15.map(e => e[1]), '#2dc937');

  setChartHeight('chartBottomLocais', Math.max(250, bot15.length * 28));
  horizontalBar('chartBottomLocais', bot15.map(e => e[0]), bot15.map(e => e[1]), '#e74c3c');

  // ── Top bairros ──
  const byBairro = {};
  props.forEach(p => {
    const b = p._bairro || '';
    if (!b) return;
    byBairro[b] = (byBairro[b] || 0) + (p._qt_votos || 0);
  });
  const sortedBairro = Object.entries(byBairro).sort((a, b) => b[1] - a[1]).slice(0, 13);
  setChartHeight('chartBairros', Math.max(220, sortedBairro.length * 28));
  horizontalBar('chartBairros', sortedBairro.map(e => e[0]), sortedBairro.map(e => e[1]), '#3498db');

  // ── Histograma de faixas ──
  const FAIXAS = [
    { label: '0–10',     min: 0,   max: 10  },
    { label: '11–30',    min: 11,  max: 30  },
    { label: '31–60',    min: 31,  max: 60  },
    { label: '61–100',   min: 61,  max: 100 },
    { label: '101–200',  min: 101, max: 200 },
    { label: '201–500',  min: 201, max: 500 },
    { label: '501–1000', min: 501, max: 1000},
    { label: '1000+',    min: 1001,max: Infinity },
  ];
  const counts = FAIXAS.map(f => props.filter(p => (p._qt_votos || 0) >= f.min && (p._qt_votos || 0) <= f.max).length);
  destroyChart('chartFaixa');
  const cfCanvas = document.getElementById('chartFaixa');
  if (cfCanvas) {
    _charts['chartFaixa'] = new Chart(cfCanvas, {
      type: 'bar',
      data: {
        labels: FAIXAS.map(f => f.label),
        datasets: [{ data: counts, backgroundColor: '#e67e22', borderRadius: 4 }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` ${ctx.raw} locais` } } },
        scales: {
          x: { grid: { color: '#2d3040' }, ticks: { color: '#8b90a7' }, title: { display: true, text: 'Faixa de votos', color: '#8b90a7' } },
          y: { grid: { color: '#2d3040' }, ticks: { color: '#8b90a7' }, title: { display: true, text: 'Locais', color: '#8b90a7' } },
        },
      },
    });
  }

  // ── Curva de Pareto ──
  const sortedDesc = Object.values(byLocal).sort((a, b) => b - a);
  const totalVotos = sortedDesc.reduce((s, v) => s + v, 0);
  if (totalVotos > 0) {
    let acc = 0;
    const paretoData = sortedDesc.map((v, i) => {
      acc += v;
      return { x: i + 1, y: parseFloat((acc / totalVotos * 100).toFixed(2)) };
    });
    destroyChart('chartPareto');
    const cpCanvas = document.getElementById('chartPareto');
    if (cpCanvas) {
      _charts['chartPareto'] = new Chart(cpCanvas, {
        type: 'line',
        data: {
          datasets: [
            {
              label: '% Acumulado',
              data: paretoData,
              borderColor: '#9b59b6',
              backgroundColor: 'rgba(155,89,182,0.15)',
              fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2,
            },
            {
              label: '80%',
              data: [{ x: 1, y: 80 }, { x: paretoData.length, y: 80 }],
              borderColor: '#e74c3c', borderDash: [6, 4], borderWidth: 1.5,
              pointRadius: 0, fill: false,
            },
          ],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: {
              label: ctx => ctx.datasetIndex === 0 ? ` ${ctx.parsed.y.toFixed(1)}% (local #${ctx.parsed.x})` : ' 80%',
            }},
          },
          scales: {
            x: { type: 'linear', grid: { color: '#2d3040' }, ticks: { color: '#8b90a7' }, title: { display: true, text: 'Nº de locais', color: '#8b90a7' } },
            y: { min: 0, max: 100, grid: { color: '#2d3040' }, ticks: { color: '#8b90a7', callback: v => v + '%' }, title: { display: true, text: '% acumulado', color: '#8b90a7' } },
          },
        },
      });
    }
  }

  // ── Zona eleitoral ──
  const byZona = {};
  props.forEach(p => {
    const z = p.NR_ZONA || p.nr_zona || p.zona || '';
    if (!z) return;
    if (!byZona[z]) byZona[z] = { total: 0, count: 0 };
    byZona[z].total += (p._qt_votos || 0);
    byZona[z].count += 1;
  });
  const zonas = Object.entries(byZona).sort((a, b) => b[1].total - a[1].total).slice(0, 20);
  const cardZona = document.getElementById('cardZona');
  if (zonas.length > 0 && cardZona) {
    cardZona.style.display = '';
    destroyChart('chartZona');
    const czCanvas = document.getElementById('chartZona');
    if (czCanvas) {
      _charts['chartZona'] = new Chart(czCanvas, {
        type: 'bar',
        data: {
          labels: zonas.map(z => `Zona ${z[0]}`),
          datasets: [
            { label: 'Total', data: zonas.map(z => z[1].total), backgroundColor: '#e63946', borderRadius: 3, yAxisID: 'y' },
            {
              label: 'Média', type: 'line',
              data: zonas.map(z => parseFloat((z[1].total / z[1].count).toFixed(1))),
              borderColor: '#f1c40f', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 3, yAxisID: 'y2',
            },
          ],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { labels: { color: '#8b90a7', boxWidth: 12 } } },
          scales: {
            x: { grid: { display: false }, ticks: { color: '#8b90a7' } },
            y: { grid: { color: '#2d3040' }, ticks: { color: '#8b90a7' }, title: { display: true, text: 'Total', color: '#8b90a7' } },
            y2: { position: 'right', grid: { display: false }, ticks: { color: '#f1c40f' }, title: { display: true, text: 'Média', color: '#f1c40f' } },
          },
        },
      });
    }
  } else if (cardZona) {
    cardZona.style.display = 'none';
  }
}

// ─── Tabela ───────────────────────────────────────────────────────────────────
function renderTable(features) {
  const props = features.map(f => f.properties || {});
  document.getElementById('tableCount').textContent = `${features.length.toLocaleString('pt-BR')} registros`;

  const head = document.getElementById('tableHead');
  const body = document.getElementById('tableBody');

  // Define colunas
  const cols = isMunicipios
    ? [{ key: '_municipio', label: 'Município' }, { key: '_qt_votos', label: 'Votos', cls: 'td-votes' }]
    : [
        { key: '_nome',      label: 'Local de votação' },
        { key: '_municipio', label: 'Município' },
        { key: '_bairro',    label: 'Bairro / Distrito' },
        { key: '_qt_votos',  label: 'Votos', cls: 'td-votes' },
      ];

  head.innerHTML = cols.map(c => `<th>${c.label}</th>`).join('');

  const sorted = [...features].sort((a, b) => (b.properties._qt_votos || 0) - (a.properties._qt_votos || 0));
  body.innerHTML = sorted.map(f => {
    const p = f.properties || {};
    return `<tr>${cols.map(c => {
      const v = p[c.key] ?? '';
      const display = (c.key === '_qt_votos') ? Number(v).toLocaleString('pt-BR') : v;
      return `<td class="${c.cls || ''}" title="${display}">${display}</td>`;
    }).join('')}</tr>`;
  }).join('');

  // CSV download
  document.getElementById('downloadCsv').onclick = () => {
    const csvRows = [
      cols.map(c => c.label).join(','),
      ...sorted.map(f => cols.map(c => {
        const v = String(f.properties[c.key] ?? '').replace(/"/g, '""');
        return `"${v}"`;
      }).join(',')),
    ];
    const blob = new Blob(['\uFEFF' + csvRows.join('\n')], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `localizavotos_${currentBase || 'dados'}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };
}

// ─── Utilitários ──────────────────────────────────────────────────────────────
function setMapLoading(show) {
  document.getElementById('mapLoading').classList.toggle('show', show);
}

function logout() { localStorage.clear(); window.location.href = '/'; }

// ─── Abas ─────────────────────────────────────────────────────────────────────
function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b === btn));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === `panel-${tab}`));
      if (tab === 'mapa' && map) { setTimeout(() => map.invalidateSize(), 50); }
    });
  });
}

// ─── Inicialização ────────────────────────────────────────────────────────────
async function init() {
  let me;
  try {
    me = await apiFetch('/api/me');
    if (!me) return;
  } catch (_) { localStorage.clear(); window.location.href = '/'; return; }

  document.getElementById('navCandidate').textContent = me.display_name;
  document.title = `LocalizaVotos — ${me.display_name}`;

  if (me.role === 'admin') {
    const adminLink = document.getElementById('adminPanelLink');
    if (adminLink) adminLink.style.display = '';
  }

  // Inicializa mapa
  map = L.map('map', { zoomControl: true, preferCanvas: true }).setView([-5.1, -39.3], 7);
  setTile('dark');  // tile escuro padrão

  // ── Botão Fullscreen ──────────────────────────────────────────────────────
  const fsBtn        = document.getElementById('mapFullscreenBtn');
  const fsIconExp    = document.getElementById('fsIconExpand');
  const fsIconCmp    = document.getElementById('fsIconCompress');
  const mapContainer = document.getElementById('mapContainer');

  function setFsIcons(isFullscreen) {
    fsIconExp.style.display = isFullscreen ? 'none' : '';
    fsIconCmp.style.display = isFullscreen ? ''     : 'none';
  }

  fsBtn.addEventListener('click', () => {
    if (!document.fullscreenElement) {
      mapContainer.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen();
    }
  });

  document.addEventListener('fullscreenchange', () => {
    const fs = !!document.fullscreenElement;
    setFsIcons(fs);
    setTimeout(() => map.invalidateSize(), 150);
  });

  // ── Sidebar mobile (drawer) ───────────────────────────────────────────────
  const sidebar        = document.getElementById('sidebar');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  const sidebarToggle  = document.getElementById('sidebarToggle');
  const sidebarClose   = document.getElementById('sidebarClose');

  function openSidebar()  { sidebar.classList.add('open');    sidebarOverlay.classList.add('visible'); }
  function closeSidebar() { sidebar.classList.remove('open'); sidebarOverlay.classList.remove('visible'); }

  sidebarToggle.addEventListener('click', openSidebar);
  sidebarClose.addEventListener('click',  closeSidebar);
  sidebarOverlay.addEventListener('click', closeSidebar);

  // Seletor de fundo do mapa
  document.querySelectorAll('.tile-btn').forEach(btn => {
    btn.addEventListener('click', () => setTile(btn.dataset.tile));
  });

  // Abas
  initTabs();

  // Carrega camadas disponíveis ANTES do primeiro loadBase (para o filtro funcionar)
  await loadLayers();

  // Bases de votos
  const bases = me.bases || [];
  const baseSelect = document.getElementById('baseSelect');
  baseSelect.innerHTML = '';
  if (!bases.length) {
    baseSelect.innerHTML = '<option value="">Nenhuma base disponível</option>';
  } else {
    bases.forEach(b => {
      const o = document.createElement('option');
      o.value = b;
      o.textContent = b.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      baseSelect.appendChild(o);
    });
    await loadBase(bases[0]);
  }

  // Eventos de filtro
  baseSelect.addEventListener('change', () => loadBase(baseSelect.value));
  document.getElementById('municipeFilter').addEventListener('change', applyFilters);
  document.getElementById('minVotesRange').addEventListener('input', function () {
    document.getElementById('minVotesLabel').textContent = this.value;
    applyFilters();
  });
}

init();
