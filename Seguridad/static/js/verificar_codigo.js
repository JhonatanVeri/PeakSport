/**
 * ========================================
 * VERIFICAR_CODIGO.JS - SCRIPT MFA 2FA
 * PeakSport - Sistema de Autenticación
 * Modal Flotante sobre el Login
 * ========================================
 */

// ========================================
// CONFIGURACIÓN INICIAL
// ========================================
const TIEMPO_TOTAL = 300; // 5 minutos en segundos
let tiempoRestante = TIEMPO_TOTAL;

// DOM Elements
const inputs = document.querySelectorAll('.code-input');
const codigoCompleto = document.getElementById('codigoCompleto');
const form = document.getElementById('mfaForm');
const resendBtn = document.getElementById('resendBtn');
const resendTimer = document.getElementById('resendTimer');
const timerDisplay = document.getElementById('timerDisplay');
const timerText = document.getElementById('timerText');
const timerCircle = document.getElementById('timerCircle');
const mensajesFlash = document.getElementById('mensajesFlash');

const circumference = 2 * Math.PI * 28;

let timerInterval = null;
let codigoExpirado = false;

// ========================================
// INICIALIZACIÓN
// ========================================
document.addEventListener('DOMContentLoaded', function() {
  inicializarInputs();
  inicializarTimer();
  inicializarFormulario();
  inputs[0].focus();
  log('✅ Modal MFA inicializado correctamente');
});

// ========================================
// GESTIÓN DE INPUTS DE CÓDIGO
// ========================================
function inicializarInputs() {
  inputs.forEach((input, index) => {
    // Auto-avanzar al siguiente input
    input.addEventListener('input', (e) => {
      // Solo permitir números
      e.target.value = e.target.value.replace(/[^0-9]/g, '');
      
      if (e.target.value.length === 1 && index < inputs.length - 1) {
        inputs[index + 1].focus();
      }
      actualizarCodigoOculto();
    });

    // Navegación hacia atrás con Backspace
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && !e.target.value && index > 0) {
        inputs[index - 1].focus();
      }
    });

    // Solo permitir números
    input.addEventListener('keypress', (e) => {
      if (!/[0-9]/.test(e.key)) {
        e.preventDefault();
      }
    });

    // Pegar código completo
    input.addEventListener('paste', (e) => {
      e.preventDefault();
      const pastedData = e.clipboardData.getData('text').replace(/[^0-9]/g, '').slice(0, 6);
      pastedData.split('').forEach((char, i) => {
        if (i < inputs.length && /[0-9]/.test(char)) {
          inputs[i].value = char;
        }
      });
      actualizarCodigoOculto();
      if (pastedData.length === 6) {
        inputs[5].focus();
      }
      log(`📋 Código pegado: ${pastedData}`);
    });
  });
}

function actualizarCodigoOculto() {
  const code = Array.from(inputs).map(input => input.value).join('');
  codigoCompleto.value = code;
}

// ========================================
// TEMPORIZADOR (COUNTDOWN)
// ========================================
function inicializarTimer() {
  tiempoRestante = TIEMPO_TOTAL;
  codigoExpirado = false;

  timerInterval = setInterval(() => {
    tiempoRestante--;

    const minutos = Math.floor(tiempoRestante / 60);
    const segundos = tiempoRestante % 60;
    const tiempoString = `${minutos}:${segundos.toString().padStart(2, '0')}`;

    // Actualizar display del temporizador
    timerDisplay.textContent = tiempoString;
    timerText.textContent = `${minutos} minuto${minutos !== 1 ? 's' : ''}`;
    resendTimer.textContent = `(${tiempoString})`;

    // Actualizar círculo del timer
    const offset = circumference - (tiempoRestante / TIEMPO_TOTAL) * circumference;
    timerCircle.style.strokeDashoffset = offset;

    // ========================================
    // CUANDO PASAN LOS 5 MINUTOS (tiempoRestante <= 0)
    // ========================================
    if (tiempoRestante <= 0 && !codigoExpirado) {
      codigoExpirado = true;
      manejarCodigoExpirado();
    }

    // ========================================
    // DESPUÉS DE 5 MINUTOS: ACTIVAR BOTÓN REENVIAR
    // ========================================
    if (tiempoRestante < 0 && codigoExpirado) {
      habilitarBotónReenvio();
    }
  }, 1000);
}

function habilitarBotónReenvio() {
  if (resendBtn.classList.contains('resend-enabled')) {
    return;
  }

  resendBtn.classList.remove('resend-disabled');
  resendBtn.classList.add('resend-enabled');
  resendBtn.disabled = false;
  resendTimer.textContent = '(Disponible)';
  
  log('✅ Botón de reenvío habilitado después de 5 minutos');
}

function manejarCodigoExpirado() {
  mostrarMensaje(
    '❌ Código expirado. Puedes solicitar uno nuevo usando el botón "Reenviar código".',
    'error'
  );
  
  inputs.forEach(input => {
    input.disabled = true;
  });
  
  const btnSubmit = document.querySelector('button[type="submit"]');
  btnSubmit.disabled = true;
  btnSubmit.style.opacity = '0.6';
  btnSubmit.innerHTML = '<i class="fas fa-clock"></i> Código Expirado';
  
  log('⏰ Código expirado - esperando reenvío');
}

// ========================================
// REENVÍO DE CÓDIGO
// ========================================
resendBtn.addEventListener('click', (e) => {
  e.preventDefault();

  if (resendBtn.disabled) {
    return;
  }

  if (confirm('¿Deseas recibir un nuevo código de verificación?')) {
    mostrarMensaje(
      '📧 Enviando nuevo código a tu correo...',
      'info'
    );

    // Llamada al servidor para reenviar el código
    fetch('{{ url_for("mfa.verificar_codigo") }}', {
      method: 'GET'
    })
    .then(response => {
      if (response.ok) {
        mostrarMensaje(
          '✅ Nuevo código enviado a tu correo. Revisa tu bandeja de entrada.',
          'success'
        );
        
        clearInterval(timerInterval);
        tiempoRestante = TIEMPO_TOTAL;
        codigoExpirado = false;
        inicializarTimer();
        
        limpiarInputsCódigo();
        
        inputs.forEach(input => {
          input.disabled = false;
        });
        
        const btnSubmit = document.querySelector('button[type="submit"]');
        btnSubmit.disabled = false;
        btnSubmit.style.opacity = '1';
        btnSubmit.innerHTML = 'Verificar';
        
        resendBtn.classList.remove('resend-enabled');
        resendBtn.classList.add('resend-disabled');
        resendBtn.disabled = true;
        
        log('✅ Código reenviado - Temporizador reiniciado');
      } else {
        mostrarMensaje(
          '❌ Error al enviar el código. Por favor, intenta nuevamente.',
          'error'
        );
        log('❌ Error al reenviar código');
      }
    })
    .catch(error => {
      console.error('Error:', error);
      mostrarMensaje(
        '❌ Error de conexión. Por favor, intenta nuevamente.',
        'error'
      );
      log(`❌ Error de conexión: ${error}`);
    });
  }
});

function limpiarInputsCódigo() {
  inputs.forEach(input => {
    input.value = '';
  });
  codigoCompleto.value = '';
  inputs[0].focus();
}

// ========================================
// FORMULARIO DE VERIFICACIÓN
// ========================================
function inicializarFormulario() {
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    actualizarCodigoOculto();

    if (codigoExpirado) {
      mostrarMensaje('❌ El código ha expirado. Solicita uno nuevo.', 'error');
      return;
    }

    if (codigoCompleto.value.length !== 6) {
      mostrarMensaje('❌ Por favor ingresa el código completo de 6 dígitos', 'error');
      return;
    }

    if (!/^\d{6}$/.test(codigoCompleto.value)) {
      mostrarMensaje('❌ El código debe contener solo números', 'error');
      return;
    }

    log(`🔐 Verificando código: ${codigoCompleto.value}`);
    
    const btnSubmit = document.querySelector('button[type="submit"]');
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verificando...';

    form.submit();
  });
}

// ========================================
// FUNCIÓN PARA MOSTRAR MENSAJES
// ========================================
function mostrarMensaje(mensaje, tipo = 'error') {
  let bgColor, icon;

  if (tipo === 'error') {
    bgColor = 'bg-red-50 border-red-200 text-red-800';
    icon = 'exclamation-circle';
  } else if (tipo === 'success') {
    bgColor = 'bg-green-50 border-green-200 text-green-800';
    icon = 'check-circle';
  } else {
    bgColor = 'bg-blue-50 border-blue-200 text-blue-800';
    icon = 'info-circle';
  }

  const mensajeHTML = `
    <div class="mb-4 p-4 rounded-xl border-2 ${bgColor} alert-message">
      <div class="flex items-center">
        <i class="fas fa-${icon} mr-2"></i>
        <span class="font-semibold">${mensaje}</span>
      </div>
    </div>
  `;

  mensajesFlash.innerHTML = mensajeHTML;

  if (tipo === 'success') {
    setTimeout(() => {
      mensajesFlash.innerHTML = '';
    }, 4000);
  }
}

// ========================================
// FUNCIÓN PARA CANCELAR MFA
// ========================================
function cancelarMFA() {
  if (confirm('¿Estás seguro de que deseas cancelar la verificación?')) {
    log('🚪 Usuario canceló la verificación MFA');
    
    fetch('{{ url_for("login.logout_usuario_route") }}', {
      method: 'POST'
    })
    .then(() => {
      window.location.href = '{{ url_for("login.vista_pantalla_login") }}';
    })
    .catch(error => {
      console.error('Error:', error);
      log(`❌ Error al cancelar: ${error}`);
      window.location.href = '{{ url_for("login.vista_pantalla_login") }}';
    });
  }
}

// ========================================
// UTILIDADES Y LOGGING
// ========================================

/**
 * Sistema de logging personalizado
 */
function log(mensaje, tipo = 'info') {
  const timestamp = new Date().toLocaleTimeString('es-CO');
  const estilos = {
    info: 'color: #3b82f6; font-weight: bold;',
    success: 'color: #10b981; font-weight: bold;',
    error: 'color: #ef4444; font-weight: bold;',
    warn: 'color: #f59e0b; font-weight: bold;'
  };
  
  console.log(
    `%c[${timestamp}] ${mensaje}`,
    estilos[tipo] || estilos.info
  );
}

/**
 * Limpiar temporizador al descargar la página
 */
window.addEventListener('beforeunload', () => {
  if (timerInterval) {
    clearInterval(timerInterval);
  }
});