/* LocalizaVotos — Login */

const API = '';  // mesmo origem

// Redireciona se já está logado
(function checkAuth() {
  const token = localStorage.getItem('lv_token');
  if (token) {
    const role = localStorage.getItem('lv_role');
    window.location.href = role === 'admin' ? '/admin.html' : '/dashboard.html';
  }
})();


// ── Campos com texto de dica (apaga ao clicar, restaura se sair vazio) ───────
document.addEventListener('DOMContentLoaded', () => {
  const hints = [
    { id: 'username', hint: 'Seu usuário', realType: 'text'     },
    { id: 'password', hint: 'Sua senha',   realType: 'password' },
  ];

  hints.forEach(({ id, hint, realType }) => {
    const el = document.getElementById(id);
    if (!el) return;

    el.addEventListener('focus', () => {
      if (el.value === hint) {
        el.value = '';
        el.type  = realType;
        el.classList.remove('input-hint');
        el.classList.add('filled');
      }
    });

    el.addEventListener('blur', () => {
      if (el.value === '') {
        el.value = hint;
        el.type  = 'text';
        el.classList.add('input-hint');
        el.classList.remove('filled');
      }
    });
  });
});

// Exibe/oculta mensagem de erro
function showError(msg) {
  const el = document.getElementById('errorMsg');
  el.textContent = msg;
  el.classList.add('show');
  el.classList.remove('alert-success');
  el.classList.add('alert-error');
}

function clearError() {
  const el = document.getElementById('errorMsg');
  el.classList.remove('show');
}

// Controla estado de loading do botão
function setLoading(loading) {
  const btn = document.getElementById('loginBtn');
  btn.classList.toggle('loading', loading);
  btn.disabled = loading;
}

// Submit do formulário
document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  clearError();

  const usernameEl = document.getElementById('username');
  const passwordEl = document.getElementById('password');
  const username = (usernameEl.value === 'Seu usuário' ? '' : usernameEl.value).trim();
  const password = (passwordEl.value === 'Sua senha'   ? '' : passwordEl.value);

  if (!username) {
    showError('Informe o usuário ou e-mail.');
    return;
  }
  if (!password) {
    showError('Informe a senha.');
    return;
  }

  setLoading(true);
  try {
    const res = await fetch(`${API}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    const data = await res.json();

    if (!res.ok) {
      showError(data.detail || 'Usuário ou senha inválidos.');
      return;
    }

    // Persiste token e info do usuário
    localStorage.setItem('lv_token', data.access_token);
    localStorage.setItem('lv_slug', data.slug);
    localStorage.setItem('lv_display_name', data.display_name);
    localStorage.setItem('lv_role', data.role);
    localStorage.setItem('lv_bases', JSON.stringify(data.bases || []));

    const dest = data.role === 'admin' ? '/admin.html' : '/dashboard.html';
    window.location.href = dest;
  } catch (err) {
    showError('Erro de conexão. Verifique sua internet e tente novamente.');
    console.error('[login] submit:', err);
  } finally {
    setLoading(false);
  }
});

