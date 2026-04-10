/* LocalizaVotos — Gerenciador de tema de cores */

const THEMES = {
  vermelho:    { label: 'Vermelho',    color: '#e63946', hover: '#c1121f', muted: 'rgba(230,57,70,0.12)'   },
  azul:        { label: 'Azul',        color: '#3b82f6', hover: '#2563eb', muted: 'rgba(59,130,246,0.12)'  },
  verde:       { label: 'Verde',       color: '#22c55e', hover: '#16a34a', muted: 'rgba(34,197,94,0.12)'   },
  amarelo:     { label: 'Amarelo',     color: '#f59e0b', hover: '#d97706', muted: 'rgba(245,158,11,0.12)'  },
  lilas:       { label: 'Lilás',       color: '#a855f7', hover: '#9333ea', muted: 'rgba(168,85,247,0.12)'  },
  ceu:         { label: 'Céu',         color: '#69c4ed', hover: '#3aaed8', muted: 'rgba(105,196,237,0.12)' },
  carmim:      { label: 'Carmim',      color: '#c51328', hover: '#9e0f20', muted: 'rgba(197,19,40,0.12)'   },
  verdeescuro: { label: 'Verde escuro',color: '#1a9b32', hover: '#157a27', muted: 'rgba(26,155,50,0.12)'   },
};

const STORAGE_KEY = 'lv_theme';

function applyTheme(key) {
  const t = THEMES[key] || THEMES.azul;
  const root = document.documentElement;
  root.style.setProperty('--accent',       t.color);
  root.style.setProperty('--accent-hover', t.hover);
  root.style.setProperty('--accent-muted', t.muted);

  // Atualiza botões de seleção, se existirem na página
  document.querySelectorAll('.theme-dot').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.theme === key);
  });
}

function setTheme(key) {
  localStorage.setItem(STORAGE_KEY, key);
  applyTheme(key);
}

function loadTheme() {
  const saved = localStorage.getItem(STORAGE_KEY) || 'azul';
  applyTheme(saved);
  return saved;
}

// Inicializa ao carregar o script
const _currentTheme = loadTheme();

// Vincula cliques nos botões de tema
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.theme-dot').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.theme === _currentTheme);
    btn.addEventListener('click', () => setTheme(btn.dataset.theme));
  });
});
