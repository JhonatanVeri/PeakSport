/**
 * =====================================================
 * ADMINISTRADOR DE RESEÑAS - PEAKSPORT
 * Versión Final Optimizada
 * =====================================================
 */

// ==================== ESTADO GLOBAL ====================
const AppState = {
    resenas: [],
    productos: [],
    filtros: {
        producto_id: '',
        estado: '',
        comentario: ''
    },
    paginacion: {
        actual: 1,
        total: 1,
        porPagina: 10
    },
    estadisticas: {
        total: 0,
        pendientes: 0,
        aprobadas: 0,
        rechazadas: 0,
        ocultas: 0
    },
    modalCallback: null,
    loading: false
};

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Iniciando aplicación de gestión de reseñas...');
    inicializarEventos();
    cargarProductos();
    cargarResenas();
});

// ==================== EVENT LISTENERS ====================
function inicializarEventos() {
    // Botón de refrescar
    const btnRefresh = document.getElementById('btnRefresh');
    if (btnRefresh) {
        btnRefresh.addEventListener('click', () => {
            btnRefresh.querySelector('i').classList.add('fa-spin');
            cargarResenas().finally(() => {
                btnRefresh.querySelector('i').classList.remove('fa-spin');
            });
            mostrarNotificacion('Datos actualizados', 'Las reseñas se han actualizado correctamente', 'success');
        });
    }

    // Botones de filtrado
    const btnFiltrar = document.getElementById('btnFiltrar');
    const btnLimpiar = document.getElementById('btnLimpiar');
    
    if (btnFiltrar) btnFiltrar.addEventListener('click', aplicarFiltros);
    if (btnLimpiar) btnLimpiar.addEventListener('click', limpiarFiltros);

    // Búsqueda con Enter
    const buscarComentario = document.getElementById('buscarComentario');
    if (buscarComentario) {
        buscarComentario.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') aplicarFiltros();
        });
    }

    // Modal - Botones
    const btnCancelarModal = document.getElementById('btnCancelarModal');
    const btnConfirmarModal = document.getElementById('btnConfirmarModal');
    
    if (btnCancelarModal) btnCancelarModal.addEventListener('click', cerrarModal);
    if (btnConfirmarModal) btnConfirmarModal.addEventListener('click', ejecutarAccionModal);

    // Cerrar modal al hacer clic fuera
    const modalConfirmacion = document.getElementById('modalConfirmacion');
    if (modalConfirmacion) {
        modalConfirmacion.addEventListener('click', (e) => {
            if (e.target.id === 'modalConfirmacion') cerrarModal();
        });
    }

    // Tecla ESC para cerrar modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') cerrarModal();
    });
}

// ==================== CARGAR DATOS ====================
async function cargarProductos() {
    try {
        const response = await fetch(window.API_ENDPOINTS.productos);
        if (!response.ok) throw new Error('Error al cargar productos');
        
        const data = await response.json();
        AppState.productos = data.productos || [];
        
        // Llenar el select de productos
        const select = document.getElementById('filtroProducto');
        if (select) {
            select.innerHTML = '<option value="">Todos los productos</option>';
            AppState.productos.forEach(p => {
                const option = document.createElement('option');
                option.value = p.id;
                option.textContent = p.nombre;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error cargando productos:', error);
    }
}

async function cargarResenas() {
    if (AppState.loading) return;
    
    try {
        AppState.loading = true;
        mostrarCargando();
        
        // Construir URL con parámetros
        const params = new URLSearchParams({
            page: AppState.paginacion.actual,
            per_page: AppState.paginacion.porPagina
        });

        if (AppState.filtros.producto_id) params.append('producto_id', AppState.filtros.producto_id);
        if (AppState.filtros.estado) params.append('estado', AppState.filtros.estado);
        if (AppState.filtros.comentario) params.append('q', AppState.filtros.comentario);

        const response = await fetch(`${window.API_ENDPOINTS.listar}?${params}`);
        if (!response.ok) throw new Error('Error al cargar reseñas');
        
        const data = await response.json();
        
        if (!data.ok) {
            throw new Error(data.error || 'Error en la respuesta');
        }
        
        // Actualizar estado
        AppState.resenas = data.resenas || [];
        
        // Calcular total de páginas
        const totalResenas = data.total || 0;
        AppState.paginacion.total = Math.ceil(totalResenas / AppState.paginacion.porPagina);
        AppState.paginacion.actual = data.page || 1;
        
        // Actualizar estadísticas
        calcularEstadisticas(totalResenas);

        renderizarTabla();
        renderizarPaginacion();
        actualizarKPIs();
        actualizarContador();

    } catch (error) {
        console.error('Error cargando reseñas:', error);
        mostrarNotificacion('Error', 'No se pudieron cargar las reseñas. Intenta nuevamente.', 'error');
        mostrarError();
    } finally {
        AppState.loading = false;
    }
}

function calcularEstadisticas(totalGlobal = null) {
    // Contar en las reseñas actuales (página actual)
    const stats = {
        total: totalGlobal || AppState.resenas.length,
        pendientes: AppState.resenas.filter(r => r.estado === 'pendiente').length,
        aprobadas: AppState.resenas.filter(r => r.estado === 'aprobada').length,
        rechazadas: AppState.resenas.filter(r => r.estado === 'rechazada').length,
        ocultas: AppState.resenas.filter(r => r.estado === 'oculta').length
    };
    
    AppState.estadisticas = stats;
}

// ==================== RENDERIZADO DE TABLA ====================
function renderizarTabla() {
    const tbody = document.getElementById('tablaResenasBody');
    if (!tbody) return;

    if (AppState.resenas.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="px-6 py-12 text-center text-gray-500">
                    <i class="fas fa-inbox text-5xl mb-4 text-gray-300"></i>
                    <p class="font-medium text-lg">No se encontraron reseñas</p>
                    <p class="text-sm mt-2">Intenta cambiar los filtros o agregar nuevas reseñas</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = AppState.resenas.map(resena => `
        <tr class="hover:bg-gray-50 transition-colors">
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                #${resena.id}
            </td>
            <td class="px-6 py-4 text-sm">
                <div class="font-medium text-gray-900 max-w-xs truncate" title="${escapeHtml(resena.producto_nombre || 'N/A')}">
                    ${escapeHtml(resena.producto_nombre || 'N/A')}
                </div>
            </td>
            <td class="px-6 py-4 text-sm">
                <div class="flex items-center gap-2">
                    <div class="w-8 h-8 bg-gradient-to-br from-red-500 to-red-700 rounded-full flex items-center justify-center text-white font-bold text-xs">
                        ${obtenerIniciales(resena.usuario_nombre || 'Usuario')}
                    </div>
                    <span class="text-gray-900">${escapeHtml(resena.usuario_nombre || 'Anónimo')}</span>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm">
                <div class="flex items-center gap-1">
                    ${renderizarEstrellas(resena.calificacion)}
                </div>
                <div class="text-xs text-gray-500 mt-1">${resena.calificacion}/5</div>
            </td>
            <td class="px-6 py-4 text-sm text-gray-600">
                <div class="max-w-xs">
                    <p class="line-clamp-2" title="${escapeHtml(resena.comentario || 'Sin comentario')}">
                        ${escapeHtml(resena.comentario || 'Sin comentario')}
                    </p>
                    ${resena.comentario && resena.comentario.length > 80 ? 
                        `<button onclick="verComentarioCompleto(${resena.id})" class="text-red-600 hover:text-red-700 text-xs font-medium mt-1">
                            Ver completo →
                        </button>` : ''}
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                ${renderizarBadgeEstado(resena.estado)}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-center">
                <div class="flex items-center justify-center gap-2">
                    ${renderizarBotonesAccion(resena)}
                </div>
            </td>
        </tr>
    `).join('');
}

function renderizarEstrellas(calificacion) {
    const stars = [];
    for (let i = 1; i <= 5; i++) {
        if (i <= calificacion) {
            stars.push('<i class="fas fa-star text-yellow-400"></i>');
        } else {
            stars.push('<i class="far fa-star text-gray-300"></i>');
        }
    }
    return stars.join('');
}

function renderizarBadgeEstado(estado) {
    const badges = {
        'pendiente': '<span class="badge badge-pendiente"><i class="fas fa-clock mr-1"></i>Pendiente</span>',
        'aprobada': '<span class="badge badge-aprobada"><i class="fas fa-check mr-1"></i>Aprobada</span>',
        'rechazada': '<span class="badge badge-rechazada"><i class="fas fa-times mr-1"></i>Rechazada</span>',
        'oculta': '<span class="badge badge-oculta"><i class="fas fa-eye-slash mr-1"></i>Oculta</span>'
    };
    return badges[estado] || `<span class="badge">${escapeHtml(estado)}</span>`;
}

function renderizarBotonesAccion(resena) {
    const botones = [];

    // Botón Aprobar
    if (resena.estado === 'pendiente' || resena.estado === 'rechazada' || resena.estado === 'oculta') {
        botones.push(`
            <button onclick="abrirModalAprobar(${resena.id})" 
                    class="text-green-600 hover:text-green-800 hover:bg-green-50 p-2 rounded-lg transition-all"
                    title="Aprobar reseña">
                <i class="fas fa-check"></i>
            </button>
        `);
    }

    // Botón Rechazar
    if (resena.estado === 'pendiente' || resena.estado === 'aprobada') {
        botones.push(`
            <button onclick="abrirModalRechazar(${resena.id})" 
                    class="text-red-600 hover:text-red-800 hover:bg-red-50 p-2 rounded-lg transition-all"
                    title="Rechazar reseña">
                <i class="fas fa-times"></i>
            </button>
        `);
    }

    // Botón Ocultar/Restaurar
    if (resena.visible) {
        botones.push(`
            <button onclick="abrirModalOcultar(${resena.id})" 
                    class="text-purple-600 hover:text-purple-800 hover:bg-purple-50 p-2 rounded-lg transition-all"
                    title="Ocultar reseña">
                <i class="fas fa-eye-slash"></i>
            </button>
        `);
    } else {
        botones.push(`
            <button onclick="abrirModalRestaurar(${resena.id})" 
                    class="text-blue-600 hover:text-blue-800 hover:bg-blue-50 p-2 rounded-lg transition-all"
                    title="Restaurar visibilidad">
                <i class="fas fa-eye"></i>
            </button>
        `);
    }

    // Botón Eliminar
    botones.push(`
        <button onclick="abrirModalEliminar(${resena.id})" 
                class="text-gray-600 hover:text-gray-800 hover:bg-gray-100 p-2 rounded-lg transition-all"
                title="Eliminar permanentemente">
            <i class="fas fa-trash"></i>
        </button>
    `);

    return botones.join('');
}

// ==================== PAGINACIÓN ====================
function renderizarPaginacion() {
    const container = document.getElementById('paginacion');
    if (!container) return;

    if (AppState.paginacion.total <= 1) {
        container.innerHTML = '';
        return;
    }

    const botones = [];

    // Botón Anterior
    botones.push(`
        <button onclick="cambiarPagina(${AppState.paginacion.actual - 1})"
                ${AppState.paginacion.actual === 1 ? 'disabled' : ''}
                class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all">
            <i class="fas fa-chevron-left"></i>
        </button>
    `);

    // Números de página
    const maxVisible = 5;
    let startPage = Math.max(1, AppState.paginacion.actual - Math.floor(maxVisible / 2));
    let endPage = Math.min(AppState.paginacion.total, startPage + maxVisible - 1);
    
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }

    if (startPage > 1) {
        botones.push(`
            <button onclick="cambiarPagina(1)" class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-all">1</button>
        `);
        if (startPage > 2) {
            botones.push(`<span class="px-2 text-gray-400">...</span>`);
        }
    }

    for (let i = startPage; i <= endPage; i++) {
        botones.push(`
            <button onclick="cambiarPagina(${i})"
                    class="px-3 py-2 border ${i === AppState.paginacion.actual ? 'bg-red-600 text-white border-red-600 font-bold' : 'border-gray-300 hover:bg-gray-50'} rounded-lg transition-all">
                ${i}
            </button>
        `);
    }

    if (endPage < AppState.paginacion.total) {
        if (endPage < AppState.paginacion.total - 1) {
            botones.push(`<span class="px-2 text-gray-400">...</span>`);
        }
        botones.push(`
            <button onclick="cambiarPagina(${AppState.paginacion.total})" class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-all">${AppState.paginacion.total}</button>
        `);
    }

    // Botón Siguiente
    botones.push(`
        <button onclick="cambiarPagina(${AppState.paginacion.actual + 1})"
                ${AppState.paginacion.actual === AppState.paginacion.total ? 'disabled' : ''}
                class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all">
            <i class="fas fa-chevron-right"></i>
        </button>
    `);

    container.innerHTML = botones.join('');
}

function actualizarContador() {
    const lblDesde = document.getElementById('lblDesde');
    const lblHasta = document.getElementById('lblHasta');
    const lblTotalPag = document.getElementById('lblTotalPag');
    const contadorTotal = document.getElementById('contadorTotal');
    
    const totalResenas = AppState.estadisticas.total;
    const inicio = (AppState.paginacion.actual - 1) * AppState.paginacion.porPagina + 1;
    const fin = Math.min(inicio + AppState.resenas.length - 1, totalResenas);
    
    if (lblDesde) lblDesde.textContent = totalResenas > 0 ? inicio : 0;
    if (lblHasta) lblHasta.textContent = fin;
    if (lblTotalPag) lblTotalPag.textContent = totalResenas;
    if (contadorTotal) contadorTotal.textContent = `Mostrando ${AppState.resenas.length} de ${totalResenas} reseñas`;
}

window.cambiarPagina = function(pagina) {
    if (pagina < 1 || pagina > AppState.paginacion.total || AppState.loading) return;
    AppState.paginacion.actual = pagina;
    cargarResenas();
    window.scrollTo({ top: 0, behavior: 'smooth' });
};

// ==================== KPIs ====================
function actualizarKPIs() {
    const stats = AppState.estadisticas;
    
    const kpiTotal = document.getElementById('kpiTotal');
    const kpiPendientes = document.getElementById('kpiPendientes');
    const kpiAprobadas = document.getElementById('kpiAprobadas');
    const kpiRechazadas = document.getElementById('kpiRechazadas');
    
    if (kpiTotal) kpiTotal.textContent = stats.total || 0;
    if (kpiPendientes) kpiPendientes.textContent = stats.pendientes || 0;
    if (kpiAprobadas) kpiAprobadas.textContent = stats.aprobadas || 0;
    if (kpiRechazadas) kpiRechazadas.textContent = (stats.rechazadas || 0) + (stats.ocultas || 0);
}

// ==================== FILTROS ====================
function aplicarFiltros() {
    AppState.filtros.producto_id = document.getElementById('filtroProducto')?.value || '';
    AppState.filtros.estado = document.getElementById('filtroEstado')?.value || '';
    AppState.filtros.comentario = document.getElementById('buscarComentario')?.value || '';
    
    AppState.paginacion.actual = 1;
    cargarResenas();
}

function limpiarFiltros() {
    const filtroProducto = document.getElementById('filtroProducto');
    const filtroEstado = document.getElementById('filtroEstado');
    const buscarComentario = document.getElementById('buscarComentario');
    
    if (filtroProducto) filtroProducto.value = '';
    if (filtroEstado) filtroEstado.value = '';
    if (buscarComentario) buscarComentario.value = '';
    
    AppState.filtros = { producto_id: '', estado: '', comentario: '' };
    AppState.paginacion.actual = 1;
    
    cargarResenas();
    mostrarNotificacion('Filtros limpiados', 'Mostrando todas las reseñas', 'info');
}

// ==================== ACCIONES DE RESEÑAS ====================
window.abrirModalAprobar = (id) => {
    abrirModal(
        '✅ Aprobar Reseña',
        '¿Estás seguro de que deseas aprobar esta reseña? Será visible públicamente en el producto.',
        async () => await ejecutarAccion('aprobar', id),
        false
    );
};

window.abrirModalRechazar = (id) => {
    abrirModal(
        '❌ Rechazar Reseña',
        'Esta reseña será rechazada y no será visible para los usuarios. Puedes indicar un motivo (opcional):',
        async () => await ejecutarAccion('rechazar', id),
        true
    );
};

window.abrirModalOcultar = (id) => {
    abrirModal(
        '👁️ Ocultar Reseña',
        'La reseña será ocultada temporalmente. Puedes restaurarla más tarde. Indica el motivo (opcional):',
        async () => await ejecutarAccion('ocultar', id),
        true
    );
};

window.abrirModalRestaurar = (id) => {
    abrirModal(
        '✨ Restaurar Visibilidad',
        '¿Deseas hacer visible esta reseña nuevamente? Volverá a mostrarse públicamente.',
        async () => await ejecutarAccion('restaurar', id),
        false
    );
};

window.abrirModalEliminar = (id) => {
    abrirModal(
        '🗑️ Eliminar Permanentemente',
        '⚠️ ADVERTENCIA: Esta acción NO se puede deshacer. La reseña será eliminada permanentemente de la base de datos.',
        async () => await ejecutarAccion('eliminar', id),
        false
    );
};

window.verComentarioCompleto = (id) => {
    const resena = AppState.resenas.find(r => r.id === id);
    if (!resena) return;
    
    alert(`Comentario completo:\n\n${resena.comentario}\n\nUsuario: ${resena.usuario_nombre || 'Anónimo'}\nCalificación: ${resena.calificacion}/5`);
};

async function ejecutarAccion(accion, id) {
    const motivo = document.getElementById('modalMotivo')?.value?.trim() || null;
    
    try {
        const url = window.API_ENDPOINTS[accion].replace('{id}', id);
        const method = accion === 'eliminar' ? 'DELETE' : 'PATCH';
        
        const opciones = {
            method,
            headers: { 'Content-Type': 'application/json' }
        };
        
        if (method === 'PATCH' && motivo) {
            opciones.body = JSON.stringify({ motivo });
        }
        
        const response = await fetch(url, opciones);
        const data = await response.json();

        if (response.ok && data.ok) {
            const mensajes = {
                aprobar: '✅ Reseña aprobada correctamente',
                rechazar: '❌ Reseña rechazada',
                ocultar: '👁️ Reseña ocultada',
                restaurar: '✨ Reseña restaurada',
                eliminar: '🗑️ Reseña eliminada permanentemente'
            };
            
            mostrarNotificacion(mensajes[accion], data.mensaje || data.message || 'Acción completada', 'success');
            await cargarResenas();
            return true;
        } else {
            mostrarNotificacion('Error', data.error || 'No se pudo completar la acción', 'error');
            return false;
        }
    } catch (error) {
        console.error(`Error en ${accion}:`, error);
        mostrarNotificacion('Error de conexión', 'No se pudo conectar con el servidor', 'error');
        return false;
    }
}

// ==================== MODAL ====================
function abrirModal(titulo, mensaje, callback, mostrarMotivo = false) {
    const modal = document.getElementById('modalConfirmacion');
    const motivoContainer = document.getElementById('modalMotivoContainer');
    const motivoInput = document.getElementById('modalMotivo');
    
    if (!modal) return;

    document.getElementById('modalTitulo').textContent = titulo;
    document.getElementById('modalMensaje').textContent = mensaje;
    
    if (mostrarMotivo && motivoContainer) {
        motivoContainer.classList.remove('hidden');
        if (motivoInput) motivoInput.value = '';
    } else if (motivoContainer) {
        motivoContainer.classList.add('hidden');
    }

    AppState.modalCallback = callback;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function cerrarModal() {
    const modal = document.getElementById('modalConfirmacion');
    if (!modal) return;

    modal.classList.add('hidden');
    modal.classList.remove('flex');
    AppState.modalCallback = null;
}

async function ejecutarAccionModal() {
    if (AppState.modalCallback) {
        const exito = await AppState.modalCallback();
        if (exito) {
            cerrarModal();
        }
    }
}

// ==================== NOTIFICACIONES ====================
function mostrarNotificacion(titulo, mensaje, tipo = 'info') {
    const notification = document.getElementById('notification');
    const icon = document.getElementById('notificationIcon');
    const title = document.getElementById('notificationTitle');
    const message = document.getElementById('notificationMessage');
    
    if (!notification) return;

    const config = {
        success: { bg: 'bg-green-500', icon: 'fa-check-circle' },
        error: { bg: 'bg-red-500', icon: 'fa-exclamation-circle' },
        info: { bg: 'bg-blue-500', icon: 'fa-info-circle' },
        warning: { bg: 'bg-yellow-500', icon: 'fa-exclamation-triangle' }
    };

    const c = config[tipo] || config.info;
    
    if (icon) {
        icon.className = `w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${c.bg}`;
        icon.innerHTML = `<i class="fas ${c.icon} text-white"></i>`;
    }
    if (title) title.textContent = titulo;
    if (message) message.textContent = mensaje;

    notification.classList.remove('translate-x-full');
    
    setTimeout(() => {
        notification.classList.add('translate-x-full');
    }, 4000);
}

// ==================== ESTADOS DE UI ====================
function mostrarCargando() {
    const tbody = document.getElementById('tablaResenasBody');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="px-6 py-16 text-center text-gray-500">
                    <i class="fas fa-spinner fa-spin text-5xl mb-4 text-red-600"></i>
                    <p class="text-lg font-medium">Cargando reseñas...</p>
                    <p class="text-sm mt-1">Por favor espera un momento</p>
                </td>
            </tr>
        `;
    }
}

function mostrarError() {
    const tbody = document.getElementById('tablaResenasBody');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="px-6 py-16 text-center text-red-500">
                    <i class="fas fa-exclamation-triangle text-5xl mb-4"></i>
                    <p class="text-lg font-bold">Error al cargar las reseñas</p>
                    <p class="text-sm text-gray-600 mt-2">Hubo un problema al conectar con el servidor</p>
                    <button onclick="cargarResenas()" 
                            class="mt-4 px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-all font-medium">
                        <i class="fas fa-redo mr-2"></i>
                        Reintentar
                    </button>
                </td>
            </tr>
        `;
    }
}

// ==================== UTILIDADES ====================
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text ? String(text).replace(/[&<>"']/g, m => map[m]) : '';
}

function obtenerIniciales(nombre) {
    if (!nombre) return 'U';
    const palabras = nombre.trim().split(' ');
    if (palabras.length === 1) return palabras[0].charAt(0).toUpperCase();
    return (palabras[0].charAt(0) + palabras[palabras.length - 1].charAt(0)).toUpperCase();
}

console.log('✅ Sistema de administración de reseñas cargado correctamente');