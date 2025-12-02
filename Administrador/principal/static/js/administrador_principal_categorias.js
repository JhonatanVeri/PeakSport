/* ===========================
   Config & State
=========================== */
const EP = window.__ADMIN_ENDPOINTS__;
const STATE = {
  page: 1,
  per_page: 20,
  total: 0,
  q: '',
  padre_id: '',
  orden: 'nombre',
  editId: null,
};

/* ===========================
   Utils
=========================== */
function slugify(text) {
  return (text || '')
    .normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/[\s_-]+/g, '-');
}

function showNotification(title, message, type = 'info') {
  const n = document.getElementById('notification');
  const icon = document.getElementById('notificationIcon');
  const titleEl = document.getElementById('notificationTitle');
  const messageEl = document.getElementById('notificationMessage');

  const config = {
    success: { icon: 'fas fa-check', color: 'bg-green-500' },
    error: { icon: 'fas fa-times', color: 'bg-red-500' },
    warning: { icon: 'fas fa-exclamation', color: 'bg-yellow-500' },
    info: { icon: 'fas fa-info', color: 'bg-blue-500' }
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
   DOM refs
=========================== */
const txtSearch = document.getElementById('txtSearch');
const selPadreFiltro = document.getElementById('selPadreFiltro');
const selOrden = document.getElementById('selOrden');
const tbody = document.getElementById('tablaCategorias');
const lblResumen = document.getElementById('lblResumen');
const paginacion = document.getElementById('paginacion');

const modal = document.getElementById('modalCategoria');
const modalTitulo = document.getElementById('modalTitulo');
const btnCerrarModal = document.getElementById('btnCerrarModal');
const btnNuevaCategoria = document.getElementById('btnNuevaCategoria');
const btnCancelar = document.getElementById('btnCancelar');
const btnGuardar = document.getElementById('btnGuardar');

const inpNombre = document.getElementById('inpNombre');
const inpSlug = document.getElementById('inpSlug');
const txtDescripcion = document.getElementById('txtDescripcion');
const selPadre = document.getElementById('selPadre');

/* ===========================
   API con mejor logging
=========================== */
async function apiListarCategorias(params = {}) {
  try {
    const usp = new URLSearchParams();
    if (STATE.padre_id !== '') usp.set('padre_id', STATE.padre_id);
    usp.set('page', STATE.page);
    usp.set('per_page', STATE.per_page);
    const url = `${EP.apiListarCategorias}?${usp.toString()}`;
    
    console.log('📤 GET:', url);
    const r = await fetch(url);
    
    if (!r.ok) {
      const errData = await r.json().catch(() => ({}));
      console.error('❌ Error listar:', r.status, errData);
      throw new Error(errData.error || `Error ${r.status}`);
    }
    
    const data = await r.json();
    console.log('✅ Categorías cargadas:', data.items?.length || 0);
    return data;
  } catch (e) {
    console.error('Error en apiListarCategorias:', e);
    throw new Error(e.message || 'No se pudo listar categorías');
  }
}

async function apiCrearCategoria(payload) {
  try {
    console.log('📤 POST /categorias:', JSON.stringify(payload, null, 2));
    
    const r = await fetch(EP.apiCrearCategoria, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const dj = await r.json();
    console.log('📥 Response:', dj);
    
    if (!r.ok || !dj.ok) {
      console.error('❌ Error crear:', r.status, dj);
      throw new Error(dj.error || `Error ${r.status}`);
    }
    
    console.log('✅ Categoría creada:', dj.categoria?.id);
    return dj;
  } catch (e) {
    console.error('Error en apiCrearCategoria:', e);
    throw new Error(e.message || 'No fue posible crear la categoría');
  }
}

async function apiActualizarCategoria(id, payload) {
  try {
    const url = EP.apiActualizarTemplate.replace(/\/0$/, `/${id}`);
    console.log('📤 PATCH:', url, JSON.stringify(payload, null, 2));
    
    const r = await fetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const dj = await r.json();
    console.log('📥 Response:', dj);
    
    if (!r.ok || !dj.ok) {
      console.error('❌ Error actualizar:', r.status, dj);
      throw new Error(dj.error || `Error ${r.status}`);
    }
    
    console.log('✅ Categoría actualizada:', id);
    return dj;
  } catch (e) {
    console.error('Error en apiActualizarCategoria:', e);
    throw new Error(e.message || 'No fue posible actualizar la categoría');
  }
}

async function apiEliminarCategoria(id) {
  try {
    const url = EP.apiEliminarTemplate.replace(/\/0$/, `/${id}`);
    console.log('📤 DELETE:', url);
    
    const r = await fetch(url, { method: 'DELETE' });
    const dj = await r.json();
    
    console.log('📥 Response:', dj);
    
    if (!r.ok || !dj.ok) {
      console.error('❌ Error eliminar:', r.status, dj);
      throw new Error(dj.error || `Error ${r.status}`);
    }
    
    console.log('✅ Categoría eliminada:', id);
    return dj;
  } catch (e) {
    console.error('Error en apiEliminarCategoria:', e);
    throw new Error(e.message || 'No fue posible eliminar la categoría');
  }
}

/* ===========================
   Render Table, Resumen, Paginación
=========================== */
function renderTable(items) {
  let rows = [...items];

  const q = (STATE.q || '').toLowerCase();
  if (q) {
    rows = rows.filter(c =>
      (c.nombre || '').toLowerCase().includes(q) ||
      (c.slug || '').toLowerCase().includes(q)
    );
  }

  if (STATE.orden === 'nombre') {
    rows.sort((a, b) => (a.nombre || '').localeCompare(b.nombre || ''));
  }

  tbody.innerHTML = rows.map(c => `
    <tr class="table-row">
      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${c.id}</td>
      <td class="px-6 py-4 whitespace-nowrap">
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium text-gray-900">${c.nombre ?? ''}</span>
          ${c.padre_id ? '' : '<span class="badge badge-root">raíz</span>'}
        </div>
      </td>
      <td class="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-800">${c.slug ?? ''}</td>
      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">${c.padre_id ?? '—'}</td>
      <td class="px-6 py-4 whitespace-nowrap text-sm">
        <div class="flex items-center gap-2">
          <button class="btn-edit px-3 py-2 text-blue-600 hover:bg-blue-50 rounded" data-id="${c.id}">
            <i class="fas fa-edit"></i>
          </button>
          <button class="btn-delete px-3 py-2 text-red-600 hover:bg-red-50 rounded" data-id="${c.id}">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </td>
    </tr>
  `).join('');

  bindRowActions();
}

function renderResumen(total) {
  const start = total === 0 ? 0 : ((STATE.page - 1) * STATE.per_page + 1);
  const end = Math.min(STATE.page * STATE.per_page, total);
  lblResumen.textContent = `Mostrando ${start} a ${end} de ${total} categorías`;
}

function renderPaginacion(total) {
  const totalPages = Math.max(1, Math.ceil(total / STATE.per_page));
  const btn = (label, pageNum, active=false, disabled=false) => `
    <button data-page="${pageNum}"
            class="px-3 py-2 text-sm ${active ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg' : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-all'}"
            ${disabled ? 'disabled' : ''}>
      ${label}
    </button>`;
  let html = '';
  html += btn('Anterior', Math.max(1, STATE.page - 1), false, STATE.page === 1);
  for (let i = 1; i <= Math.min(totalPages, 3); i++) {
    html += btn(String(i), i, STATE.page === i);
  }
  if (totalPages > 3) {
    html += `<span class="text-gray-400 px-2">...</span>`;
    html += btn(String(totalPages), totalPages, STATE.page === totalPages);
  }
  html += btn('Siguiente', Math.min(totalPages, STATE.page + 1), false, STATE.page === totalPages);

  paginacion.innerHTML = html;
  paginacion.querySelectorAll('button[data-page]').forEach(b => {
    b.addEventListener('click', (e) => {
      const nextPage = parseInt(e.currentTarget.getAttribute('data-page'), 10);
      if (nextPage && nextPage !== STATE.page) {
        STATE.page = nextPage;
        loadCategorias();
      }
    });
  });
}

/* ===========================
   Modal Crear/Editar
=========================== */
function openModal(editId = null, cat = null, listaPadres = []) {
  STATE.editId = editId;
  modalTitulo.textContent = editId ? 'Editar categoría' : 'Nueva categoría';
  inpNombre.value = cat?.nombre || '';
  inpSlug.value = cat?.slug || '';
  txtDescripcion.value = cat?.descripcion || '';

  selPadre.innerHTML = `<option value="">(Sin padre) — raíz</option>` +
    listaPadres.map(c => `<option value="${c.id}">${c.nombre}</option>`).join('');
  selPadre.value = cat?.padre_id || '';

  modal.classList.add('modal-open');
}

function closeModal() {
  modal.classList.remove('modal-open');
  STATE.editId = null;
}

/* ===========================
   Modal Eliminar Categoría
=========================== */
function mostrarModalEliminarCategoria(id, nombre) {
  let modalEliminar = document.getElementById('modalEliminarCategoria');
  
  if (!modalEliminar) {
    modalEliminar = document.createElement('div');
    modalEliminar.id = 'modalEliminarCategoria';
    document.body.appendChild(modalEliminar);
  }

  modalEliminar.className = 'fixed inset-0 bg-black/50 backdrop-blur-sm z-[9999] hidden items-center justify-center p-4';
  modalEliminar.innerHTML = `
    <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 modal-content-eliminar animate-slideUp">
      <div class="text-center mb-6">
        <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4 pulse-danger">
          <i class="fas fa-trash text-red-600 text-2xl"></i>
        </div>
        <h2 class="text-2xl font-bold text-gray-900 mb-2">Eliminar categoría</h2>
        <p class="text-gray-600">¿Estás seguro de que quieres eliminar esta categoría?</p>
      </div>

      <div class="bg-gray-50 rounded-xl p-4 mb-6">
        <div class="flex items-center space-x-4">
          <div class="w-16 h-16 bg-gradient-to-br from-red-500 to-red-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <i class="fas fa-tag text-white text-2xl"></i>
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="font-semibold text-gray-900 truncate">${nombre}</h3>
            <p class="text-sm text-gray-600 mt-1">ID: ${id}</p>
          </div>
        </div>
      </div>

      <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <div class="flex items-start">
          <i class="fas fa-exclamation-triangle text-red-500 mr-3 mt-0.5"></i>
          <div class="text-sm">
            <p class="text-red-800 font-medium">Esta acción no se puede deshacer</p>
            <p class="text-red-700 mt-1">La categoría será eliminada permanentemente.</p>
          </div>
        </div>
      </div>

      <div class="flex space-x-3">
        <button onclick="cerrarModalEliminarCategoria()" 
                class="flex-1 px-6 py-3 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition-all font-medium">
          <i class="fas fa-times mr-2"></i> Cancelar
        </button>
        <button onclick="confirmarEliminarCategoriaFinal(${id})" 
                class="flex-1 px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl transition-all font-medium shadow-lg btn-confirmar-eliminar">
          <i class="fas fa-check mr-2"></i> Confirmar
        </button>
      </div>
    </div>
  `;

  modalEliminar.classList.remove('hidden');
  modalEliminar.style.display = 'flex';

  modalEliminar.addEventListener('click', (e) => {
    if (e.target === modalEliminar) cerrarModalEliminarCategoria();
  });

  const handleEsc = (e) => {
    if (e.key === 'Escape' && modalEliminar.style.display === 'flex') {
      cerrarModalEliminarCategoria();
      document.removeEventListener('keydown', handleEsc);
    }
  };
  document.addEventListener('keydown', handleEsc);
}

function cerrarModalEliminarCategoria() {
  const modal = document.getElementById('modalEliminarCategoria');
  if (modal) {
    modal.classList.add('hidden');
    modal.style.display = 'none';
  }
}

async function confirmarEliminarCategoriaFinal(id) {
  const modal = document.getElementById('modalEliminarCategoria');
  const btnConfirmar = modal.querySelector('.btn-confirmar-eliminar');
  
  btnConfirmar.disabled = true;
  btnConfirmar.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Eliminando...';

  try {
    await apiEliminarCategoria(id);
    showNotification('Categoría eliminada', 'La categoría ha sido eliminada correctamente', 'success');
    cerrarModalEliminarCategoria();
    loadCategorias();
  } catch (err) {
    console.error(err);
    showNotification('Error', err.message, 'error');
    btnConfirmar.disabled = false;
    btnConfirmar.innerHTML = '<i class="fas fa-check mr-2"></i> Confirmar';
  }
}

window.mostrarModalEliminarCategoria = mostrarModalEliminarCategoria;
window.cerrarModalEliminarCategoria = cerrarModalEliminarCategoria;
window.confirmarEliminarCategoriaFinal = confirmarEliminarCategoriaFinal;

/* ===========================
   Bind Row Actions
=========================== */
function bindRowActions() {
  document.querySelectorAll('.btn-edit').forEach(b => {
    b.addEventListener('click', async (e) => {
      const id = e.currentTarget.getAttribute('data-id');
      const data = await apiListarCategorias();
      const items = data.items || [];
      const cat = items.find(x => String(x.id) === String(id));
      const padres = items.filter(x => !x.padre_id && String(x.id) !== String(id));
      openModal(id, cat, padres);
    });
  });

  document.querySelectorAll('.btn-delete').forEach(b => {
    b.addEventListener('click', (e) => {
      const id = e.currentTarget.getAttribute('data-id');
      const fila = e.currentTarget.closest('tr');
      const nombre = fila.querySelector('td:nth-child(2)').textContent.trim();
      mostrarModalEliminarCategoria(id, nombre);
    });
  });
}

/* ===========================
   Init Handlers
=========================== */
function initHandlers() {
  let t;
  txtSearch.addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(() => {
      STATE.q = txtSearch.value.trim();
      loadCategorias();
    }, 250);
  });

  selOrden.addEventListener('change', () => {
    STATE.orden = selOrden.value;
    loadCategorias();
  });

  selPadreFiltro.addEventListener('change', () => {
    STATE.padre_id = selPadreFiltro.value;
    STATE.page = 1;
    loadCategorias();
  });

  btnNuevaCategoria.addEventListener('click', async () => {
    const data = await apiListarCategorias();
    const items = data.items || [];
    const padres = items.filter(x => !x.padre_id);
    openModal(null, null, padres);
  });

  [btnCerrarModal, btnCancelar].forEach(btn => btn.addEventListener('click', closeModal));

  inpNombre.addEventListener('input', () => {
    if (!inpSlug.value || inpSlug.dataset.touched !== 'true') {
      inpSlug.value = slugify(inpNombre.value || '');
    }
  });
  inpSlug.addEventListener('input', () => { inpSlug.dataset.touched = 'true'; });

  btnGuardar.addEventListener('click', async () => {
    const nombre = (inpNombre.value || '').trim();
    if (!nombre) {
      showNotification('Faltan datos', 'El nombre es obligatorio', 'warning');
      return;
    }

    const payload = {
      nombre,
      slug: (inpSlug.value || slugify(nombre)).trim(),
      descripcion: (txtDescripcion.value || '').trim(),
      padre_id: selPadre.value ? Number(selPadre.value) : null
    };

    console.log('🔍 Payload a enviar:', payload);

    try {
      if (STATE.editId) {
        await apiActualizarCategoria(STATE.editId, payload);
        showNotification('Actualizada', 'Categoría actualizada', 'success');
      } else {
        await apiCrearCategoria(payload);
        showNotification('Creada', 'Categoría creada', 'success');
      }
      closeModal();
      loadCategorias();
    } catch (err) {
      console.error(err);
      showNotification('Error', err.message, 'error');
    }
  });
}

/* ===========================
   Load Categorías
=========================== */
async function loadCategorias() {
  try {
    const data = await apiListarCategorias();
    const items = data.items || [];
    STATE.total = data.total || items.length;

    if (!selPadreFiltro.dataset.init) {
      const roots = items.filter(x => !x.padre_id);
      selPadreFiltro.innerHTML = `<option value="">(Todas) Solo raíces</option>` +
        roots.map(r => `<option value="${r.id}">${r.nombre}</option>`).join('');
      selPadreFiltro.dataset.init = '1';
    }

    let visibles = items;
    if (STATE.padre_id) {
      visibles = items.filter(x => String(x.padre_id || '') === String(STATE.padre_id));
      STATE.total = visibles.length;
    }

    renderTable(visibles);
    renderResumen(STATE.total);
    renderPaginacion(STATE.total);
  } catch (e) {
    console.error(e);
    showNotification('Error', 'No se pudo cargar categorías', 'error');
  }
}

/* ===========================
   Boot
=========================== */
document.addEventListener('DOMContentLoaded', () => {
  console.log('🚀 Iniciando categorías...');
  console.log('📍 Endpoints:', EP);
  initHandlers();
  loadCategorias();
  showNotification('Listo', 'Gestión de categorías lista para usar', 'success');
});