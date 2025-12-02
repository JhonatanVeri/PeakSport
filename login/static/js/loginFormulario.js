// =========================
// ENDPOINTS (ajústalos si cambias rutas)
// =========================
const ENDPOINTS = {
  login:   '/login/auth/login',  // POST
  me:      '/login/auth/me',     // GET  (opcional, para consultar estado)
  register:'/login/auth/register'     // POST (si migras: '/login/auth/register')
};

// =========================
 // HELPERS UI
// =========================
function setBusy(btnEl, spinnerEl, busy) {
  if (!btnEl || !spinnerEl) return;
  btnEl.disabled = !!busy;
  btnEl.setAttribute('aria-busy', busy ? 'true' : 'false');
  spinnerEl.classList.toggle('hidden', !busy);
}

function showInline(el, msg, type = 'error') {
  if (!el) return;
  el.textContent = msg || '';
  el.classList.toggle('hidden', !msg);
  el.classList.remove('text-red-600', 'text-green-600');
  el.classList.add(type === 'success' ? 'text-green-600' : 'text-red-600');
}

function showGlobalAlert(msg, type = 'error') {
  const box = document.getElementById('global-alert');
  if (!box) return;
  if (!msg) {
    box.classList.add('hidden'); 
    box.textContent = '';
    return;
  }
  box.textContent = msg;
  box.classList.remove('hidden');
  box.className = `mb-4 rounded-lg px-4 py-3 text-sm font-semibold ${
    type === 'success'
      ? 'bg-green-100 text-green-700 border border-green-300'
      : 'bg-red-100 text-red-700 border border-red-300'
  }`;
}

// =========================
// TABS LOGIN / REGISTRO
// =========================
function switchTab(tab) {
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");
  const loginTab = document.getElementById("login-tab");
  const registerTab = document.getElementById("register-tab");
  showGlobalAlert(null);

  if (tab === "login") {
    loginForm.classList.remove("hidden");
    registerForm.classList.add("hidden");
    loginTab.classList.add("tab-active");
    loginTab.classList.remove("tab-inactive");
    registerTab.classList.add("tab-inactive");
    registerTab.classList.remove("tab-active");
  } else {
    registerForm.classList.remove("hidden");
    loginForm.classList.add("hidden");
    registerTab.classList.add("tab-active");
    registerTab.classList.remove("tab-inactive");
    loginTab.classList.add("tab-inactive");
    loginTab.classList.remove("tab-active");
  }
}

// =========================
// LOGIN
// =========================
async function handleLogin(event) {
  event.preventDefault();
  showGlobalAlert(null);

  const email = document.getElementById('login-email');
  const pass  = document.getElementById('login-password');
  const btn   = document.getElementById('login-submit');
  const spin  = document.getElementById('login-spinner');
  const errEl = document.getElementById('login-error');

  showInline(errEl, null);
  setBusy(btn, spin, true);

  try {
    const resp = await fetch(ENDPOINTS.login, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      // Tu backend acepta 'correo'/'contrasena' O 'Correo'/'Contrasena'
      body: JSON.stringify({ Correo: email.value.trim(), Contrasena: pass.value })
    });

    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      // Manejo de 400/401/500
      const msg = data.error || 'No se pudo iniciar sesión.';
      showInline(errEl, msg, 'error');
      return;
    }

    if (data.ok && data.redirect) {
      window.location.href = data.redirect; // el backend decide según rol
    } else {
      showInline(errEl, data.error || 'Credenciales inválidas', 'error');
    }
  } catch (e) {
    showInline(errEl, 'Error de red. Intenta nuevamente.', 'error');
    console.error('login error:', e);
  } finally {
    setBusy(btn, spin, false);
  }
}

// =========================
// REGISTRO
// =========================
async function handleRegister(event) {
  event.preventDefault();
  showGlobalAlert(null);

  const name = document.getElementById('reg-name');
  const email= document.getElementById('reg-email');
  const birth= document.getElementById('birthdate');
  const pass = document.getElementById('register-password');
  const conf = document.getElementById('confirm-password');

  const errB = document.getElementById('birthdate-error');
  const btn  = document.getElementById('register-submit');
  const spin = document.getElementById('register-spinner');
  const err  = document.getElementById('register-error');
  const ok   = document.getElementById('register-success');

  showInline(err, null);
  showInline(ok, null, 'success');

  // Validaciones
  if (!validateBirthdate(birth.value)) {
    errB.textContent = "Debes ser mayor de 18 años para registrarte.";
    errB.classList.remove("hidden");
    birth.classList.add("border-red-500");
    return;
  } else {
    errB.classList.add("hidden");
    birth.classList.remove("border-red-500");
  }

  if (pass.value !== conf.value) {
    showInline(err, "Las contraseñas no coinciden ❌", 'error');
    return;
  }

  setBusy(btn, spin, true);

  try {
    const resp = await fetch(ENDPOINTS.register, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        Nombre_Completo: name.value.trim(),
        Correo: email.value.trim(),
        Fecha_Nacimiento: birth.value, // ISO yyyy-mm-dd
        Contrasena: pass.value
      })
    });

    // Respuesta puede venir como texto (si hay error). Intentamos parsear.
    const text = await resp.text();
    let data;
    try { data = JSON.parse(text); } catch { data = {}; }

    if (!resp.ok) {
      const msg = data.error || 'No se pudo registrar el usuario.';
      showInline(err, msg, 'error');
      return;
    }

    if (data.mensaje) {
      showInline(ok, 'Registro exitoso 🎉 Ahora puedes iniciar sesión.', 'success');
      // Cambiamos a tab login
      setTimeout(() => { switchTab('login'); }, 900);
    } else {
      showInline(err, data.error || 'No se pudo registrar el usuario.', 'error');
    }
  } catch (e) {
    showInline(err, 'Error de red. Intenta nuevamente.', 'error');
    console.error('register error:', e);
  } finally {
    setBusy(btn, spin, false);
  }
}

// =========================
// VALIDACIONES AUX
// =========================
function validateBirthdate(dateString) {
  if (!dateString) return false;
  const birthDate = new Date(dateString);
  const today = new Date();
  let age = today.getFullYear() - birthDate.getFullYear();
  const monthDiff = today.getMonth() - birthDate.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) age--;
  return age >= 18;
}

function checkPasswordStrength(password) {
  const strengthBar = document.getElementById("strength-bar");
  const strengthText = document.getElementById("strength-text");
  let strength = 0;
  if (password.length >= 8) strength++;
  if (/[A-Z]/.test(password)) strength++;
  if (/[0-9]/.test(password)) strength++;
  if (/[^A-Za-z0-9]/.test(password)) strength++;
  strengthBar.className = "strength-indicator";
  if (strength <= 1) { strengthBar.classList.add("strength-weak"); strengthText.textContent = "Débil"; }
  else if (strength === 2) { strengthBar.classList.add("strength-medium"); strengthText.textContent = "Media"; }
  else { strengthBar.classList.add("strength-strong"); strengthText.textContent = "Fuerte"; }
}

function checkPasswordMatch() {
  const p = document.getElementById("register-password").value;
  const c = document.getElementById("confirm-password").value;
  const msg = document.getElementById("password-match");
  if (c === "") { msg.classList.add("hidden"); return; }
  if (p === c) {
    msg.textContent = "Las contraseñas coinciden ✅";
    msg.classList.remove("hidden", "text-red-600");
    msg.classList.add("text-green-600");
  } else {
    msg.textContent = "Las contraseñas no coinciden ❌";
    msg.classList.remove("hidden", "text-green-600");
    msg.classList.add("text-red-600");
  }
}

function togglePassword(inputId, btnEl) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const isPass = input.type === 'password';
  input.type = isPass ? 'text' : 'password';
  if (btnEl && btnEl.querySelector('i')) {
    btnEl.querySelector('i').className = isPass ? 'fa-regular fa-eye-slash' : 'fa-regular fa-eye';
  }
}

// =========================
// OLVIDAR CONTRASEÑA (modal demo)
// =========================
function showForgotPassword() {
  document.getElementById("forgot-modal").classList.remove("hidden");
}
function closeForgotModal() {
  document.getElementById("forgot-modal").classList.add("hidden");
}
function handleForgotPassword(event) {
  event.preventDefault();
  const email = document.getElementById('forgot-email').value;
  // Aquí luego puedes llamar a un endpoint real: /login/auth/forgot
  showGlobalAlert(`Enlace de recuperación enviado a ${email} 📩 (demo)`, 'success');
  closeForgotModal();
}

// =========================
// HOME / SOPORTE (stubs)
// =========================
function goHome() { window.location = '/'; }
function showSupport() { alert("Contactando a soporte 💬 (ejemplo)"); }

// =========================
// INIT (opcional: leer estado de sesión)
// =========================
async function initSessionUI() {
  try {
    const r = await fetch(ENDPOINTS.me);
    const j = await r.json();
    // Si ya está logueado y entraste aquí, podrías redirigir:
    // if (j.logged_in) window.location = '/login/dashboard';
  } catch {}
}
document.addEventListener('DOMContentLoaded', () => {
  initSessionUI();
  // Animación de tarjetas si existieran
  document.querySelectorAll('.card').forEach((card, i) => {
    setTimeout(() => card.classList.add('show'), i * 200);
  });
});
