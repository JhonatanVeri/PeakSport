# -*- coding: utf-8 -*-
"""
Archivo: Apis/resenas_api.py
Descripción: API REST para el sistema de reseñas (Público + Administración)
Autor: Sistema PeakSport
Versión: 2.0.0 (Con moderación)
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
from typing import Dict, Any

from Log_PeakSport import log_info, log_warning, log_error

# Importar funciones CRUD de reseñas
from Modelo_de_Datos_PostgreSQL_y_CRUD.Resenas import (
    crear_resena,
    obtener_resena_por_id,
    listar_resenas_producto,
    listar_resenas_usuario,
    actualizar_resena,
    eliminar_resena,
    obtener_estadisticas_producto,
    verificar_usuario_puede_resenar,
    # Funciones de moderación (NUEVAS)
    listar_resenas,
    aprobar_resena,
    rechazar_resena,
    ocultar_resena,
    restaurar_resena,
    to_dict
)
from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import obtener_producto_por_id

# Crear Blueprint
bp_resenas_api = Blueprint('resenas_api', __name__)


# ===================== HELPERS =====================

def verificar_autenticacion() -> Dict[str, Any]:
    """
    Verifica si el usuario está autenticado
    
    Returns:
        Dict con 'autenticado' (bool) y 'usuario_id' (int o None)
    """
    usuario_id = session.get('usuario_id')
    logged_in = session.get('logged_in') or session.get('mfa_verificado')
    
    return {
        'autenticado': bool(logged_in and usuario_id),
        'usuario_id': usuario_id
    }


def requiere_admin(fn):
    """Decorator para verificar rol de administrador"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_dict = session.get("usuario") or {}
        rol = user_dict.get("rol") or session.get("usuario_rol")
        
        if rol != "Administrador":
            usuario_correo = session.get('usuario_correo', 'desconocido')
            log_warning(f"[seguridad] Acceso denegado a reseñas (no es admin): {usuario_correo}")
            return jsonify({'ok': False, 'error': 'Acceso denegado. Se requiere rol de administrador'}), 403
        
        return fn(*args, **kwargs)
    return wrapper


def respuesta_error(mensaje: str, codigo: int = 400) -> tuple:
    """Helper para respuestas de error consistentes"""
    return jsonify({
        'success': False,
        'error': mensaje
    }), codigo


def respuesta_exito(data: Any = None, mensaje: str = None) -> tuple:
    """Helper para respuestas exitosas consistentes"""
    response = {'success': True}
    if mensaje:
        response['message'] = mensaje
    if data is not None:
        response['data'] = data
    return jsonify(response), 200


# ===================== ENDPOINTS PÚBLICOS =====================

@bp_resenas_api.route('/productos/<int:producto_id>/resenas', methods=['GET'])
def obtener_resenas_producto(producto_id: int):
    """
    GET /api/resenas/productos/<producto_id>/resenas
    
    Obtiene las reseñas de un producto con paginación
    
    Query params:
        - page: número de página (default: 1)
        - per_page: reseñas por página (default: 10)
        - orden: 'recientes', 'antiguas', 'mejor_calificadas', 'peor_calificadas'
    """
    try:
        # Parámetros de paginación
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        orden = request.args.get('orden', 'recientes', type=str)
        
        # Validar parámetros
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 50:
            per_page = 10
        
        # Obtener reseñas (solo visibles/aprobadas)
        resenas, total = listar_resenas_producto(
            producto_id=producto_id,
            page=page,
            per_page=per_page,
            orden=orden,
            solo_visibles=True
        )
        
        # Serializar reseñas
        resenas_dict = [r.to_dict() for r in resenas]
        
        # Obtener estadísticas (solo de reseñas aprobadas)
        estadisticas = obtener_estadisticas_producto(producto_id, solo_visibles=True)
        
        # Verificar si el usuario puede reseñar
        auth = verificar_autenticacion()
        puede_resenar = False
        if auth['autenticado']:
            puede_resenar = verificar_usuario_puede_resenar(
                producto_id, 
                auth['usuario_id']
            )
        
        return respuesta_exito({
            'resenas': resenas_dict,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'estadisticas': estadisticas,
            'puede_resenar': puede_resenar,
            'autenticado': auth['autenticado']
        })
        
    except Exception as e:
        log_error(f"Error en obtener_resenas_producto: {str(e)}")
        return respuesta_error("Error al obtener reseñas", 500)


@bp_resenas_api.route('/productos/<int:producto_id>/resenas', methods=['POST'])
def crear_resena_producto(producto_id: int):
    """
    POST /api/resenas/productos/<producto_id>/resenas
    
    Crea una nueva reseña para un producto (estado: pendiente)
    
    Body JSON:
        {
            "calificacion": 1-5,
            "comentario": "texto de la reseña"
        }
    """
    try:
        # Verificar autenticación
        auth = verificar_autenticacion()
        if not auth['autenticado']:
            return respuesta_error("Debes iniciar sesión para dejar una reseña", 401)
        
        # Obtener datos del body
        data = request.get_json()
        if not data:
            return respuesta_error("No se proporcionaron datos")
        
        calificacion = data.get('calificacion')
        comentario = data.get('comentario', '').strip()
        
        # Validaciones
        if not calificacion or not comentario:
            return respuesta_error("Calificación y comentario son obligatorios")
        
        try:
            calificacion = int(calificacion)
        except (ValueError, TypeError):
            return respuesta_error("Calificación debe ser un número")
        
        if not (1 <= calificacion <= 5):
            return respuesta_error("Calificación debe estar entre 1 y 5")
        
        if len(comentario) < 10:
            return respuesta_error("El comentario debe tener al menos 10 caracteres")
        
        # Verificar si ya dejó una reseña
        if not verificar_usuario_puede_resenar(producto_id, auth['usuario_id']):
            return respuesta_error("Ya dejaste una reseña para este producto")
        
        # Crear reseña (estado: pendiente)
        nueva_resena = crear_resena(
            producto_id=producto_id,
            usuario_id=auth['usuario_id'],
            calificacion=calificacion,
            comentario=comentario,
            compra_verificada=False
        )
        
        if not nueva_resena:
            return respuesta_error("No se pudo crear la reseña", 500)
        
        log_info(f"Reseña creada: {nueva_resena.id} por usuario {auth['usuario_id']} (estado: pendiente)")
        
        return respuesta_exito(
            data=nueva_resena.to_dict(),
            mensaje="Reseña enviada exitosamente. Está pendiente de moderación."
        )
        
    except Exception as e:
        log_error(f"Error en crear_resena_producto: {str(e)}")
        return respuesta_error("Error al crear reseña", 500)


@bp_resenas_api.route('/resenas/<int:resena_id>', methods=['GET'])
def obtener_resena(resena_id: int):
    """
    GET /api/resenas/resenas/<resena_id>
    
    Obtiene una reseña específica por ID
    """
    try:
        resena = obtener_resena_por_id(resena_id)
        
        if not resena:
            return respuesta_error("Reseña no encontrada", 404)
        
        return respuesta_exito(data=resena.to_dict())
        
    except Exception as e:
        log_error(f"Error en obtener_resena: {str(e)}")
        return respuesta_error("Error al obtener reseña", 500)


@bp_resenas_api.route('/resenas/<int:resena_id>', methods=['PUT'])
def actualizar_resena_endpoint(resena_id: int):
    """
    PUT /api/resenas/resenas/<resena_id>
    
    Actualiza una reseña existente
    Solo el autor puede actualizarla
    
    Body JSON:
        {
            "calificacion": 1-5 (opcional),
            "comentario": "texto" (opcional)
        }
    """
    try:
        # Verificar autenticación
        auth = verificar_autenticacion()
        if not auth['autenticado']:
            return respuesta_error("Debes iniciar sesión", 401)
        
        # Verificar que la reseña existe
        resena = obtener_resena_por_id(resena_id)
        if not resena:
            return respuesta_error("Reseña no encontrada", 404)
        
        # Verificar que es el autor
        if resena.usuario_id != auth['usuario_id']:
            return respuesta_error("No tienes permiso para editar esta reseña", 403)
        
        # Obtener datos del body
        data = request.get_json()
        if not data:
            return respuesta_error("No se proporcionaron datos")
        
        calificacion = data.get('calificacion')
        comentario = data.get('comentario')
        
        # Validar calificación si se proporciona
        if calificacion is not None:
            try:
                calificacion = int(calificacion)
            except (ValueError, TypeError):
                return respuesta_error("Calificación debe ser un número")
            
            if not (1 <= calificacion <= 5):
                return respuesta_error("Calificación debe estar entre 1 y 5")
        
        # Validar comentario si se proporciona
        if comentario is not None:
            comentario = comentario.strip()
            if len(comentario) < 10:
                return respuesta_error("El comentario debe tener al menos 10 caracteres")
        
        # Actualizar reseña
        resena_actualizada = actualizar_resena(
            resena_id=resena_id,
            calificacion=calificacion,
            comentario=comentario
        )
        
        if not resena_actualizada:
            return respuesta_error("No se pudo actualizar la reseña", 500)
        
        log_info(f"Reseña actualizada: {resena_id} por usuario {auth['usuario_id']}")
        
        return respuesta_exito(
            data=resena_actualizada.to_dict(),
            mensaje="Reseña actualizada exitosamente"
        )
        
    except Exception as e:
        log_error(f"Error en actualizar_resena_endpoint: {str(e)}")
        return respuesta_error("Error al actualizar reseña", 500)


@bp_resenas_api.route('/resenas/<int:resena_id>', methods=['DELETE'])
def eliminar_resena_endpoint(resena_id: int):
    """
    DELETE /api/resenas/resenas/<resena_id>
    
    Elimina una reseña
    Solo el autor o un administrador pueden eliminarla
    """
    try:
        # Verificar autenticación
        auth = verificar_autenticacion()
        if not auth['autenticado']:
            return respuesta_error("Debes iniciar sesión", 401)
        
        # Verificar que la reseña existe
        resena = obtener_resena_por_id(resena_id)
        if not resena:
            return respuesta_error("Reseña no encontrada", 404)
        
        # Verificar permisos
        user_dict = session.get("usuario") or {}
        rol = user_dict.get("rol") or session.get("usuario_rol")
        es_autor = resena.usuario_id == auth['usuario_id']
        es_admin = rol == 'Administrador'
        
        if not es_autor and not es_admin:
            return respuesta_error("No tienes permiso para eliminar esta reseña", 403)
        
        # Eliminar reseña
        if not eliminar_resena(resena_id, auth['usuario_id'] if es_autor else None):
            return respuesta_error("No se pudo eliminar la reseña", 500)
        
        log_info(f"Reseña eliminada: {resena_id} por usuario {auth['usuario_id']}")
        
        return respuesta_exito(mensaje="Reseña eliminada exitosamente")
        
    except Exception as e:
        log_error(f"Error en eliminar_resena_endpoint: {str(e)}")
        return respuesta_error("Error al eliminar reseña", 500)


@bp_resenas_api.route('/productos/<int:producto_id>/estadisticas', methods=['GET'])
def obtener_estadisticas_endpoint(producto_id: int):
    """
    GET /api/resenas/productos/<producto_id>/estadisticas
    
    Obtiene las estadísticas de reseñas de un producto (solo aprobadas)
    """
    try:
        estadisticas = obtener_estadisticas_producto(producto_id, solo_visibles=True)
        return respuesta_exito(data=estadisticas)
        
    except Exception as e:
        log_error(f"Error en obtener_estadisticas_endpoint: {str(e)}")
        return respuesta_error("Error al obtener estadísticas", 500)


@bp_resenas_api.route('/usuarios/mis-resenas', methods=['GET'])
def obtener_mis_resenas():
    """
    GET /api/resenas/usuarios/mis-resenas
    
    Obtiene las reseñas del usuario autenticado
    
    Query params:
        - page: número de página (default: 1)
        - per_page: reseñas por página (default: 10)
    """
    try:
        # Verificar autenticación
        auth = verificar_autenticacion()
        if not auth['autenticado']:
            return respuesta_error("Debes iniciar sesión", 401)
        
        # Parámetros de paginación
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Validar parámetros
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 50:
            per_page = 10
        
        # Obtener reseñas del usuario
        resenas, total = listar_resenas_usuario(
            usuario_id=auth['usuario_id'],
            page=page,
            per_page=per_page
        )
        
        # Serializar reseñas
        resenas_dict = [r.to_dict() for r in resenas]
        
        return respuesta_exito({
            'resenas': resenas_dict,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
        
    except Exception as e:
        log_error(f"Error en obtener_mis_resenas: {str(e)}")
        return respuesta_error("Error al obtener tus reseñas", 500)


# ===================== ENDPOINTS DE ADMINISTRACIÓN (NUEVOS) =====================

@bp_resenas_api.route('/admin/resenas', methods=['GET'])
@requiere_admin
def api_listar_resenas():
    """
    GET /api/resenas/admin/resenas?page=1&per_page=20&producto_id=&estado=&q=
    Lista todas las reseñas con filtros (para administrador)
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        producto_id = request.args.get('producto_id', type=int)
        estado = request.args.get('estado', '').strip()
        q = request.args.get('q', '').strip()
        
        filtros = {}
        if producto_id:
            filtros['producto_id'] = producto_id
        if estado:
            filtros['estado'] = estado
        if q:
            filtros['q'] = q
        
        items, total = listar_resenas(filtros=filtros, page=page, per_page=per_page)
        data = [to_dict(r) for r in items]
        
        usuario_correo = session.get('usuario_correo', 'desconocido')
        log_info(f"[audit] API listar_resenas accedida por {usuario_correo}")
        
        return jsonify({
            'ok': True,
            'resenas': data,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }), 200
        
    except Exception as e:
        log_error(f"[resenas_api] Error en api_listar_resenas: {e}")
        return jsonify({'ok': False, 'error': 'Error al cargar reseñas'}), 500


@bp_resenas_api.route('/admin/resenas/producto/<int:producto_id>', methods=['GET'])
@requiere_admin
def api_resenas_por_producto(producto_id: int):
    """
    GET /api/resenas/admin/resenas/producto/<id>
    Obtiene todas las reseñas de un producto específico (para administrador)
    """
    try:
        producto = obtener_producto_por_id(producto_id)
        if not producto:
            return jsonify({'ok': False, 'error': 'Producto no encontrado'}), 404
        
        items, total = listar_resenas(filtros={'producto_id': producto_id}, page=1, per_page=9999)
        data = [to_dict(r) for r in items]
        
        return jsonify({
            'ok': True,
            'producto': {
                'id': producto.id,
                'nombre': producto.nombre,
                'slug': producto.slug
            },
            'resenas': data,
            'total': total
        }), 200
        
    except Exception as e:
        log_error(f"[resenas_api] Error en api_resenas_por_producto: {e}")
        return jsonify({'ok': False, 'error': 'Error al cargar reseñas del producto'}), 500


@bp_resenas_api.route('/admin/resenas/<int:resena_id>/aprobar', methods=['PATCH'])
@requiere_admin
def api_aprobar_resena(resena_id: int):
    """PATCH /api/resenas/admin/resenas/<id>/aprobar"""
    try:
        usuario_correo = session.get('usuario_correo', 'desconocido')
        usuario_id = session.get('usuario_id')
        
        if not usuario_id:
            return jsonify({'ok': False, 'error': 'Usuario no identificado'}), 401
        
        payload = request.get_json(silent=True) or {}
        motivo = payload.get('motivo', '').strip() or None
        
        resena = aprobar_resena(resena_id, usuario_id, motivo)
        
        if not resena:
            log_warning(f"[audit] Error al aprobar reseña {resena_id} por {usuario_correo}")
            return jsonify({'ok': False, 'error': 'No se pudo aprobar la reseña'}), 400
        
        log_info(f"[audit] Reseña {resena_id} aprobada por {usuario_correo}")
        return jsonify({
            'ok': True,
            'mensaje': 'Reseña aprobada exitosamente',
            'resena': to_dict(resena)
        }), 200
        
    except Exception as e:
        log_error(f"[resenas_api] Error en api_aprobar_resena: {e}")
        return jsonify({'ok': False, 'error': 'Error interno del servidor'}), 500


@bp_resenas_api.route('/admin/resenas/<int:resena_id>/rechazar', methods=['PATCH'])
@requiere_admin
def api_rechazar_resena(resena_id: int):
    """PATCH /api/resenas/admin/resenas/<id>/rechazar"""
    try:
        usuario_correo = session.get('usuario_correo', 'desconocido')
        usuario_id = session.get('usuario_id')
        
        if not usuario_id:
            return jsonify({'ok': False, 'error': 'Usuario no identificado'}), 401
        
        payload = request.get_json(silent=True) or {}
        motivo = payload.get('motivo', '').strip() or None
        
        resena = rechazar_resena(resena_id, usuario_id, motivo)
        
        if not resena:
            log_warning(f"[audit] Error al rechazar reseña {resena_id} por {usuario_correo}")
            return jsonify({'ok': False, 'error': 'No se pudo rechazar la reseña'}), 400
        
        log_info(f"[audit] Reseña {resena_id} rechazada por {usuario_correo}")
        return jsonify({
            'ok': True,
            'mensaje': 'Reseña rechazada exitosamente',
            'resena': to_dict(resena)
        }), 200
        
    except Exception as e:
        log_error(f"[resenas_api] Error en api_rechazar_resena: {e}")
        return jsonify({'ok': False, 'error': 'Error interno del servidor'}), 500


@bp_resenas_api.route('/admin/resenas/<int:resena_id>/ocultar', methods=['PATCH'])
@requiere_admin
def api_ocultar_resena(resena_id: int):
    """PATCH /api/resenas/admin/resenas/<id>/ocultar"""
    try:
        usuario_correo = session.get('usuario_correo', 'desconocido')
        usuario_id = session.get('usuario_id')
        
        if not usuario_id:
            return jsonify({'ok': False, 'error': 'Usuario no identificado'}), 401
        
        payload = request.get_json(silent=True) or {}
        motivo = payload.get('motivo', '').strip() or None
        
        resena = ocultar_resena(resena_id, usuario_id, motivo)
        
        if not resena:
            log_warning(f"[audit] Error al ocultar reseña {resena_id} por {usuario_correo}")
            return jsonify({'ok': False, 'error': 'No se pudo ocultar la reseña'}), 400
        
        log_info(f"[audit] Reseña {resena_id} ocultada por {usuario_correo}")
        return jsonify({
            'ok': True,
            'mensaje': 'Reseña ocultada exitosamente',
            'resena': to_dict(resena)
        }), 200
        
    except Exception as e:
        log_error(f"[resenas_api] Error en api_ocultar_resena: {e}")
        return jsonify({'ok': False, 'error': 'Error interno del servidor'}), 500


@bp_resenas_api.route('/admin/resenas/<int:resena_id>/restaurar', methods=['PATCH'])
@requiere_admin
def api_restaurar_resena(resena_id: int):
    """PATCH /api/resenas/admin/resenas/<id>/restaurar"""
    try:
        usuario_correo = session.get('usuario_correo', 'desconocido')
        usuario_id = session.get('usuario_id')
        
        if not usuario_id:
            return jsonify({'ok': False, 'error': 'Usuario no identificado'}), 401
        
        resena = restaurar_resena(resena_id, usuario_id)
        
        if not resena:
            log_warning(f"[audit] Error al restaurar reseña {resena_id} por {usuario_correo}")
            return jsonify({'ok': False, 'error': 'No se pudo restaurar la reseña'}), 400
        
        log_info(f"[audit] Reseña {resena_id} restaurada por {usuario_correo}")
        return jsonify({
            'ok': True,
            'mensaje': 'Reseña restaurada exitosamente',
            'resena': to_dict(resena)
        }), 200
        
    except Exception as e:
        log_error(f"[resenas_api] Error en api_restaurar_resena: {e}")
        return jsonify({'ok': False, 'error': 'Error interno del servidor'}), 500


@bp_resenas_api.route('/admin/resenas/<int:resena_id>', methods=['DELETE'])
@requiere_admin
def api_eliminar_resena_admin(resena_id: int):
    """DELETE /api/resenas/admin/resenas/<id> (administrador)"""
    try:
        usuario_correo = session.get('usuario_correo', 'desconocido')
        
        ok = eliminar_resena(resena_id)
        
        if not ok:
            log_warning(f"[audit] Error al eliminar reseña {resena_id} por {usuario_correo}")
            return jsonify({'ok': False, 'error': 'No se pudo eliminar la reseña'}), 400
        
        log_info(f"[audit] Reseña {resena_id} eliminada permanentemente por {usuario_correo}")
        return jsonify({
            'ok': True,
            'mensaje': 'Reseña eliminada permanentemente'
        }), 200
        
    except Exception as e:
        log_error(f"[resenas_api] Error en api_eliminar_resena_admin: {e}")
        return jsonify({'ok': False, 'error': 'Error interno del servidor'}), 500


# ===================== HEALTH CHECK =====================

@bp_resenas_api.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar estado de la API"""
    return respuesta_exito(
        data={
            'service': 'API de Reseñas',
            'status': 'operational',
            'version': '2.0.0',
            'features': ['public', 'moderation', 'admin']
        }
    )