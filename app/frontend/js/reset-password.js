/* LocalizaVotos — Redefinição de Senha */

const API = '';

// Lê token da URL
const params = new URLSearchParams(window.location.search);
const TOKEN = params.get('token') || '';

// Valida presença do token
if (!TOKEN) {
  document.getElementById('tokenError').textContent =
    'Link inválido. Solicite um novo link de recuperação.';
  document.getElementById('tokenError').classList.add('show');
  document.getElementById('resetForm').style.display = 'none';
}

function showMsg(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.classList.add('show');
}

function clearMsgs() {
  ['errorMsg', 'successMsg'].forEach(id => {
    const el = document.getElementById(id);
    el.classList.remove('show');
    el.textContent = '';
  });
}

function setLoading(loading) {
  const btn = document.getElementById('submitBtn');
  btn.classList.toggle('loading', loading);
  btn.disabled = loading;
}

document.getElementById('resetForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  clearMsgs();

  const password = document.getElementById('password').value;
  const confirm  = document.getElementById('confirm').value;

  if (password.length < 6) {
    showMsg('errorMsg', 'A senha deve ter pelo menos 6 caracteres.');
    return;
  }

  if (password !== confirm) {
    showMsg('errorMsg', 'As senhas não coincidem.');
    return;
  }

  setLoading(true);
  try {
    const res = await fetch(`${API}/api/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: TOKEN, new_password: password }),
    });

    const data = await res.json();

    if (!res.ok) {
      showMsg('errorMsg', data.detail || 'Ocorreu um erro. O link pode ter expirado.');
      return;
    }

    // Sucesso — oculta form e exibe confirmação
    document.getElementById('resetForm').style.display = 'none';
    showMsg('successMsg', 'Senha atualizada com sucesso! Redirecionando para o login…');

    setTimeout(() => { window.location.href = '/'; }, 2500);
  } catch (err) {
    showMsg('errorMsg', 'Erro de conexão. Verifique sua internet e tente novamente.');
    console.error('[reset-password]', err);
  } finally {
    setLoading(false);
  }
});
