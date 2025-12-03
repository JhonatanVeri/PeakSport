/*!
 * PeakSport – Administración de Inventario
 * Frontend JS para listar, filtrar, ver detalles y eliminar productos.
 * Stack: Flask (backend + templates) + Tailwind + FontAwesome
 *
 * Incluye:
 *  - Normalizador robusto de URLs de imagen (getImageUrl)
 *  - Vista tabla y tarjetas (cards)
 *  - Modales Detalle / Eliminar con portada correcta
 *  - Filtros, orden, paginación
 *  - Exportar a PDF (print iframe)
 *  - Logs estructurados (console.group) y namespacing
 *
 * Importante:
 *  - Flask debe inyectar window._ADMIN_ENDPOINTS_ antes de este archivo.
 *  - imagen_portada viene del backend (URL absoluta/relativa).
 */

(() => {
  // Evitar doble ejecución si el bundle se incluye 2 veces
  if (window.PeakSportInventoryLoaded) {
    console.warn('[PS/BOOT] Script ya estaba cargado. Se evita doble inicialización.');
    return;
  }
  window.PeakSportInventoryLoaded = true;

  /* ===========================
     Logger (namespaced)
  ============================ */
  const Log = (ns = 'PS') => ({
    info:  (...args) => console.info(`[${ns}]`, ...args),
    warn:  (...args) => console.warn(`[${ns}]`, ...args),
    error: (...args) => console.error(`[${ns}]`, ...args),
    group: (label)  => console.group(`[${ns}] ${label}`),
    groupEnd:       () => console.groupEnd(),
  });

  const logBoot   = Log('BOOT');
  const logRender = Log('RENDER');
  const logData   = Log('DATA');
  const logModal  = Log('MODAL');
  const logUI     = Log('UI');

  /* ===========================
     Endpoints Safe Loader
  ============================ */
  let EP = null;

  /**
   * Resuelve endpoints publicados por Flask en window._ADMIN_ENDPOINTS_.
   * Si no existen, intenta leer un bloque JSON con id="admin-endpoints-json".
   * @param {string} ctx
   * @returns {{apiListar:string, apiEliminarTemplate:string, vistaEditarTemplate:string, ...}}
   */
  function resolveEndpointsOrThrow(ctx = 'init') {
    if (EP && EP.apiListar) return EP;

    // 1) Variable global esperada
    if (window._ADMIN_ENDPOINTS_) {
      EP = window._ADMIN_ENDPOINTS_;
    }

    // 2) Fallback JSON embebido
    if ((!EP || !EP.apiListar) && document.getElementById('admin-endpoints-json')) {
      try {
        EP = JSON.parse(document.getElementById('admin-endpoints-json').textContent || '{}');
        window._ADMIN_ENDPOINTS_ = EP;
      } catch (err) {
        console.error('[ENDPOINTS] No se pudo parsear admin-endpoints-json:', err);
      }
    }

    if (!EP || !EP.apiListar) {
      console.error(`[ENDPOINTS] No disponibles en ${ctx}. Verifica el orden de los <script> en el HTML.`);
      throw new Error('Endpoints no definidos: window._ADMIN_ENDPOINTS_');
    }
    return EP;
  }

  /* ===========================
     Estado
  ============================ */
  const STATE = {
    page: 1,
    per_page: 20,
    q: '',
    filtroStock: 'all',   // all | in-stock | out-stock | low-stock
    categoria_id: '',
    orden: 'nombre',      // nombre | precio | fecha | stock
    total: 0,
    productos: [],
    vistaActual: 'tabla', // tabla | cards
  };

  /* ===========================
     Utils
  ============================ */
  function numberToCOP(cents, currency = 'COP') {
    const amount = (cents || 0) / 100;
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency }).format(amount);
  }

  /**
   * Normaliza rutas de imagen:
   *  - http/https → tal cual
   *  - /root      → tal cual
   *  - static/... → antepone '/'
   *  - uploads/...→ antepone '/static/'
   *  - otro       → fallback '/static/uploads/productos/<url>'
   * @param {string|null|undefined} url
   * @returns {string|null}
   */
  function getImageUrl(url) {
    if (!url) return null;
    if (/^https?:\/\//i.test(url) || url.startsWith('/')) return url;
    if (url.startsWith('static/'))  return `/${url}`;
    if (url.startsWith('uploads/')) return `/static/${url}`;
    return `/static/uploads/productos/${url}`;
  }

  function showNotification(title, message, type = 'info') {
    const n = document.getElementById('notification');
    const icon = document.getElementById('notificationIcon');
    const titleEl = document.getElementById('notificationTitle');
    const messageEl = document.getElementById('notificationMessage');

    const config = {
      success: { icon: 'fas fa-check',        color: 'bg-green-500'  },
      error:   { icon: 'fas fa-times',        color: 'bg-red-500'    },
      warning: { icon: 'fas fa-exclamation',  color: 'bg-yellow-500' },
      info:    { icon: 'fas fa-info',         color: 'bg-blue-500'   },
    };

    const typeCfg = config[type] || config.info;
    icon.className = `w-10 h-10 ${typeCfg.color} rounded-full flex items-center justify-center`;
    icon.innerHTML = `<i class="${typeCfg.icon} text-white"></i>`;

    titleEl.textContent = title;
    messageEl.textContent = message;

    n.classList.remove('translate-x-full');
    setTimeout(() => n.classList.add('translate-x-full'), 3500);
  }

  /* ===========================
     KPIs
  ============================ */
  function renderKPIs({ total, activos, valorTotalEstimado }) {
    const grid = document.getElementById('kpiGrid');
    grid.innerHTML = `
      <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 card-hover slide-in">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-600 text-sm font-medium">Total Productos</p>
            <p class="text-3xl font-bold text-gray-900 mt-2">${total.toLocaleString('es-CO')}</p>
            <p class="text-green-600 text-sm mt-1"><i class="fas fa-arrow-up mr-1"></i>Datos en vivo</p>
          </div>
          <div class="w-16 h-16 rounded-2xl flex items-center justify-center" style="background: linear-gradient(135deg, #000000 0%, #ff0011 100%);">
            <i class="fas fa-boxes text-white text-2xl"></i>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 card-hover slide-in">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-600 text-sm font-medium">Activos</p>
            <p class="text-3xl font-bold text-green-600 mt-2">${activos.toLocaleString('es-CO')}</p>
            <p class="text-green-600 text-sm mt-1"><i class="fas fa-check mr-1"></i>Publicados</p>
          </div>
          <div class="w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl flex items-center justify-center">
            <i class="fas fa-toggle-on text-white text-2xl"></i>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 card-hover slide-in">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-600 text-sm font-medium">Valor Total (estimado)</p>
            <p class="text-3xl font-bold text-green-600 mt-2">${numberToCOP(valorTotalEstimado,'COP')}</p>
            <p class="text-green-600 text-sm mt-1"><i class="fas fa-dollar-sign mr-1"></i>Suma precios</p>
          </div>
          <div class="w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl flex items-center justify-center">
            <i class="fas fa-dollar-sign text-white text-2xl"></i>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 card-hover slide-in">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-600 text-sm font-medium">Categorías</p>
            <p class="text-3xl font-bold text-purple-600 mt-2">—</p>
            <p class="text-gray-500 text-sm mt-1"><i class="fas fa-tags mr-1"></i>Activas</p>
          </div>
          <div class="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl flex items-center justify-center">
            <i class="fas fa-tags text-white text-2xl"></i>
          </div>
        </div>
      </div>
    `;
  }

  /* ===========================
     Render: Tabla / Cards
  ============================ */
  function renderTable(items, page, perPage, total) {
    logRender.group('renderTable()');
    const container = document.getElementById('productsTableBody').parentElement.parentElement.parentElement;

    if (STATE.vistaActual === 'tabla') {
      const tbody = document.getElementById('productsTableBody');
      tbody.innerHTML = items.map(p => {
        const estadoBadge = p.activo
          ? `<span class="status-badge status-in-stock"><i class="fas fa-check-circle mr-1"></i>Activo</span>`
          : `<span class="status-badge status-out-stock"><i class="fas fa-times-circle mr-1"></i>Inactivo</span>`;

        const precio = numberToCOP(p.precio_centavos, p.moneda || 'COP');

        let imagenUrl = null;
        if (p.imagen_portada) {
          imagenUrl = getImageUrl(p.imagen_portada);
        } else if (p.imagenes?.length) {
          const portada = p.imagenes.find(img => img.es_portada) || p.imagenes[0];
          imagenUrl = portada?.url ? getImageUrl(portada.url) : null;
        }

        return `
          <tr class="table-row">
            <td class="px-6 py-4 whitespace-nowrap">
              <input type="checkbox" class="rounded border-gray-300">
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="flex items-center space-x-4">
                <div class="w-12 h-12 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center flex-shrink-0">
                  ${
                    imagenUrl
                      ? `<img src="${imagenUrl}" alt="${p.nombre}" class="w-full h-full object-cover"
                           onerror="this.parentElement.innerHTML='<i class=&quot;fas fa-image text-gray-400&quot;></i>'">`
                      : `<i class="fas fa-image text-gray-400"></i>`
                  }
                </div>
                <div>
                  <p class="text-sm font-medium text-gray-900">${p.nombre ?? ''}</p>
                  <p class="text-xs text-gray-500">ID: ${p.id}</p>
                </div>
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono">${p.slug ?? ''}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${precio}</td>
            <td class="px-6 py-4 whitespace-nowrap">${estadoBadge}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
              <div class="flex items-center space-x-2">
                <button data-id="${p.id}" class="btn-edit text-blue-600 hover:text-blue-900 p-2 hover:bg-blue-50 rounded-lg transition-all" title="Editar">
                  <i class="fas fa-edit"></i>
                </button>
                <button data-id="${p.id}" class="btn-view text-green-600 hover:text-green-900 p-2 hover:bg-green-50 rounded-lg transition-all" title="Ver detalles">
                  <i class="fas fa-eye"></i>
                </button>
                <button
                  data-id="${p.id}"
                  data-nombre="${(p.nombre || '').replace(/"/g, '&quot;')}"
                  data-slug="${p.slug ?? ''}"
                  data-precio="${precio}"
                  data-imagen_portada="${imagenUrl || ''}"
                  class="btn-delete text-red-600 hover:text-red-900 p-2 hover:bg-red-50 rounded-lg transition-all"
                  title="Eliminar">
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        `;
      }).join('');
    } else {
      // Cards
      const cardsContainer = document.createElement('div');
      cardsContainer.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 p-6';
      cardsContainer.id = 'cardsContainer';

      cardsContainer.innerHTML = items.map(p => {
        const estadoBadge = p.activo
          ? `<span class="status-badge status-in-stock"><i class="fas fa-check-circle mr-1"></i>Activo</span>`
          : `<span class="status-badge status-out-stock"><i class="fas fa-times-circle mr-1"></i>Inactivo</span>`;

        const precio = numberToCOP(p.precio_centavos, p.moneda || 'COP');

        let imagenUrl = null;
        if (p.imagen_portada) {
          imagenUrl = getImageUrl(p.imagen_portada);
        } else if (p.imagenes?.length) {
          const portada = p.imagenes.find(img => img.es_portada) || p.imagenes[0];
          imagenUrl = portada?.url ? getImageUrl(portada.url) : null;
        }

        return `
          <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden card-hover transition-all">
            <div class="h-48 bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center relative overflow-hidden">
              ${
                imagenUrl
                  ? `<img src="${imagenUrl}" alt="${p.nombre}" class="w-full h-full object-cover"
                       onerror="this.parentElement.innerHTML='<i class=&quot;fas fa-box text-gray-400 text-5xl&quot;></i>'">`
                  : `<i class="fas fa-box text-gray-400 text-5xl"></i>`
              }
              <div class="absolute top-3 right-3">${estadoBadge}</div>
            </div>
            <div class="p-5">
              <h3 class="font-bold text-gray-900 text-lg mb-1 truncate" title="${p.nombre}">${p.nombre ?? 'Sin nombre'}</h3>
              <p class="text-xs text-gray-500 mb-3 font-mono truncate">${p.slug ?? '-'}</p>
              <div class="flex items-center justify-between mb-4">
                <span class="text-2xl font-bold text-green-600">${precio}</span>
                <span class="text-xs text-gray-500">ID: ${p.id}</span>
              </div>
              <div class="flex items-center gap-2">
                <button data-id="${p.id}" class="btn-edit flex-1 px-3 py-2 bg-blue-50 text-blue-600 hover:bg-blue-100 rounded-lg transition-all text-sm font-medium" title="Editar">
                  <i class="fas fa-edit"></i>
                </button>
                <button data-id="${p.id}" class="btn-view flex-1 px-3 py-2 bg-green-50 text-green-600 hover:bg-green-100 rounded-lg transition-all text-sm font-medium" title="Ver">
                  <i class="fas fa-eye"></i>
                </button>
                <button
                  data-id="${p.id}"
                  data-nombre="${(p.nombre || '').replace(/"/g, '&quot;')}"
                  data-slug="${p.slug ?? ''}"
                  data-precio="${precio}"
                  data-imagen_portada="${imagenUrl || ''}"
                  class="btn-delete flex-1 px-3 py-2 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg transition-all text-sm font-medium"
                  title="Eliminar">
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </div>
          </div>
        `;
      }).join('');

      const tableContainer = container.querySelector('.overflow-x-auto');
      if (tableContainer) {
        tableContainer.style.display = 'none';
        let existingCards = container.querySelector('#cardsContainer');
        if (existingCards) {
          existingCards.replaceWith(cardsContainer);
        } else {
          tableContainer.insertAdjacentElement('afterend', cardsContainer);
        }
      }
    }

    // Volver a tabla si corresponde
    if (STATE.vistaActual === 'tabla') {
      const tableContainer = container.querySelector('.overflow-x-auto');
      if (tableContainer) {
        tableContainer.style.display = 'block';
        const existingCards = container.querySelector('#cardsContainer');
        if (existingCards) existingCards.remove();
      }
    }

    // Resumen + paginación + acciones
    const lbl = document.getElementById('lblResumen');
    const start = total === 0 ? 0 : ((page - 1) * perPage) + 1;
    const end = Math.min(page * perPage, total);
    lbl.textContent = `Mostrando ${start} a ${end} de ${total} productos`;

    renderPagination(page, perPage, total);
    bindRowActions(); // 🔧 ¡Ahora sí existe!
    logRender.groupEnd();
  }

  /* ===========================
     Paginación
  ============================ */
  function renderPagination(page, perPage, total) {
    const container = document.getElementById('paginacion');
    const totalPages = Math.max(1, Math.ceil(total / perPage));

    const btn = (label, pageNum, active=false, disabled=false) => `
      <button data-page="${pageNum}"
              class="px-3 py-2 text-sm ${active ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg' : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-all'}"
              ${disabled ? 'disabled' : ''}>
        ${label}
      </button>`;

    let html = '';
    html += btn('Anterior', Math.max(1, page - 1), false, page === 1);

    for (let i = 1; i <= Math.min(totalPages, 3); i++) {
      html += btn(String(i), i, page === i);
    }

    if (totalPages > 3) {
      html += `<span class="text-gray-400 px-2">...</span>`;
      html += btn(String(totalPages), totalPages, page === totalPages);
    }

    html += btn('Siguiente', Math.min(totalPages, page + 1), false, page === totalPages);

    container.innerHTML = html;

    container.querySelectorAll('button[data-page]').forEach(b => {
      b.addEventListener('click', (e) => {
        const nextPage = parseInt(e.currentTarget.getAttribute('data-page'), 10);
        if (nextPage && nextPage !== STATE.page) {
          STATE.page = nextPage;
          logUI.info('Paginación → page:', STATE.page);
          loadProducts();
        }
      });
    });
  }

  /* ===========================
     Data: Cargar productos
  ============================ */
  async function loadProducts() {
    logData.group('loadProducts()');
    try {
      const params = new URLSearchParams();
      if (STATE.q) params.set('q', STATE.q);
      if (STATE.categoria_id) params.set('categoria_id', STATE.categoria_id);
      params.set('page', STATE.page);
      params.set('per_page', STATE.per_page);

      const ep = resolveEndpointsOrThrow('loadProducts');
      const url = `${ep.apiListar}?${params.toString()}`;
      logData.info('GET', url);

      const resp = await fetch(url);
      if (!resp.ok) throw new Error('Error al cargar productos');
      const data = await resp.json();

      const items = data.items || [];
      STATE.total = data.total || 0;

      const activos = items.filter(p => p.activo).length;
      const valorTotalEstimado = items.reduce((acc, p) => acc + (p.precio_centavos || 0), 0);
      renderKPIs({ total: STATE.total, activos, valorTotalEstimado });

      let sorted = [...items];
      if (STATE.orden === 'nombre') sorted.sort((a,b) => (a.nombre||'').localeCompare(b.nombre||''));
      if (STATE.orden === 'precio') sorted.sort((a,b) => (a.precio_centavos||0) - (b.precio_centavos||0));
      if (STATE.orden === 'fecha')  sorted.sort((a,b) => new Date(b.created_at||0) - new Date(a.created_at||0));
      if (STATE.orden === 'stock')  sorted.sort((a,b) => (a.stock ?? 0) - (b.stock ?? 0));

      if (STATE.filtroStock !== 'all') {
        if (STATE.filtroStock === 'in-stock')  sorted = sorted.filter(p => p.activo);
        if (STATE.filtroStock === 'out-stock') sorted = sorted.filter(p => !p.activo);
        // low-stock: define tu criterio, p.ej. (p.stock ?? 0) < 5
      }

      renderTable(sorted, STATE.page, STATE.per_page, STATE.total);
      STATE.productos = sorted;

      logData.info('Items:', items.length, 'Total:', STATE.total);
    } catch (e) {
      logData.error(e);
      showNotification('Error', 'No se pudo cargar el listado', 'error');
    } finally {
      logData.groupEnd();
    }
  }

 /* ===========================
   Exportar PDF - Diseño Elegante "Esquina Roja"
============================ */
  async function exportarPDF() {
    const log = Log('EXPORT');
    try {
      showNotification('Exportando', 'Generando PDF con diseño elegante...', 'info');
      
      const iframe = document.createElement('iframe');
      iframe.style.display = 'none';
      document.body.appendChild(iframe);

      const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

      const adminInfo = {
        empresa: 'PeakSport',
        telefono: '3219359010',
        email: 'PeakSport_@hotmail.com',
        fecha: new Date().toLocaleDateString('es-CO', { 
          year: 'numeric', 
          month: 'long', 
          day: 'numeric' 
        }),
      };

      const consolidado = {
        totalProductos: STATE.total,
        productosActivos: STATE.productos.filter(p => p.activo).length,
        productosInactivos: STATE.productos.filter(p => !p.activo).length,
        valorTotal: STATE.productos.reduce((acc, p) => acc + (p.precio_centavos || 0), 0),
        productos: STATE.productos,
      };

      const htmlContent = `
        <!DOCTYPE html>
        <html lang="es">
        <head>
          <meta charset="UTF-8">
          <title>Informe de Inventario - PeakSport</title>
          <style>
            * {
              margin: 0;
              padding: 0;
              box-sizing: border-box;
            }

            body {
              font-family: 'Arial', 'Helvetica', sans-serif;
              background: white;
              color: #000;
            }

            .page {
              width: 210mm;
              min-height: 297mm;
              margin: 0 auto;
              background: white;
              position: relative;
              padding: 30mm 20mm;
            }

            /* ========== ESQUINA ROJA DECORATIVA ========== */
            .red-corner {
              position: absolute;
              top: 0;
              right: 0;
              width: 0;
              height: 0;
              border-style: solid;
              border-width: 0 180px 180px 0;
              border-color: transparent #ff0011 transparent transparent;
              z-index: 1;
            }

            /* ========== ENCABEZADO PRINCIPAL ========== */
            .header-section {
              text-align: center;
              margin-bottom: 60px;
              position: relative;
              z-index: 2;
            }

            .main-title {
              font-size: 48px;
              font-weight: 900;
              letter-spacing: 8px;
              color: #000;
              margin-bottom: 10px;
              text-transform: uppercase;
              line-height: 1.2;
            }

            .subtitle {
              font-size: 36px;
              font-weight: 300;
              letter-spacing: 4px;
              color: #000;
              margin-bottom: 40px;
              text-transform: uppercase;
            }

            /* ========== INFORMACIÓN DE CONTACTO ========== */
            .contact-info {
              text-align: center;
              margin-bottom: 50px;
            }

            .contact-info p {
              font-size: 16px;
              color: #333;
              margin: 8px 0;
              letter-spacing: 1px;
            }

            .company-name {
              font-size: 24px;
              font-weight: bold;
              color: #ff0011;
              margin-top: 15px;
              letter-spacing: 2px;
            }

            /* ========== FECHA ========== */
            .date-section {
              text-align: center;
              margin-bottom: 40px;
              padding: 15px;
              background: #f8f8f8;
              border-left: 4px solid #ff0011;
            }

            .date-section p {
              font-size: 14px;
              color: #666;
              letter-spacing: 1px;
            }

            /* ========== KPIs RESUMEN ========== */
            .kpis-section {
              display: grid;
              grid-template-columns: repeat(4, 1fr);
              gap: 15px;
              margin-bottom: 40px;
            }

            .kpi-card {
              background: linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%);
              padding: 20px;
              text-align: center;
              border-radius: 8px;
              border: 1px solid #ddd;
            }

            .kpi-card.primary {
              background: linear-gradient(135deg, #000000 0%, #333333 100%);
              color: white;
            }

            .kpi-card.success {
              background: linear-gradient(135deg, #4caf50 0%, #2e7d32 100%);
              color: white;
            }

            .kpi-card.danger {
              background: linear-gradient(135deg, #ff0011 0%, #cc0000 100%);
              color: white;
            }

            .kpi-label {
              font-size: 11px;
              text-transform: uppercase;
              letter-spacing: 1px;
              opacity: 0.8;
              margin-bottom: 8px;
              font-weight: bold;
            }

            .kpi-value {
              font-size: 28px;
              font-weight: 900;
              letter-spacing: 1px;
            }

            /* ========== SECCIÓN DE TÍTULO ========== */
            .section-title {
              font-size: 20px;
              font-weight: bold;
              color: #000;
              margin: 40px 0 20px 0;
              padding-bottom: 10px;
              border-bottom: 3px solid #ff0011;
              text-transform: uppercase;
              letter-spacing: 2px;
            }

            /* ========== TABLA DE PRODUCTOS ========== */
            .products-table {
              width: 100%;
              border-collapse: collapse;
              margin-bottom: 40px;
              font-size: 11px;
            }

            .products-table thead {
              background: linear-gradient(135deg, #000000 0%, #333333 100%);
              color: white;
            }

            .products-table th {
              padding: 12px 10px;
              text-align: left;
              font-weight: bold;
              text-transform: uppercase;
              letter-spacing: 1px;
              font-size: 10px;
            }

            .products-table td {
              padding: 10px;
              border-bottom: 1px solid #e0e0e0;
            }

            .products-table tbody tr:nth-child(even) {
              background: #f9f9f9;
            }

            .products-table tbody tr:hover {
              background: #f0f0f0;
            }

            /* Estados */
            .badge {
              display: inline-block;
              padding: 4px 10px;
              border-radius: 12px;
              font-size: 9px;
              font-weight: bold;
              text-transform: uppercase;
              letter-spacing: 0.5px;
            }

            .badge-active {
              background: #d4edda;
              color: #155724;
            }

            .badge-inactive {
              background: #f8d7da;
              color: #721c24;
            }

            /* Precios */
            .price-cell {
              font-weight: bold;
              color: #2e7d32;
              text-align: right;
              font-family: 'Courier New', monospace;
            }

            /* ========== FOOTER ========== */
            .footer {
              margin-top: 60px;
              padding-top: 20px;
              border-top: 2px solid #e0e0e0;
              text-align: center;
            }

            .footer p {
              font-size: 9px;
              color: #999;
              margin: 5px 0;
              letter-spacing: 0.5px;
            }

            /* ========== ESTILOS DE IMPRESIÓN ========== */
            @media print {
              body {
                margin: 0;
                padding: 0;
              }
              
              .page {
                margin: 0;
                page-break-after: always;
              }

              .red-corner {
                print-color-adjust: exact;
                -webkit-print-color-adjust: exact;
              }

              .kpi-card,
              .products-table thead {
                print-color-adjust: exact;
                -webkit-print-color-adjust: exact;
              }
            }
          </style>
        </head>
        <body>
          <div class="page">
            <!-- ESQUINA ROJA DECORATIVA -->
            <div class="red-corner"></div>

            <!-- ENCABEZADO -->
            <div class="header-section">
              <h1 class="main-title">INFORME</h1>
              <h2 class="subtitle">DE INVENTARIO</h2>
            </div>

            <!-- INFORMACIÓN DE CONTACTO -->
            <div class="contact-info">
              <p>${adminInfo.telefono}</p>
              <p>${adminInfo.email}</p>
              <p class="company-name">${adminInfo.empresa}</p>
            </div>

            <!-- FECHA -->
            <div class="date-section">
              <p><strong>Fecha de generación:</strong> ${adminInfo.fecha}</p>
            </div>

            <!-- KPIs -->
            <div class="kpis-section">
              <div class="kpi-card primary">
                <div class="kpi-label">Total Productos</div>
                <div class="kpi-value">${consolidado.totalProductos.toLocaleString('es-CO')}</div>
              </div>
              <div class="kpi-card success">
                <div class="kpi-label">Activos</div>
                <div class="kpi-value">${consolidado.productosActivos.toLocaleString('es-CO')}</div>
              </div>
              <div class="kpi-card danger">
                <div class="kpi-label">Inactivos</div>
                <div class="kpi-value">${consolidado.productosInactivos.toLocaleString('es-CO')}</div>
              </div>
              <div class="kpi-card success">
                <div class="kpi-label">Valor Total</div>
                <div class="kpi-value">${numberToCOP(consolidado.valorTotal, 'COP')}</div>
              </div>
            </div>

            <!-- TÍTULO DE SECCIÓN -->
            <h3 class="section-title">Detalle de Productos</h3>

            <!-- TABLA DE PRODUCTOS -->
            <table class="products-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre del Producto</th>
                  <th>SKU/Slug</th>
                  <th style="text-align: right;">Precio</th>
                  <th style="text-align: center;">Estado</th>
                </tr>
              </thead>
              <tbody>
                ${consolidado.productos.map(p => `
                  <tr>
                    <td><strong>${p.id}</strong></td>
                    <td>${p.nombre || '-'}</td>
                    <td><small style="color: #666;">${p.slug || '-'}</small></td>
                    <td class="price-cell">${numberToCOP(p.precio_centavos, p.moneda || 'COP')}</td>
                    <td style="text-align: center;">
                      <span class="badge ${p.activo ? 'badge-active' : 'badge-inactive'}">
                        ${p.activo ? '✓ Activo' : '✗ Inactivo'}
                      </span>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>

            <!-- FOOTER -->
            <div class="footer">
              <p>📄 Este documento fue generado automáticamente por el sistema de gestión de PeakSport</p>
              <p>© ${new Date().getFullYear()} PeakSport. Todos los derechos reservados.</p>
              <p>Documento confidencial - Solo para uso interno</p>
            </div>
          </div>
        </body>
        </html>
      `;

      iframeDoc.open();
      iframeDoc.write(htmlContent);
      iframeDoc.close();

      // Esperar a que cargue y luego imprimir
      setTimeout(() => {
        iframe.contentWindow.print();
        
        setTimeout(() => {
          document.body.removeChild(iframe);
          showNotification('PDF Generado', 'El informe elegante está listo', 'success');
          log.info('✅ Exportación completada con diseño elegante');
        }, 800);
      }, 500);

    } catch (error) {
      console.error('❌ Error al exportar PDF:', error);
      showNotification('Error', 'No se pudo generar el PDF: ' + error.message, 'error');
    }
  }

  // Asegurarse de que esté disponible globalmente
  window.exportarPDF = exportarPDF;

  /* ===========================
     Modales: Detalles
  ============================ */
  function mostrarModalDetalles(producto) {
    logModal.group('mostrarModalDetalles()');
    const modal = document.getElementById("modalDetalles");
    const modalContent = modal.querySelector(".modal-content");

    let imagenUrl = null;
    if (producto.imagen_portada) {
      imagenUrl = getImageUrl(producto.imagen_portada);
    } else if (producto.imagenes?.length) {
      const portada = producto.imagenes.find(img => img.es_portada) || producto.imagenes[0];
      imagenUrl = portada?.url ? getImageUrl(portada.url) : null;
    }

    const html = `
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
        <!-- Imagen -->
        <div>
          <div class="relative rounded-xl overflow-hidden bg-gradient-to-br from-gray-100 to-gray-200 aspect-square mb-4">
            ${
              imagenUrl
                ? `<img src="${imagenUrl}" alt="${producto.nombre}" class="w-full h-full object-cover"
                     onerror="console.error('Error cargando imagen:', this.src); this.style.display='none'; this.parentElement.innerHTML='<div class=&quot;w-full h-full flex items-center justify-center&quot;><i class=&quot;fas fa-box text-gray-400 text-6xl&quot;></i></div>';">`
                : `<div class="w-full h-full flex items-center justify-center"><i class="fas fa-box text-gray-400 text-6xl"></i></div>`
            }
            <div class="absolute top-3 right-3 flex gap-2">
              <button class="p-3 rounded-full backdrop-blur-md bg-white/20 text-white hover:bg-white/30 transition">
                <i class="fas fa-heart text-lg"></i>
              </button>
              <button class="p-3 rounded-full backdrop-blur-md bg-white/20 text-white hover:bg-white/30 transition">
                <i class="fas fa-share-alt text-lg"></i>
              </button>
            </div>
            <div class="absolute bottom-3 left-3">
              <span class="bg-green-500 text-white px-4 py-2 rounded-full text-sm font-semibold">
                <i class="fas fa-box mr-1"></i> ${producto.activo ? 'En Stock' : 'Agotado'}
              </span>
            </div>
          </div>
        </div>

        <!-- Información -->
        <div>
          <div class="mb-6">
            <p class="text-sm text-gray-500 font-medium uppercase mb-2">${producto.moneda || 'COP'}</p>
            <h1 class="text-3xl font-bold text-gray-900 mb-3">${producto.nombre}</h1>
            <p class="text-gray-600">${producto.descripcion || 'Sin descripción disponible'}</p>
          </div>

          <div class="bg-gradient-to-r from-red-50 to-orange-50 rounded-xl p-4 mb-6">
            <p class="text-sm text-gray-600 mb-2">Precio</p>
            <p class="text-4xl font-bold text-red-600">${(producto.precio_centavos / 100).toLocaleString('es-CO')}</p>
          </div>

          <div class="grid grid-cols-2 gap-4 mb-6">
            <div class="bg-blue-50 rounded-lg p-4">
              <p class="text-xs text-gray-600 font-semibold uppercase mb-1">SKU</p>
              <p class="text-lg font-bold text-gray-900">${producto.sku || 'N/A'}</p>
            </div>
            <div class="bg-purple-50 rounded-lg p-4">
              <p class="text-xs text-gray-600 font-semibold uppercase mb-1">Stock</p>
              <p class="text-lg font-bold text-green-600">${producto.stock ?? 0} units</p>
            </div>
          </div>

          <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <p class="text-sm font-semibold text-blue-900 mb-3">📦 Información de Stock</p>
            <div class="space-y-2">
              <div class="flex justify-between items-center">
                <span class="text-sm text-gray-700">Estado:</span>
                <span class="px-3 py-1 ${producto.activo ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'} rounded-full text-xs font-semibold">
                  ${producto.activo ? '✓ Activo' : '✗ Inactivo'}
                </span>
              </div>
            </div>
          </div>

          <div class="flex gap-3">
            <button onclick="cerrarModalDetalles()" class="flex-1 px-6 py-3 border border-gray-300 text-gray-700 font-semibold rounded-lg hover:bg-gray-50 transition">
              Cerrar
            </button>
            <button id="btnEditarModal" class="flex-1 px-6 py-3 bg-gradient-to-r from-red-600 to-red-700 text-white font-semibold rounded-lg hover:shadow-lg transition flex items-center justify-center gap-2">
              <i class="fas fa-edit mr-2"></i> Editar
            </button>
          </div>
        </div>
      </div>
    `;

    modalContent.innerHTML = html;
    modal.style.display = "flex";

    document.getElementById("btnEditarModal").addEventListener('click', () => {
      const ep = resolveEndpointsOrThrow('modal-editar');
      const editarUrl = ep.vistaEditarTemplate.replace(/\/0\/editar$/, `/${producto.id}/editar`);
      window.location.href = editarUrl;
    });

    logModal.info('Producto:', producto);
    logModal.info('Imagen URL:', imagenUrl);
    logModal.groupEnd();
  }
  function cerrarModalDetalles() {
    const modal = document.getElementById('modalDetalles');
    modal.classList.add('hidden');
    modal.style.display = 'none';
  }
  window.cerrarModalDetalles = cerrarModalDetalles;

  /* ===========================
     Modales: Eliminar
  ============================ */
  function mostrarModalEliminar(id, nombre, slug, precio, imagen_portada) {
    logModal.group('mostrarModalEliminar()');
    const modal = document.getElementById('modalEliminar');
    const content = modal.querySelector('.modal-content');

    const src = imagen_portada ? getImageUrl(imagen_portada) : '/static/img/no-image.png';

    content.innerHTML = `
      <div class="text-center mb-6">
        <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4 pulse-danger">
          <i class="fas fa-trash text-red-600 text-2xl"></i>
        </div>
        <h2 class="text-2xl font-bold text-gray-900 mb-2">Eliminar este producto</h2>
        <p class="text-gray-600">¿Estás seguro de que quieres eliminar este producto del inventario?</p>
      </div>

      <div class="bg-gray-50 rounded-xl p-4 mb-6">
        <div class="flex items-center space-x-4">
          <div class="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0 bg-gray-100">
            <img src="${src}" alt="${nombre}" class="w-full h-full object-cover" onerror="this.src='/static/img/no-image.png'"/>
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="font-semibold text-gray-900 truncate">${nombre}</h3>
            <p class="text-sm text-gray-600 mt-1">SKU: ${slug}</p>
            <p class="text-sm font-medium text-gray-900 mt-1">${precio}</p>
          </div>
        </div>
      </div>

      <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <div class="flex items-start">
          <i class="fas fa-exclamation-triangle text-red-500 mr-3 mt-0.5"></i>
          <div class="text-sm">
            <p class="text-red-800 font-medium">Esta acción no se puede deshacer</p>
            <p class="text-red-700 mt-1">El producto será eliminado permanentemente del inventario junto con todas sus imágenes.</p>
          </div>
        </div>
      </div>

      <div class="flex space-x-4">
        <button onclick="cerrarModalEliminar()" 
                class="flex-1 px-6 py-3 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition-all font-medium">
          <i class="fas fa-times mr-2"></i> Cancelar
        </button>
        <button onclick="confirmarEliminar(${id})" 
                class="flex-1 px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl transition-all font-medium shadow-lg">
          <i class="fas fa-check mr-2"></i> Confirmar
        </button>
      </div>
    `;

    modal.classList.remove('hidden');
    modal.style.display = 'flex';
    logModal.info('ID:', id, 'Nombre:', nombre, 'Slug:', slug, 'Precio:', precio, 'Src:', src);
    logModal.groupEnd();
  }
  function cerrarModalEliminar() {
    const modal = document.getElementById('modalEliminar');
    modal.classList.add('hidden');
    modal.style.display = 'none';
  }
  window.cerrarModalEliminar = cerrarModalEliminar;

  async function confirmarEliminar(id) {
    logModal.group('confirmarEliminar()');
    const modal = document.getElementById('modalEliminar');
    const btnConfirmar = modal.querySelector('button[onclick^="confirmarEliminar"]');

    btnConfirmar.disabled = true;
    btnConfirmar.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Eliminando...';

    try {
      const ep = resolveEndpointsOrThrow('confirmarEliminar');
      const eliminarUrl = ep.apiEliminarTemplate.replace('/0', `/${id}`);
      logModal.info('DELETE', eliminarUrl);

      const response = await fetch(eliminarUrl, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });

      const data = await response.json();

      if (!response.ok || !data.ok) {
        throw new Error(data.error || 'No fue posible eliminar el producto');
      }

      showNotification('Producto eliminado', 'El producto ha sido eliminado del inventario', 'success');
      cerrarModalEliminar();

      setTimeout(() => {
        loadProducts();
      }, 800);

    } catch (error) {
      logModal.error('Error al eliminar:', error);
      showNotification('Error', error.message, 'error');
      btnConfirmar.disabled = false;
      btnConfirmar.innerHTML = '<i class="fas fa-check mr-2"></i> Confirmar';
    } finally {
      logModal.groupEnd();
    }
  }
  window.confirmarEliminar = confirmarEliminar;

  /* ===========================
     Acciones fila (editar, ver, eliminar)
  ============================ */
  function bindRowActions() {
    // Editar
    document.querySelectorAll('.btn-edit').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        const ep = resolveEndpointsOrThrow('btn-edit');
        const editarUrl = ep.vistaEditarTemplate.replace(/\/0\/editar$/, `/${id}/editar`);
        window.location.href = editarUrl;
      });
    });

    // Ver detalles
    document.querySelectorAll('.btn-view').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = parseInt(e.currentTarget.getAttribute('data-id'), 10);
        const producto = STATE.productos.find(p => p.id === id);
        if (producto) mostrarModalDetalles(producto);
        else showNotification('Error', 'Producto no encontrado', 'error');
      });
    });

    // Eliminar
    document.querySelectorAll('.btn-delete').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id     = e.currentTarget.getAttribute('data-id');
        const nombre = e.currentTarget.getAttribute('data-nombre');
        const slug   = e.currentTarget.getAttribute('data-slug');
        const precio = e.currentTarget.getAttribute('data-precio');
        const img    = e.currentTarget.getAttribute('data-imagen_portada');
        mostrarModalEliminar(id, nombre, slug, precio, img);
      });
    });
  }

  /* ===========================
     UI: filtros / orden / toggle
  ============================ */
  function setActiveFilter(targetBtn) {
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.classList.remove('filter-active');
      btn.classList.add('text-gray-600', 'hover:bg-gray-100');
    });
    targetBtn.classList.add('filter-active');
    targetBtn.classList.remove('text-gray-600', 'hover:bg-gray-100');
  }

  function initFilters() {
    // Filtros
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', (ev) => {
        const filter = ev.currentTarget.getAttribute('data-filter') || 'all';
        STATE.filtroStock = filter;
        setActiveFilter(ev.currentTarget);
        showNotification('Filtro aplicado', `Mostrando: ${filter}`, 'info');
        logUI.info('Filtro aplicado:', filter);
        STATE.page = 1;
        loadProducts();
      });
    });

    // Búsqueda
    const txt = document.getElementById('txtSearch');
    let t;
    txt.addEventListener('input', () => {
      clearTimeout(t);
      t = setTimeout(() => {
        STATE.q = txt.value.trim();
        STATE.page = 1;
        logUI.info('Búsqueda:', STATE.q);
        loadProducts();
      }, 300);
    });

    // Orden
    const selOrden = document.getElementById('selOrden');
    selOrden.addEventListener('change', (e) => {
      STATE.orden = e.target.value;
      logUI.info('Orden:', STATE.orden);
      loadProducts();
    });

    // Categoría
    const selCat = document.getElementById('selCategoria');
    if (selCat) {
      selCat.addEventListener('change', (e) => {
        STATE.categoria_id = e.target.value;
        STATE.page = 1;
        logUI.info('Categoría:', STATE.categoria_id);
        loadProducts();
      });
    }

    // Exportar PDF
    const btnExport = document.getElementById('btnExport');
    btnExport.addEventListener('click', exportarPDF);

    // Toggle vista (tabla/cards)
    const btnToggle = document.getElementById('btnToggleView');
    btnToggle.addEventListener('click', () => {
      STATE.vistaActual = STATE.vistaActual === 'tabla' ? 'cards' : 'tabla';

      const icono = STATE.vistaActual === 'tabla'
        ? '<i class="fas fa-th-large mr-2"></i>'
        : '<i class="fas fa-table mr-2"></i>';
      const texto = STATE.vistaActual === 'tabla' ? 'Vista' : 'Tabla';
      btnToggle.innerHTML = `${icono} ${texto}`;

      let sorted = [...STATE.productos];
      if (STATE.orden === 'nombre') sorted.sort((a,b) => (a.nombre||'').localeCompare(b.nombre||''));
      if (STATE.orden === 'precio') sorted.sort((a,b) => (a.precio_centavos||0) - (b.precio_centavos||0));
      if (STATE.orden === 'fecha')  sorted.sort((a,b) => new Date(b.created_at||0) - new Date(a.created_at||0));
      if (STATE.orden === 'stock')  sorted.sort((a,b) => (a.stock ?? 0) - (b.stock ?? 0));

      if (STATE.filtroStock !== 'all') {
        if (STATE.filtroStock === 'in-stock')  sorted = sorted.filter(p => p.activo);
        if (STATE.filtroStock === 'out-stock') sorted = sorted.filter(p => !p.activo);
      }

      renderTable(sorted, STATE.page, STATE.per_page, STATE.total);

      showNotification('Vista cambiada', `Mostrando vista de ${STATE.vistaActual === 'tabla' ? 'tabla' : 'tarjetas'}`, 'info');
      logUI.info('Vista actual:', STATE.vistaActual);
    });
  }

  /* ===========================
     Boot
  ============================ */
  document.addEventListener('DOMContentLoaded', () => {
    logBoot.info('Iniciando módulo Inventario…');

    try { resolveEndpointsOrThrow('DOMContentLoaded'); }
    catch (e) {
      showNotification('Error', 'No se encontraron endpoints del backend', 'error');
      // Continuamos: si luego se inyecta el bloque JSON, se resolverá en el primer uso.
    }

    initFilters();
    loadProducts();
    showNotification('Sistema cargado', 'Gestión de almacén lista para usar', 'success');

    // ESC cierra modales
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const modalEliminar = document.getElementById('modalEliminar');
        const modalDetalles = document.getElementById('modalDetalles');

        if (modalEliminar.style.display === 'flex') cerrarModalEliminar();
        if (modalDetalles.style.display === 'flex') cerrarModalDetalles();
      }
    });

    // Click fuera para cerrar modales
    const modalEliminar = document.getElementById('modalEliminar');
    modalEliminar.addEventListener('click', (e) => {
      if (e.target === modalEliminar) cerrarModalEliminar();
    });

    const modalDetalles = document.getElementById('modalDetalles');
    modalDetalles.addEventListener('click', (e) => {
      if (e.target === modalDetalles) cerrarModalDetalles();
    });
  });

})(); // IIFE
