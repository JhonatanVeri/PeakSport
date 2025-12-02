# -*- coding: utf-8 -*-
"""
Controlador de Administrador (Principal) - VERSIÓN CORREGIDA
CRUD de Productos, gestión de Imágenes y asociación con Categorías.

CAMBIOS REALIZADOS:
1. ✅ Importar @requiere_mfa desde utils
2. ✅ Agregar @requiere_mfa a TODAS las rutas protegidas
3. ✅ Reemplazar renderizar_vista_entorno_desarrollo_y_produccion() con renderizar_vista_protegida()
4. ✅ Agregar logs de auditoría con usuario_correo
"""

import os
import unicodedata
import re
from typing import Optional
from flask import (
    request, jsonify, session, redirect, url_for, current_app, abort
)
from werkzeug.utils import secure_filename

# ✅ CAMBIO 1: Importar decorador MFA
from utils import renderizar_vista_protegida, requiere_mfa

from Log_PeakSport import log_info, log_warning, log_error, log_critical
from Modelo_de_Datos_PostgreSQL_y_CRUD.conexion_postgres import db
from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import (
    Producto,
    crear_producto,
    obtener_producto_por_id,
    listar_productos,
    actualizar_producto,
    eliminar_producto,
    agregar_categoria_a_producto,
    quitar_categoria_de_producto,
)
from Modelo_de_Datos_PostgreSQL_y_CRUD.Categorias import (
    Categoria,
    crear_categoria,
    listar_categorias,
)
from Modelo_de_Datos_PostgreSQL_y_CRUD.Producto_Imagenes import (
    ProductoImagen,
    agregar_imagen,
    listar_imagenes_producto,
    actualizar_imagen as actualizar_imagen_db,
    reordenar_imagen,
    eliminar_imagen as eliminar_imagen_db,
    set_portada
)

# =========================
# Helpers
# =========================

def _slugify(text: str) -> str:
    """Genera un slug URL-safe a partir de 'text'."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text

def _uploads_root() -> str:
    return os.path.join(current_app.static_folder, "uploads", "productos")

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

def _allowed_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def _requiere_admin():
    """
    Verifica rol de Administrador.
    Acepta dos estilos de sesión:
    - session['usuario'] = {'rol': 'Administrador', ...}
    - o llaves sueltas: session['usuario_rol'] == 'Administrador'
    """
    user_dict = session.get("usuario") or {}
    rol = user_dict.get("rol") or session.get("usuario_rol")
    if rol != "Administrador":
        log_warning(f"[seguridad] Acceso denegado (no es admin): {session.get('usuario_correo')}")
        abort(403)


def requiere_admin(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        _requiere_admin()
        return fn(*args, **kwargs)
    return wrapper

# =========================
# Registro de rutas
# =========================

def registrar_rutas(bp):

    # ═══════════════════════════════════════════════════════
    # VISTAS HTML - PRODUCTOS
    # ═══════════════════════════════════════════════════════
    
    @bp.route("/admin/productos", methods=["GET"])
    @requiere_mfa  # ✅ NUEVO: Verifica MFA antes
    @requiere_admin
    def vista_listado_productos():
        """Lista de productos con paginación y filtros"""
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        q = request.args.get("q", "").strip()
        activo = request.args.get("activo")
        categoria_id = request.args.get("categoria_id", type=int)

        filtros = {}
        if q:
            filtros["q"] = q
        if activo in {"true", "false"}:
            filtros["activo"] = (activo == "true")
        if categoria_id:
            filtros["categoria_id"] = categoria_id

        items, total = listar_productos(filtros=filtros, page=page, per_page=per_page)
        cats, _ = listar_categorias(padre_id=None, page=1, per_page=9999)

        # ✅ Usar renderizar_vista_protegida en lugar de renderizar_vista_entorno_desarrollo_y_produccion
        return renderizar_vista_protegida(
            "administrador_principal.html",
            productos=items,
            total=total,
            page=page,
            per_page=per_page,
            q=q,
            activo=activo,
            categoria_id=categoria_id,
            categorias=cats,
        )

    @bp.route("/admin/productos/nuevo", methods=["GET"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def vista_nuevo_producto():
        """Formulario para crear nuevo producto"""
        cats, _ = listar_categorias(padre_id=None, page=1, per_page=9999)
        
        # ✅ Cambiar a renderizar_vista_protegida
        return renderizar_vista_protegida(
            "administrador_principal_crear.html",
            producto=None,
            categorias=cats,
            modo="crear"
        )

    @bp.route("/admin/productos/<int:producto_id>/editar", methods=["GET"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def vista_editar_producto(producto_id: int):
        """Formulario para editar producto"""
        prod = obtener_producto_por_id(producto_id)
        if not prod:
            abort(404)
        
        cats, _ = listar_categorias(padre_id=None, page=1, per_page=9999)
        imgs = listar_imagenes_producto(producto_id)

        # ✅ Cambiar a renderizar_vista_protegida
        return renderizar_vista_protegida(
            "administrador_principal_editar.html",
            producto=prod,
            categorias=cats,
            imagenes=imgs,
            modo="editar"
        )
    
    @bp.route("/admin/productos/<int:producto_id>/eliminar", methods=["GET"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def vista_eliminar_producto(producto_id: int):
        """Vista de confirmación para eliminar producto"""
        prod = obtener_producto_por_id(producto_id)
        if not prod:
            abort(404)
        
        # ✅ Cambiar a renderizar_vista_protegida
        return renderizar_vista_protegida(
            "administrador_principal_eliminar.html",
            producto=prod
        )
    
    # ═══════════════════════════════════════════════════════
    # API - CRUD PRODUCTOS
    # ═══════════════════════════════════════════════════════
    
    @bp.route("/api/admin/productos/<int:producto_id>/eliminar", methods=["DELETE"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def api_eliminar_producto(producto_id: int):
        """Elimina un producto (API)"""
        try:
            usuario_correo = session.get('usuario_correo', 'desconocido')
            
            ok = eliminar_producto(producto_id)
            if not ok:
                log_warning(f"[audit] Intento fallido de eliminar producto {producto_id} por {usuario_correo}")
                return jsonify({
                    "ok": False,
                    "error": f"No se pudo eliminar el producto con ID {producto_id}"
                }), 400

            # ✅ Log de auditoría mejorado
            log_info(f"[audit] Producto {producto_id} eliminado por {usuario_correo}")
            return jsonify({"ok": True, "mensaje": "Producto eliminado correctamente"}), 200

        except Exception as e:
            log_error(f"[admin] Error al eliminar producto {producto_id}: {e}")
            return jsonify({"ok": False, "error": "Error interno del servidor"}), 500

    @bp.route("/api/admin/productos", methods=["GET"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def api_listar_productos():
        """Lista productos en formato JSON (API)"""
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        q = request.args.get("q", "").strip()
        activo = request.args.get("activo")
        categoria_id = request.args.get("categoria_id", type=int)

        filtros = {}
        if q:
            filtros["q"] = q
        if activo in {"true", "false"}:
            filtros["activo"] = (activo == "true")
        if categoria_id:
            filtros["categoria_id"] = categoria_id

        items, total = listar_productos(filtros=filtros, page=page, per_page=per_page)
        data = []
        
        for p in items:
            # Encontrar imagen portada
            imagen_portada = None
            for img in p.imagenes:
                if img.es_portada:
                    imagen_portada = img.to_dict()["url"]
                    break
            
            # Fallback a primera imagen
            if not imagen_portada and p.imagenes:
                imagen_portada = p.imagenes[0].to_dict()["url"]

            data.append({
                "id": p.id,
                "nombre": p.nombre,
                "slug": p.slug,
                "descripcion": p.descripcion,
                "precio_centavos": p.precio_centavos,
                "moneda": p.moneda,
                "stock": p.stock or 0,
                "sku": p.sku or None,
                "activo": p.activo,
                "imagen_portada": imagen_portada,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            })
        
        # ✅ Log de auditoría
        log_info(f"[audit] API listar_productos accedida por {session.get('usuario_correo')}")
        
        return jsonify({"items": data, "total": total, "page": page, "per_page": per_page})

    @bp.route("/api/admin/productos", methods=["POST"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def api_crear_producto():
        """Crea nuevo producto (API)"""
        usuario_correo = session.get('usuario_correo', 'desconocido')
        payload = request.get_json(silent=True) or request.form.to_dict()
        nombre = (payload.get("nombre") or "").strip()
        slug = (payload.get("slug") or _slugify(nombre)).strip()
        descripcion = payload.get("descripcion")
        moneda = (payload.get("moneda") or "COP").strip().upper()
        sku = (payload.get("sku") or "").strip() or None
        activo = payload.get("activo")
        
        if isinstance(activo, str):
            activo = activo.lower() in {"1", "true", "t", "yes", "on"}
        elif activo is None:
            activo = True

        if not nombre:
            log_warning(f"[audit] Intento de crear producto sin nombre por {usuario_correo}")
            return jsonify({"ok": False, "error": "El nombre es obligatorio"}), 400

        try:
            precio_centavos = int(payload.get("precio_centavos", 0))
        except Exception:
            return jsonify({"ok": False, "error": "precio_centavos inválido"}), 400

        try:
            stock = int(payload.get("stock", 0))
            if stock < 0:
                return jsonify({"ok": False, "error": "El stock no puede ser negativo"}), 400
        except Exception:
            return jsonify({"ok": False, "error": "stock inválido"}), 400

        usuario_id = None

        prod = crear_producto(
            nombre=nombre,
            slug=slug,
            precio_centavos=precio_centavos,
            stock=stock,
            sku=sku,
            descripcion=descripcion,
            moneda=moneda,
            activo=bool(activo),
            usuario_id=usuario_id
        )
        
        if not prod:
            log_warning(f"[audit] Error al crear producto '{nombre}' por {usuario_correo}")
            return jsonify({"ok": False, "error": "No fue posible crear el producto"}), 400

        # ✅ Log de auditoría mejorado
        log_info(f"[audit] Producto '{slug}' creado por {usuario_correo}")
        
        return jsonify({"ok": True, "id": prod.id, "slug": prod.slug}), 201
    
    @bp.route("/api/admin/productos/<int:producto_id>", methods=["GET"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def api_detalle_producto(producto_id: int):
        """Obtiene detalles de un producto (API)"""
        p = obtener_producto_por_id(producto_id)
        if not p:
            return jsonify({"ok": False, "error": "Producto no encontrado"}), 404

        portada = None
        for img in p.imagenes:
            if img.es_portada:
                portada = {
                    "id": img.id,
                    "url": img.to_dict()["url"],
                    "alt": img.alt,
                    "orden": img.orden,
                    "es_portada": img.es_portada
                }
                break

        return jsonify({
            "ok": True,
            "producto": {
                "id": p.id,
                "nombre": p.nombre,
                "slug": p.slug,
                "descripcion": p.descripcion,
                "precio_centavos": p.precio_centavos,
                "moneda": p.moneda,
                "activo": p.activo,
                "categorias": [{"id": c.id, "nombre": c.nombre, "slug": c.slug} for c in p.categorias],
                "portada": portada
            }
        })

    @bp.route("/api/admin/productos/<int:producto_id>", methods=["PATCH"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def api_actualizar_producto(producto_id: int):
        """Actualiza un producto (API)"""
        usuario_correo = session.get('usuario_correo', 'desconocido')
        payload = request.get_json(silent=True) or request.form.to_dict()
        campos = {}
        
        for k in ["nombre", "slug", "descripcion", "moneda"]:
            if k in payload:
                campos[k] = payload[k]
        
        if "activo" in payload:
            v = payload["activo"]
            if isinstance(v, str):
                v = v.lower() in {"1", "true", "t", "yes", "on"}
            campos["activo"] = bool(v)
        
        if "precio_centavos" in payload:
            try:
                campos["precio_centavos"] = int(payload["precio_centavos"])
            except Exception:
                return jsonify({"ok": False, "error": "precio_centavos inválido"}), 400
        
        if "stock" in payload:
            try:
                stock = int(payload["stock"])
                if stock < 0:
                    return jsonify({"ok": False, "error": "El stock no puede ser negativo"}), 400
                campos["stock"] = stock
            except Exception:
                return jsonify({"ok": False, "error": "stock inválido"}), 400
        
        if "sku" in payload:
            campos["sku"] = payload.get("sku") or None

        p = actualizar_producto(producto_id, **campos)
        if not p:
            log_warning(f"[audit] Error al actualizar producto {producto_id} por {usuario_correo}")
            return jsonify({"ok": False, "error": "No fue posible actualizar"}), 400
        
        # ✅ Log de auditoría
        log_info(f"[audit] Producto {producto_id} actualizado por {usuario_correo}")
        
        return jsonify({"ok": True})
    
    # ═══════════════════════════════════════════════════════
    # API - CATEGORÍAS
    # ═══════════════════════════════════════════════════════

    @bp.route("/api/admin/productos/<int:producto_id>/categorias", methods=["POST"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def api_agregar_categoria(producto_id: int):
        """Asocia categoría a producto (API)"""
        payload = request.get_json(silent=True) or request.form.to_dict()
        categoria_id = payload.get("categoria_id", type=int) if hasattr(payload, "get") else payload.get("categoria_id")
        
        try:
            categoria_id = int(categoria_id)
        except Exception:
            return jsonify({"ok": False, "error": "categoria_id inválido"}), 400

        ok = agregar_categoria_a_producto(producto_id, categoria_id)
        if not ok:
            return jsonify({"ok": False, "error": "No fue posible asociar la categoría"}), 400
        
        log_info(f"[audit] Categoría {categoria_id} asociada a producto {producto_id}")
        return jsonify({"ok": True})

    @bp.route("/api/admin/productos/<int:producto_id>/categorias/<int:categoria_id>", methods=["DELETE"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def api_quitar_categoria(producto_id: int, categoria_id: int):
        """Desasocia categoría de producto (API)"""
        ok = quitar_categoria_de_producto(producto_id, categoria_id)
        if not ok:
            return jsonify({"ok": False, "error": "No fue posible remover la categoría"}), 400
        
        log_info(f"[audit] Categoría {categoria_id} removida de producto {producto_id}")
        return jsonify({"ok": True})

    # ═══════════════════════════════════════════════════════
    # API - IMÁGENES
    # ═══════════════════════════════════════════════════════

    @bp.route("/api/admin/productos/<int:producto_id>/imagenes", methods=["GET"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def api_listar_imagenes(producto_id: int):
        """Lista imágenes de producto (API)"""
        imgs = listar_imagenes_producto(producto_id)
        data = [{
            "id": i.id,
            "url": i.url,
            "alt": i.alt,
            "orden": i.orden,
            "es_portada": i.es_portada
        } for i in imgs]
        return jsonify({"ok": True, "items": data})

    @bp.route("/api/admin/productos/<int:producto_id>/imagenes", methods=["POST"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def api_subir_imagenes(producto_id: int):
        """Sube imágenes para un producto (API)"""
        prod = obtener_producto_por_id(producto_id)
        if not prod:
            return jsonify({"ok": False, "error": "Producto no encontrado"}), 404

        files = request.files.getlist("files") or request.files.getlist("imagenes")
        if not files:
            return jsonify({"ok": False, "error": "No se enviaron archivos"}), 400

        alts = request.form.getlist("alt")
        portada_index = request.form.get("portada_index")
        try:
            portada_index = int(portada_index) if portada_index is not None else None
        except Exception:
            portada_index = None

        base = _uploads_root()
        _ensure_dir(base)
        dest_dir = os.path.join(base, str(producto_id))
        _ensure_dir(dest_dir)

        creadas = []
        portada_set = False

        for idx, file in enumerate(files):
            filename = secure_filename(file.filename or "")
            if not filename or not _allowed_image(filename):
                log_warning(f"Archivo inválido omitido: {filename}")
                continue

            name, ext = os.path.splitext(filename)
            safe_name = filename
            c = 1
            while os.path.exists(os.path.join(dest_dir, safe_name)):
                safe_name = f"{name}_{c}{ext}"
                c += 1

            save_path = os.path.join(dest_dir, safe_name)
            file.save(save_path)

            rel_path = os.path.relpath(save_path, current_app.static_folder).replace("\\", "/")
            url_publica = f"/static/{rel_path}"

            alt_txt = alts[idx] if idx < len(alts) else None
            es_portada = (portada_index == idx)

            img = agregar_imagen(producto_id=producto_id, url=url_publica, alt=alt_txt, orden=0, es_portada=es_portada)
            if img:
                creadas.append({
                    "id": img.id,
                    "url": img.to_dict()["url"],
                    "alt": img.alt,
                    "orden": img.orden,
                    "es_portada": img.es_portada
                })
                if es_portada:
                    portada_set = True

        if not portada_set:
            existentes = listar_imagenes_producto(producto_id)
            if existentes and not any(i.es_portada for i in existentes):
                set_portada(producto_id, existentes[0].id)

        log_info(f"[audit] {len(creadas)} imágenes subidas a producto {producto_id}")
        return jsonify({"ok": True, "creadas": creadas})

    @bp.route("/api/admin/imagenes/<int:imagen_id>", methods=["PATCH"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def api_actualizar_imagen(imagen_id: int):
        """Actualiza una imagen (API)"""
        payload = request.get_json(silent=True) or request.form.to_dict()
        campos = {}
        
        if "alt" in payload:
            campos["alt"] = payload["alt"]
        if "orden" in payload:
            try:
                campos["orden"] = int(payload["orden"])
            except Exception:
                return jsonify({"ok": False, "error": "orden inválido"}), 400
        if "es_portada" in payload:
            v = payload["es_portada"]
            if isinstance(v, str):
                v = v.lower() in {"1", "true", "t", "yes", "on"}
            campos["es_portada"] = bool(v)

        if "orden" in campos and len(campos) == 1:
            img = reordenar_imagen(imagen_id, campos["orden"])
            if not img:
                return jsonify({"ok": False, "error": "No fue posible reordenar"}), 400
            return jsonify({"ok": True})

        img = actualizar_imagen_db(imagen_id, **campos)
        if not img:
            return jsonify({"ok": False, "error": "No fue posible actualizar imagen"}), 400
        
        log_info(f"[audit] Imagen {imagen_id} actualizada")
        return jsonify({"ok": True})

    @bp.route("/api/admin/imagenes/<int:imagen_id>", methods=["DELETE"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def api_eliminar_imagen(imagen_id: int):
        """Elimina una imagen (API)"""
        img = ProductoImagen.query.get(imagen_id)
        if not img:
            return jsonify({"ok": False, "error": "Imagen no encontrada"}), 404

        try:
            if img.url and img.url.startswith("/static/"):
                abs_path = os.path.join(current_app.root_path, img.url.lstrip("/"))
                if os.path.isfile(abs_path):
                    os.remove(abs_path)
        except Exception as e:
            log_warning(f"No se pudo borrar archivo físico de la imagen {imagen_id}: {e}")

        ok = eliminar_imagen_db(imagen_id)
        if not ok:
            return jsonify({"ok": False, "error": "No fue posible eliminar imagen"}), 400
        
        log_info(f"[audit] Imagen {imagen_id} eliminada")
        return jsonify({"ok": True})

    # ═══════════════════════════════════════════════════════
    # VISTAS HTML - CATEGORÍAS
    # ═══════════════════════════════════════════════════════
    
    @bp.route("/admin/categorias", methods=["GET"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def vista_categorias():
        """Lista de categorías"""
        try:
            page = int(request.args.get("page", 1))
            per_page = int(request.args.get("per_page", 50))
            padre_id = request.args.get("padre_id", type=int)

            cats, total = listar_categorias(padre_id=padre_id, page=page, per_page=per_page)
            
            # ✅ Usar renderizar_vista_protegida
            return renderizar_vista_protegida(
                "administrador_principal_categorias.html",
                categorias=cats,
                total=total,
                page=page,
                per_page=per_page
            )
        except Exception as e:
            log_error(f"vista_categorias ERROR: {e}")
            return abort(500)

    # ═══════════════════════════════════════════════════════
    # API - CRUD CATEGORÍAS
    # ═══════════════════════════════════════════════════════
    
    @bp.route("/api/admin/categorias", methods=["GET"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def api_listar_categorias():
        """Lista categorías (API)"""
        try:
            page = int(request.args.get("page", 1))
            per_page = int(request.args.get("per_page", 50))
            padre_id = request.args.get("padre_id", type=int)

            cats, total = listar_categorias(padre_id=padre_id, page=page, per_page=per_page)
            data = [{
                "id": c.id,
                "nombre": c.nombre,
                "slug": c.slug,
                "descripcion": c.descripcion,
                "padre_id": c.padre_id
            } for c in cats]
            
            return jsonify({"ok": True, "items": data, "total": total})
        except Exception as e:
            log_error(f"api_listar_categorias ERROR: {e}")
            return jsonify({"ok": False, "error": "Error interno listando categorías"}), 500

    @bp.route("/api/admin/categorias", methods=["POST"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def api_crear_categoria():
        """Crea nueva categoría (API)"""
        from Modelo_de_Datos_PostgreSQL_y_CRUD.Categorias import crear_categoria
        
        try:
            usuario_correo = session.get('usuario_correo', 'desconocido')
            payload = request.get_json(silent=True) or request.form.to_dict()
            nombre = (payload.get("nombre") or "").strip()
            slug = (payload.get("slug") or "").strip().lower()
            descripcion = payload.get("descripcion")

            _padre = payload.get("padre_id")
            try:
                padre_id = int(_padre) if (_padre not in (None, "", "null")) else None
            except Exception:
                padre_id = None

            cat = crear_categoria(nombre=nombre, slug=slug, descripcion=descripcion, padre_id=padre_id)
            if not cat:
                log_warning(f"[audit] Error al crear categoría '{nombre}' por {usuario_correo}")
                return jsonify({"ok": False, "error": "No fue posible crear la categoría"}), 400
            
            log_info(f"[audit] Categoría '{slug}' creada por {usuario_correo}")
            return jsonify({"ok": True, "id": cat.id})
        except Exception as e:
            log_error(f"api_crear_categoria ERROR: {e}")
            return jsonify({"ok": False, "error": "Error interno creando categoría"}), 500
    
    # ════════════════════════════════════════════════════════════
    # CONTINUACIÓN: MÉTODOS DE ACTUALIZACIÓN Y ELIMINACIÓN CATEGORÍAS
    # ════════════════════════════════════════════════════════════

    @bp.route("/api/admin/categorias/<int:categoria_id>", methods=["PATCH"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def api_actualizar_categoria(categoria_id: int):
        """Actualiza una categoría (API)"""
        from Modelo_de_Datos_PostgreSQL_y_CRUD.Categorias import actualizar_categoria
        
        try:
            usuario_correo = session.get('usuario_correo', 'desconocido')
            payload = request.get_json(silent=True) or request.form.to_dict()
            campos = {}
            
            for k in ["nombre", "slug", "descripcion", "padre_id"]:
                if k in payload:
                    campos[k] = payload[k]
            
            if "padre_id" in campos:
                try:
                    v = campos["padre_id"]
                    campos["padre_id"] = int(v) if (v not in (None, "", "null")) else None
                except Exception:
                    campos.pop("padre_id", None)

            cat = actualizar_categoria(categoria_id, **campos)
            if not cat:
                log_warning(f"[audit] Error al actualizar categoría {categoria_id} por {usuario_correo}")
                return jsonify({"ok": False, "error": "No fue posible actualizar"}), 400
            
            log_info(f"[audit] Categoría {categoria_id} actualizada por {usuario_correo}")
            return jsonify({"ok": True})
        except Exception as e:
            log_error(f"api_actualizar_categoria ERROR: {e}")
            return jsonify({"ok": False, "error": "Error interno actualizando categoría"}), 500

    @bp.route("/api/admin/categorias/<int:categoria_id>", methods=["DELETE"])
    @requiere_mfa  # ✅ NUEVO
    @requiere_admin
    def api_eliminar_categoria(categoria_id: int):
        """Elimina una categoría (API)"""
        from Modelo_de_Datos_PostgreSQL_y_CRUD.Categorias import eliminar_categoria
        
        try:
            usuario_correo = session.get('usuario_correo', 'desconocido')
            
            ok = eliminar_categoria(categoria_id)
            if not ok:
                log_warning(f"[audit] Error al eliminar categoría {categoria_id} por {usuario_correo}")
                return jsonify({"ok": False, "error": "No fue posible eliminar"}), 400
            
            log_info(f"[audit] Categoría {categoria_id} eliminada por {usuario_correo}")
            return jsonify({"ok": True})
        except Exception as e:
            log_error(f"api_eliminar_categoria ERROR: {e}")
            return jsonify({"ok": False, "error": "Error interno eliminando categoría"}), 500


