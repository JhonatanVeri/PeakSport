/* ===========================
   Helpers
=========================== */
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

function toCents(value) {
  const n = Number(value);
  if (isNaN(n) || n < 0) return 0;
  return Math.round(n * 100);
}

/* ===========================
   Refs & State
=========================== */
const EP = window.__ADMIN_ENDPOINTS__;
const PRODUCTO_ID = window.__PRODUCTO_ID__;

const inpNombre = document.getElementById('inpNombre');
const inpSlug = document.getElementById('inpSlug');
const inpPrecio = document.getElementById('inpPrecio');
const inpStock = document.getElementById('inpStock');
const selMoneda = document.getElementById('selMoneda');
const txtDescripcion = document.getElementById('txtDescripcion');
const chkActivo = document.getElementById('chkActivo');

const listaCategorias = document.getElementById('listaCategorias');

const imagenesGrid = document.getElementById('imagenesGrid');
const inpFiles = document.getElementById('inpFiles');

const btnGuardar = document.getElementById('btnGuardar');

let IMAGENES = []; // [{id,url,alt,orden,es_portada}...]

/* ===========================
   Carga inicial
=========================== */
async function cargarProducto() {
  try {
    const r = await fetch(EP.apiDetalle);
    if (!r.ok) throw new Error('No se pudo cargar el producto');
    const dj = await r.json();
    if (!dj.ok) throw new Error('Respuesta inválida');
    const p = dj.producto;

    // Datos básicos
    inpNombre.value = p.nombre || '';
    inpSlug.value = p.slug || '';
    inpPrecio.value = ((p.precio_centavos || 0) / 100).toFixed(2);
    inpStock.value = p.stock || 0;
    selMoneda.value = p.moneda || 'COP';
    txtDescripcion.value = p.descripcion || '';
    chkActivo.checked = !!p.activo;

    // Categorías (marcar checks que ya están)
    const seleccionadas = new Set((p.categorias || []).map(c => c.id));
    listaCategorias.querySelectorAll('.categoria-check').forEach(ch => {
      ch.checked = seleccionadas.has(parseInt(ch.value, 10));
    });

    // Imágenes
    await cargarImagenes();
  } catch (e) {
    console.error(e);
    showNotification('Error', e.message, 'error');
  }
}

async function cargarImagenes() {
  try {
    const r = await fetch(EP.apiListarImagenes);
    if (!r.ok) throw new Error('No se pudieron cargar imágenes');
    const dj = await r.json();
    IMAGENES = dj.items || [];
    renderImagenes();
  } catch (e) {
    console.error(e);
    showNotification('Error', e.message, 'error');
  }
}

/* ===========================
   Guardar datos
=========================== */
btnGuardar.addEventListener('click', async () => {
  const payload = {
    nombre: inpNombre.value.trim(),
    slug: inpSlug.value.trim(),
    precio_centavos: toCents(inpPrecio.value),
    stock: parseInt(inpStock.value) || 0,
    moneda: (selMoneda.value || 'COP').toUpperCase(),
    descripcion: txtDescripcion.value.trim(),
    activo: !!chkActivo.checked
  };
  if (!payload.nombre) {
    showNotification('Faltan datos', 'El nombre es obligatorio', 'warning');
    return;
  }

  try {
    const r = await fetch(EP.apiActualizar, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const dj = await r.json();
    if (!r.ok || !dj.ok) throw new Error(dj.error || 'No fue posible guardar');
    showNotification('Guardado', 'Cambios aplicados', 'success');
  } catch (e) {
    console.error(e);
    showNotification('Error', e.message, 'error');
  }
});

/* ===========================
   Categorías (toggle inmediato) - ÚNICO LISTENER
=========================== */
listaCategorias.addEventListener('change', async (e) => {
  const target = e.target;
  if (!target.classList.contains('categoria-check')) return;
  const categoriaId = parseInt(target.value, 10);
  try {
    if (target.checked) {
      // ✅ CORRECTO: Usar JSON en lugar de URLSearchParams
      const r = await fetch(EP.apiAgregarCategoriaBase, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ categoria_id: categoriaId })
      });
      const dj = await r.json();
      if (!r.ok || !dj.ok) {
        throw new Error(dj.error || 'No se pudo asociar');
      }
      showNotification('Categoría', 'Asociada', 'success');
    } else {
      // DELETE ya está bien
      const url = `${EP.apiQuitarCategoriaBase}${categoriaId}`;
      const r = await fetch(url, { method: 'DELETE' });
      const dj = await r.json();
      if (!r.ok || !dj.ok) throw new Error(dj.error || 'No se pudo quitar');
      showNotification('Categoría', 'Removida', 'success');
    }
  } catch (e2) {
    console.error(e2);
    showNotification('Error', e2.message, 'error');
    target.checked = !target.checked;
  }
});

/* ===========================
   Imágenes (listar / subir / acciones)
=========================== */
function renderImagenes() {
  imagenesGrid.innerHTML = IMAGENES.map((img, idx) => {
    return `
      <div class="img-card" data-id="${img.id}" data-idx="${idx}">
        <img class="img-thumb" src="${img.url}" alt="${img.alt ?? ''}">
        <div>
          <div class="flex items-center gap-2">
            <span class="img-title">ID ${img.id}</span>
            ${img.es_portada ? `<span class="badge-portada"><i class="fas fa-star"></i> Portada</span>` : ''}
          </div>
          <div class="mt-2">
            <input class="img-alt" type="text" placeholder="Texto alternativo"
                   value="${(img.alt ?? '').replace(/"/g,'&quot;')}" data-id="${img.id}">
          </div>
          <div class="text-xs text-gray-500 mt-1">Orden: ${img.orden}</div>
        </div>
        <div class="img-actions">
          <button class="btn-icon btn-primary btn-up" title="Subir orden" data-id="${img.id}">
            <i class="fas fa-arrow-up"></i>
          </button>
          <button class="btn-icon btn-primary btn-down" title="Bajar orden" data-id="${img.id}">
            <i class="fas fa-arrow-down"></i>
          </button>
          <button class="btn-icon btn-primary btn-star ${img.es_portada ? 'active' : ''}" title="Marcar portada" data-id="${img.id}">
            <i class="fas fa-star"></i>
          </button>
          <button class="btn-icon btn-danger btn-del" title="Eliminar" data-id="${img.id}">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>
    `;
  }).join('');

  // ALT change (debounce)
  imagenesGrid.querySelectorAll('.img-alt').forEach(inp => {
    let t;
    inp.addEventListener('input', (e) => {
      clearTimeout(t);
      const id = parseInt(e.currentTarget.dataset.id, 10);
      const val = e.currentTarget.value;
      t = setTimeout(() => actualizarImagen(id, { alt: val }), 400);
    });
  });

  // Orden up/down
  imagenesGrid.querySelectorAll('.btn-up').forEach(b => {
    b.addEventListener('click', () => moverOrden(parseInt(b.dataset.id,10), -1));
  });
  imagenesGrid.querySelectorAll('.btn-down').forEach(b => {
    b.addEventListener('click', () => moverOrden(parseInt(b.dataset.id,10), +1));
  });

  // Portada
  imagenesGrid.querySelectorAll('.btn-star').forEach(b => {
    b.addEventListener('click', () => marcarPortada(parseInt(b.dataset.id,10)));
  });

  // Eliminar
  imagenesGrid.querySelectorAll('.btn-del').forEach(b => {
    b.addEventListener('click', () => eliminarImagen(parseInt(b.dataset.id,10)));
  });
}

async function actualizarImagen(imagenId, campos) {
  try {
    const r = await fetch(`${EP.apiActualizarImagen}${imagenId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(campos)
    });
    const dj = await r.json();
    if (!r.ok || !dj.ok) throw new Error(dj.error || 'No se pudo actualizar');
    showNotification('Imagen', 'Actualizada', 'success');
  } catch (e) {
    console.error(e);
    showNotification('Error', e.message, 'error');
  }
}

async function moverOrden(imagenId, delta) {
  const idx = IMAGENES.findIndex(i => i.id === imagenId);
  if (idx === -1) return;
  const current = IMAGENES[idx];
  const nuevoOrden = (current.orden || 0) + delta;
  if (nuevoOrden < 0) return;

  try {
    const r = await fetch(`${EP.apiActualizarImagen}${imagenId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ orden: nuevoOrden })
    });
    const dj = await r.json();
    if (!r.ok || !dj.ok) throw new Error(dj.error || 'No se pudo reordenar');
    await cargarImagenes();
  } catch (e) {
    console.error(e);
    showNotification('Error', e.message, 'error');
  }
}

async function marcarPortada(imagenId) {
  try {
    const r = await fetch(`${EP.apiActualizarImagen}${imagenId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ es_portada: true })
    });
    const dj = await r.json();
    if (!r.ok || !dj.ok) throw new Error(dj.error || 'No se pudo marcar portada');
    await cargarImagenes();
    showNotification('Portada', 'Actualizada', 'success');
  } catch (e) {
    console.error(e);
    showNotification('Error', e.message, 'error');
  }
}

async function eliminarImagen(imagenId) {
  const imagen = IMAGENES.find(i => i.id === imagenId);
  if (!imagen) {
    showNotification('Error', 'Imagen no encontrada', 'error');
    return;
  }
  
  mostrarModalEliminarImagen(imagenId, imagen.url);
}

inpFiles.addEventListener('change', async (e) => {
  const files = Array.from(e.target.files || []);
  if (!files.length) return;
  const form = new FormData();
  files.forEach(f => form.append('files', f));
  try {
    const r = await fetch(EP.apiSubirImagenes, { method: 'POST', body: form });
    const dj = await r.json();
    if (!r.ok || !dj.ok) throw new Error(dj.error || 'Error al subir imágenes');
    await cargarImagenes();
    showNotification('Imágenes', 'Cargadas', 'success');
    inpFiles.value = '';
  } catch (e2) {
    console.error(e2);
    showNotification('Error', e2.message, 'error');
  }
});

/* ===========================
   Modal Eliminar Imagen
=========================== */

function mostrarModalEliminarImagen(imagenId, imagenUrl) {
  let modal = document.getElementById('modalEliminarImagenEditar');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'modalEliminarImagenEditar';
    modal.className = 'fixed inset-0 bg-black/50 flex items-center justify-center z-50 hidden';
    modal.innerHTML = `
      <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 modal-content-imagen-editar">
        <!-- Contenido aquí -->
      </div>
    `;
    document.body.appendChild(modal);
  }

  const content = modal.querySelector('.modal-content-imagen-editar');
  
  content.innerHTML = `
    <div class="p-6">
      <div class="text-center mb-6">
        <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4 pulse-danger">
          <i class="fas fa-trash text-red-600 text-2xl"></i>
        </div>
        <h2 class="text-2xl font-bold text-gray-900 mb-2">Eliminar esta imagen</h2>
        <p class="text-gray-600">¿Estás seguro de que quieres eliminar esta imagen?</p>
      </div>

      <div class="bg-gray-50 rounded-xl p-4 mb-6">
        <div class="flex items-center space-x-4">
          <div class="w-16 h-16 bg-gradient-to-br from-red-600 to-black rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden">
            <img src="${imagenUrl}" alt="Imagen a eliminar" class="w-full h-full object-cover">
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="font-semibold text-gray-900 truncate">Imagen ID: ${imagenId}</h3>
            <p class="text-sm text-gray-600 mt-1">Será eliminada permanentemente</p>
          </div>
        </div>
      </div>

      <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <div class="flex items-start">
          <i class="fas fa-exclamation-triangle text-red-500 mr-3 mt-0.5"></i>
          <div class="text-sm">
            <p class="text-red-800 font-medium">Esta acción no se puede deshacer</p>
            <p class="text-red-700 mt-1">La imagen será eliminada del servidor.</p>
          </div>
        </div>
      </div>

      <div class="flex space-x-3">
        <button onclick="cerrarModalEliminarImagenEditar()" 
                class="flex-1 px-6 py-3 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition-all font-medium">
          <i class="fas fa-times mr-2"></i> Cancelar
        </button>
        <button onclick="confirmarEliminarImagenEditar(${imagenId})" 
                class="flex-1 px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl transition-all font-medium shadow-lg">
          <i class="fas fa-check mr-2"></i> Confirmar
        </button>
      </div>
    </div>
  `;

  modal.classList.remove('hidden');
  modal.style.display = 'flex';

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      cerrarModalEliminarImagenEditar();
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.style.display === 'flex') {
      cerrarModalEliminarImagenEditar();
    }
  });
}

function cerrarModalEliminarImagenEditar() {
  const modal = document.getElementById('modalEliminarImagenEditar');
  if (modal) {
    modal.classList.add('hidden');
    modal.style.display = 'none';
  }
}

function confirmarEliminarImagenEditar(imagenId) {
  eliminarImagenConfirmado(imagenId);
  cerrarModalEliminarImagenEditar();
}

async function eliminarImagenConfirmado(imagenId) {
  try {
    const r = await fetch(`${EP.apiEliminarImagen}${imagenId}`, { method: 'DELETE' });
    const dj = await r.json();
    if (!r.ok || !dj.ok) throw new Error(dj.error || 'No se pudo eliminar imagen');
    await cargarImagenes();
    showNotification('Imagen', 'Eliminada correctamente', 'success');
  } catch (e) {
    console.error(e);
    showNotification('Error', e.message, 'error');
  }
}

// Hacer funciones globales
window.mostrarModalEliminarImagen = mostrarModalEliminarImagen;
window.cerrarModalEliminarImagenEditar = cerrarModalEliminarImagenEditar;
window.confirmarEliminarImagenEditar = confirmarEliminarImagenEditar;

/* ===========================
   Boot
=========================== */
document.addEventListener('DOMContentLoaded', () => {
  cargarProducto();
  showNotification('Editor', `Producto #${PRODUCTO_ID}`, 'info');
});