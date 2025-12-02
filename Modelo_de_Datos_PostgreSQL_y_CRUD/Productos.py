# Modelo_de_Datos_PostgreSQL_y_CRUD/Productos.py
# -*- coding: utf-8 -*-
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import CheckConstraint, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from Modelo_de_Datos_PostgreSQL_y_CRUD.conexion_postgres import db
from Log_PeakSport import log_info, log_error, log_warning
from Modelo_de_Datos_PostgreSQL_y_CRUD.Categorias import Categoria
from Modelo_de_Datos_PostgreSQL_y_CRUD.associations import producto_categorias

class Producto(db.Model):
    __tablename__ = 'productos'

    id              = db.Column(db.BigInteger, primary_key=True)
    nombre          = db.Column(db.String(255), nullable=False, index=True)
    slug            = db.Column(db.String(255), nullable=False, unique=True)
    descripcion     = db.Column(db.Text)
    precio_centavos = db.Column(db.BigInteger, nullable=False)
    moneda          = db.Column(db.String(3), nullable=False, server_default='COP')
    stock           = db.Column(db.Integer, nullable=False, server_default='0')
    sku             = db.Column(db.String(100), unique=True, nullable=True)
    activo          = db.Column(db.Boolean, nullable=False, server_default=db.text("TRUE"))
    usuario_id      = db.Column(db.BigInteger, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    created_at      = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at      = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    __table_args__ = (
        CheckConstraint("precio_centavos >= 0", name="chk_precio_no_negativo"),
        CheckConstraint("stock >= 0", name="chk_stock_no_negativo"),
    )

    usuario = db.relationship('Usuario', backref=db.backref('productos', lazy='dynamic', passive_deletes=True))

    categorias = db.relationship(
        'Categoria',
        secondary=producto_categorias,
        back_populates='productos',
        lazy='dynamic'
    )

    # Importa por nombre de clase; la clase real está en Producto_imagenes.py
    imagenes = db.relationship(
        'ProductoImagen',
        back_populates='producto',
        cascade='all, delete-orphan',
        passive_deletes=True,
        order_by='ProductoImagen.orden'
    )

    def __repr__(self):
        return f"<Producto {self.slug}>"

# ===================== CRUD =====================

def crear_producto(
    nombre: str,
    slug: str,
    precio_centavos: int,
    stock: int = 0,
    sku: Optional[str] = None,
    descripcion: Optional[str] = None,
    moneda: str = 'COP',
    activo: bool = True,
    usuario_id: Optional[int] = None,
) -> Optional[Producto]:
    try:
        if not nombre or not slug:
            log_warning("crear_producto: nombre y slug son obligatorios")
            return None
        if precio_centavos is None or precio_centavos < 0:
            log_warning("crear_producto: precio_centavos inválido")
            return None
        if stock is None or stock < 0:
            log_warning("crear_producto: stock inválido")
            return None
        if Producto.query.filter_by(slug=slug).first():
            log_warning(f"crear_producto: slug ya existe '{slug}'")
            return None
        if sku and Producto.query.filter_by(sku=sku).first():
            log_warning(f"crear_producto: sku ya existe '{sku}'")
            return None

        prod = Producto(
            nombre=nombre,
            slug=slug,
            precio_centavos=precio_centavos,
            stock=stock,
            sku=sku,
            descripcion=descripcion,
            moneda=moneda,
            activo=activo,
            usuario_id=usuario_id
        )
        db.session.add(prod)
        db.session.commit()
        log_info(f"Producto creado: {slug} (stock: {stock})")
        return prod
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al crear producto '{slug}': {str(e)}")
        return None


def obtener_producto_por_id(producto_id: int) -> Optional[Producto]:
    try:
        prod = db.session.get(Producto, producto_id)
        if prod:
            log_info(f"Producto obtenido por id: {producto_id}")
        else:
            log_warning(f"Producto no encontrado id: {producto_id}")
        return prod
    except SQLAlchemyError as e:
        log_error(f"Error al obtener producto id {producto_id}: {str(e)}")
        return None


def obtener_producto_por_slug(slug: str) -> Optional[Producto]:
    try:
        prod = Producto.query.filter_by(slug=slug).first()
        if prod:
            log_info(f"Producto obtenido por slug: {slug}")
        else:
            log_warning(f"Producto no encontrado slug: {slug}")
        return prod
    except SQLAlchemyError as e:
        log_error(f"Error al obtener producto slug {slug}: {str(e)}")
        return None


def listar_productos(
    filtros: Optional[Dict[str, Any]] = None,
    page: int = 1,
    per_page: int = 20,
) -> Tuple[List[Producto], int]:
    try:
        filtros = filtros or {}

        query = Producto.query.options(joinedload(Producto.imagenes))  # 👈 clave

        if 'activo' in filtros:
            query = query.filter(Producto.activo == filtros['activo'])
        if 'usuario_id' in filtros:
            query = query.filter(Producto.usuario_id == filtros['usuario_id'])
        if 'q' in filtros and filtros['q']:
            q = f"%{filtros['q']}%"
            query = query.filter(Producto.nombre.ilike(q))
        if 'categoria_id' in filtros and filtros['categoria_id']:
            query = query.join(Producto.categorias).filter(Categoria.id == filtros['categoria_id'])

        total = query.count()
        items = (
            query.order_by(Producto.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        log_info(f"listar_productos: page={page}, per_page={per_page}, total={total}")
        return items, total
    except SQLAlchemyError as e:
        log_error(f"Error en listar_productos: {str(e)}")
        return [], 0


def listar_productos2(
    filtros: Optional[Dict[str, Any]] = None,
    page: int = 1,
    per_page: int = 20,
) -> Tuple[List[Producto], int]:
    """
    Retorna (items, total)
    filtros soportados: {'activo': bool, 'usuario_id': int, 'categoria_id': int, 'q': str}
    """

    try:
        query = Producto.query
        filtros = filtros or {}

        if 'activo' in filtros:
            query = query.filter(Producto.activo == filtros['activo'])
        if 'usuario_id' in filtros:
            query = query.filter(Producto.usuario_id == filtros['usuario_id'])
        if 'q' in filtros and filtros['q']:
            q = f"%{filtros['q']}%"
            query = query.filter(Producto.nombre.ilike(q))
        if 'categoria_id' in filtros:
            query = query.join(Producto.categorias).filter(Categoria.id == filtros['categoria_id'])

        total = query.count()
        items = query.order_by(Producto.created_at.desc()) \
                     .offset((page - 1) * per_page).limit(per_page).all()

        log_info(f"listar_productos: page={page}, per_page={per_page}, total={total}")
        return items, total
    except SQLAlchemyError as e:
        log_error(f"Error en listar_productos: {str(e)}")
        return [], 0


def actualizar_producto(producto_id: int, **kwargs) -> Optional[Producto]:
    """
    Campos permitidos: nombre, slug, descripcion, precio_centavos, moneda, stock, sku, activo, usuario_id
    """
    permitidos = {'nombre', 'slug', 'descripcion', 'precio_centavos', 'moneda', 'stock', 'sku', 'activo', 'usuario_id'}
    try:
        prod = db.session.get(Producto, producto_id)
        if not prod:
            log_warning(f"Producto no encontrado para actualizar: {producto_id}")
            return None

        for k, v in kwargs.items():
            if k not in permitidos:
                log_warning(f"actualizar_producto: campo ignorado '{k}'")
                continue
            if k == 'precio_centavos' and (v is None or v < 0):
                log_warning("actualizar_producto: precio_centavos inválido")
                continue
            if k == 'stock' and (v is None or v < 0):
                log_warning("actualizar_producto: stock inválido")
                continue
            setattr(prod, k, v)

        db.session.commit()
        log_info(f"Producto actualizado: {producto_id}")
        return prod
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al actualizar producto {producto_id}: {str(e)}")
        return None


def eliminar_producto(producto_id: int) -> bool:
    try:
        prod = db.session.get(Producto, producto_id)
        if not prod:
            log_warning(f"Producto no encontrado para eliminar: {producto_id}")
            return False
        db.session.delete(prod)
        db.session.commit()
        log_info(f"Producto eliminado: {producto_id}")
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al eliminar producto {producto_id}: {str(e)}")
        return False


# ----- Helpers N–N con categorías (opcional, cómodo tenerlos aquí) -----

def agregar_categoria_a_producto(producto_id: int, categoria_id: int) -> bool:

    try:
        prod = db.session.get(Producto, producto_id)
        cat = db.session.get(Categoria, categoria_id)
        if not prod or not cat:
            log_warning("agregar_categoria_a_producto: producto o categoria no existe")
            return False
        if prod.categorias.filter(Categoria.id == categoria_id).first():
            log_info("agregar_categoria_a_producto: ya estaba asociada")
            return True
        prod.categorias.append(cat)
        db.session.commit()
        log_info(f"Categoria {categoria_id} asociada a producto {producto_id}")
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al asociar categoria {categoria_id} a producto {producto_id}: {str(e)}")
        return False


def quitar_categoria_de_producto(producto_id: int, categoria_id: int) -> bool:
    try:
        prod = db.session.get(Producto, producto_id)
        if not prod:
            log_warning("quitar_categoria_de_producto: producto no existe")
            return False
        cat = prod.categorias.filter(Categoria.id == categoria_id).first()
        if not cat:
            log_warning("quitar_categoria_de_producto: asociación no existe")
            return False
        prod.categorias.remove(cat)
        db.session.commit()
        log_info(f"Categoria {categoria_id} removida de producto {producto_id}")
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al remover categoria {categoria_id} de producto {producto_id}: {str(e)}")
        return False