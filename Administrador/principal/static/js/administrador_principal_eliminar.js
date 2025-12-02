/* ===========================
   Config & Refs
=========================== */
const PRODUCTO_ID = window.__PRODUCTO_ID__;
const EP = window.__ADMIN_ENDPOINTS__;

const btnRechazar = document.getElementById('btnRechazar');
const btnConfirmar = document.getElementById('btnConfirmar');

/* ===========================
   Utils
=========================== */
function showNotification(title, message, type = 'info') {
  const notification = document.getElementById('notification');
  const icon = document.getElementById('notificationIcon');
  const titleEl = document.getElementById('notificationTitle');
  const messageEl = document.getElementById('notificationMessage');
  
  const config = {
    success: { icon: 'fas fa-check', color: 'bg-green-500' },
    error: { icon: 'fas fa-times', color: 'bg-red-500' },
    warning: { icon: 'fas fa-exclamation', color: 'bg-yellow-500' },
    info: { icon: 'fas fa-info', color: 'bg-blue-500' }
  };
  
  const typeConfig = config[type] || config.info;
  icon.className = `w-8 h-8 ${typeConfig.color} rounded-full flex items-center justify-center`;
  icon.innerHTML = `<i class="${typeConfig.icon} text-white text-sm"></i>`;
  
  titleEl.textContent = title;
  messageEl.textContent = message;
  
  notification.classList.remove('translate-x-full');
  
  setTimeout(() => {
    notification.classList.add('translate-x-full');
  }, 3000);
}

/* ===========================
   Handlers
=========================== */
btnRechazar.addEventListener('click', () => {
  showNotification('Eliminación cancelada', 'El producto se mantiene en el inventario', 'info');
  
  setTimeout(() => {
    window.location.href = EP.vistaListado;
  }, 1000);
});

btnConfirmar.addEventListener('click', async () => {
  // Deshabilitar botones para evitar doble clic
  btnConfirmar.disabled = true;
  btnRechazar.disabled = true;
  btnConfirmar.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Eliminando...';

  try {
    // ✅ CORRECCIÓN: Cambiar método a DELETE
    const response = await fetch(EP.apiEliminar, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.error || 'No fue posible eliminar el producto');
    }

    showNotification('Producto eliminado', 'El producto ha sido eliminado del inventario', 'success');
    
    setTimeout(() => {
      showNotification('Redirigiendo...', 'Volviendo al inventario', 'info');
      setTimeout(() => {
        window.location.href = EP.vistaListado;
      }, 800);
    }, 1500);

  } catch (error) {
    console.error('Error al eliminar:', error);
    showNotification('Error', error.message, 'error');
    
    // Rehabilitar botones en caso de error
    btnConfirmar.disabled = false;
    btnRechazar.disabled = false;
    btnConfirmar.innerHTML = '<i class="fas fa-check mr-2"></i> Confirmar';
  }
});

/* ===========================
   Boot
=========================== */
document.addEventListener('DOMContentLoaded', () => {
  showNotification('Confirma la acción', 'Revisa los datos antes de eliminar', 'warning');
});

/* ===========================
   Cerrar con ESC
=========================== */
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    btnRechazar.click();
  }
});

/* Cerrar al hacer clic fuera del modal */
document.querySelector('.modal-overlay').addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    btnRechazar.click();
  }
});