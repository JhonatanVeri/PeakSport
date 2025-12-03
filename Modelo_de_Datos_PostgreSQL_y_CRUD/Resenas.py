# -*- coding: utf-8 -*-
"""
Archivo: Modelo_de_Datos_PostgreSQL_y_CRUD/Resenas.py
Descripción: Modelo y CRUD para reseñas de productos
Autor: Sistema PicSport
Versión: 1.0.0
"""

from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy import CheckConstraint, func, Index
from sqlalchemy.exc import SQLAlchemyError

from Modelo_de_Datos_PostgreSQL_y_CRUD.conexion_postgres import db
from Log_PeakSport import log_info, log_warning, log_error


class Resena(db.Model):
    """
    Modelo de reseñas de productos
    
    Relaciones:
    - Muchos a Uno con Producto (una reseña pertenece a un producto)
    - Muchos a Uno con Usuario (una reseña es creada por un usuario)
    """
    __tablename__ = 'resenas'

    id = db.Column(db.BigInteger, primary_key=True)
    producto_id = db.Column(
        db.BigInteger, 
        db.ForeignKey('productos.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    usuario_id = db.Column(
        db.BigInteger, 
        db.ForeignKey('usuarios.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    
    # Calificación (1-5 estrellas)
    calificacion = db.Column(db.Integer, nullable=False)
    
    # Comentario
    comentario = db.Column(db.Text, nullable=False)
    
    # Verificación de compra
    compra_verificada = db.Column(
        db.Boolean, 
        nullable=False, 
        server_default=db.text("FALSE")
    )
    
    # Timestamps
    created_at = db.Column(
        db.DateTime, 
        nullable=False, 
        server_default=func.current_timestamp()
    )
    updated_at = db.Column(
        db.DateTime, 
        nullable=False, 
        server_default=func.current_timestamp(), 
        onupdate=func.current_timestamp()
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "calificacion >= 1 AND calificacion <= 5", 
            name="chk_calificacion_rango"
        ),
        CheckConstraint(
            "LENGTH(comentario) >= 10", 
            name="chk_comentario_minimo"
        ),
        # Índice compuesto para queries comunes
        Index('idx_resenas_producto_fecha', 'producto_id', 'created_at'),
        Index('idx_resenas_usuario_fecha', 'usuario_id', 'created_at'),
    )

    # Relaciones
    producto = db.relationship(
        'Producto', 
        backref=db.backref('resenas', lazy='dynamic', cascade='all, delete-orphan')
    )
    usuario = db.relationship(
        'Usuario', 
        backref=db.backref('resenas', lazy='dynamic', cascade='all, delete-orphan')
    )

    def __repr__(self):
        return f"<Resena {self.id} prod={self.producto_id} user={self.usuario_id}>"

    def to_dict(self) -> Dict[str, Any]:
        """Serializa la reseña para JSON"""
        return {
            "id": self.id,
            "producto_id": self.producto_id,
            "usuario_id": self.usuario_id,
            "usuario_nombre": self.usuario.nombre_completo if self.usuario else "Usuario",
            "calificacion": self.calificacion,
            "comentario": self.comentario,
            "compra_verificada": self.compra_verificada,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "tiempo_transcurrido": self._calcular_tiempo_transcurrido()
        }

    def _calcular_tiempo_transcurrido(self) -> str:
        """Calcula el tiempo transcurrido desde la creación"""
        if not self.created_at:
            return "Hace un momento"
        
        ahora = datetime.utcnow()
        diferencia = ahora - self.created_at
        
        if diferencia.days > 365:
            anos = diferencia.days // 365
            return f"Hace {anos} año{'s' if anos > 1 else ''}"
        elif diferencia.days > 30:
            meses = diferencia.days // 30
            return f"Hace {meses} mes{'es' if meses > 1 else ''}"
        elif diferencia.days > 0:
            return f"Hace {diferencia.days} día{'s' if diferencia.days > 1 else ''}"
        elif diferencia.seconds > 3600:
            horas = diferencia.seconds // 3600
            return f"Hace {horas} hora{'s' if horas > 1 else ''}"
        elif diferencia.seconds > 60:
            minutos = diferencia.seconds // 60
            return f"Hace {minutos} minuto{'s' if minutos > 1 else ''}"
        else:
            return "Hace un momento"


# ===================== CRUD DE RESEÑAS =====================

def crear_resena(
    producto_id: int,
    usuario_id: int,
    calificacion: int,
    comentario: str,
    compra_verificada: bool = False
) -> Optional[Resena]:
    """
    Crea una nueva reseña
    
    Args:
        producto_id: ID del producto
        usuario_id: ID del usuario que hace la reseña
        calificacion: Calificación de 1 a 5 estrellas
        comentario: Texto de la reseña (mínimo 10 caracteres)
        compra_verificada: Si el usuario compró el producto
    
    Returns:
        Objeto Resena o None si hay error
    """
    try:
        # Validaciones
        if not all([producto_id, usuario_id, calificacion, comentario]):
            log_warning("crear_resena: Faltan campos obligatorios")
            return None
        
        if not (1 <= calificacion <= 5):
            log_warning(f"crear_resena: Calificación inválida ({calificacion})")
            return None
        
        if len(comentario.strip()) < 10:
            log_warning("crear_resena: Comentario muy corto (mínimo 10 caracteres)")
            return None
        
        # Verificar que producto y usuario existen
        from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import Producto
        from Modelo_de_Datos_PostgreSQL_y_CRUD.Usuarios import Usuario
        
        if not db.session.get(Producto, producto_id):
            log_warning(f"crear_resena: Producto {producto_id} no existe")
            return None
        
        if not db.session.get(Usuario, usuario_id):
            log_warning(f"crear_resena: Usuario {usuario_id} no existe")
            return None
        
        # Verificar si ya existe una reseña de este usuario para este producto
        resena_existente = Resena.query.filter_by(
            producto_id=producto_id,
            usuario_id=usuario_id
        ).first()
        
        if resena_existente:
            log_warning(
                f"crear_resena: Usuario {usuario_id} ya reseñó producto {producto_id}"
            )
            return None
        
        # Crear reseña
        nueva_resena = Resena(
            producto_id=producto_id,
            usuario_id=usuario_id,
            calificacion=calificacion,
            comentario=comentario.strip(),
            compra_verificada=compra_verificada
        )
        
        db.session.add(nueva_resena)
        db.session.commit()
        
        log_info(
            f"Reseña creada: ID={nueva_resena.id} "
            f"producto={producto_id} usuario={usuario_id}"
        )
        return nueva_resena
        
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al crear reseña: {str(e)}")
        return None


def obtener_resena_por_id(resena_id: int) -> Optional[Resena]:
    """Obtiene una reseña por su ID"""
    try:
        resena = db.session.get(Resena, resena_id)
        if resena:
            log_info(f"Reseña obtenida: {resena_id}")
        else:
            log_warning(f"Reseña no encontrada: {resena_id}")
        return resena
    except SQLAlchemyError as e:
        log_error(f"Error al obtener reseña {resena_id}: {str(e)}")
        return None


def listar_resenas_producto(
    producto_id: int,
    page: int = 1,
    per_page: int = 10,
    orden: str = 'recientes'
) -> Tuple[List[Resena], int]:
    """
    Lista las reseñas de un producto con paginación
    
    Args:
        producto_id: ID del producto
        page: Número de página
        per_page: Reseñas por página
        orden: 'recientes', 'antiguas', 'mejor_calificadas', 'peor_calificadas'
    
    Returns:
        Tupla (lista_resenas, total_count)
    """
    try:
        query = Resena.query.filter_by(producto_id=producto_id)
        
        # Ordenamiento
        if orden == 'recientes':
            query = query.order_by(Resena.created_at.desc())
        elif orden == 'antiguas':
            query = query.order_by(Resena.created_at.asc())
        elif orden == 'mejor_calificadas':
            query = query.order_by(Resena.calificacion.desc(), Resena.created_at.desc())
        elif orden == 'peor_calificadas':
            query = query.order_by(Resena.calificacion.asc(), Resena.created_at.desc())
        else:
            query = query.order_by(Resena.created_at.desc())
        
        total = query.count()
        resenas = query.offset((page - 1) * per_page).limit(per_page).all()
        
        log_info(
            f"listar_resenas_producto: producto={producto_id} "
            f"page={page} total={total}"
        )
        return resenas, total
        
    except SQLAlchemyError as e:
        log_error(f"Error al listar reseñas de producto {producto_id}: {str(e)}")
        return [], 0


def listar_resenas_usuario(
    usuario_id: int,
    page: int = 1,
    per_page: int = 10
) -> Tuple[List[Resena], int]:
    """Lista las reseñas de un usuario"""
    try:
        query = Resena.query.filter_by(usuario_id=usuario_id)
        query = query.order_by(Resena.created_at.desc())
        
        total = query.count()
        resenas = query.offset((page - 1) * per_page).limit(per_page).all()
        
        log_info(f"listar_resenas_usuario: usuario={usuario_id} total={total}")
        return resenas, total
        
    except SQLAlchemyError as e:
        log_error(f"Error al listar reseñas de usuario {usuario_id}: {str(e)}")
        return [], 0


def actualizar_resena(
    resena_id: int,
    calificacion: Optional[int] = None,
    comentario: Optional[str] = None
) -> Optional[Resena]:
    """
    Actualiza una reseña existente
    Solo permite actualizar calificación y comentario
    """
    try:
        resena = db.session.get(Resena, resena_id)
        if not resena:
            log_warning(f"actualizar_resena: Reseña {resena_id} no encontrada")
            return None
        
        # Actualizar calificación
        if calificacion is not None:
            if not (1 <= calificacion <= 5):
                log_warning(f"actualizar_resena: Calificación inválida ({calificacion})")
                return None
            resena.calificacion = calificacion
        
        # Actualizar comentario
        if comentario is not None:
            comentario = comentario.strip()
            if len(comentario) < 10:
                log_warning("actualizar_resena: Comentario muy corto")
                return None
            resena.comentario = comentario
        
        db.session.commit()
        log_info(f"Reseña actualizada: {resena_id}")
        return resena
        
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al actualizar reseña {resena_id}: {str(e)}")
        return None


def eliminar_resena(resena_id: int, usuario_id: Optional[int] = None) -> bool:
    """
    Elimina una reseña
    
    Args:
        resena_id: ID de la reseña
        usuario_id: ID del usuario (para verificar que sea el dueño)
    
    Returns:
        True si se eliminó, False si no
    """
    try:
        resena = db.session.get(Resena, resena_id)
        if not resena:
            log_warning(f"eliminar_resena: Reseña {resena_id} no encontrada")
            return False
        
        # Verificar que el usuario sea el dueño de la reseña
        if usuario_id is not None and resena.usuario_id != usuario_id:
            log_warning(
                f"eliminar_resena: Usuario {usuario_id} no es dueño de reseña {resena_id}"
            )
            return False
        
        db.session.delete(resena)
        db.session.commit()
        log_info(f"Reseña eliminada: {resena_id}")
        return True
        
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al eliminar reseña {resena_id}: {str(e)}")
        return False


def obtener_estadisticas_producto(producto_id: int) -> Dict[str, Any]:
    """
    Obtiene estadísticas de reseñas de un producto
    
    Returns:
        Dict con promedio, total, distribución por estrellas, etc.
    """
    try:
        resenas = Resena.query.filter_by(producto_id=producto_id).all()
        
        if not resenas:
            return {
                "total": 0,
                "promedio": 0.0,
                "distribucion": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        
        # Calcular promedio
        total = len(resenas)
        suma_calificaciones = sum(r.calificacion for r in resenas)
        promedio = round(suma_calificaciones / total, 1)
        
        # Distribución por estrellas
        distribucion = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for resena in resenas:
            distribucion[resena.calificacion] += 1
        
        # Porcentajes
        porcentajes = {
            estrella: round((count / total) * 100, 1)
            for estrella, count in distribucion.items()
        }
        
        log_info(f"Estadísticas producto {producto_id}: promedio={promedio}")
        
        return {
            "total": total,
            "promedio": promedio,
            "distribucion": distribucion,
            "porcentajes": porcentajes
        }
        
    except SQLAlchemyError as e:
        log_error(f"Error al obtener estadísticas de producto {producto_id}: {str(e)}")
        return {
            "total": 0,
            "promedio": 0.0,
            "distribucion": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        }


def verificar_usuario_puede_resenar(producto_id: int, usuario_id: int) -> bool:
    """
    Verifica si un usuario puede dejar una reseña para un producto
    (es decir, si aún no ha dejado una reseña)
    """
    try:
        resena_existente = Resena.query.filter_by(
            producto_id=producto_id,
            usuario_id=usuario_id
        ).first()
        
        return resena_existente is None
        
    except SQLAlchemyError as e:
        log_error(f"Error al verificar si usuario puede reseñar: {str(e)}")
        return False