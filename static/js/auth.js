/**
 * Tanilink — Auth page JS
 * Handles tab switching, form validation, and API calls to /auth/register & /auth/login
 */

const API_BASE = '';  // same origin; change to 'http://localhost:8000' if needed

// ── DOM helpers ──────────────────────────────────────────────────────────────

const $ = (sel) => document.querySelector(sel);

function showAlert(id, message, type = 'error') {
  const el = $(`#${id}`);
  el.textContent = message;
  el.className = `alert ${type}`;
}

function hideAlert(id) {
  $(`#${id}`).className = 'alert hidden';
}

function setFieldError(fieldId, message) {
  const input = $(`#${fieldId}`);
  const err   = $(`#err-${fieldId}`);
  if (input) input.classList.toggle('invalid', !!message);
  if (err)   err.textContent = message || '';
}

function clearErrors(prefix) {
  document.querySelectorAll(`[id^="err-${prefix}"]`).forEach(el => {
    el.textContent = '';
  });
  document.querySelectorAll(`#tab-${prefix} input`).forEach(el => {
    el.classList.remove('invalid');
  });
}

// ── Tabs ─────────────────────────────────────────────────────────────────────

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
    btn.classList.add('active');
    $(`#tab-${tab}`).classList.remove('hidden');
  });
});

// ── Token storage ─────────────────────────────────────────────────────────────

function saveTokens(access, refresh) {
  sessionStorage.setItem('tanilink_access', access);
  sessionStorage.setItem('tanilink_refresh', refresh);
}

// ── Login ────────────────────────────────────────────────────────────────────

$('#login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  clearErrors('login');
  hideAlert('login-alert');

  const email    = $('#login-email').value.trim();
  const password = $('#login-password').value;
  let valid = true;

  if (!email)    { setFieldError('login-email', 'Email wajib diisi.'); valid = false; }
  if (!password) { setFieldError('login-password', 'Password wajib diisi.'); valid = false; }
  if (!valid) return;

  const btn = $('#login-submit');
  btn.disabled = true;
  btn.textContent = 'Memproses...';

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();

    if (!res.ok) {
      showAlert('login-alert', data.detail || 'Login gagal.', 'error');
      return;
    }

    saveTokens(data.access_token, data.refresh_token);
    showAlert('login-alert', `Selamat datang, ${data.user.full_name}! Mengalihkan...`, 'success');

    // TODO: redirect to dashboard when it's ready
    // setTimeout(() => window.location.href = '/static/dashboard.html', 1200);

  } catch {
    showAlert('login-alert', 'Tidak dapat terhubung ke server.', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Masuk';
  }
});

// ── Register ─────────────────────────────────────────────────────────────────

$('#register-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  clearErrors('reg');
  hideAlert('register-alert');

  const full_name = $('#reg-name').value.trim();
  const email     = $('#reg-email').value.trim();
  const phone     = $('#reg-phone').value.trim() || null;
  const password  = $('#reg-password').value;
  const roleEl    = document.querySelector('input[name="role"]:checked');
  const province  = $('#reg-province').value.trim() || null;
  const city      = $('#reg-city').value.trim() || null;
  let valid = true;

  if (full_name.length < 2) { setFieldError('reg-name', 'Nama minimal 2 karakter.'); valid = false; }
  if (!email)                { setFieldError('reg-email', 'Email wajib diisi.'); valid = false; }
  if (password.length < 8)   { setFieldError('reg-password', 'Password minimal 8 karakter.'); valid = false; }
  if (!roleEl)               { setFieldError('reg-role', 'Pilih peran Anda.'); valid = false; }
  if (phone && !/^(\+62|0)[0-9]{8,13}$/.test(phone)) {
    setFieldError('reg-phone', 'Format nomor tidak valid (contoh: 081234567890).');
    valid = false;
  }
  if (!valid) return;

  const btn = $('#register-submit');
  btn.disabled = true;
  btn.textContent = 'Mendaftarkan...';

  const payload = { full_name, email, password, role: roleEl.value, province, city };
  if (phone) payload.phone = phone;

  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      if (res.status === 409) {
        setFieldError('reg-email', 'Email sudah terdaftar.');
      } else if (res.status === 422 && data.detail) {
        // Pydantic validation errors
        data.detail.forEach(err => {
          const field = err.loc?.at(-1);
          if (field) setFieldError(`reg-${field}`, err.msg);
        });
      } else {
        showAlert('register-alert', data.detail || 'Pendaftaran gagal.', 'error');
      }
      return;
    }

    saveTokens(data.access_token, data.refresh_token);
    showAlert('register-alert', `Akun berhasil dibuat! Selamat datang, ${data.user.full_name}.`, 'success');
    $('#register-form').reset();

    // TODO: redirect to dashboard when it's ready

  } catch {
    showAlert('register-alert', 'Tidak dapat terhubung ke server.', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Daftar Sekarang';
  }
});
