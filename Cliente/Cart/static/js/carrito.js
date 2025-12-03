// =======================================
// carrito.js - Lógica del carrito CORREGIDA
// =======================================

const CART_API = "/cart/api/cart";

/**
 * Carga el carrito desde la BD
 */
async function cargarCarrito() {
  try {
    const response = await fetch(CART_API, {
      credentials: 'same-origin'
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    if (!data.success) {
      mostrarCarritoVacio();
      return;
    }
    
    const cart = data.cart;
    const totales = data.totales;
    
    if (!cart.items || cart.items.length === 0) {
      mostrarCarritoVacio();
      return;
    }
    
    renderizarItems(cart.items, totales);
    ocultarCargando();
    
  } catch (error) {
    console.error('Error cargando carrito:', error);
    mostrarCarritoVacio();
    showNotification('Error', 'No se pudo cargar el carrito', 'error');
  }
}

/**
 * Renderiza los items del carrito
 */
function renderizarItems(items, totales) {
  const cartItemsContainer = document.getElementById('cartItems');
  cartItemsContainer.innerHTML = '';
  
  items.forEach((item) => {
    // ✅ CORREGIDO: El campo correcto es precio_unitario (ya viene en formato decimal desde la API)
    const precioUnitario = parseFloat(item.precio_unitario) || 0;
    const subtotal = item.cantidad * precioUnitario;
    
    console.log('🔍 DEBUG Item:', {
      id: item.id,
      nombre: item.producto?.nombre,
      item_completo: item,
      precioUnitario: precioUnitario,
      cantidad: item.cantidad,
      subtotal: subtotal
    });
    
    // ✅ CORREGIDO: Acceder correctamente a las imágenes
    let img = 'https://via.placeholder.com/200?text=Producto';
    if (item.producto?.imagenes && item.producto.imagenes.length > 0) {
      img = item.producto.imagenes[0].url || img;
    }
    
    const nombreProducto = item.producto?.nombre || 'Producto sin nombre';
    const descripcion = item.producto?.descripcion || '';
    
    const itemDiv = document.createElement('div');
    itemDiv.className = 'glass-card rounded-2xl p-4 sm:p-6 border border-white/10 fade-in';
    itemDiv.innerHTML = `
      <div class="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-6">
        <div class="flex-shrink-0">
          <img src="${img}" 
               alt="${nombreProducto}" 
               class="w-20 h-20 sm:w-24 sm:h-24 rounded-lg object-cover border border-white/20" 
               onerror="this.src='https://via.placeholder.com/100?text=Imagen+no+disponible'">
        </div>
        
        <div class="flex-1 space-y-2">
          <div>
            <h4 class="font-bold text-white text-sm sm:text-base">${nombreProducto}</h4>
            ${descripcion ? `<p class="text-gray-400 text-xs sm:text-sm line-clamp-2">${descripcion}</p>` : ''}
          </div>
          
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0">
            <div class="flex items-center space-x-3">
              <div class="text-sm text-gray-400">Precio:</div>
              <div class="text-lg font-bold text-red-400">$${precioUnitario.toFixed(2)}</div>
            </div>
            
            <div class="flex items-center space-x-3">
              <div class="flex items-center space-x-2 glass-card rounded-lg px-3 py-2">
                <button onclick="updateItemQuantity(${item.id}, ${item.cantidad - 1})" 
                        class="w-7 h-7 glass-card rounded-full flex items-center justify-center hover:bg-white/10 transition-all">
                  <i class="fas fa-minus text-xs text-gray-400"></i>
                </button>
                <span class="text-white font-bold w-8 text-center text-sm">${item.cantidad}</span>
                <button onclick="updateItemQuantity(${item.id}, ${item.cantidad + 1})" 
                        class="w-7 h-7 glass-card rounded-full flex items-center justify-center hover:bg-white/10 transition-all">
                  <i class="fas fa-plus text-xs text-gray-400"></i>
                </button>
              </div>
              
              <button onclick="removeItemFromCart(${item.id})" 
                      class="w-8 h-8 glass-card rounded-full flex items-center justify-center hover:bg-red-500/20 transition-all"
                      title="Eliminar producto">
                <i class="fas fa-trash text-xs text-gray-400 hover:text-red-400"></i>
              </button>
            </div>
          </div>
          
          <div class="flex justify-between items-center pt-2 border-t border-white/10">
            <span class="text-sm text-gray-400">Subtotal:</span>
            <span class="text-xl font-bold text-white">${subtotal.toFixed(2)}</span>
          </div>
        </div>
      </div>
    `;
    cartItemsContainer.appendChild(itemDiv);
  });
  
  // Actualizar totales
  actualizarTotales(totales);
  
  document.getElementById('emptyCart').classList.add('hidden');
  document.getElementById('continueShoppingSection').classList.remove('hidden');
  
  const totalItems = totales.total_items || items.length;
  document.getElementById('itemCount').textContent = `${totalItems} artículo${totalItems !== 1 ? 's' : ''}`;
}

/**
 * Actualiza los totales mostrados
 */
function actualizarTotales(totales) {
  const subtotal = totales.subtotal || 0;
  const envio = totales.envio || 0;
  const impuestos = totales.impuestos || 0;
  const total = totales.total || 0;
  const envioGratis = totales.envio_gratis || false;
  
  document.getElementById('subtotal').textContent = `$${subtotal.toFixed(2)}`;
  document.getElementById('shipping').textContent = envioGratis ? 'GRATIS 🎉' : `$${envio.toFixed(2)}`;
  document.getElementById('taxes').textContent = `$${impuestos.toFixed(2)}`;
  document.getElementById('total').textContent = `$${total.toFixed(2)}`;
}

/**
 * Muestra el carrito vacío
 */
function mostrarCarritoVacio() {
  document.getElementById('loadingSpinner').classList.add('hidden');
  document.getElementById('emptyCart').classList.remove('hidden');
  document.getElementById('cartItems').innerHTML = '';
  document.getElementById('continueShoppingSection').classList.add('hidden');
  document.getElementById('itemCount').textContent = '0 artículos';
  
  // Resetear totales
  document.getElementById('subtotal').textContent = '$0.00';
  document.getElementById('shipping').textContent = '$0.00';
  document.getElementById('taxes').textContent = '$0.00';
  document.getElementById('total').textContent = '$0.00';
}

/**
 * Oculta el spinner de carga
 */
function ocultarCargando() {
  document.getElementById('loadingSpinner').classList.add('hidden');
}

/**
 * Actualiza la cantidad de un item
 */
async function updateItemQuantity(itemId, newQuantity) {
  if (newQuantity <= 0) {
    removeItemFromCart(itemId);
    return;
  }
  
  try {
    const response = await fetch(`/cart/api/cart/update/${itemId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ cantidad: newQuantity })
    });
    
    const data = await response.json();
    
    if (data.success) {
      await cargarCarrito();
      showNotification('✅ Actualizado', `Cantidad modificada a ${newQuantity}`, 'success');
    } else {
      showNotification('❌ Error', data.error || 'No se pudo actualizar la cantidad', 'error');
    }
  } catch (error) {
    console.error('Error actualizando cantidad:', error);
    showNotification('❌ Error', 'No se pudo actualizar la cantidad', 'error');
  }
}

/**
 * Elimina un item del carrito
 */
async function removeItemFromCart(itemId) {
  if (!confirm('¿Eliminar este producto del carrito?')) {
    return;
  }
  
  try {
    const response = await fetch(`/cart/api/cart/remove/${itemId}`, {
      method: 'DELETE',
      credentials: 'same-origin'
    });
    
    const data = await response.json();
    
    if (data.success) {
      showNotification('✅ Eliminado', 'Producto removido del carrito', 'success');
      await cargarCarrito();
    } else {
      showNotification('❌ Error', data.error || 'No se pudo eliminar el producto', 'error');
    }
  } catch (error) {
    console.error('Error eliminando producto:', error);
    showNotification('❌ Error', 'No se pudo eliminar el producto', 'error');
  }
}

/**
 * Vacía el carrito completo
 */
async function clearCart() {
  if (!confirm('¿Estás seguro de que deseas vaciar el carrito completamente?')) {
    return;
  }
  
  try {
    const response = await fetch(`${CART_API}/clear`, {
      method: 'DELETE',
      credentials: 'same-origin'
    });
    
    const data = await response.json();
    
    if (data.success) {
      showNotification('✅ Carrito vaciado', 'Se han removido todos los productos', 'success');
      await cargarCarrito();
    } else {
      showNotification('❌ Error', data.error || 'No se pudo vaciar el carrito', 'error');
    }
  } catch (error) {
    console.error('Error vaciando carrito:', error);
    showNotification('❌ Error', 'No se pudo vaciar el carrito', 'error');
  }
}

/**
 * Procede al checkout
 */
function proceedToCheckout() {
  const total = document.getElementById('total').textContent;
  showNotification('🎉 Procesando...', `Redirigiendo a pago - ${total}`, 'info');
  
  setTimeout(() => {
    // Aquí redirigirías a tu página de checkout real
    window.location.href = '/checkout';
  }, 1500);
}

/**
 * Muestra una notificación
 */
function showNotification(title, message, type = 'info') {
  const notification = document.getElementById('notification');
  const icon = document.getElementById('notificationIcon');
  const titleEl = document.getElementById('notificationTitle');
  const messageEl = document.getElementById('notificationMessage');
  
  const styles = {
    success: {
      icon: 'fas fa-check-circle text-green-400',
      bg: 'gradient-green',
      border: 'border-green-500/30'
    },
    error: {
      icon: 'fas fa-exclamation-circle text-red-400',
      bg: 'gradient-bg',
      border: 'border-red-500/30'
    },
    info: {
      icon: 'fas fa-info-circle text-blue-400',
      bg: 'gradient-blue',
      border: 'border-blue-500/30'
    },
    warning: {
      icon: 'fas fa-exclamation-triangle text-yellow-400',
      bg: 'gradient-purple',
      border: 'border-yellow-500/30'
    }
  };
  
  const style = styles[type] || styles.info;
  
  // Actualizar icono y estilos
  icon.className = `w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${style.bg}`;
  icon.innerHTML = `<i class="${style.icon}"></i>`;
  
  notification.className = `fixed top-24 right-4 sm:right-6 glass-card text-white px-4 sm:px-6 py-4 rounded-2xl shadow-2xl transform translate-x-full transition-all duration-500 z-50 border ${style.border} elegant-shadow max-w-sm`;
  
  titleEl.textContent = title;
  messageEl.textContent = message;
  
  // Mostrar notificación
  setTimeout(() => {
    notification.classList.remove('translate-x-full');
  }, 100);
  
  // Ocultar después de 4 segundos
  setTimeout(() => {
    notification.classList.add('translate-x-full');
  }, 4000);
}

/**
 * Inicialización cuando carga la página
 */
document.addEventListener('DOMContentLoaded', () => {
  console.log('🛒 Cargando carrito de compras...');
  
  cargarCarrito();
  
  setTimeout(() => {
    showNotification('¡Bienvenido! 👋', 'Revisa y modifica tus productos', 'info');
  }, 500);
});