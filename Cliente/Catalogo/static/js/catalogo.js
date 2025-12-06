// =======================================
// catalogo.js - CATÁLOGO PEAKSPORT CORREGIDO
// =======================================

// ========== VARIABLES GLOBALES ==========
let currentCategory = 'all';
let allProducts = []; // ✅ Guardamos TODOS los productos
let filteredProducts = []; // ✅ Productos después de filtrar
let cartItems = 0;
let gridColumns = 3;
let currentPage = 1;
let totalPages = 1;
let isLoading = false;

const PRODUCTOS_POR_PAGINA = 12;
const API_BASE = "/catalogo/api";

// ========== FUNCIONES UTILITARIAS ==========

function formatearPrecio(precio) {
  return `$${Math.round(precio).toLocaleString('es-CO')}`;
}

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
    console.error(`Error en ${url}:`, error);
    throw error;
  }
}

function showNotification(title, message, type = 'info') {
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
  setTimeout(() => notification.classList.remove('translate-x-full'), 100);
  setTimeout(() => {
    notification.classList.add('translate-x-full');
    setTimeout(() => notification.remove(), 500);
  }, 4000);
}

// ========== GESTIÓN DE PRODUCTOS ==========

async function cargarProductos(page = 1, aplicarFiltros = false) {
  if (isLoading) return;
  
  try {
    isLoading = true;
    mostrarCargando();
    
    let url;
    const params = new URLSearchParams({
      page: page,
      per_page: PRODUCTOS_POR_PAGINA
    });

    // ✅ CORREGIDO: Decidir qué endpoint usar
    if (currentCategory !== 'all') {
      url = `${API_BASE}/categorias/${currentCategory}/productos?${params}`;
    } else {
      url = `${API_BASE}/productos/list?${params}`;
    }

    const data = await fetchJSON(url);
    
    if (!data.success) {
      throw new Error(data.error || 'Error cargando productos');
    }

    // ✅ Guardamos los productos originales
    allProducts = data.productos || [];
    currentPage = data.page || 1;
    totalPages = data.total_pages || 1;
    
    // ✅ Si hay filtros activos, aplicarlos
    if (aplicarFiltros) {
      aplicarFiltrosLocales();
    } else {
      filteredProducts = [...allProducts];
    }
    
    renderizarProductos();
    renderizarPaginacion();
    actualizarContador();
    
  } catch (error) {
    console.error('Error al cargar productos:', error);
    showNotification('Error', 'No se pudieron cargar los productos', 'error');
    mostrarError('Error cargando productos. Intenta nuevamente.');
  } finally {
    isLoading = false;
  }
}

async function cargarCategorias() {
  try {
    const data = await fetchJSON(`${API_BASE}/categorias`);
    
    if (!data.success) return;
    
    const lista = document.getElementById('categoriesList');
    if (!lista) return;
    
    lista.innerHTML = (data.categorias || []).map(cat => `
      <button 
        onclick="filterByCategory(${cat.id}, '${cat.nombre}')" 
        class="category-btn w-full text-left px-4 py-3 rounded-xl transition-all hover:bg-white/10 text-gray-300"
        data-category-id="${cat.id}">
        <i class="fas fa-tag mr-3"></i>${cat.nombre}
        <span class="text-xs text-gray-500 ml-2">(${cat.cantidad_productos || 0})</span>
      </button>
    `).join('');
    
  } catch (error) {
    console.error('Error cargando categorías:', error);
  }
}

function renderizarProductos() {
  const contenedor = document.getElementById('productsGrid');
  if (!contenedor) return;

  // Animación de salida
  contenedor.classList.add('fade-out');

  setTimeout(() => {
    if (filteredProducts.length === 0) {
      contenedor.innerHTML = `
        <div class="col-span-full text-center glass-card rounded-2xl p-12">
          <i class="fas fa-box-open text-6xl text-gray-600 mb-4"></i>
          <h3 class="text-2xl font-bold text-gray-400 mb-2">No hay productos</h3>
          <p class="text-gray-500">Intenta con otros filtros</p>
          <button onclick="clearFilters()" class="mt-4 gradient-bg text-white px-6 py-3 rounded-xl hover:scale-105 transition-all">
            <i class="fas fa-refresh mr-2"></i>Limpiar filtros
          </button>
        </div>`;
      
      document.getElementById('productCount').textContent = '0 productos encontrados';
      contenedor.classList.remove('fade-out');
      contenedor.classList.add('fade-in');
      return;
    }

  const gridClasses = {
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
  };
  contenedor.className = `grid ${gridClasses[gridColumns]} gap-6`;

  contenedor.innerHTML = filteredProducts.map((p, index) => {
    const imagen = p.imagen?.url || 'https://via.placeholder.com/300x300?text=PeakSport';
    
    return `
      <div class="glass-card rounded-3xl card-hover p-7 border border-white/10 group fade-in" style="animation-delay: ${index * 0.06}s">
        <div class="relative mb-6 overflow-hidden rounded-xl">
          <img src="${imagen}" 
               class="w-full h-48 object-cover group-hover:scale-110 transition-transform duration-500" 
               alt="${p.nombre}" 
               onerror="this.src='https://via.placeholder.com/300x300?text=PeakSport'">
          <div class="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          ${p.stock < 10 && p.stock > 0 ? `
            <div class="absolute top-3 right-3 bg-yellow-500 text-black text-xs font-bold px-3 py-1 rounded-full">
              ¡Últimas ${p.stock}!
            </div>
          ` : ''}
          ${p.stock === 0 ? `
            <div class="absolute top-3 right-3 bg-red-500 text-white text-xs font-bold px-3 py-1 rounded-full">
              Agotado
            </div>
          ` : ''}
        </div>
        <h4 class="font-bold text-xl mb-2 text-white group-hover:text-red-400 transition-colors line-clamp-2">${p.nombre}</h4>
        <p class="text-gray-400 text-sm mb-4 line-clamp-2">${p.descripcion || 'Producto de alta calidad'}</p>
        <div class="flex items-center justify-between mb-6">
          <span class="text-2xl font-bold text-red-400">${formatearPrecio(p.precio_actual)}</span>
          <div class="flex items-center space-x-1">
            <i class="fas fa-star text-yellow-400 text-sm"></i>
            <span class="text-sm text-gray-400">4.5</span>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <button 
            onclick="verDetalle('${p.slug}')"
            class="w-full glass-card text-white py-3 rounded-xl hover:bg-white/10 transition-all font-medium">
            Ver
          </button>
          <button 
            class="w-full gradient-bg text-white py-3 rounded-xl hover:scale-105 transition-all font-medium elegant-shadow ${p.stock === 0 ? 'opacity-50 cursor-not-allowed' : ''}" 
            onclick="addToCart(${p.id}, '${p.nombre.replace(/'/g, "\\'")}', ${p.precio_actual})"
            ${p.stock === 0 ? 'disabled' : ''}>
            <i class="fas fa-cart-plus mr-2"></i>${p.stock === 0 ? 'Agotado' : 'Agregar'}
          </button>
        </div>
      </div>`;
  }).join('');

  // Animación de entrada
  contenedor.classList.remove('fade-out');
  contenedor.classList.add('fade-in');

  document.getElementById('productCount').textContent = 
    `${filteredProducts.length} productos encontrados`;
  }, 200);
}

function renderizarPaginacion() {
  const contenedor = document.getElementById('paginationContainer');
  if (!contenedor) return;

  // Si solo hay una página, ocultar paginación
  if (totalPages <= 1) {
    contenedor.innerHTML = '';
    contenedor.classList.add('hidden');
    return;
  }

  contenedor.classList.remove('hidden');

  // Calcular rango de páginas a mostrar
  const maxButtons = 5;
  let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
  let endPage = Math.min(totalPages, startPage + maxButtons - 1);

  // Ajustar si estamos cerca del final
  if (endPage - startPage < maxButtons - 1) {
    startPage = Math.max(1, endPage - maxButtons + 1);
  }

  let html = `
    <div class="flex items-center justify-center space-x-2 mt-8">
      <!-- Botón Anterior -->
      <button 
        onclick="cambiarPagina(${currentPage - 1})"
        ${currentPage === 1 ? 'disabled' : ''}
        class="glass-card px-4 py-2 rounded-xl hover:bg-white/10 transition-all flex items-center space-x-2 ${currentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'}">
        <i class="fas fa-chevron-left text-gray-300"></i>
        <span class="text-gray-300 hidden sm:inline">Anterior</span>
      </button>

      <!-- Primera página si no está en el rango -->
      ${startPage > 1 ? `
        <button 
          onclick="cambiarPagina(1)"
          class="glass-card px-4 py-2 rounded-xl hover:bg-white/10 transition-all text-gray-300 hover:scale-105">
          1
        </button>
        ${startPage > 2 ? '<span class="text-gray-500 px-2">...</span>' : ''}
      ` : ''}

      <!-- Botones de página -->
      ${Array.from({ length: endPage - startPage + 1 }, (_, i) => {
        const pageNum = startPage + i;
        const isActive = pageNum === currentPage;
        return `
          <button 
            onclick="cambiarPagina(${pageNum})"
            class="${isActive ? 'gradient-bg' : 'glass-card hover:bg-white/10'} px-4 py-2 rounded-xl transition-all text-white ${isActive ? 'scale-110 font-bold elegant-shadow' : 'hover:scale-105'}">
            ${pageNum}
          </button>
        `;
      }).join('')}

      <!-- Última página si no está en el rango -->
      ${endPage < totalPages ? `
        ${endPage < totalPages - 1 ? '<span class="text-gray-500 px-2">...</span>' : ''}
        <button 
          onclick="cambiarPagina(${totalPages})"
          class="glass-card px-4 py-2 rounded-xl hover:bg-white/10 transition-all text-gray-300 hover:scale-105">
          ${totalPages}
        </button>
      ` : ''}

      <!-- Botón Siguiente -->
      <button 
        onclick="cambiarPagina(${currentPage + 1})"
        ${currentPage === totalPages ? 'disabled' : ''}
        class="glass-card px-4 py-2 rounded-xl hover:bg-white/10 transition-all flex items-center space-x-2 ${currentPage === totalPages ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'}">
        <span class="text-gray-300 hidden sm:inline">Siguiente</span>
        <i class="fas fa-chevron-right text-gray-300"></i>
      </button>
    </div>

    <!-- Información de página -->
    <div class="text-center mt-4 text-gray-400 text-sm">
      Página ${currentPage} de ${totalPages} 
      <span class="hidden sm:inline">
        (${filteredProducts.length} de ${allProducts.length} productos)
      </span>
    </div>
  `;

  contenedor.innerHTML = html;
}

function cambiarPagina(nuevaPagina) {
  if (nuevaPagina < 1 || nuevaPagina > totalPages || nuevaPagina === currentPage) {
    return;
  }

  // Scroll suave hacia arriba
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });

  // Cargar nueva página
  cargarProductos(nuevaPagina, true);
}

function mostrarCargando() {
  const contenedor = document.getElementById('productsGrid');
  if (contenedor) {
    contenedor.innerHTML = `
      <div class="col-span-full flex flex-col items-center justify-center py-20">
        <div class="animate-spin rounded-full h-16 w-16 border-b-4 border-red-500 mb-4"></div>
        <p class="text-gray-400 text-lg">Cargando productos...</p>
      </div>`;
  }
}

function mostrarError(mensaje) {
  const contenedor = document.getElementById('productsGrid');
  if (contenedor) {
    contenedor.innerHTML = `
      <div class="col-span-full text-center py-12 glass-card rounded-2xl p-8">
        <svg class="mx-auto h-16 w-16 text-red-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 class="text-2xl font-bold text-white mb-2">Error</h3>
        <p class="text-gray-400 mb-4">${mensaje}</p>
        <button onclick="cargarProductos(1)" class="gradient-bg text-white px-6 py-3 rounded-xl hover:scale-105 transition-all">
          <i class="fas fa-refresh mr-2"></i>Reintentar
        </button>
      </div>`;
  }
}

// ========== FILTROS Y BÚSQUEDA ==========

function filterByCategory(categoryId, categoryName = '') {
  currentCategory = categoryId;
  currentPage = 1;
  
  // Actualizar UI de categorías
  document.querySelectorAll('.category-btn').forEach(btn => {
    btn.classList.remove('category-active');
    btn.classList.add('text-gray-300');
  });
  
  const activeBtn = document.querySelector(`[data-category-id="${categoryId}"]`) || 
                    document.querySelector('.category-btn');
  if (activeBtn) {
    activeBtn.classList.add('category-active');
    activeBtn.classList.remove('text-gray-300');
  }
  
  // Actualizar título
  document.getElementById('categoryTitle').textContent = 
    categoryId === 'all' ? 'Todos los productos' : categoryName || 'Categoría';
  
  cargarProductos(1);
}

// ✅ CORREGIDO: Aplicar filtros locales sin mutar allProducts
function aplicarFiltrosLocales() {
  const searchTerm = (document.getElementById('searchInput')?.value || '').toLowerCase().trim();
  const minPrice = parseFloat(document.getElementById('minPrice')?.value) || 0;
  const maxPrice = parseFloat(document.getElementById('maxPrice')?.value) || Infinity;
  
  filteredProducts = allProducts.filter(p => {
    const matchesSearch = !searchTerm || p.nombre.toLowerCase().includes(searchTerm);
    const matchesPrice = p.precio_actual >= minPrice && p.precio_actual <= maxPrice;
    return matchesSearch && matchesPrice;
  });
}

// ✅ Nueva función para búsqueda con API
async function buscarProductos() {
  const searchTerm = (document.getElementById('searchInput')?.value || '').trim();
  
  if (searchTerm.length < 2) {
    // Si no hay búsqueda, volver a cargar todos
    currentCategory = 'all';
    cargarProductos(1);
    return;
  }
  
  try {
    mostrarCargando();
    const params = new URLSearchParams({
      q: searchTerm,
      page: 1,
      per_page: PRODUCTOS_POR_PAGINA
    });
    
    const data = await fetchJSON(`${API_BASE}/productos/buscar?${params}`);
    
    if (data.success) {
      allProducts = data.productos || [];
      filteredProducts = [...allProducts];
      currentPage = 1;
      totalPages = data.total_pages || 1;
      renderizarProductos();
      
      document.getElementById('categoryTitle').textContent = 
        `Resultados para "${searchTerm}"`;
    }
  } catch (error) {
    console.error('Error en búsqueda:', error);
    showNotification('Error', 'No se pudo realizar la búsqueda', 'error');
  }
}

// Debounce para la búsqueda
let searchTimeout;
function filterProducts() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    const searchTerm = document.getElementById('searchInput')?.value || '';
    
    if (searchTerm.length >= 2) {
      buscarProductos();
    } else if (searchTerm.length === 0) {
      aplicarFiltrosLocales();
      renderizarProductos();
    }
  }, 500);
}

function sortProducts() {
  const sortBy = document.getElementById('sortSelect')?.value || 'name';
  
  // ✅ Ordenar filteredProducts, no allProducts
  filteredProducts.sort((a, b) => {
    switch(sortBy) {
      case 'name':
        return a.nombre.localeCompare(b.nombre);
      case 'price-low':
        return a.precio_actual - b.precio_actual;
      case 'price-high':
        return b.precio_actual - a.precio_actual;
      default:
        return 0;
    }
  });
  
  renderizarProductos();
}

function setPriceRange(min, max) {
  document.getElementById('minPrice').value = min;
  document.getElementById('maxPrice').value = max === 200 ? '' : max;
  aplicarFiltrosLocales();
  renderizarProductos();
}

function clearFilters() {
  document.getElementById('searchInput').value = '';
  document.getElementById('minPrice').value = '';
  document.getElementById('maxPrice').value = '';
  document.getElementById('sortSelect').value = 'name';
  
  currentCategory = 'all';
  filterByCategory('all', 'Todos los productos');
  
  showNotification('Filtros limpiados', 'Mostrando todos los productos', 'info');
}

function setGridView(columns) {
  gridColumns = columns;
  renderizarProductos();
}

function toggleFilters() {
  const panel = document.getElementById('filtersPanel');
  panel?.classList.toggle('hidden');
}

// ========== GESTIÓN DE CARRITO ==========

async function addToCart(productoId, productName, price) {
  try {
    const response = await fetch('/cart/api/cart/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        producto_id: productoId,
        cantidad: 1
      })
    });

    const data = await response.json();

    if (data.success) {
      showNotification('¡Agregado!', `${productName} fue agregado al carrito`, 'success');
      cartItems++;
      actualizarContador();
    } else {
      showNotification('Error', data.error || 'No se pudo agregar al carrito', 'error');
    }
  } catch (error) {
    console.error('Error:', error);
    showNotification('Error', 'No se pudo agregar al carrito', 'error');
  }
}

function goToCart() {
  window.location.href = '/cart';
}

function verDetalle(slug) {
  window.location.href = `/producto/${slug}`;
}

function actualizarContador() {
  const badge = document.getElementById('cartCount');
  if (badge) {
    if (cartItems > 0) {
      badge.textContent = cartItems;
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  }
}

// ========== MENÚS Y NAVEGACIÓN ==========

function showUserMenu() {
  document.getElementById('userMenuModal')?.classList.remove('hidden');
}

function closeUserMenu() {
  document.getElementById('userMenuModal')?.classList.add('hidden');
}

function toggleMobileMenu() {
  document.getElementById('mobileMenu')?.classList.toggle('hidden');
}

async function logout() {
  try {
    const resp = await fetch('/login/auth/logout', {
      method: 'POST',
      credentials: 'same-origin'
    });
    const data = await resp.json().catch(() => ({}));
    setTimeout(() => {
      window.location = data.redirect || '/login/';
    }, 1000);
  } catch (error) {
    console.error('Error:', error);
    window.location = '/login/';
  }
}

// ========== INICIALIZACIÓN ==========

document.addEventListener('DOMContentLoaded', function () {
  console.log('🚀 Catálogo PeakSport inicializado');
  
  // Cargar datos iniciales
  cargarProductos(1);
  cargarCategorias();
  
  // ✅ NUEVO: Navegación con teclado
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      closeUserMenu();
    }
    
    // Navegación de páginas con flechas (solo si no estás escribiendo)
    if (!document.activeElement || 
        (document.activeElement.tagName !== 'INPUT' && 
         document.activeElement.tagName !== 'TEXTAREA')) {
      
      if (e.key === 'ArrowLeft' && currentPage > 1) {
        cambiarPagina(currentPage - 1);
      } else if (e.key === 'ArrowRight' && currentPage < totalPages) {
        cambiarPagina(currentPage + 1);
      }
    }
  });
  
  // Cerrar modal al hacer click afuera
  document.addEventListener('click', function (e) {
    if (e.target.id === 'userMenuModal') {
      closeUserMenu();
    }
  });
  
  // Mensaje de bienvenida
  setTimeout(() => {
    showNotification('🎉 ¡Bienvenido!', 'Explora nuestro catálogo de productos', 'success');
  }, 800);
  
  // ✅ NUEVO: Mostrar ayuda de teclado
  setTimeout(() => {
    const helpDiv = document.createElement('div');
    helpDiv.className = 'fixed bottom-6 left-6 glass-card text-white px-4 py-3 rounded-xl text-sm z-40 hidden lg:block';
    helpDiv.innerHTML = `
      <div class="flex items-center space-x-3">
        <i class="fas fa-keyboard text-gray-400"></i>
        <span class="text-gray-300">
          Usa <kbd class="px-2 py-1 bg-white/10 rounded text-xs">←</kbd> 
          <kbd class="px-2 py-1 bg-white/10 rounded text-xs">→</kbd> 
          para navegar
        </span>
      </div>
    `;
    document.body.appendChild(helpDiv);
    
    // Ocultar después de 5 segundos
    setTimeout(() => {
      helpDiv.style.opacity = '0';
      helpDiv.style.transition = 'opacity 0.5s';
      setTimeout(() => helpDiv.remove(), 500);
    }, 5000);
  }, 3000);
});