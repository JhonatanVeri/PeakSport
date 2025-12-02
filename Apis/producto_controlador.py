# -*- coding: utf-8 -*-
from flask import request, jsonify
from Log_PeakSport import log_info, log_error
from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import (
    listar_productos, obtener_producto_por_slug
)


def _to_card2(prod):
    """Serializa producto a formato de tarjeta/front."""
    return {
        "id": prod.id,
        "name": prod.nombre,
        "slug": prod.slug,
        "price": round((prod.precio_centavos or 0) / 100.0, 2),
        "image": (prod.imagenes[0].url if getattr(prod, 'imagenes', None) and len(prod.imagenes) else "https://via.placeholder.com/300x300?text=PeakSport"),
        "rating": 4.7,  # si no manejas rating en BD, pon un default momentáneo
        "currency": prod.moneda or "COP",
        "active": bool(prod.activo),
    }

def _to_card(prod):
    """Serializa producto a formato de tarjeta/front, mostrando solo la portada."""
    portada = None

    if getattr(prod, 'imagenes', None) and len(prod.imagenes) > 0:
        # Buscar la portada
        portada = next((img for img in prod.imagenes if img.es_portada), None)
        # Si no hay portada, usar la primera imagen
        if not portada:
            portada = prod.imagenes[0]

    return {
        "id": prod.id,
        "name": prod.nombre,
        "slug": prod.slug,
        "price": round((prod.precio_centavos or 0) / 100.0, 2),
        "image": (portada.url if portada else "https://via.placeholder.com/300x300?text=PeakSport"),
        "rating": 4.7,  # valor fijo temporal
        "currency": prod.moneda or "COP",
        "active": bool(prod.activo),
    }


def registrar_rutas(bp):
    """Registra las rutas del blueprint pasado como parámetro."""

    @bp.get('/todos')
    def api_listar_productos():
        """
        GET /todos?q=&categoria_id=&activo=&page=&per_page=
        """
        try:
            filtros = {}
            q = request.args.get('q')
            categoria_id = request.args.get('categoria_id', type=int)
            activo = request.args.get('activo')
            if q: filtros['q'] = q
            if categoria_id is not None: filtros['categoria_id'] = categoria_id
            if activo is not None: filtros['activo'] = (activo.lower() == 'true')

            page = request.args.get('page', default=1, type=int)
            per_page = request.args.get('per_page', default=12, type=int)

            items, total = listar_productos(filtros=filtros, page=page, per_page=per_page)
            data = [_to_card(p) for p in items]
            return jsonify({
                "items": data,
                "total": total,
                "page": page,
                "per_page": per_page
            })
        except Exception as e:
            log_error(f"[productos] api_listar_productos error: {e}")
            return jsonify({"error": "Error interno"}), 500

    @bp.get('/recomendados')
    def api_recomendados():
        """
        GET /recomendados
        Usa listar_productos con filtros mínimos (ej. activos) y trae primeros 8
        """
        try:
            items, total = listar_productos(filtros={"activo": True}, page=1, per_page=8)
            data = [_to_card(p) for p in items]
            return jsonify({"items": data, "total": total})
        except Exception as e:
            log_error(f"[productos] api_recomendados error: {e}")
            return jsonify({"error": "Error interno"}), 500

    @bp.get('/<slug>')
    def api_detalle_producto(slug):
        try:
            prod = obtener_producto_por_slug(slug)
            if not prod:
                return jsonify({"error": "No encontrado"}), 404
            return jsonify(_to_card(prod))
        except Exception as e:
            log_error(f"[productos] api_detalle_producto error: {e}")
            return jsonify({"error": "Error interno"}), 500
