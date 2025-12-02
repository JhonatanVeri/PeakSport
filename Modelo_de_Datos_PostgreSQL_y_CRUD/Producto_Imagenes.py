# -*- coding: utf-8 -*-
"""
Autor: Jherson Sanchez (ajustado)
Descripción: Modelo y CRUD para la tabla `producto_imagenes`. Incluye utilidades de portada única.
Nota: Mantén en la DB el índice parcial único:
  CREATE UNIQUE INDEX IF NOT EXISTS ux_portada_por_producto
    ON producto_imagenes (producto_id) WHERE es_portada = TRUE;
"""

from typing import Optional, List
from flask import url_for
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from Modelo_de_Datos_PostgreSQL_y_CRUD.conexion_postgres import db
from Log_PeakSport import log_info, log_warning, log_error, log_critical

class ProductoImagen(db.Model):
    __tablename__ = 'producto_imagenes'

    id          = db.Column(db.BigInteger, primary_key=True)
    producto_id = db.Column(db.BigInteger, db.ForeignKey('productos.id', ondelete='CASCADE'), nullable=False, index=True)
    url         = db.Column(db.Text, nullable=False)
    alt         = db.Column(db.Text)
    orden       = db.Column(db.Integer, nullable=False, server_default='0')
    es_portada  = db.Column(db.Boolean, nullable=False, server_default=db.text("FALSE"))
    created_at  = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())

    producto    = db.relationship('Producto', back_populates='imagenes')

    def __repr__(self):
        return f"<ProductoImagen {self.id} prod={self.producto_id}>"

##importante: este método genera la URL completa para uso en frontend

    def to_dict(self):
        """
        Devuelve un diccionario con la URL absoluta de la imagen,
        lista para usarse directamente en el frontend.
        """
        if self.url and not self.url.startswith("http"):
            # Quita el prefijo '/static/' y genera la URL completa
            clean_path = self.url.replace('/static/', '')
            full_url = url_for('static', filename=clean_path, _external=True)
        else:
            full_url = self.url

        return {
            "id": self.id,
            "producto_id": self.producto_id,
            "url": full_url,
            "alt": self.alt,
            "orden": self.orden,
            "es_portada": self.es_portada,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

# ===================== CRUD =====================

def agregar_imagen(
    producto_id: int,
    url: str,
    alt: Optional[str] = None,
    orden: int = 0,
    es_portada: bool = False
) -> Optional[ProductoImagen]:
    try:
        if not url:
            log_warning("agregar_imagen: url es obligatoria")
            return None

        img = ProductoImagen(
            producto_id=producto_id,
            url=url,
            alt=alt,
            orden=orden,
            es_portada=False  # si piden portada, se aplica abajo para garantizar unicidad
        )
        db.session.add(img)
        db.session.flush()  # obtener id antes del commit

        if es_portada:
            db.session.query(ProductoImagen) \
                      .filter(ProductoImagen.producto_id == producto_id) \
                      .update({ProductoImagen.es_portada: False})
            img.es_portada = True

        db.session.commit()
        log_info(f"Imagen agregada id={img.id} a producto {producto_id} (portada={img.es_portada})")
        return img
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al agregar imagen a producto {producto_id}: {str(e)}")
        return None


def listar_imagenes_producto(producto_id: int) -> List[ProductoImagen]:
    try:
        imgs = ProductoImagen.query.filter_by(producto_id=producto_id) \
                                   .order_by(ProductoImagen.orden.asc(), ProductoImagen.id.asc()) \
                                   .all()
        log_info(f"listar_imagenes_producto: {producto_id} -> {len(imgs)}")
        return imgs
    except SQLAlchemyError as e:
        log_error(f"Error en listar_imagenes_producto {producto_id}: {str(e)}")
        return []


def obtener_imagen_por_id(imagen_id: int) -> Optional[ProductoImagen]:
    try:
        img = db.session.get(ProductoImagen, imagen_id)
        if img:
            log_info(f"Imagen obtenida id: {imagen_id}")
        else:
            log_warning(f"Imagen no encontrada id: {imagen_id}")
        return img
    except SQLAlchemyError as e:
        log_error(f"Error al obtener imagen id {imagen_id}: {str(e)}")
        return None


def set_portada(producto_id: int, imagen_id: int) -> bool:
    """
    Marca imagen_id como portada y quita portada al resto (una sola portada por producto).
    Recomendado: mantener el índice parcial único en DB.
    """
    try:
        img = db.session.get(ProductoImagen, imagen_id)
        if not img or img.producto_id != producto_id:
            log_warning("set_portada: imagen no existe o pertenece a otro producto")
            return False

        db.session.query(ProductoImagen) \
                  .filter(ProductoImagen.producto_id == producto_id) \
                  .update({ProductoImagen.es_portada: False})
        img.es_portada = True
        db.session.commit()
        log_info(f"set_portada: producto {producto_id} -> imagen {imagen_id}")
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error en set_portada producto {producto_id}, imagen {imagen_id}: {str(e)}")
        return False


def reordenar_imagen(imagen_id: int, nuevo_orden: int) -> Optional[ProductoImagen]:
    try:
        img = db.session.get(ProductoImagen, imagen_id)
        if not img:
            log_warning("reordenar_imagen: imagen no existe")
            return None
        img.orden = nuevo_orden
        db.session.commit()
        log_info(f"reordenar_imagen: imagen {imagen_id} -> orden {nuevo_orden}")
        return img
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error en reordenar_imagen {imagen_id}: {str(e)}")
        return None


def actualizar_imagen(imagen_id: int, **kwargs) -> Optional[ProductoImagen]:
    """
    Campos permitidos: url, alt, orden, es_portada, producto_id
    Si es_portada=True, se garantiza unicidad dentro del producto.
    """
    permitidos = {'url', 'alt', 'orden', 'es_portada', 'producto_id'}
    try:
        img = db.session.get(ProductoImagen, imagen_id)
        if not img:
            log_warning("actualizar_imagen: imagen no existe")
            return None

        es_portada_flag = False
        producto_id_objetivo = img.producto_id

        for k, v in kwargs.items():
            if k not in permitidos:
                log_warning(f"actualizar_imagen: campo ignorado '{k}'")
                continue
            if k == 'producto_id' and v is not None:
                producto_id_objetivo = v
            if k == 'es_portada' and bool(v):
                es_portada_flag = True
            setattr(img, k, v)

        if es_portada_flag:
            db.session.query(ProductoImagen) \
                      .filter(ProductoImagen.producto_id == producto_id_objetivo,
                              ProductoImagen.id != img.id) \
                      .update({ProductoImagen.es_portada: False})

        db.session.commit()
        log_info(f"Imagen actualizada: {imagen_id}")
        return img
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al actualizar imagen {imagen_id}: {str(e)}")
        return None


def eliminar_imagen(imagen_id: int) -> bool:
    try:
        img = db.session.get(ProductoImagen, imagen_id)
        if not img:
            log_warning("eliminar_imagen: imagen no existe")
            return False
        db.session.delete(img)
        db.session.commit()
        log_info(f"Imagen eliminada: {imagen_id}")
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al eliminar imagen {imagen_id}: {str(e)}")
        return False
