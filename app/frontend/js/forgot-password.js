/* LocalizaVotos — Recuperação de Senha */

const API = '';

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

document.getElementById('forgotForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  clearMsgs();

  const email = document.getElementById('email').value.trim();

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    showMsg('errorMsg', 'Informe um endereço de e-mail válido.');
    return;
  }

  setLoading(true);
  try {
    const res = await fetch(`${API}/api/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });

    const data = await res.json();

    if (!res.ok) {
      showMsg('errorMsg', data.detail || 'Ocorreu um erro. Tente novamente.');
      return;
    }

    // Sucesso — mostra mensagem genérica e oculta o formulário
    document.getElementById('forgotForm').style.display = 'none';
    showMsg('successMsg',
      data.message ||
      'Se o e-mail estiver cadastrado, você receberá um link em breve. Verifique também sua caixa de spam.'
    );
  } catch (err) {
    showMsg('errorMsg', 'Erro de conexão. Verifique sua internet e tente novamente.');
    console.error('[forgot-password]', err);
  } finally {
    setLoading(false);
  }
});
