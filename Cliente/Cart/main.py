# -- coding: utf-8 --
"""
Blueprint del carrito de compras
Maneja vistas y rutas relacionadas con el carrito
"""

import os
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from Log_PeakSport import log_info, log_error, log_warning

from Modelo_de_Datos_PostgreSQL_y_CRUD.Cart import (
    obtener_o_crear_carrito,
    agregar_item_carrito,
    actualizar_cantidad_item,
    eliminar_item_carrito,
    vaciar_carrito,
    calcular_totales_carrito,
    migrar_carrito_sesion_a_usuario
)

# ✅ CREAR BLUEPRINT CON RUTAS ABSOLUTAS
bp_cart = Blueprint(
    'cart',
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'static'),
    static_url_path='/cart/static'
)


# ===================== HELPERS =====================

def get_cart_identifier():
    """
    Obtiene el identificador del carrito (usuario_id o session_id)
    
    Returns:
        tuple: (usuario_id, session_id)
    """
    usuario_id = session.get('usuario_id')
    session_id = session.get('session_id') or session.sid
    
    return usuario_id, session_id


def get_or_create_cart_for_current_user():
    """
    Obtiene o crea el carrito para el usuario/sesión actual
    
    Returns:
        Cart o None
    """
    usuario_id, session_id = get_cart_identifier()
    return obtener_o_crear_carrito(usuario_id=usuario_id, session_id=session_id)


# ===================== VISTAS =====================

@bp_cart.route('/')
@bp_cart.route('/carrito')
def vista_carrito():
    """
    Vista principal del carrito de compras
    """
    try:
        # Obtener información del usuario
        logged = bool(session.get('logged_in') or session.get('mfa_verificado'))
        usuario_nombre = session.get('usuario_nombre', 'Invitado')
        usuario_email = session.get('usuario_email')
        
        # Obtener carrito
        cart = get_or_create_cart_for_current_user()
        
        if not cart:
            cart_data = {
                'id': None,
                'items': [],
                'total_items': 0,
                'subtotal': 0
            }
        else:
            # ✅ CORREGIDO: Usar list() directamente (lazy='select')
            items_list = list(cart.items)
            cart_data = {
                'id': cart.id,
                'usuario_id': cart.usuario_id,
                'session_id': cart.session_id,
                'activo': cart.activo,
                'items': [item.to_dict() for item in items_list],
                'total_items': sum(item.cantidad for item in items_list),
                'subtotal': sum((item.cantidad * item.precio_unitario) / 100 for item in items_list)
            }
        
        return render_template(
            'carrito.html',
            usuario_autenticado=logged,
            usuario_nombre=usuario_nombre,
            usuario_email=usuario_email,
            cart=cart_data
        )
        
    except Exception as e:
        log_error(f"[cart] vista_carrito error: {e}")
        return render_template('500.html'), 500


# ===================== API ENDPOINTS =====================

@bp_cart.route('/api/cart', methods=['GET'])
def api_obtener_carrito():
    """
    GET /api/cart
    Obtiene el carrito actual con todos sus items
    
    Response:
        {
            "success": true,
            "cart": {
                "id": 1,
                "items": [...],
                "total_items": 3,
                "subtotal": 206.00
            },
            "totales": {
                "subtotal": 206.00,
                "impuestos": 20.60,
                "envio": 15.00,
                "total": 241.60
            }
        }
    """
    try:
        cart = get_or_create_cart_for_current_user()
        
        if not cart:
            return jsonify({
                'success': False,
                'error': 'No se pudo obtener el carrito'
            }), 400
        
        # ✅ CORREGIDO: Usar list() directamente (lazy='select')
        items_list = list(cart.items)
        cart_data = {
            'id': cart.id,
            'usuario_id': cart.usuario_id,
            'session_id': cart.session_id,
            'activo': cart.activo,
            'items': [item.to_dict() for item in items_list],
            'total_items': sum(item.cantidad for item in items_list),
            'subtotal': sum((item.cantidad * item.precio_unitario) / 100 for item in items_list)
        }
        
        totales = calcular_totales_carrito(cart.id)
        
        log_info(f"[cart_api] carrito obtenido: {cart.id}, items: {len(items_list)}")
        
        return jsonify({
            'success': True,
            'cart': cart_data,
            'totales': totales
        }), 200
        
    except Exception as e:
        log_error(f"[cart_api] obtener_carrito error: {e}")
        return jsonify({
            'success': False,
            'error': 'Error al obtener el carrito'
        }), 500


@bp_cart.route('/api/cart/add', methods=['POST'])
def api_agregar_producto():
    """
    POST /api/cart/add
    Agrega un producto al carrito
    
    Body:
        {
            "producto_id": 1,
            "cantidad": 2
        }
    
    Response:
        {
            "success": true,
            "message": "Producto agregado al carrito",
            "item": {...},
            "cart_total_items": 5
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No se recibieron datos'
            }), 400
        
        producto_id = data.get('producto_id')
        cantidad = data.get('cantidad', 1)
        
        if not producto_id:
            return jsonify({
                'success': False,
                'error': 'producto_id es requerido'
            }), 400
        
        try:
            producto_id = int(producto_id)
            cantidad = int(cantidad)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'producto_id y cantidad deben ser números'
            }), 400
        
        if cantidad <= 0:
            return jsonify({
                'success': False,
                'error': 'La cantidad debe ser mayor a 0'
            }), 400
        
        # Obtener o crear carrito
        cart = get_or_create_cart_for_current_user()
        
        if not cart:
            return jsonify({
                'success': False,
                'error': 'No se pudo crear el carrito'
            }), 500
        
        # Agregar item
        item = agregar_item_carrito(cart.id, producto_id, cantidad)
        
        if not item:
            return jsonify({
                'success': False,
                'error': 'No se pudo agregar el producto (stock insuficiente o producto no disponible)'
            }), 400
        
        # Actualizar totales
        totales = calcular_totales_carrito(cart.id)
        
        log_info(f"[cart_api] producto {producto_id} agregado al carrito {cart.id}")
        
        return jsonify({
            'success': True,
            'message': 'Producto agregado al carrito',
            'item': item.to_dict(),
            'cart_total_items': totales['total_items'],
            'totales': totales
        }), 200
        
    except Exception as e:
        log_error(f"[cart_api] agregar_producto error: {e}")
        return jsonify({
            'success': False,
            'error': 'Error al agregar producto al carrito'
        }), 500


@bp_cart.route('/api/cart/update/<int:item_id>', methods=['PUT'])
def api_actualizar_cantidad(item_id):
    """
    PUT /api/cart/update/<item_id>
    Actualiza la cantidad de un item en el carrito
    
    Body:
        {
            "cantidad": 3
        }
    
    Response:
        {
            "success": true,
            "message": "Cantidad actualizada",
            "item": {...},
            "totales": {...}
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'cantidad' not in data:
            return jsonify({
                'success': False,
                'error': 'cantidad es requerida'
            }), 400
        
        try:
            cantidad = int(data['cantidad'])
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'cantidad debe ser un número'
            }), 400
        
        if cantidad <= 0:
            return jsonify({
                'success': False,
                'error': 'La cantidad debe ser mayor a 0'
            }), 400
        
        # Actualizar cantidad
        item = actualizar_cantidad_item(item_id, cantidad)
        
        if not item:
            return jsonify({
                'success': False,
                'error': 'No se pudo actualizar (item no encontrado o stock insuficiente)'
            }), 400
        
        # Calcular totales
        totales = calcular_totales_carrito(item.cart_id)
        
        log_info(f"[cart_api] item {item_id} actualizado a cantidad {cantidad}")
        
        return jsonify({
            'success': True,
            'message': 'Cantidad actualizada',
            'item': item.to_dict(),
            'totales': totales
        }), 200
        
    except Exception as e:
        log_error(f"[cart_api] actualizar_cantidad error: {e}")
        return jsonify({
            'success': False,
            'error': 'Error al actualizar cantidad'
        }), 500


@bp_cart.route('/api/cart/remove/<int:item_id>', methods=['DELETE'])
def api_eliminar_producto(item_id):
    """
    DELETE /api/cart/remove/<item_id>
    Elimina un producto del carrito
    
    Response:
        {
            "success": true,
            "message": "Producto eliminado del carrito",
            "totales": {...}
        }
    """
    try:
        from Modelo_de_Datos_PostgreSQL_y_CRUD.conexion_postgres import db
        from Modelo_de_Datos_PostgreSQL_y_CRUD.Cart import CartItem
        
        item = db.session.get(CartItem, item_id)
        if not item:
            return jsonify({
                'success': False,
                'error': 'Item no encontrado'
            }), 404
        
        cart_id = item.cart_id
        
        # Eliminar item
        success = eliminar_item_carrito(item_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'No se pudo eliminar el producto'
            }), 400
        
        # Calcular totales actualizados
        totales = calcular_totales_carrito(cart_id)
        
        log_info(f"[cart_api] item {item_id} eliminado del carrito")
        
        return jsonify({
            'success': True,
            'message': 'Producto eliminado del carrito',
            'totales': totales
        }), 200
        
    except Exception as e:
        log_error(f"[cart_api] eliminar_producto error: {e}")
        return jsonify({
            'success': False,
            'error': 'Error al eliminar producto'
        }), 500


@bp_cart.route('/api/cart/clear', methods=['DELETE'])
def api_vaciar_carrito():
    """
    DELETE /api/cart/clear
    Vacía completamente el carrito
    
    Response:
        {
            "success": true,
            "message": "Carrito vaciado"
        }
    """
    try:
        cart = get_or_create_cart_for_current_user()
        
        if not cart:
            return jsonify({
                'success': False,
                'error': 'No se encontró el carrito'
            }), 404
        
        success = vaciar_carrito(cart.id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'No se pudo vaciar el carrito'
            }), 400
        
        log_info(f"[cart_api] carrito {cart.id} vaciado")
        
        return jsonify({
            'success': True,
            'message': 'Carrito vaciado'
        }), 200
        
    except Exception as e:
        log_error(f"[cart_api] vaciar_carrito error: {e}")
        return jsonify({
            'success': False,
            'error': 'Error al vaciar carrito'
        }), 500


@bp_cart.route('/api/cart/totales', methods=['GET'])
def api_calcular_totales():
    """
    GET /api/cart/totales
    Calcula los totales del carrito actual
    
    Response:
        {
            "success": true,
            "totales": {
                "subtotal": 206.00,
                "impuestos": 20.60,
                "envio": 15.00,
                "total": 241.60,
                "total_items": 4,
                "envio_gratis": false
            }
        }
    """
    try:
        cart = get_or_create_cart_for_current_user()
        
        if not cart:
            return jsonify({
                'success': False,
                'error': 'No se encontró el carrito'
            }), 404
        
        totales = calcular_totales_carrito(cart.id)
        
        return jsonify({
            'success': True,
            'totales': totales
        }), 200
        
    except Exception as e:
        log_error(f"[cart_api] calcular_totales error: {e}")
        return jsonify({
            'success': False,
            'error': 'Error al calcular totales'
        }), 500


# ===================== CONTEXT PROCESSOR =====================

@bp_cart.context_processor
def inject_cart_data():
    """
    Inyecta datos del carrito en todos los templates
    """
    try:
        cart = get_or_create_cart_for_current_user()
        if cart:
            totales = calcular_totales_carrito(cart.id)
            return {
                'cart_items_count': totales.get('total_items', 0)
            }
    except:
        pass
    
    return {'cart_items_count': 0}