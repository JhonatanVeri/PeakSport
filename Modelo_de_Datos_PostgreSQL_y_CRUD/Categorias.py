# -*- coding: utf-8 -*-
"""
Autor: Jherson Sanchez (ajustado)
Descripción: Modelo y CRUD para la tabla `categorias` (auto-relación padre/hijas).
"""

from typing import Optional, List, Tuple
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from Modelo_de_Datos_PostgreSQL_y_CRUD.conexion_postgres import db
from Log_PeakSport import log_info, log_warning, log_error, log_critical


class Categoria(db.Model):
    __tablename__ = 'categorias'

    id          = db.Column(db.BigInteger, primary_key=True)
    nombre      = db.Column(db.String(255), nullable=False, index=True)
    slug        = db.Column(db.String(255), nullable=False, unique=True)
    descripcion = db.Column(db.Text)
    padre_id    = db.Column(db.BigInteger, db.ForeignKey('categorias.id', ondelete='SET NULL'))
    created_at  = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())

    padre     = db.relationship('Categoria', remote_side=[id], backref='hijas')
    productos = db.relationship('Producto', secondary='producto_categorias', back_populates='categorias', lazy='dynamic')

    def __repr__(self):
        return f"<Categoria {self.slug}>"


# ===================== CRUD =====================

def crear_categoria(
    nombre: str,
    slug: str,
    descripcion: Optional[str] = None,
    padre_id: Optional[int] = None,
) -> Optional[Categoria]:
    try:
        if not nombre or not slug:
            log_warning("crear_categoria: nombre y slug son obligatorios")
            return None
        if Categoria.query.filter_by(slug=slug).first():
            log_warning(f"crear_categoria: slug ya existe '{slug}'")
            return None
        if padre_id and not db.session.get(Categoria, padre_id):
            log_warning(f"crear_categoria: padre_id {padre_id} no existe (se deja NULL)")
            padre_id = None

        cat = Categoria(
            nombre=nombre,
            slug=slug,
            descripcion=descripcion,
            padre_id=padre_id
        )
        db.session.add(cat)
        db.session.commit()
        log_info(f"Categoria creada: {slug}")
        return cat
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al crear categoria '{slug}': {str(e)}")
        return None


def obtener_categoria_por_id(categoria_id: int) -> Optional[Categoria]:
    try:
        cat = db.session.get(Categoria, categoria_id)
        if cat:
            log_info(f"Categoria obtenida id: {categoria_id}")
        else:
            log_warning(f"Categoria no encontrada id: {categoria_id}")
        return cat
    except SQLAlchemyError as e:
        log_error(f"Error al obtener categoria id {categoria_id}: {str(e)}")
        return None


def obtener_categoria_por_slug(slug: str) -> Optional[Categoria]:
    try:
        cat = Categoria.query.filter_by(slug=slug).first()
        if cat:
            log_info(f"Categoria obtenida slug: {slug}")
        else:
            log_warning(f"Categoria no encontrada slug: {slug}")
        return cat
    except SQLAlchemyError as e:
        log_error(f"Error al obtener categoria slug {slug}: {str(e)}")
        return None


def listar_categorias(
    padre_id: Optional[int] = None,
    page: int = 1,
    per_page: int = 50
) -> Tuple[List[Categoria], int]:
    try:
        query = Categoria.query
        if padre_id is None:
            query = query.filter(Categoria.padre_id.is_(None))
        else:
            query = query.filter(Categoria.padre_id == padre_id)

        total = query.count()
        items = query.order_by(Categoria.nombre.asc()) \
                     .offset((page - 1) * per_page).limit(per_page).all()
        log_info(f"listar_categorias: padre_id={padre_id}, total={total}")
        return items, total
    except SQLAlchemyError as e:
        log_error(f"Error en listar_categorias: {str(e)}")
        return [], 0


def actualizar_categoria(categoria_id: int, **kwargs) -> Optional[Categoria]:
    """
    Campos permitidos: nombre, slug, descripcion, padre_id
    """
    permitidos = {'nombre', 'slug', 'descripcion', 'padre_id'}
    try:
        cat = db.session.get(Categoria, categoria_id)
        if not cat:
            log_warning(f"Categoria no encontrada para actualizar: {categoria_id}")
            return None

        for k, v in kwargs.items():
            if k not in permitidos:
                log_warning(f"actualizar_categoria: campo ignorado '{k}'")
                continue
            if k == 'padre_id' and v == categoria_id:
                log_warning("actualizar_categoria: padre_id no puede ser igual al propio id")
                continue
            if k == 'padre_id' and v and not db.session.get(Categoria, v):
                log_warning(f"actualizar_categoria: padre_id {v} no existe (se ignora)")
                continue
            setattr(cat, k, v)

        db.session.commit()
        log_info(f"Categoria actualizada: {categoria_id}")
        return cat
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al actualizar categoria {categoria_id}: {str(e)}")
        return None


def eliminar_categoria(categoria_id: int) -> bool:
    """
    Al eliminar una categoría, sus hijas quedan huérfanas (padre_id = NULL).
    Las N–N con productos se limpian por FK en la tabla puente.
    """
    try:
        cat = db.session.get(Categoria, categoria_id)
        if not cat:
            log_warning(f"Categoria no encontrada para eliminar: {categoria_id}")
            return False

        for hija in list(cat.hijas):
            hija.padre_id = None

        db.session.delete(cat)
        db.session.commit()
        log_info(f"Categoria eliminada: {categoria_id}")
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al eliminar categoria {categoria_id}: {str(e)}")
        return False
