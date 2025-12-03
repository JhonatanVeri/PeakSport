# -*- coding: utf-8 -*-
from flask import request, jsonify
from Log_PeakSport import log_info, log_error, log_warning
from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import (
    listar_productos, obtener_producto_por_slug
)


def _to_card(prod):
    """Serializa producto a formato completo para el frontend."""
    portada = None

    if getattr(prod, 'imagenes', None) and len(prod.imagenes) > 0:
        # Buscar la portada
        portada = next((img for img in prod.imagenes if img.es_portada), None)
        # Si no hay portada, usar la primera imagen
        if not portada:
            portada = prod.imagenes[0]

    # ✅ CORREGIDO: Usar solo los campos que existen en el modelo
    precio_actual = round((prod.precio_centavos or 0) / 100.0, 2)
    
    # ✅ Verificar si existe precio_original_centavos antes de usarlo
    precio_original = precio_actual
    if hasattr(prod, 'precio_original_centavos') and prod.precio_original_centavos:
        precio_original = round(prod.precio_original_centavos / 100.0, 2)

    return {
        "id": prod.id,
        "nombre": prod.nombre,
        "slug": prod.slug,
        "descripcion": prod.descripcion,
        "precio_actual": precio_actual,
        "precio_original": precio_original,
        "stock": prod.stock,
        "activo": bool(prod.activo),
        "moneda": prod.moneda or "COP",
        "rating": 4.7,  # valor fijo temporal
        "vistas": getattr(prod, 'vistas', 0),
        "imagenes": [{"url": img.url, "es_portada": img.es_portada} for img in prod.imagenes] if hasattr(prod, 'imagenes') else [],
        "categorias": [{"id": cat.id, "nombre": cat.nombre} for cat in prod.categorias] if hasattr(prod, 'categorias') else []
    }


def registrar_rutas(bp):
    """Registra las rutas del blueprint pasado como parámetro."""

    @bp.get('/list')
    @bp.get('/todos')
    def api_listar_productos():
        """
        GET /list o /todos?q=&categoria_id=&activo=&page=&per_page=
        Lista todos los productos con paginación y filtros
        """
        try:
            filtros = {}
            q = request.args.get('q')
            categoria_id = request.args.get('categoria_id', type=int)
            activo = request.args.get('activo')
            
            if q: 
                filtros['q'] = q
            if categoria_id is not None: 
                filtros['categoria_id'] = categoria_id
            if activo is not None: 
                filtros['activo'] = (activo.lower() == 'true')

            page = request.args.get('page', default=1, type=int)
            per_page = request.args.get('per_page', default=100, type=int)

            items, total = listar_productos(filtros=filtros, page=page, per_page=per_page)
            data = [_to_card(p) for p in items]
            
            log_info(f"listar_productos: page={page}, per_page={per_page}, total={total}")
            
            return jsonify({
                "success": True,
                "productos": data,
                "total": total,
                "page": page,
                "per_page": per_page
            }), 200
            
        except Exception as e:
            log_error(f"[productos] api_listar_productos error: {e}")
            return jsonify({
                "success": False,
                "error": "Error al cargar productos"
            }), 500

    @bp.get('/recomendados')
    def api_recomendados():
        """
        GET /recomendados
        Obtiene productos recomendados (primeros 8 activos)
        """
        try:
            items, total = listar_productos(filtros={"activo": True}, page=1, per_page=8)
            data = [_to_card(p) for p in items]
            
            log_info(f"api_recomendados: {len(data)} productos")
            
            return jsonify({
                "success": True,
                "productos": data,
                "total": total
            }), 200
            
        except Exception as e:
            log_error(f"[productos] api_recomendados error: {e}")
            return jsonify({
                "success": False,
                "error": "Error al cargar recomendados"
            }), 500

    @bp.get('/<slug>')
    def api_detalle_producto(slug):
        """
        GET /<slug>
        Obtiene detalle de un producto por su slug
        """
        try:
            prod = obtener_producto_por_slug(slug)
            if not prod:
                log_warning(f"[productos] Producto no encontrado slug: {slug}")
                return jsonify({
                    "success": False,
                    "error": "Producto no encontrado"
                }), 404
            
            return jsonify({
                "success": True,
                "producto": _to_card(prod)
            }), 200
            
        except Exception as e:
            log_error(f"[productos] api_detalle_producto error: {e}")
            return jsonify({
                "success": False,
                "error": "Error al cargar producto"
            }), 500