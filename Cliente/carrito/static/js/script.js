// 🛒 Estado global del carrito
let cartData = {
  items: [
    {
      id: 1,
      name: 'Zapatillas Running Pro',
      brand: 'Nike Air Zoom',
      price: 96.00,
      originalPrice: 120.00,
      quantity: 1,
      image: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=200&h=200&fit=crop',
      size: '42',
      color: 'Negro/Rojo'
    },
    {
      id: 2,
      name: 'Camiseta Dry-Fit',
      brand: 'Adidas Performance',
      price: 35.00,
      originalPrice: null,
      quantity: 2,
      image: 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=200&h=200&fit=crop',
      size: 'L',
      color: 'Azul'
    },
    {
      id: 3,
      name: 'Balón Oficial',
      brand: 'FIFA Approved',
      price: 50.00,
      originalPrice: null,
      quantity: 1,
      image: 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=200&h=200&fit=crop',
      size: '5',
      color: 'Blanco/Negro'
    },
    {
      id: 4,
      name: 'Guantes de Gym',
      brand: 'Premium Grip',
      price: 25.00,
      originalPrice: null,
      quantity: 1,
      image: 'https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=200&h=200&fit=crop',
      size: 'M',
      color: 'Negro'
    }
  ],
  subtotal: 0,
  shipping: 15.00,
  taxes: 0,
  discount: 0,
  total: 0
};

// 🔹 Renderizar productos del carrito
function renderCartItems() {
  const container = document.getElementById('cartItems');
  container.innerHTML = '';
  
  cartData.items.forEach((item, index) => {
    const itemElement = document.createElement('div');
    itemElement.className = 'glass-card rounded-2xl p-6 border border-white/10 card-hover fade-in';
    itemElement.innerHTML = `
      <div class="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-6">
        <div class="flex-shrink-0">
          <img src="${item.image}" alt="${item.name}" class="w-24 h-24 sm:w-32 sm:h-32 rounded-xl object-cover border border-white/20">
        </div>
        <div class="flex-1 space-y-3">
          <div>
            <h4 class="font-bold text-white text-lg">${item.name}</h4>
            <p class="text-gray-400 text-sm">${item.brand}</p>
            <div class="flex space-x-4 text-sm text-gray-500 mt-1">
              <span>Talla: ${item.size}</span>
              <span>Color: ${item.color}</span>
            </div>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
            <div class="flex items-center space-x-3">
              <div class="flex items-center space-x-2">
                <span class="text-xl font-bold text-red-400">$${item.price.toFixed(2)}</span>
                ${item.originalPrice ? `<span class="text-sm text-gray-500 line-through">$${item.originalPrice.toFixed(2)}</span>` : ''}
              </div>
            </div>
            <div class="flex items-center space-x-4">
              <div class="flex items-center space-x-2">
                <button onclick="updateQuantity(${index}, -1)" class="w-10 h-10 glass-card rounded-full flex items-center justify-center hover:bg-white/10 transition-all">
                  <i class="fas fa-minus text-sm text-gray-400"></i>
                </button>
                <input 
                  type="number" 
                  value="${item.quantity}" 
                  min="1" 
                  max="10"
                  class="quantity-input w-16 h-10 rounded-lg text-center text-white font-bold"
                  onchange="setQuantity(${index}, this.value)"
                >
                <button onclick="updateQuantity(${index}, 1)" class="w-10 h-10 glass-card rounded-full flex items-center justify-center hover:bg-white/10 transition-all">
                  <i class="fas fa-plus text-sm text-gray-400"></i>
                </button>
              </div>
              <button onclick="removeItem(${index})" class="w-10 h-10 glass-card rounded-full flex items-center justify-center hover:bg-red-500/20 transition-all group">
                <i class="fas fa-trash text-sm text-gray-400 group-hover:text-red-400"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
    container.appendChild(itemElement);
  });
  
  updateTotals();
}

// 🔹 Actualizar cantidad
function updateQuantity(index, change) {
  const item = cartData.items[index];
  const newQuantity = item.quantity + change;
  
  if (newQuantity <= 0) {
    removeItem(index);
    return;
  }
  
  if (newQuantity > 10) {
    showNotification('Límite alcanzado', 'Máximo 10 unidades por producto', 'warning');
    return;
  }
  
  item.quantity = newQuantity;
  renderCartItems();
  showNotification('Cantidad actualizada', `${item.name} - ${newQuantity} unidades`, 'success');
}

// 🔹 Establecer cantidad manualmente
function setQuantity(index, value) {
  const quantity = parseInt(value);
  if (quantity <= 0) {
    removeItem(index);
    return;
  }
  if (quantity > 10) {
    showNotification('Límite alcanzado', 'Máximo 10 unidades por producto', 'warning');
    return;
  }
  cartData.items[index].quantity = quantity;
  renderCartItems();
}

// 🔹 Eliminar producto
function removeItem(index) {
  const item = cartData.items[index];
  cartData.items.splice(index, 1);
  renderCartItems();
  showNotification('Producto eliminado', `${item.name} removido del carrito`, 'info');
}

// 🔹 Actualizar totales
function updateTotals() {
  cartData.subtotal = cartData.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  cartData.taxes = cartData.subtotal * 0.1;
  cartData.total = cartData.subtotal + cartData.shipping + cartData.taxes - cartData.discount;
  
  document.getElementById('subtotal').textContent = `$${cartData.subtotal.toFixed(2)}`;
  document.getElementById('shipping').textContent = cartData.subtotal >= 100 ? 'GRATIS' : `$${cartData.shipping.toFixed(2)}`;
  document.getElementById('taxes').textContent = `$${cartData.taxes.toFixed(2)}`;
  document.getElementById('total').textContent = `$${cartData.total.toFixed(2)}`;
  
  const totalItems = cartData.items.reduce((sum, item) => sum + item.quantity, 0);
  document.getElementById('itemCount').textContent = `${totalItems} artículo${totalItems !== 1 ? 's' : ''}`;
  
  if (cartData.subtotal >= 100) {
    cartData.shipping = 0;
    cartData.total = cartData.subtotal + cartData.taxes - cartData.discount;
    document.getElementById('total').textContent = `$${cartData.total.toFixed(2)}`;
  }
}

// 🔹 Aplicar cupón
function applyCoupon() {
  const couponCode = document.getElementById('couponCode').value.trim().toUpperCase();
  const validCoupons = {
    'DESCUENTO10': 0.10,
    'WELCOME20': 0.20,
    'SPORT15': 0.15,
    'SAVE25': 0.25
  };
  
  if (validCoupons[couponCode]) {
    cartData.discount = cartData.subtotal * validCoupons[couponCode];
    document.getElementById('discountRow').classList.remove('hidden');
    document.getElementById('discount').textContent = `-$${cartData.discount.toFixed(2)}`;
    document.getElementById('couponCode').value = '';
    updateTotals();
    showNotification('¡Cupón aplicado!', `${(validCoupons[couponCode] * 100)}% de descuento aplicado`, 'success');
  } else if (couponCode) {
    showNotification('Cupón inválido', 'El código ingresado no es válido', 'error');
  } else {
    showNotification('Código requerido', 'Por favor ingresa un código de cupón', 'warning');
  }
}

// 🔹 Acciones principales
function goBack() {
  showNotification('Regresando...', 'Volviendo a la tienda principal', 'info');
  setTimeout(() => window.history.back(), 1000);
}

function continueShopping() {
  showNotification('Redirigiendo...', 'Abriendo catálogo de productos', 'info');
}

function proceedToCheckout() {
  if (cartData.items.length === 0) {
    showNotification('Carrito vacío', 'Agrega productos antes de continuar', 'warning');
    return;
  }
  showNotification('Procesando...', 'Redirigiendo a la página de pago', 'success');
  setTimeout(() => {
    showNotification('¡Éxito!', `Procesando pago de $${cartData.total.toFixed(2)}`, 'success');
  }, 2000);
}

function saveForLater() {
  showNotification('Guardado', 'Carrito guardado en tu lista de deseos', 'success');
}

// 🔹 Sistema de notificaciones
function showNotification(title, message, type = 'info') {
  const notification = document.getElementById('notification');
  const icon = document.getElementById('notificationIcon');
  const titleEl = document.getElementById('notificationTitle');
  const messageEl = document.getElementById('notificationMessage');
  
  const config = {
    success: { icon: 'fas fa-check', color: 'gradient-green', border: 'border-green-500/30' },
    error: { icon: 'fas fa-times', color: 'gradient-bg', border: 'border-red-500/30' },
    warning: { icon: 'fas fa-exclamation', color: 'bg-yellow-500', border: 'border-yellow-500/30' },
    info: { icon: 'fas fa-info', color: 'gradient-blue', border: 'border-blue-500/30' }
  };
  
  const typeConfig = config[type];
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

// 🔹 Inicialización
document.addEventListener('DOMContentLoaded', function() {
  renderCartItems();
  setTimeout(() => {
    showNotification('¡Bienvenido!', 'Revisa y modifica tus productos', 'info');
  }, 500);
});
