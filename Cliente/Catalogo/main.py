# -*- coding: utf-8 -*-
"""
Cliente/Catalogo/main.py - Blueprint del Catálogo
Integrado con el modelo real de PeakSport
Rutas: /catalogo, /catalogo/api/...
"""

from flask import Blueprint, render_template, jsonify, request, session
from Cliente.Catalogo.controlador import CatalogoControlador
from Log_PeakSport import log_info, log_error

# Crear blueprint
bp_catalogo = Blueprint(
    'catalogo',
    __name__,
    url_prefix='/catalogo',
    template_folder='templates',
    static_folder='static',
    static_url_path='/catalogo/static'
)

# Instanciar controlador
catalogo = CatalogoControlador()


# ==================== RUTAS WEB ====================

@bp_catalogo.route('/')
def vista_catalogo():
    """
    Página principal del catálogo
    Renderiza el HTML del catálogo
    """
    try:
        usuario_autenticado = bool(session.get('logged_in') or session.get('mfa_verificado'))
        usuario_nombre = session.get('usuario_nombre', 'Invitado')
        usuario_email = session.get('usuario_email')
        usuario_id = session.get('usuario_id')
        
        return render_template(
            'Catalogo.html',
            usuario_autenticado=usuario_autenticado,
            usuario_nombre=usuario_nombre,
            usuario_email=usuario_email,
            usuario_id=usuario_id
        )
    except Exception as e:
        log_error(f"Error en vista_catalogo: {str(e)}")
        return f"<h1>Error cargando el catálogo</h1><p>{str(e)}</p>", 500


# ==================== RUTAS API ====================

@bp_catalogo.route('/api/productos/list', methods=['GET'])
def api_listar_productos():
    """
    API - Listar productos con paginación
    
    Query Parameters:
        page (int): Número de página (default: 1)
        per_page (int): Productos por página (default: 12)
    
    Returns:
        JSON con productos, total, página, etc.
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 12, type=int)
        
        # Validaciones
        page = max(1, page)
        per_page = max(1, min(per_page, 100))  # Máximo 100 por página
        
        resultado = catalogo.obtener_todos_productos(page=page, per_page=per_page)
        
        log_info(f"API listar_productos: page={page}, per_page={per_page}, total={resultado.get('total', 0)}")
        
        return jsonify(resultado)
    except Exception as e:
        log_error(f"Error en api_listar_productos: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp_catalogo.route('/api/productos/<int:producto_id>', methods=['GET'])
def api_obtener_producto(producto_id):
    """
    API - Obtener un producto específico
    
    URL Parameters:
        producto_id (int): ID del producto
    
    Returns:
        JSON con datos completos del producto
    """
    try:
        producto = catalogo.obtener_producto(producto_id)
        
        if not producto:
            return jsonify({'success': False, 'error': 'Producto no encontrado'}), 404
        
        return jsonify({'success': True, 'producto': producto})
    except Exception as e:
        log_error(f"Error en api_obtener_producto {producto_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp_catalogo.route('/api/productos/slug/<slug>', methods=['GET'])
def api_obtener_por_slug(slug):
    """
    API - Obtener producto por slug
    
    URL Parameters:
        slug (str): Slug del producto
    
    Returns:
        JSON con datos del producto
    """
    try:
        producto = catalogo.obtener_producto_por_slug(slug)
        
        if not producto:
            return jsonify({'success': False, 'error': 'Producto no encontrado'}), 404
        
        return jsonify({'success': True, 'producto': producto})
    except Exception as e:
        log_error(f"Error en api_obtener_por_slug {slug}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp_catalogo.route('/api/productos/buscar', methods=['GET'])
def api_buscar():
    """
    API - Buscar productos
    
    Query Parameters:
        q (str): Término de búsqueda
        page (int): Número de página (default: 1)
        per_page (int): Productos por página (default: 12)
    
    Returns:
        JSON con productos encontrados
    """
    try:
        q = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 12, type=int)
        
        if not q or len(q) < 2:
            return jsonify({
                'success': False,
                'error': 'Búsqueda muy corta (mínimo 2 caracteres)',
                'productos': []
            }), 400
        
        resultado = catalogo.buscar_productos(q=q, page=page, per_page=per_page)
        
        log_info(f"API buscar: q='{q}', resultados={resultado.get('total', 0)}")
        
        return jsonify(resultado)
    except Exception as e:
        log_error(f"Error en api_buscar: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp_catalogo.route('/api/categorias', methods=['GET'])
def api_obtener_categorias():
    """
    API - Obtener lista de categorías
    
    Returns:
        JSON con array de categorías
    """
    try:
        categorias = catalogo.obtener_categorias_con_productos()
        
        return jsonify({
            'success': True,
            'categorias': categorias
        })
    except Exception as e:
        log_error(f"Error en api_obtener_categorias: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp_catalogo.route('/api/categorias/<int:categoria_id>/productos', methods=['GET'])
def api_productos_por_categoria(categoria_id):
    """
    API - Obtener productos de una categoría
    
    URL Parameters:
        categoria_id (int): ID de la categoría
    
    Query Parameters:
        page (int): Número de página (default: 1)
        per_page (int): Productos por página (default: 12)
    
    Returns:
        JSON con productos de la categoría
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 12, type=int)
        
        resultado = catalogo.obtener_productos_por_categoria(
            categoria_id=categoria_id,
            page=page,
            per_page=per_page
        )
        
        return jsonify(resultado)
    except Exception as e:
        log_error(f"Error en api_productos_por_categoria: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp_catalogo.route('/api/filtrar', methods=['GET'])
def api_filtrar():
    """
    API - Filtrar productos
    
    Query Parameters:
        categoria_id (int): ID de la categoría
        precio_min (int): Precio mínimo (en pesos)
        precio_max (int): Precio máximo (en pesos)
        q (str): Búsqueda por nombre
        page (int): Número de página
        per_page (int): Productos por página
    
    Returns:
        JSON con productos filtrados
    """
    try:
        resultado = catalogo.filtrar_productos()
        return jsonify(resultado)
    except Exception as e:
        log_error(f"Error en api_filtrar: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp_catalogo.route('/api/ordenar/<criterio>', methods=['GET'])
def api_ordenar(criterio):
    """
    API - Ordenar productos
    
    URL Parameters:
        criterio (str): nombre, precio_asc, precio_desc, rating, popular, recientes
    
    Returns:
        JSON con productos ordenados
    """
    try:
        productos = catalogo.ordenar_productos(criterio)
        
        return jsonify({
            'success': True,
            'criterio': criterio,
            'productos': productos
        })
    except Exception as e:
        log_error(f"Error en api_ordenar: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp_catalogo.route('/api/productos/recomendados', methods=['GET'])
def api_recomendados():
    """
    API - Obtener productos recomendados (últimos 12 productos activos)
    
    Returns:
        JSON con productos recomendados
    """
    try:
        resultado = catalogo.obtener_todos_productos(page=1, per_page=12)
        resultado['titulo'] = 'Productos Recomendados'
        
        log_info(f"API recomendados: {resultado.get('total', 0)} productos")
        
        return jsonify(resultado)
    except Exception as e:
        log_error(f"Error en api_recomendados: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp_catalogo.route('/api/recomendados', methods=['GET'])
def api_recomendados_legacy():
    """
    API - Alias para compatibilidad (ruta legacy)
    Redirige a /api/productos/recomendados
    """
    try:
        resultado = catalogo.obtener_todos_productos(page=1, per_page=12)
        resultado['titulo'] = 'Productos Recomendados'
        
        return jsonify(resultado)
    except Exception as e:
        log_error(f"Error en api_recomendados_legacy: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500