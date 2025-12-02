// ---------- Estado global ----------
let cartItems = 0;
let cartTotal = 0.00;
let cartProducts = [];

// ---------- Util ----------
function money(v) {
  const n = Number(v || 0);
  return `$${n.toFixed(2)}`;
}

// ---------- API Productos ----------
async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}

async function cargarRecomendados() {
  try {
    const data = await fetchJSON(`${window.__API_BASE__}/recomendados`);
    const grid = document.getElementById('recomendadosGrid');
    if (!grid) return;

    const items = (data && data.items) ? data.items : [];
    if (!items.length) {
      grid.innerHTML = `
        <div class="col-span-full text-gray-400 text-center glass-card rounded-2xl p-8">
          No hay productos recomendados por ahora.
        </div>`;
      return;
    }
    grid.innerHTML = items.map(cardHtml).join('');
    // animación
    const cards = grid.querySelectorAll('.card-hover');
    cards.forEach((card, index) => {
      card.style.animationDelay = `${index * 0.06}s`;
      card.classList.add('slide-in');
    });
  } catch (e) {
    console.error(e);
    showAdvancedNotification('⚠️ Error', 'No se pudieron cargar los recomendados', 'error');
  }
}

async function showAllProducts(page = 1, perPage = 12) {
  try {
    showAdvancedNotification('🛍️ Catálogo', 'Cargando productos...', 'info');
    const data = await fetchJSON(`${window.__API_BASE__}/todos?page=${page}&per_page=${perPage}`);
    const grid = document.getElementById('recomendadosGrid'); // reutilizamos grid
    if (!grid) return;
    const items = (data && data.items) ? data.items : [];
    grid.innerHTML = items.map(cardHtml).join('');
    showAdvancedNotification('✅ Listo', `Mostrando ${items.length} de ${data.total}`, 'success');
  } catch (e) {
    console.error(e);
    showAdvancedNotification('⚠️ Error', 'No se pudo cargar el catálogo', 'error');
  }
}

function cardHtml(p) {
  const price = (p.price ?? 0).toFixed(2);
  const img = p.image || 'https://via.placeholder.com/300x300?text=PeakSport';
  const rating = (p.rating ?? 4.7).toFixed(1);

  return `
    <div class="glass-card rounded-3xl card-hover p-7 border border-white/10 group">
      <div class="relative mb-6 overflow-hidden rounded-xl">
        <img src="${img}" class="w-full h-48 object-cover group-hover:scale-110 transition-transform duration-500" alt="${p.name}">
        <div class="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
      </div>
      <h4 class="font-bold text-xl mb-2 text-white group-hover:text-red-400 transition-colors">${p.name}</h4>
      <p class="text-gray-400 text-sm mb-4">${p.currency || 'COP'}</p>
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center space-x-2">
          <span class="text-2xl font-bold text-red-400">${money(p.price)}</span>
        </div>
        <div class="flex items-center space-x-1">
          <i class="fas fa-star text-yellow-400 text-sm"></i>
          <span class="text-sm text-gray-400 ml-1">${rating}</span>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <button class="w-full glass-card text-white py-3 rounded-xl hover:bg-white/10 transition-all font-medium"
                onclick="verDetalle('${p.slug}')">
          Ver
        </button>
        <button class="w-full gradient-bg text-white py-3 rounded-xl hover:scale-105 transition-all font-medium elegant-shadow"
                onclick="addToCart('${p.name.replace(/'/g, "\\'")}', ${p.price || 0})">
          <i class="fas fa-cart-plus mr-2"></i> Agregar
        </button>
      </div>
    </div>`;
}

async function verDetalle(slug) {
  try {
    const data = await fetchJSON(`${window.__API_BASE__}/${slug}`);
    showAdvancedNotification('🔍 Detalle', `${data.name} • ${money(data.price)}`, 'info');
    // Aquí puedes abrir modal de detalle o navegar a una vista específica si la creas.
  } catch (e) {
    console.error(e);
    showAdvancedNotification('⚠️ Error', 'Producto no encontrado', 'error');
  }
}

// ---------- Carrito ----------
function addToCart(productName, price) {
  if (!window.__LOGGED__) {
    showAdvancedNotification('🔐 Requiere iniciar sesión', 'Inicia sesión para agregar al carrito', 'warning');
    setTimeout(() => { window.location = "/login/"; }, 900);
    return;
  }

  cartItems++;
  cartTotal += Number(price || 0);

  const existingProduct = cartProducts.find(p => p.name === productName);
  if (existingProduct) {
    existingProduct.quantity++;
  } else {
    cartProducts.push({
      name: productName,
      price: Number(price || 0),
      quantity: 1,
      image: getProductImage(productName)
    });
  }

  const cartCount = document.getElementById('cartCount');
  if (cartCount) {
    cartCount.textContent = cartItems;
    cartCount.classList.add('pulse-animation');
    setTimeout(() => cartCount.classList.remove('pulse-animation'), 1000);
  }

  showNotification(productName, Number(price || 0));
  updateCartDisplay();
}

function getProductImage(productName) {
  // puedes mapear por slug si quieres; por ahora placeholder
  return 'https://via.placeholder.com/100';
}

function showNotification(productName, price) {
  const notification = document.getElementById('cartNotification');
  const message = document.getElementById('cartMessage');
  const subMessage = document.getElementById('cartSubMessage');

  if (!notification || !message || !subMessage) return;

  message.textContent = `${productName}`;
  subMessage.textContent = `${money(price)} • Agregado al carrito`;

  notification.classList.remove('translate-x-full');

  setTimeout(() => {
    notification.classList.add('translate-x-full');
  }, 4000);
}

function toggleCart() {
  document.getElementById('cartModal')?.classList.remove('hidden');
  updateCartDisplay();
}

function closeCart() {
  document.getElementById('cartModal')?.classList.add('hidden');
}

function updateCartDisplay() {
  const cartItemsContainer = document.getElementById('cartItems');
  const cartTotalElement = document.getElementById('cartTotal');
  if (!cartItemsContainer || !cartTotalElement) return;

  cartItemsContainer.innerHTML = '';

  cartProducts.forEach((product, index) => {
    const itemElement = document.createElement('div');
    itemElement.className = 'glass-card rounded-xl p-4 flex items-center space-x-4';
    itemElement.innerHTML = `
      <img src="${product.image}" alt="${product.name}" class="w-16 h-16 rounded-lg object-cover">
      <div class="flex-1">
        <h4 class="font-bold text-white">${product.name}</h4>
        <p class="text-gray-400">${money(product.price)} c/u</p>
      </div>
      <div class="flex items-center space-x-3">
        <button class="w-8 h-8 glass-card rounded-full flex items-center justify-center hover:bg-white/10 transition-all" onclick="updateQuantity(${index}, -1)">
          <i class="fas fa-minus text-sm text-gray-400"></i>
        </button>
        <span class="text-white font-bold w-8 text-center">${product.quantity}</span>
        <button class="w-8 h-8 glass-card rounded-full flex items-center justify-center hover:bg-white/10 transition-all" onclick="updateQuantity(${index}, 1)">
          <i class="fas fa-plus text-sm text-gray-400"></i>
        </button>
        <button class="w-8 h-8 glass-card rounded-full flex items-center justify-center hover:bg-red-500/20 transition-all ml-4" onclick="removeFromCart(${index})">
          <i class="fas fa-trash text-sm text-red-400"></i>
        </button>
      </div>
    `;
    cartItemsContainer.appendChild(itemElement);
  });

  cartTotalElement.textContent = money(cartTotal);
}

function updateQuantity(index, change) {
  const product = cartProducts[index];
  const newQuantity = product.quantity + change;

  if (newQuantity <= 0) {
    removeFromCart(index);
    return;
  }

  cartTotal += product.price * change;
  cartItems += change;
  product.quantity = newQuantity;

  const cartCount = document.getElementById('cartCount');
  if (cartCount) cartCount.textContent = cartItems;

  updateCartDisplay();
}

function removeFromCart(index) {
  const product = cartProducts[index];
  cartTotal -= product.price * product.quantity;
  cartItems -= product.quantity;
  cartProducts.splice(index, 1);

  const cartCount = document.getElementById('cartCount');
  if (cartCount) cartCount.textContent = cartItems;

  updateCartDisplay();
}

function checkout() {
  if (!window.__LOGGED__) {
    showAdvancedNotification('🔐 Requiere iniciar sesión', 'Inicia sesión para pagar', 'warning');
    return;
  }
  showAdvancedNotification('🎉 Procesando pago...', 'Redirigiendo a la pasarela de pago segura', 'success');
  setTimeout(() => {
    showAdvancedNotification('✅ ¡Compra exitosa!', `Total: ${money(cartTotal)} • Gracias por tu compra`, 'success');
  }, 2000);
}

// ---------- Navegación / Modales ----------
function ensureAuth() {
  if (!window.__LOGGED__) {
    showAdvancedNotification('🔐 Requiere iniciar sesión', 'Por favor, inicia sesión para continuar', 'warning');
    setTimeout(() => { window.location = "{{ url_for('login.vista_pantalla_login') }}"; }, 1000);
    return false;
  }
  return true;
}

function navigateTo(section) {
  const privateSections = new Set(['orders', 'profile', 'settings', 'checkout']);
  if (privateSections.has(section) && !ensureAuth()) return;

  const sections = {
    home: '🏠 Cargando inicio...',
    products: '🛍️ Mostrando catálogo completo...',
    orders: '📦 Cargando historial de pedidos...',
    profile: '👤 Abriendo perfil de usuario...',
    settings: '⚙️ Configuración del sistema...'
  };

  showAdvancedNotification('Navegando...', sections[section] || 'Cargando sección...', 'info');
  closeUserMenu();

  if (section === 'products') {
    showAllProducts(); // reutiliza el grid para catálogo completo
    window.scrollTo({ top: document.getElementById('recomendadosGrid').offsetTop - 120, behavior: 'smooth' });
  }
}

function showUserMenu() {
  if (!window.__LOGGED__) { ensureAuth(); return; }
  document.getElementById('userMenuModal')?.classList.remove('hidden');
}

function closeUserMenu() {
  document.getElementById('userMenuModal')?.classList.add('hidden');
}

async function logout() {
  try {
    showAdvancedNotification('👋 Cerrando sesión...', 'Hasta pronto', 'info');
    const resp = await fetch('/auth/logout', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
    const data = await resp.json();
    if (data && data.redirect) {
      window.location = data.redirect;
    } else {
      window.location.reload();
    }
  } catch (e) {
    window.location.reload();
  }
}

function toggleMobileMenu() {
  const menu = document.getElementById('mobileMenu');
  menu?.classList.toggle('hidden');
}

// ---------- Sistema de notificaciones ----------
function showAdvancedNotification(title, message, type = 'info') {
  const notification = document.createElement('div');
  const colors = {
    success: 'border-green-500/30 bg-green-500/10',
    error:   'border-red-500/30 bg-red-500/10',
    info:    'border-blue-500/30 bg-blue-500/10',
    warning: 'border-yellow-500/30 bg-yellow-500/10'
  };
  const icons = {
    success: 'fas fa-check-circle text-green-400',
    error:   'fas fa-exclamation-circle text-red-400',
    info:    'fas fa-info-circle text-blue-400',
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
    setTimeout(() => { notification.parentNode && notification.parentNode.removeChild(notification); }, 500);
  }, 4000);
}

// ---------- Inicialización ----------
document.addEventListener('DOMContentLoaded', function () {
  // Render inicial del carrito
  const cartCount = document.getElementById('cartCount');
  if (cartCount) cartCount.textContent = cartItems;
  updateCartDisplay();

  // Cargar recomendados de la API
  cargarRecomendados();

  // Mensaje de bienvenida
  setTimeout(() => {
    showAdvancedNotification('🎉 ¡Bienvenido!', window.__LOGGED__ ? 'Tenemos nuevas ofertas para ti' : 'Explora el catálogo y crea tu cuenta', 'success');
  }, 800);

  // Cerrar modales al hacer clic afuera
  document.addEventListener('click', function (e) {
    if (e.target.id === 'userMenuModal') closeUserMenu();
    if (e.target.id === 'cartModal') closeCart();
  });
});
