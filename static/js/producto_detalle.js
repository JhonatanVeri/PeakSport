// =======================================
// producto_detalle.js - Sistema completo de reseñas
// =======================================

// ---------- Variables globales inyectadas por el HTML ----------
const PRODUCTO = window.__PRODUCTO_DATA__ || {};
const IS_LOGGED = window.__LOGGED__ || false;
const USUARIO_ID = window.__USUARIO_ID__ || null;
const USUARIO_NOMBRE = window.__USUARIO_NOMBRE__ || 'Invitado';
const PUEDE_RESENAR = window.__PUEDE_RESENAR__ || false;
const API_BASE_URL = window.__API_BASE_URL__ || '/api/resenas';
const LOGIN_URL = window.__LOGIN_URL__ || '/login/';

// ---------- Estado de reseñas ----------
let currentPage = 1;
let totalPages = 1;
let reviewsData = {
  resenas: [],
  total: 0,
  estadisticas: null
};

// ---------- Inicialización ----------
document.addEventListener('DOMContentLoaded', function() {
  console.log('🚀 Producto cargado:', PRODUCTO.nombre);
  
  // Cargar reseñas al inicio
  loadReviews();
  
  // Setup listeners del formulario de reseña
  setupReviewForm();
  
  // Setup contador de caracteres
  setupCharCounter();
  
  // Mensaje de bienvenida
  setTimeout(() => {
    showNotification('Producto cargado', `Explorando: ${PRODUCTO.nombre}`, 'info');
  }, 500);
});

// ===================== GALERÍA DE IMÁGENES =====================

function changeMainImage(src) {
  const mainImage = document.getElementById('mainImage');
  if (!mainImage) return;
  
  mainImage.src = src;
  
  // Actualizar thumbnails
  document.querySelectorAll('.thumbnail-btn').forEach(btn => {
    btn.classList.remove('border-red-500', 'opacity-100');
    btn.classList.add('border-transparent', 'opacity-60');
  });
  
  event.target.closest('.thumbnail-btn')?.classList.remove('border-transparent', 'opacity-60');
  event.target.closest('.thumbnail-btn')?.classList.add('border-red-500', 'opacity-100');
}

// ===================== CANTIDAD =====================

function updateQuantity(change) {
  const quantityInput = document.getElementById('quantity');
  if (!quantityInput) return;
  
  const currentValue = parseInt(quantityInput.value) || 1;
  const newValue = currentValue + change;
  const maxStock = parseInt(quantityInput.max) || 100;
  
  if (newValue >= 1 && newValue <= maxStock) {
    quantityInput.value = newValue;
  }
}

// ===================== CARRITO =====================

function addToCart() {
  if (!IS_LOGGED) {
    showNotification('Inicia sesión', 'Debes iniciar sesión para agregar al carrito', 'warning');
    setTimeout(() => window.location.href = LOGIN_URL, 1500);
    return;
  }
  
  if (PRODUCTO.stock <= 0) {
    showNotification('Sin stock', 'Este producto está agotado', 'error');
    return;
  }
  
  const quantity = parseInt(document.getElementById('quantity')?.value) || 1;
  
  showNotification(
    'Agregado al carrito',
    `${quantity} x ${PRODUCTO.nombre} - $${(PRODUCTO.precio * quantity).toFixed(2)}`,
    'success'
  );
  
  // Actualizar contador del carrito (si existe)
  const cartCount = document.getElementById('cartCount');
  if (cartCount) {
    const current = parseInt(cartCount.textContent) || 0;
    cartCount.textContent = current + quantity;
    cartCount.classList.add('pulse-animation');
    setTimeout(() => cartCount.classList.remove('pulse-animation'), 1000);
  }
}

function buyNow() {
  if (!IS_LOGGED) {
    showNotification('Inicia sesión', 'Debes iniciar sesión para comprar', 'warning');
    setTimeout(() => window.location.href = LOGIN_URL, 1500);
    return;
  }
  
  if (PRODUCTO.stock <= 0) {
    showNotification('Sin stock', 'Este producto está agotado', 'error');
    return;
  }
  
  showNotification('Procesando...', 'Redirigiendo al checkout', 'info');
  // Aquí iría la lógica de redirección al checkout
}

function addToWishlist() {
  if (!IS_LOGGED) {
    showNotification('Inicia sesión', 'Debes iniciar sesión para guardar favoritos', 'warning');
    return;
  }
  
  showNotification('Agregado a favoritos', `${PRODUCTO.nombre} guardado en tu lista`, 'success');
}

function shareProduct() {
  if (navigator.share) {
    navigator.share({
      title: `${PRODUCTO.nombre} - PeakSport`,
      text: `Mira este producto: ${PRODUCTO.nombre}`,
      url: window.location.href
    }).then(() => {
      showNotification('Compartido', 'Producto compartido exitosamente', 'success');
    }).catch(() => {
      copyToClipboard(window.location.href);
    });
  } else {
    copyToClipboard(window.location.href);
  }
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showNotification('Enlace copiado', 'URL copiada al portapapeles', 'success');
  }).catch(() => {
    showNotification('Error', 'No se pudo copiar el enlace', 'error');
  });
}

function toggleCart() {
  showNotification('Carrito', 'Abriendo carrito de compras', 'info');
  // Aquí iría la lógica del modal del carrito
}

// ===================== TABS =====================

function showTab(tabName) {
  // Ocultar todos los contenidos
  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.add('hidden');
  });
  
  // Mostrar el contenido seleccionado
  const selectedTab = document.getElementById(tabName);
  if (selectedTab) {
    selectedTab.classList.remove('hidden');
  }
  
  // Actualizar botones de tab
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('tab-active');
    btn.classList.add('text-gray-300');
  });
  
  if (event?.target) {
    event.target.classList.add('tab-active');
    event.target.classList.remove('text-gray-300');
  }
  
  // Si se abre la tab de reseñas, asegurar que estén cargadas
  if (tabName === 'reviews' && reviewsData.resenas.length === 0) {
    loadReviews();
  }
}

// ===================== SISTEMA DE RESEÑAS =====================

async function loadReviews(page = 1) {
  try {
    showNotification('Cargando reseñas...', 'Obteniendo opiniones', 'info');
    
    const response = await fetch(
      `${API_BASE_URL}/productos/${PRODUCTO.id}/resenas?page=${page}&per_page=10&orden=recientes`,
      {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        },
        credentials: 'same-origin'
      }
    );
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Error al cargar reseñas');
    }
    
    // Actualizar estado global
    currentPage = data.data.page;
    totalPages = data.data.total_pages;
    reviewsData = data.data;
    
    // Renderizar estadísticas
    renderReviewStats(data.data.estadisticas);
    
    // Renderizar lista de reseñas
    renderReviewsList(data.data.resenas, page === 1);
    
    // Actualizar contador en tab
    const tabCount = document.getElementById('tabReviewCount');
    if (tabCount) {
      tabCount.textContent = data.data.total;
    }
    
    // Mostrar/ocultar botón "cargar más"
    const loadMoreContainer = document.getElementById('loadMoreContainer');
    if (loadMoreContainer) {
      if (currentPage < totalPages) {
        loadMoreContainer.classList.remove('hidden');
      } else {
        loadMoreContainer.classList.add('hidden');
      }
    }
    
    showNotification('Reseñas cargadas', `${data.data.total} opiniones disponibles`, 'success');
    
  } catch (error) {
    console.error('Error al cargar reseñas:', error);
    showNotification('Error', 'No se pudieron cargar las reseñas', 'error');
    
    // Mostrar mensaje en la interfaz
    const reviewsList = document.getElementById('reviewsList');
    if (reviewsList && page === 1) {
      reviewsList.innerHTML = `
        <div class="text-center text-gray-400 py-8">
          <i class="fas fa-exclamation-circle text-4xl mb-4"></i>
          <p>No se pudieron cargar las reseñas. Intenta de nuevo más tarde.</p>
        </div>
      `;
    }
  }
}

function renderReviewStats(stats) {
  const statsContainer = document.getElementById('reviewStats');
  if (!statsContainer || !stats) return;
  
  const { total, promedio, distribucion, porcentajes } = stats;
  
  statsContainer.innerHTML = `
    <div class="glass-card rounded-xl p-6">
      <div class="text-center mb-6">
        <div class="text-5xl font-bold text-red-400 mb-2">${promedio.toFixed(1)}</div>
        <div class="flex justify-center star-rating text-2xl mb-2">
          ${generateStarHTML(promedio)}
        </div>
        <p class="text-gray-400">Basado en ${total} reseña${total !== 1 ? 's' : ''}</p>
      </div>
    </div>
    
    <div class="space-y-3">
      ${[5, 4, 3, 2, 1].map(estrella => `
        <div class="flex items-center space-x-3">
          <span class="text-sm text-gray-400 w-8">${estrella}★</span>
          <div class="flex-1 progress-bar">
            <div class="progress-fill" style="width: ${porcentajes[estrella] || 0}%"></div>
          </div>
          <span class="text-sm text-gray-400 w-12">${distribucion[estrella] || 0}</span>
        </div>
      `).join('')}
    </div>
  `;
}

function renderReviewsList(resenas, replace = true) {
  const reviewsList = document.getElementById('reviewsList');
  if (!reviewsList) return;
  
  if (resenas.length === 0 && replace) {
    reviewsList.innerHTML = `
      <div class="text-center text-gray-400 py-12">
        <i class="fas fa-comments text-5xl mb-4 opacity-50"></i>
        <p class="text-xl mb-2">Aún no hay reseñas</p>
        <p>Sé el primero en compartir tu opinión sobre este producto</p>
      </div>
    `;
    return;
  }
  
  const reviewsHTML = resenas.map(resena => `
    <div class="glass-card rounded-xl p-6 fade-in" data-review-id="${resena.id}">
      <div class="flex items-start space-x-4">
        <img src="https://i.pravatar.cc/50?seed=${resena.usuario_id}" 
             alt="${resena.usuario_nombre}" 
             class="w-12 h-12 rounded-full border-2 border-red-500">
        <div class="flex-1">
          <div class="flex items-center justify-between mb-2">
            <div>
              <h5 class="font-semibold text-white">
                ${resena.usuario_nombre}
                ${resena.compra_verificada ? '<i class="fas fa-check-circle text-green-400 ml-2" title="Compra verificada"></i>' : ''}
              </h5>
              <div class="flex star-rating text-sm">
                ${generateStarHTML(resena.calificacion)}
              </div>
            </div>
            <div class="flex items-center space-x-3">
              <span class="text-gray-400 text-sm">${resena.tiempo_transcurrido}</span>
              ${IS_LOGGED && USUARIO_ID === resena.usuario_id ? `
                <button onclick="deleteReview(${resena.id})" 
                        class="text-red-400 hover:text-red-300 transition-colors"
                        title="Eliminar reseña">
                  <i class="fas fa-trash"></i>
                </button>
              ` : ''}
            </div>
          </div>
          <p class="text-gray-300 mb-3">${escapeHTML(resena.comentario)}</p>
        </div>
      </div>
    </div>
  `).join('');
  
  if (replace) {
    reviewsList.innerHTML = reviewsHTML;
  } else {
    reviewsList.insertAdjacentHTML('beforeend', reviewsHTML);
  }
}

function loadMoreReviews() {
  if (currentPage < totalPages) {
    loadReviews(currentPage + 1);
  }
}

// ===================== MODAL DE NUEVA RESEÑA =====================

let selectedRating = 0;

function openReviewModal() {
  if (!IS_LOGGED) {
    showNotification('Inicia sesión', 'Debes iniciar sesión para dejar una reseña', 'warning');
    setTimeout(() => window.location.href = LOGIN_URL, 1500);
    return;
  }
  
  if (!PUEDE_RESENAR) {
    showNotification('Ya reseñaste', 'Ya dejaste una reseña para este producto', 'info');
    return;
  }
  
  const modal = document.getElementById('reviewModal');
  if (modal) {
    modal.classList.remove('hidden');
    // Reset form
    document.getElementById('reviewForm')?.reset();
    selectedRating = 0;
    updateStarButtons();
    updateCharCount();
  }
}

function closeReviewModal() {
  const modal = document.getElementById('reviewModal');
  if (modal) {
    modal.classList.add('hidden');
  }
}

function setRating(rating) {
  selectedRating = rating;
  document.getElementById('ratingInput').value = rating;
  updateStarButtons();
  
  // Ocultar error si existía
  const error = document.getElementById('ratingError');
  if (error) {
    error.classList.add('hidden');
  }
}

function updateStarButtons() {
  document.querySelectorAll('.star-btn').forEach((btn, index) => {
    const star = btn.querySelector('i');
    if (index < selectedRating) {
      star.classList.remove('far', 'text-gray-600');
      star.classList.add('fas', 'text-yellow-400');
    } else {
      star.classList.remove('fas', 'text-yellow-400');
      star.classList.add('far', 'text-gray-600');
    }
  });
}

function setupReviewForm() {
  const form = document.getElementById('reviewForm');
  if (!form) return;
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const calificacion = selectedRating;
    const comentario = document.getElementById('commentInput')?.value.trim();
    
    // Validaciones
    let hasError = false;
    
    if (!calificacion || calificacion < 1 || calificacion > 5) {
      const error = document.getElementById('ratingError');
      if (error) {
        error.classList.remove('hidden');
      }
      hasError = true;
    }
    
    if (!comentario || comentario.length < 10) {
      const error = document.getElementById('commentError');
      if (error) {
        error.classList.remove('hidden');
      }
      hasError = true;
    }
    
    if (hasError) {
      showNotification('Campos incompletos', 'Por favor completa todos los campos correctamente', 'warning');
      return;
    }
    
    // Enviar reseña
    await submitReview(calificacion, comentario);
  });
}

async function submitReview(calificacion, comentario) {
  try {
    showNotification('Enviando reseña...', 'Publicando tu opinión', 'info');
    
    const response = await fetch(
      `${API_BASE_URL}/productos/${PRODUCTO.id}/resenas`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        credentials: 'same-origin',
        body: JSON.stringify({
          calificacion: calificacion,
          comentario: comentario
        })
      }
    );
    
    const data = await response.json();
    
    if (!response.ok || !data.success) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }
    
    showNotification('¡Reseña publicada!', 'Gracias por compartir tu opinión', 'success');
    
    // Cerrar modal
    closeReviewModal();
    
    // Recargar reseñas
    await loadReviews();
    
    // Cambiar a tab de reseñas
    showTab('reviews');
    
    // Actualizar flag de puede reseñar
    window.__PUEDE_RESENAR__ = false;
    
  } catch (error) {
    console.error('Error al enviar reseña:', error);
    showNotification('Error', error.message || 'No se pudo publicar la reseña', 'error');
  }
}

async function deleteReview(reviewId) {
  if (!confirm('¿Estás seguro de que deseas eliminar esta reseña?')) {
    return;
  }
  
  try {
    showNotification('Eliminando...', 'Procesando solicitud', 'info');
    
    const response = await fetch(
      `${API_BASE_URL}/resenas/${reviewId}`,
      {
        method: 'DELETE',
        headers: {
          'Accept': 'application/json'
        },
        credentials: 'same-origin'
      }
    );
    
    const data = await response.json();
    
    if (!response.ok || !data.success) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }
    
    showNotification('Reseña eliminada', 'Tu reseña ha sido eliminada', 'success');
    
    // Remover del DOM con animación
    const reviewElement = document.querySelector(`[data-review-id="${reviewId}"]`);
    if (reviewElement) {
      reviewElement.style.opacity = '0';
      reviewElement.style.transform = 'translateX(-20px)';
      setTimeout(() => {
        reviewElement.remove();
      }, 300);
    }
    
    // Recargar reseñas después de un momento
    setTimeout(() => loadReviews(), 500);
    
    // Actualizar flag de puede reseñar
    window.__PUEDE_RESENAR__ = true;
    
  } catch (error) {
    console.error('Error al eliminar reseña:', error);
    showNotification('Error', error.message || 'No se pudo eliminar la reseña', 'error');
  }
}

function setupCharCounter() {
  const commentInput = document.getElementById('commentInput');
  const charCount = document.getElementById('charCount');
  const commentError = document.getElementById('commentError');
  
  if (!commentInput || !charCount) return;
  
  commentInput.addEventListener('input', updateCharCount);
}

function updateCharCount() {
  const commentInput = document.getElementById('commentInput');
  const charCount = document.getElementById('charCount');
  const commentError = document.getElementById('commentError');
  
  if (!commentInput || !charCount) return;
  
  const length = commentInput.value.length;
  charCount.textContent = length;
  
  if (length >= 10) {
    charCount.classList.remove('text-red-400');
    charCount.classList.add('text-green-400');
    if (commentError) {
      commentError.classList.add('hidden');
    }
  } else {
    charCount.classList.remove('text-green-400');
    charCount.classList.add('text-red-400');
  }
}

// ===================== HELPERS =====================

function generateStarHTML(rating) {
  const fullStars = Math.floor(rating);
  const hasHalfStar = rating % 1 >= 0.5;
  let html = '';
  
  for (let i = 0; i < 5; i++) {
    if (i < fullStars) {
      html += '<i class="fas fa-star"></i>';
    } else if (i === fullStars && hasHalfStar) {
      html += '<i class="fas fa-star-half-alt"></i>';
    } else {
      html += '<i class="far fa-star text-gray-600"></i>';
    }
  }
  
  return html;
}

function escapeHTML(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ===================== NOTIFICACIONES =====================

function showNotification(title, message, type = 'info') {
  const notification = document.getElementById('notification');
  const icon = document.getElementById('notificationIcon');
  const titleEl = document.getElementById('notificationTitle');
  const messageEl = document.getElementById('notificationMessage');
  
  if (!notification || !icon || !titleEl || !messageEl) return;
  
  const config = {
    success: { 
      icon: 'fas fa-check', 
      color: 'gradient-green', 
      border: 'border-green-500/30' 
    },
    error: { 
      icon: 'fas fa-times', 
      color: 'gradient-bg', 
      border: 'border-red-500/30' 
    },
    warning: { 
      icon: 'fas fa-exclamation', 
      color: 'bg-yellow-500', 
      border: 'border-yellow-500/30' 
    },
    info: { 
      icon: 'fas fa-info', 
      color: 'gradient-blue', 
      border: 'border-blue-500/30' 
    }
  };
  
  const typeConfig = config[type] || config.info;
  
  icon.className = `w-10 h-10 ${typeConfig.color} rounded-full flex items-center justify-center`;
  icon.innerHTML = `<i class="${typeConfig.icon} text-white"></i>`;
  notification.className = `fixed top-24 right-6 glass-card text-white px-6 py-4 rounded-2xl shadow-2xl transform translate-x-full transition-all duration-500 z-50 border ${typeConfig.border} elegant-shadow`;
  
  titleEl.textContent = title;
  messageEl.textContent = message;
  
  notification.classList.remove('translate-x-full');
  
  setTimeout(() => {
    notification.classList.add('translate-x-full');
  }, 4000);
}

// ===================== CERRAR MODALES AL HACER CLIC FUERA =====================

document.addEventListener('click', function(e) {
  if (e.target.id === 'reviewModal') {
    closeReviewModal();
  }
});