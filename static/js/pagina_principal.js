// =======================================
// pagina_principal.js - VERSIÓN 3.0 COMPLETA CORREGIDA
// =======================================
// Sistema integral de carrito, productos, autenticación y navegación
// Estado: Productos + Carrito + Menús + Modales - TODO FUNCIONANDO

// ---------- CONSTANTES DE ENTORNO (Inyectadas por HTML) ----------
const IS_LOGGED = typeof window !== "undefined" ? !!window.__LOGGED__ : false;
const USERNAME = typeof window !== "undefined" ? (window.__USERNAME__ || "Invitado") : "Invitado";
const USER_EMAIL = typeof window !== "undefined" ? (window.__USER_EMAIL__ || null) : null;

// URLs de sistema
const LOGIN_URL = typeof window !== "undefined" ? (window.__LOGIN_URL__ || "/login/") : "/login/";
const LOGOUT_URL = typeof window !== "undefined" ? (window.__LOGOUT_URL__ || "/login/auth/logout") : "/login/auth/logout";

// APIs
const API_PRODUCTOS = "/api/productos";
const API_CARRITO = "/cart/api/cart";

// ---------- ESTADO GLOBAL ----------
let cartItems = 0;
let cartTotal = 0.00;
let cartProducts = [];
let productosActuales = [];
let paginaActual = 1;
let cargando = false;

const PRODUCTOS_POR_PAGINA = 12;

// ---------- UTILIDADES ----------

/**
 * Formatea número como moneda
 */
function money(v) {
  const n = Number(v || 0);
  return `$${n.toFixed(2)}`;
}

/**
 * Formatea precio colombiano
 */
function formatearPrecio(precio, moneda = 'COP') {
  const formatters = {
    'COP': (p) => `$${Math.round(p).toLocaleString('es-CO')}`,
    'USD': (p) => `$${p.toFixed(2)}`,
    'EUR': (p) => `€${p.toFixed(2)}`
  };
  
  return formatters[moneda] ? formatters[moneda](precio) : `${moneda} ${precio}`;
}

/**
 * Fetch wrapper con manejo de errores
 */
async function fetchJSON(url, opts = {}) {
  try {
    const r = await fetch(url, {
      credentials: "same-origin",
      ...opts,
      headers: {
        "Accept": "application/json",
        ...(opts.headers || {})
      }
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  } catch (error) {
    console.error(`[fetchJSON] Error en ${url}:`, error);
    throw error;
  }
}

// ---------- NOTIFICACIONES ----------

/**
 * Notificación avanzada con estilos
 */
function showAdvancedNotification(title, message, type = 'info') {
  const notification = document.createElement('div');
  const colors = {
    success: 'border-green-500/30 bg-green-500/10',
    error: 'border-red-500/30 bg-red-500/10',
    info: 'border-blue-500/30 bg-blue-500/10',
    warning: 'border-yellow-500/30 bg-yellow-500/10'
  };
  const icons = {
    success: 'fas fa-check-circle text-green-400',
    error: 'fas fa-exclamation-circle text-red-400',
    info: 'fas fa-info-circle text-blue-400',
    warning: 'fas fa-exclamation-triangle text-yellow-400'
  };

  notification.className = `fixed top-24 right-6 glass-card ${colors[type]} text-white px-6 py-4 rounded-2xl shadow-2xl z-50 border glow-effect transform translate-x-full transition-all duration-500`;
  notification.innerHTML = `
    <div class="flex items-start space-x-3">
      <i class="${icons[type]} text-xl mt-1"></i>
      <div>
        <div class="font-bold text-lg">${title}</div>
        <div class="text-gray-300 text-sm mt-1">${message}</div>
      </div>
    </div>
  `;

  document.body.appendChild(notification);
  setTimeout(() => { notification.classList.remove('translate-x-full'); }, 100);
  setTimeout(() => {
    notification.classList.add('translate-x-full');
    setTimeout(() => { notification.parentNode?.removeChild(notification); }, 500);
  }, 4000);
}

/**
 * Notificación de carrito (simple)
 */
function showCartNotification(productName, price) {
  const notification = document.getElementById('cartNotification');
  const message = document.getElementById('cartMessage');
  const subMessage = document.getElementById('cartSubMessage');

  if (!notification || !message || !subMessage) return;

  message.textContent = productName;
  subMessage.textContent = `${money(price)} • Agregado al carrito`;

  notification.classList.remove('translate-x-full');
  setTimeout(() => {
    notification.classList.add('translate-x-full');
  }, 4000);
}

// ---------- GESTIÓN DE PRODUCTOS ----------

/**
 * Carga productos desde la API
 */
async function cargarProductos(pagina = 1, limpiar = true) {
  if (cargando) return;
  
  try {
    cargando = true;
    mostrarCargando();

    const params = new URLSearchParams({
      page: pagina,
      per_page: PRODUCTOS_POR_PAGINA
    });

    const data = await fetchJSON(`${API_PRODUCTOS}/list?${params}`);
    
    if (limpiar) {
      productosActuales = data.productos || [];
    } else {
      productosActuales = [...productosActuales, ...(data.productos || [])];
    }

    paginaActual = pagina;
    renderizarProductos(limpiar);
    
  } catch (error) {
    console.error('Error al cargar productos:', error);
    mostrarError('Error al cargar los productos. Por favor, intenta nuevamente.');
    showAdvancedNotification('⚠ Error', 'No se pudieron cargar los productos', 'error');
  } finally {
    cargando = false;
    ocultarCargando();
  }
}

/**
 * Carga productos recomendados (home)
 */
async function cargarRecomendados() {
  try {
    const data = await fetchJSON(`${API_PRODUCTOS}/recomendados`);
    const grid = document.getElementById('recomendadosGrid');
    if (!grid) return;

    const items = (data && data.productos) ? data.productos : [];
    if (!items.length) {
      grid.innerHTML = `
        <div class="col-span-full text-gray-400 text-center glass-card rounded-2xl p-8">
          No hay productos recomendados por ahora.
        </div>`;
      return;
    }
    
    grid.innerHTML = items.map(cardHtml).join('');
    
    // Animación de entrada
    const cards = grid.querySelectorAll('.card-hover');
    cards.forEach((card, index) => {
      card.style.animationDelay = `${index * 0.06}s`;
      card.classList.add('slide-in');
    });
  } catch (e) {
    console.error('Error en cargarRecomendados:', e);
    showAdvancedNotification('⚠ Error', 'No se pudieron cargar los recomendados', 'error');
  }
}

/**
 * Carga todos los productos
 */
async function showAllProducts(page = 1) {
  try {
    showAdvancedNotification('🛍 Catálogo', 'Cargando productos...', 'info');
    const data = await fetchJSON(`${API_PRODUCTOS}/list?page=${page}&per_page=${PRODUCTOS_POR_PAGINA}`);
    const grid = document.getElementById('recomendadosGrid');
    if (!grid) return;
    
    const items = (data && data.productos) ? data.productos : [];
    grid.innerHTML = items.map(cardHtml).join('');
    showAdvancedNotification('✅ Listo', `Mostrando ${items.length} de ${data.total}`, 'success');
  } catch (e) {
    console.error('Error en showAllProducts:', e);
    showAdvancedNotification('⚠ Error', 'No se pudo cargar el catálogo', 'error');
  }
}

/**
 * HTML de tarjeta de producto
 */
function cardHtml(p) {
  // Manejar imagen
  const img = p.image || (p.imagenes && p.imagenes[0] ? p.imagenes[0].url : null) || 'https://via.placeholder.com/300x300?text=PeakSport';
  
  // Manejar rating
  const rating = (p.rating ?? 4.7).toFixed(1);
  
  // Manejar nombre
  const nombre = p.nombre || p.name || 'Producto';
  
  // Manejar slug
  const slug = p.slug || 'producto';
  
  // ✅ CORREGIDO: El precio ya viene en formato decimal desde la API
  const precio = p.precio_actual || p.price || 0;
  
  // Precio original para mostrar descuento
  const precioOriginal = p.precio_original || 0;
  const tieneDescuento = precioOriginal > precio && precioOriginal > 0;
  
  // Manejar moneda
  const moneda = p.moneda || p.currency || 'COP';
  
  // Stock y disponibilidad
  const stock = p.stock || 0;
  const activo = p.activo !== false;

  return `
    <div class="glass-card rounded-3xl card-hover p-7 border border-white/10 group">
      <div class="relative mb-6 overflow-hidden rounded-xl">
        ${tieneDescuento ? `
          <div class="absolute top-3 right-3 gradient-bg px-3 py-1 rounded-full text-white text-xs font-bold z-10">
            -${Math.round(((precioOriginal - precio) / precioOriginal) * 100)}%
          </div>
        ` : ''}
        ${!activo ? `
          <div class="absolute top-3 left-3 bg-red-500 px-3 py-1 rounded-full text-white text-xs font-bold z-10">
            No disponible
          </div>
        ` : ''}
        <img src="${img}" 
             class="w-full h-48 object-cover group-hover:scale-110 transition-transform duration-500" 
             alt="${nombre}" 
             onerror="this.src='https://via.placeholder.com/300x300?text=PeakSport'">
        <div class="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
      </div>
      <h4 class="font-bold text-xl mb-2 text-white group-hover:text-red-400 transition-colors line-clamp-2">${nombre}</h4>
      <p class="text-gray-400 text-sm mb-4">${moneda}</p>
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center space-x-2">
          <span class="text-2xl font-bold text-red-400">${formatearPrecio(precio, moneda)}</span>
          ${tieneDescuento ? `
            <span class="text-sm text-gray-500 line-through">${formatearPrecio(precioOriginal, moneda)}</span>
          ` : ''}
        </div>
        <div class="flex items-center space-x-1">
          <i class="fas fa-star text-yellow-400 text-sm"></i>
          <span class="text-sm text-gray-400 ml-1">${rating}</span>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <button class="w-full glass-card text-white py-3 rounded-xl hover:bg-white/10 transition-all font-medium"
                onclick="verDetalle('${slug}')">
          Ver
        </button>
        <button class="w-full gradient-bg text-white py-3 rounded-xl hover:scale-105 transition-all font-medium elegant-shadow ${!activo || stock === 0 ? 'opacity-50 cursor-not-allowed' : ''}"
                onclick="addToCart(${p.id || 0}, '${nombre.replace(/'/g, "\\'")}', ${precio})"
                ${!activo || stock === 0 ? 'disabled' : ''}>
          <i class="fas fa-cart-plus mr-2"></i> Agregar
        </button>
      </div>
    </div>`;
}

/**
 * Ver detalle de producto
 */
async function verDetalle(slug) {
  try {
    const data = await fetchJSON(`${API_PRODUCTOS}/${slug}`);
    if (data && data.success) {
      window.location.href = `/producto/${slug}`;
    } else {
      showAdvancedNotification('⚠ Error', 'Producto no encontrado', 'error');
    }
  } catch (e) {
    console.error('Error en verDetalle:', e);
    showAdvancedNotification('⚠ Error', 'No se pudo cargar el producto', 'error');
  }
}

/**
 * Renderiza productos en el grid
 */
function renderizarProductos(limpiar = true) {
  const contenedor = document.getElementById('recomendadosGrid');
  if (!contenedor) return;

  if (limpiar) {
    contenedor.innerHTML = '';
  }

  if (productosActuales.length === 0) {
    contenedor.innerHTML = `
      <div class="col-span-full text-gray-400 text-center glass-card rounded-2xl p-8">
        No hay productos disponibles
      </div>`;
    return;
  }

  contenedor.innerHTML = productosActuales.map(cardHtml).join('');
}

/**
 * Muestra indicador de carga
 */
function mostrarCargando() {
  const contenedor = document.getElementById('recomendadosGrid');
  if (contenedor && contenedor.children.length === 0) {
    contenedor.innerHTML = `
      <div class="col-span-full flex justify-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-red-500"></div>
      </div>`;
  }
}

/**
 * Oculta indicador de carga
 */
function ocultarCargando() {
  // Se elimina automáticamente al renderizar
}

/**
 * Muestra error
 */
function mostrarError(mensaje) {
  const contenedor = document.getElementById('recomendadosGrid');
  if (contenedor) {
    contenedor.innerHTML = `
      <div class="col-span-full text-center py-12">
        <svg class="mx-auto h-12 w-12 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 class="mt-2 text-lg font-medium text-white">Error</h3>
        <p class="mt-1 text-sm text-gray-400">${mensaje}</p>
      </div>`;
  }
}

// ---------- GESTIÓN DE CARRITO ----------

/**
 * Carga contador del carrito desde el backend
 */
async function loadCartCount() {
  if (!IS_LOGGED) {
    updateCartBadge(0);
    return;
  }
  
  try {
    const response = await fetch(`${API_CARRITO}/totales`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      },
      credentials: 'same-origin'
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.success) {
        updateCartBadge(data.totales.total_items || 0);
      }
    }
  } catch (error) {
    console.error('Error al cargar contador del carrito:', error);
  }
}

/**
 * Actualiza el badge del carrito
 */
function updateCartBadge(count) {
  const badge = document.getElementById('cartCount');
  if (!badge) return;
  
  cartItems = count;
  badge.textContent = count;
  
  // Mostrar/ocultar badge según la cantidad
  if (count === 0) {
    badge.classList.add('hidden');
  } else {
    badge.classList.remove('hidden');
    // Animar si cambió
    badge.classList.add('pulse-animation');
    setTimeout(() => {
      badge.classList.remove('pulse-animation');
    }, 1000);
  }
}

/**
 * Agrega producto al carrito
 */
async function addToCart(productoId, productName, price) {
  if (!IS_LOGGED) {
    showAdvancedNotification('🔐 Requiere iniciar sesión', 'Inicia sesión para agregar al carrito', 'warning');
    setTimeout(() => { window.location = LOGIN_URL; }, 1500);
    return;
  }

  try {
    const response = await fetch(`${API_CARRITO}/add`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      credentials: 'same-origin',
      body: JSON.stringify({
        producto_id: productoId,
        cantidad: 1
      })
    });

    const data = await response.json();

    if (data.success) {
      updateCartBadge(data.cart_total_items);
      showAdvancedNotification('¡Producto agregado!', data.message || 'El producto se agregó al carrito', 'success');
      showCartNotification(productName, price);
    } else {
      showAdvancedNotification('Error', data.error || 'No se pudo agregar el producto', 'error');
    }
  } catch (error) {
    console.error('Error al agregar al carrito:', error);
    showAdvancedNotification('Error', 'No se pudo agregar el producto', 'error');
  }
}

/**
 * Actualiza visualización del carrito (deprecado - usar backend)
 */
function updateCartDisplay() {
  // Esta función se mantiene por compatibilidad pero ya no se usa
  // El carrito real está en /cart
}

/**
 * Actualiza cantidad de producto (deprecado - usar backend)
 */
function updateQuantity(index, change) {
  // Redirigir al carrito real
  window.location.href = '/cart';
}

/**
 * Elimina producto del carrito (deprecado - usar backend)
 */
function removeFromCart(index) {
  // Redirigir al carrito real
  window.location.href = '/cart';
}

/**
 * Va a la página del carrito
 */
function goToCart() {
  if (!IS_LOGGED) {
    showAdvancedNotification('Inicia sesión', 'Debes iniciar sesión para ver tu carrito', 'warning');
    setTimeout(() => {
      window.location.href = LOGIN_URL;
    }, 1500);
    return;
  }
  
  window.location.href = '/cart';
}

/**
 * Abre modal del carrito (deprecado - redirige a /cart)
 */
function toggleCart() {
  goToCart();
}

/**
 * Cierra modal del carrito (deprecado)
 */
function closeCart() {
  // No hace nada, se mantiene por compatibilidad
}

/**
 * Procede al checkout
 */
function checkout() {
  if (!IS_LOGGED) {
    showAdvancedNotification('🔐 Requiere iniciar sesión', 'Inicia sesión para continuar', 'warning');
    setTimeout(() => { window.location = LOGIN_URL; }, 1500);
    return;
  }

  showAdvancedNotification('Redirigiendo', 'Llevándote al carrito...', 'success');
  
  setTimeout(() => {
    window.location.href = '/cart';
  }, 1000);
}

// ---------- NAVEGACIÓN Y AUTENTICACIÓN ----------

/**
 * Verifica autenticación
 */
function ensureAuth() {
  if (!IS_LOGGED) {
    showAdvancedNotification('🔐 Requiere iniciar sesión', 'Por favor, inicia sesión para continuar', 'warning');
    setTimeout(() => { window.location = LOGIN_URL; }, 1000);
    return false;
  }
  return true;
}

/**
 * Navega a diferentes secciones
 */
function navigateTo(section) {
  const privateSections = new Set(['orders', 'profile', 'settings', 'checkout']);
  if (privateSections.has(section) && !ensureAuth()) return;

  const sections = {
    home: '🏠 Cargando inicio...',
    products: '🛍 Mostrando catálogo completo...',
    orders: '📦 Cargando historial de pedidos...',
    profile: '👤 Abriendo perfil de usuario...',
    settings: '⚙ Configuración del sistema...'
  };

  showAdvancedNotification('Navegando...', sections[section] || 'Cargando sección...', 'info');
  closeUserMenu();

  if (section === 'products') {
    showAllProducts();
    const grid = document.getElementById('recomendadosGrid');
    if (grid) window.scrollTo({ top: grid.offsetTop - 120, behavior: 'smooth' });
  }
}

/**
 * Abre menú de usuario
 */
function showUserMenu() {
  if (!ensureAuth()) return;
  document.getElementById('userMenuModal')?.classList.remove('hidden');
}

/**
 * Cierra menú de usuario
 */
function closeUserMenu() {
  document.getElementById('userMenuModal')?.classList.add('hidden');
}

/**
 * Abre menú mobile
 */
function toggleMobileMenu() {
  const menu = document.getElementById('mobileMenu');
  menu?.classList.toggle('hidden');
}

/**
 * Cierra sesión
 */
async function logout() {
  try {
    showAdvancedNotification('👋 Cerrando sesión...', 'Hasta pronto', 'info');
    const resp = await fetch(LOGOUT_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      credentials: 'same-origin'
    });
    const data = await resp.json().catch(() => ({}));
    
    setTimeout(() => {
      window.location = data.redirect || LOGIN_URL;
    }, 1000);
  } catch (error) {
    console.error('Error en logout:', error);
    setTimeout(() => {
      window.location = LOGIN_URL;
    }, 1000);
  }
}

// ---------- INICIALIZACIÓN ----------

document.addEventListener('DOMContentLoaded', function () {
  console.log('🚀 Inicializando PeakSport...');
  console.log('Usuario logueado:', IS_LOGGED);
  
  // Cargar recomendados
  cargarRecomendados();
  
  // Si está logueado, cargar contador del carrito
  if (IS_LOGGED) {
    loadCartCount();
    // Actualizar cada 30 segundos
    setInterval(loadCartCount, 30000);
  }

  // Mensaje de bienvenida
  setTimeout(() => {
    showAdvancedNotification(
      '🎉 ¡Bienvenido!',
      IS_LOGGED ? 'Tenemos nuevas ofertas para ti' : 'Explora el catálogo y crea tu cuenta',
      'success'
    );
  }, 800);

  // Cerrar modales al hacer clic afuera
  document.addEventListener('click', function (e) {
    if (e.target.id === 'userMenuModal') closeUserMenu();
  });
  
  // Cerrar modales con ESC
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      closeUserMenu();
    }
  });
});

console.log('✅ PeakSport inicializado correctamente');