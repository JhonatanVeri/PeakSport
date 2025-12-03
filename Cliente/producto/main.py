# -*- coding: utf-8 -*-
"""
Archivo: Cliente/producto/main.py
Descripción: Blueprint para la vista individual de productos
Autor: Sistema PicSport
Versión: 1.0.0
"""

from flask import Blueprint, render_template, session, abort
from Log_PeakSport import log_info, log_warning, log_error

# Importar funciones CRUD
from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import (
    obtener_producto_por_slug,
    listar_productos
)
from Modelo_de_Datos_PostgreSQL_y_CRUD.Resenas import (
    obtener_estadisticas_producto,
    verificar_usuario_puede_resenar
)

# Crear Blueprint
bp_producto_detalle = Blueprint(
    'producto_detalle',
    __name__,
    template_folder='../../templates',
    static_folder='../../static'
)


# ===================== HELPERS =====================

def obtener_datos_sesion():
    """
    Extrae información de sesión del usuario de forma segura
    
    Returns:
        Dict con datos de sesión
    """
    logged = session.get('logged_in') or session.get('mfa_verificado') or False
    
    return {
        'usuario_autenticado': bool(logged),
        'usuario_id': session.get('usuario_id'),
        'usuario_nombre': session.get('usuario_nombre', 'Invitado'),
        'usuario_email': session.get('usuario_email'),
        'usuario_rol': session.get('usuario_rol', 'Cliente')
    }


def serializar_producto_para_template(producto):
    """
    Serializa un producto con todas sus relaciones para el template
    
    Args:
        producto: Objeto Producto de SQLAlchemy
    
    Returns:
        Dict con toda la información necesaria
    """
    if not producto:
        return None
    
    # Obtener imágenes del producto
    imagenes = []
    imagen_portada = None
    
    for img in producto.imagenes:
        img_dict = img.to_dict()
        imagenes.append(img_dict)
        if img.es_portada:
            imagen_portada = img_dict['url']
    
    # Si no hay portada, usar la primera imagen
    if not imagen_portada and imagenes:
        imagen_portada = imagenes[0]['url']
    
    # Fallback si no hay imágenes
    if not imagen_portada:
        imagen_portada = 'https://via.placeholder.com/600x600?text=PeakSport'
    
    # Obtener categorías
    categorias = []
    for cat in producto.categorias:
        categorias.append({
            'id': cat.id,
            'nombre': cat.nombre,
            'slug': cat.slug
        })
    
    # Calcular precio en formato decimal
    precio_decimal = producto.precio_centavos / 100 if producto.precio_centavos else 0
    
    # Obtener estadísticas de reseñas
    stats = obtener_estadisticas_producto(producto.id)
    
    return {
        'id': producto.id,
        'nombre': producto.nombre,
        'slug': producto.slug,
        'descripcion': producto.descripcion or 'Sin descripción disponible',
        'precio_centavos': producto.precio_centavos,
        'precio': precio_decimal,
        'moneda': producto.moneda,
        'stock': producto.stock,
        'sku': producto.sku,
        'activo': producto.activo,
        'imagen_portada': imagen_portada,
        'imagenes': imagenes,
        'categorias': categorias,
        'rating_promedio': stats.get('promedio', 0),
        'total_resenas': stats.get('total', 0),
        'created_at': producto.created_at.isoformat() if producto.created_at else None,
        'updated_at': producto.updated_at.isoformat() if producto.updated_at else None
    }


# ===================== RUTAS =====================

@bp_producto_detalle.route('/producto/<slug>')
def vista_producto(slug: str):
    """
    Vista individual de un producto
    
    URL: /producto/<slug>
    
    Muestra:
    - Información completa del producto
    - Galería de imágenes
    - Sistema de reseñas
    - Productos relacionados
    """
    try:
        # Obtener información de sesión
        sesion_data = obtener_datos_sesion()
        
        # Buscar producto por slug
        producto = obtener_producto_por_slug(slug)
        
        if not producto:
            log_warning(f"Producto no encontrado: {slug}")
            abort(404)
        
        # Verificar que el producto esté activo (opcional: admins pueden ver inactivos)
        if not producto.activo and sesion_data['usuario_rol'] != 'Administrador':
            log_warning(f"Intento de acceso a producto inactivo: {slug}")
            abort(404)
        
        # Serializar producto
        producto_data = serializar_producto_para_template(producto)
        
        # Verificar si el usuario puede dejar reseña
        puede_resenar = False
        if sesion_data['usuario_autenticado'] and sesion_data['usuario_id']:
            puede_resenar = verificar_usuario_puede_resenar(
                producto.id,
                sesion_data['usuario_id']
            )
        
        # Obtener productos relacionados (misma categoría)
        productos_relacionados = []
        try:
            if producto.categorias and len(list(producto.categorias)) > 0:
                primera_categoria = list(producto.categorias)[0]
                productos_rel, _ = listar_productos(
                    filtros={
                        'activo': True,
                        'categoria_id': primera_categoria.id
                    },
                    page=1,
                    per_page=4
                )
                
                # Excluir el producto actual
                productos_relacionados = [
                    serializar_producto_para_template(p) 
                    for p in productos_rel 
                    if p.id != producto.id
                ][:4]  # Máximo 4 productos relacionados
        except Exception as e:
            log_warning(f"No se pudieron cargar productos relacionados: {str(e)}")
            productos_relacionados = []
        
        log_info(f"Vista producto: {slug} por usuario {sesion_data['usuario_nombre']}")
        
        # Renderizar template
        return render_template(
            'producto_detalle.html',
            # Datos de sesión
            **sesion_data,
            # Datos del producto
            producto=producto_data,
            puede_resenar=puede_resenar,
            # Productos relacionados
            productos_relacionados=productos_relacionados,
            # URLs para JavaScript
            api_base_url='/api/resenas',
            login_url='/login/'
        )
        
    except Exception as e:
        log_error(f"Error en vista_producto [{slug}]: {str(e)}")
        abort(500)

@bp_producto_detalle.route('/producto/<slug>/preview')
def vista_preview_producto(slug: str):
    """
    Vista previa de producto (para administradores)
    Permite ver productos inactivos
    
    URL: /producto/<slug>/preview
    """
    try:
        # Obtener información de sesión
        sesion_data = obtener_datos_sesion()
        
        # Solo administradores pueden ver preview
        if sesion_data['usuario_rol'] != 'Administrador':
            log_warning(f"Intento de acceso no autorizado a preview: {slug}")
            abort(403)
        
        # Buscar producto por slug (sin validar si está activo)
        producto = obtener_producto_por_slug(slug)
        
        if not producto:
            log_warning(f"Producto no encontrado para preview: {slug}")
            abort(404)
        
        # Serializar producto
        producto_data = serializar_producto_para_template(producto)
        
        log_info(f"Preview producto: {slug} por admin {sesion_data['usuario_nombre']}")
        
        # Renderizar template con banner de preview
        return render_template(
            'producto_detalle.html',
            **sesion_data,
            producto=producto_data,
            puede_resenar=False,
            productos_relacionados=[],
            api_base_url='/api/resenas',
            login_url='/login/',
            modo_preview=True  # Flag para mostrar banner de preview
        )
        
    except Exception as e:
        log_error(f"Error en vista_preview_producto [{slug}]: {str(e)}")
        abort(500)