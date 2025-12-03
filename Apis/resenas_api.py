# -*- coding: utf-8 -*-
"""
Archivo: Apis/resenas_api.py
Descripción: API REST para el sistema de reseñas
Autor: Sistema PicSport
Versión: 1.0.0
"""

from flask import Blueprint, request, jsonify, session
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
    verificar_usuario_puede_resenar
)

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


# ===================== ENDPOINTS =====================

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
        
        # Obtener reseñas
        resenas, total = listar_resenas_producto(
            producto_id=producto_id,
            page=page,
            per_page=per_page,
            orden=orden
        )
        
        # Serializar reseñas
        resenas_dict = [r.to_dict() for r in resenas]
        
        # Obtener estadísticas
        estadisticas = obtener_estadisticas_producto(producto_id)
        
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
    
    Crea una nueva reseña para un producto
    
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
        
        # Crear reseña
        nueva_resena = crear_resena(
            producto_id=producto_id,
            usuario_id=auth['usuario_id'],
            calificacion=calificacion,
            comentario=comentario,
            compra_verificada=False  # TODO: implementar verificación de compra
        )
        
        if not nueva_resena:
            return respuesta_error("No se pudo crear la reseña", 500)
        
        log_info(f"Reseña creada: {nueva_resena.id} por usuario {auth['usuario_id']}")
        
        return respuesta_exito(
            data=nueva_resena.to_dict(),
            mensaje="Reseña publicada exitosamente"
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
        # TODO: implementar verificación de rol de administrador
        es_autor = resena.usuario_id == auth['usuario_id']
        # es_admin = session.get('usuario_rol') == 'Administrador'
        
        if not es_autor:  # and not es_admin
            return respuesta_error("No tienes permiso para eliminar esta reseña", 403)
        
        # Eliminar reseña
        if not eliminar_resena(resena_id, auth['usuario_id']):
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
    
    Obtiene las estadísticas de reseñas de un producto
    """
    try:
        estadisticas = obtener_estadisticas_producto(producto_id)
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


# ===================== HEALTH CHECK =====================

@bp_resenas_api.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar estado de la API"""
    return respuesta_exito(
        data={
            'service': 'API de Reseñas',
            'status': 'operational',
            'version': '1.0.0'
        }
    )