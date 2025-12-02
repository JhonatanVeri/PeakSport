/* ===========================
   Config
=========================== */

const EP = window.__ADMIN_ENDPOINTS__;
let imagenesCargadas = [];

const FORM = {
  nombre: '',
  slug: '',
  precio: 0,
  stock: 0,
  moneda: 'COP',
  sku: '',
  descripcion: '',
  activo: true,
  categorias: []
};

/* ===========================
   Utils
=========================== */

function slugify(text) {
  return text
    .toLowerCase()
    .trim()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-+|-+$/g, '');
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

  const cfg = config[type] || config.info;
  icon.className = `w-10 h-10 ${cfg.color} rounded-full flex items-center justify-center`;
  icon.innerHTML = `<i class="${cfg.icon} text-white"></i>`;

  titleEl.textContent = title;
  messageEl.textContent = message;

  n.classList.remove('translate-x-full');
  setTimeout(() => n.classList.add('translate-x-full'), 3500);
}

/* ===========================
   Validación
=========================== */

function validarFormulario() {
  const nombre = document.getElementById('inpNombre').value.trim();
  const precio = parseFloat(document.getElementById('inpPrecio').value) || 0;
  const stock = parseInt(document.getElementById('inpStock').value) || 0;

  if (!nombre) {
    showNotification('Error', 'El nombre del producto es obligatorio', 'error');
    return false;
  }

  if (precio <= 0) {
    showNotification('Error', 'El precio debe ser mayor a 0', 'error');
    return false;
  }

  if (stock < 0) {
    showNotification('Error', 'El stock no puede ser negativo', 'error');
    return false;
  }

  return true;
}

/* ===========================
   Categorías
=========================== */

async function cargarCategorias() {
  try {
    const resp = await fetch(EP.apiListarCategorias);
    if (!resp.ok) throw new Error('Error al cargar categorías');
    const data = await resp.json();
    
    const lista = document.getElementById('listaCategorias');
    
    if (!data.items || data.items.length === 0) {
      lista.innerHTML = '<p class="text-sm text-gray-500 col-span-3">No hay categorías disponibles.</p>';
      return;
    }

    lista.innerHTML = data.items.map(c => `
      <label class="flex items-center gap-2 px-3 py-2 border rounded-xl hover:bg-gray-50 cursor-pointer transition">
        <input type="checkbox" class="h-4 w-4 categoria-check" value="${c.id}" data-nombre="${c.nombre}">
        <span class="text-sm">${c.nombre}</span>
      </label>
    `).join('');

    document.querySelectorAll('.categoria-check').forEach(chk => {
      chk.addEventListener('change', (e) => {
        const id = parseInt(e.target.value);
        if (e.target.checked) {
          if (!FORM.categorias.includes(id)) FORM.categorias.push(id);
        } else {
          FORM.categorias = FORM.categorias.filter(cid => cid !== id);
        }
      });
    });
  } catch (error) {
    console.error('Error cargando categorías:', error);
    showNotification('Error', 'No se pudieron cargar las categorías', 'error');
  }
}

/* ===========================
   Imágenes
=========================== */

function renderizarImagenes() {
  const grid = document.getElementById('imagenesGrid');
  
  if (imagenesCargadas.length === 0) {
    grid.innerHTML = `
      <i class="fas fa-image text-gray-300 text-4xl mb-2"></i>
      <p class="text-gray-500 text-sm">Sube imágenes del producto aquí</p>
    `;
    return;
  }

  grid.innerHTML = imagenesCargadas.map((img, idx) => `
    <div class="relative inline-block">
      <div class="w-20 h-20 rounded-lg overflow-hidden border-2 ${img.portada ? 'border-yellow-400' : 'border-gray-200'} hover:border-purple-400 transition">
        <img src="${img.preview}" alt="Img ${idx + 1}" class="w-full h-full object-cover">
      </div>
      <div class="absolute -top-2 -right-2 flex gap-1">
        <button type="button" onclick="marcarPortada(${idx})" class="w-6 h-6 bg-yellow-400 hover:bg-yellow-500 rounded-full flex items-center justify-center transition" title="Portada">
          <i class="fas fa-star text-white text-xs"></i>
        </button>
        <button type="button" onclick="eliminarImagen(${idx})" class="w-6 h-6 bg-red-500 hover:bg-red-600 rounded-full flex items-center justify-center transition" title="Eliminar">
          <i class="fas fa-trash text-white text-xs"></i>
        </button>
      </div>
      ${img.portada ? '<div class="absolute bottom-1 left-1 bg-yellow-400 text-white px-1 rounded text-xs font-bold">Portada</div>' : ''}
    </div>
  `).join('');
}

function marcarPortada(idx) {
  imagenesCargadas.forEach((img, i) => {
    img.portada = i === idx;
  });
  renderizarImagenes();
}

function eliminarImagen(idx) {
  imagenesCargadas.splice(idx, 1);
  
  // Si eliminamos la portada, marcar la primera como portada
  if (imagenesCargadas.length > 0 && !imagenesCargadas.some(img => img.portada)) {
    imagenesCargadas[0].portada = true;
  }
  
  renderizarImagenes();
  showNotification('Imagen eliminada', 'La imagen fue removida', 'info');
}

function manejarArchivos(e) {
  const files = Array.from(e.target.files);
  
  if (imagenesCargadas.length + files.length > 5) {
    showNotification('Límite alcanzado', 'Máximo 5 imágenes por producto', 'warning');
    return;
  }

  files.forEach(file => {
    if (!file.type.startsWith('image/')) {
      showNotification('Archivo inválido', `${file.name} no es una imagen`, 'error');
      return;
    }

    if (file.size > 2 * 1024 * 1024) {
      showNotification('Archivo muy grande', `${file.name} supera 2MB`, 'error');
      return;
    }

    const reader = new FileReader();
    reader.onload = (ev) => {
      imagenesCargadas.push({
        file: file,
        preview: ev.target.result,
        portada: imagenesCargadas.length === 0
      });
      renderizarImagenes();
    };
    reader.readAsDataURL(file);
  });

  document.getElementById('inpFiles').value = '';
}

/* ===========================
   Crear Producto
=========================== */

async function crearProducto() {
  if (!validarFormulario()) return;

  const btnCrear = document.getElementById('btnCrear');
  btnCrear.disabled = true;
  btnCrear.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Creando producto...';

  try {
    // 1. Preparar datos del producto
    const datos = {
      nombre: document.getElementById('inpNombre').value.trim(),
      slug: document.getElementById('inpSlug').value.trim() || null,
      precio_centavos: Math.round(parseFloat(document.getElementById('inpPrecio').value) * 100),
      stock: parseInt(document.getElementById('inpStock').value) || 0,
      moneda: document.getElementById('selMoneda').value,
      sku: document.getElementById('inpSKU').value.trim() || null,
      descripcion: document.getElementById('txtDescripcion').value.trim(),
      activo: document.getElementById('chkActivo').checked
    };

    // 2. Crear producto
    const respCrear = await fetch(EP.apiCrear, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(datos)
    });

    const dataCrear = await respCrear.json();
    
    if (!respCrear.ok || !dataCrear.ok) {
      throw new Error(dataCrear.error || 'No se pudo crear el producto');
    }

    const productoId = dataCrear.id;
    console.log('✅ Producto creado con ID:', productoId);

    // 3. Asociar categorías (SI HAY SELECCIONADAS)
    if (FORM.categorias.length > 0) {
      btnCrear.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Asociando categorías...';
      
      for (const categoriaId of FORM.categorias) {
        try {
          const respCat = await fetch(`/administrador/principal/api/admin/productos/${productoId}/categorias`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ categoria_id: categoriaId })
          });
          
          if (!respCat.ok) {
            console.warn(`⚠️ No se pudo asociar categoría ${categoriaId}`);
          }
        } catch (err) {
          console.error(`Error asociando categoría ${categoriaId}:`, err);
        }
      }
      console.log('✅ Categorías asociadas');
    }

    // 4. Subir imágenes (SI HAY IMÁGENES) - ✅ CORREGIDO
    if (imagenesCargadas.length > 0) {
      btnCrear.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Subiendo imágenes...';
      
      const formData = new FormData();
      
      // Agregar archivos y sus alts
      imagenesCargadas.forEach((img) => {
        formData.append('files', img.file);
        // Enviar alt para cada archivo (backend espera getlist('alt'))
        const altText = img.file.name.split('.')[0];
        formData.append('alt', altText);
      });
      
      // Marcar la portada por índice
      const portadaIndex = imagenesCargadas.findIndex(img => img.portada);
      if (portadaIndex !== -1) {
        formData.append('portada_index', portadaIndex.toString());
      }

      console.log('📤 Subiendo', imagenesCargadas.length, 'imágenes al producto:', productoId);
      console.log('⭐ Índice de portada:', portadaIndex);
      console.log('📋 FormData preparado con files y alts');

      // ✅ USAR LA RUTA CORRECTA CON EL PREFIJO DEL BLUEPRINT
      const respImg = await fetch(`/administrador/principal/api/admin/productos/${productoId}/imagenes`, {
        method: 'POST',
        body: formData
      });

      const dataImg = await respImg.json();
      
      if (!respImg.ok) {
        console.error('❌ Error subiendo imágenes:', dataImg);
        console.error('📄 Respuesta del servidor:', dataImg);
        throw new Error(dataImg.error || 'No se pudieron subir las imágenes');
      }
      
      console.log('✅ Imágenes subidas correctamente:', dataImg);
    }

    // 5. Todo exitoso
    showNotification('¡Éxito!', 'Producto creado correctamente', 'success');
    
    setTimeout(() => {
      window.location.href = EP.vistaListado;
    }, 1500);

  } catch (error) {
    console.error('❌ Error:', error);
    showNotification('Error', error.message, 'error');
    btnCrear.disabled = false;
    btnCrear.innerHTML = '<i class="fas fa-plus mr-2"></i> Crear producto';
  }
}

/* ===========================
   Init
=========================== */

document.addEventListener('DOMContentLoaded', () => {
  cargarCategorias();

  // Inputs
  document.getElementById('inpNombre').addEventListener('input', (e) => {
    FORM.nombre = e.target.value.trim();
    const slugGenerado = slugify(FORM.nombre);
    document.getElementById('inpSlug').value = slugGenerado;
    FORM.slug = slugGenerado;
  });

  document.getElementById('inpSlug').addEventListener('input', (e) => {
    FORM.slug = e.target.value.trim();
  });

  document.getElementById('inpPrecio').addEventListener('input', (e) => {
    FORM.precio = parseFloat(e.target.value) || 0;
  });

  document.getElementById('inpStock').addEventListener('input', (e) => {
    FORM.stock = parseInt(e.target.value) || 0;
  });

  document.getElementById('selMoneda').addEventListener('change', (e) => {
    FORM.moneda = e.target.value;
  });

  document.getElementById('inpSKU').addEventListener('input', (e) => {
    FORM.sku = e.target.value.trim();
  });

  document.getElementById('txtDescripcion').addEventListener('input', (e) => {
    FORM.descripcion = e.target.value.trim();
  });

  document.getElementById('chkActivo').addEventListener('change', (e) => {
    FORM.activo = e.target.checked;
  });

  // Archivos
  document.getElementById('inpFiles').addEventListener('change', manejarArchivos);

  // Botón crear
  document.getElementById('btnCrear').addEventListener('click', crearProducto);

  showNotification('Sistema cargado', 'Listo para crear productos', 'info');
});

// Funciones globales
window.marcarPortada = marcarPortada;
window.eliminarImagen = eliminarImagen;