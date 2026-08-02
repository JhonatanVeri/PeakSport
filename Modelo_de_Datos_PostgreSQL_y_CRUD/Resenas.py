# -*- coding: utf-8 -*-
"""
Archivo: Modelo_de_Datos_PostgreSQL_y_CRUD/Resenas.py
Descripción: Modelo y CRUD para reseñas de productos con moderación
Autor: Sistema PeakSport
Versión: 2.0.0 (Con sistema de moderación)
"""

from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy import CheckConstraint, func, Index
from sqlalchemy.exc import SQLAlchemyError

from Modelo_de_Datos_PostgreSQL_y_CRUD.conexion_postgres import db
from Log_PeakSport import log_info, log_warning, log_error


class Resena(db.Model):
    """
    Modelo de reseñas de productos con sistema de moderación
    
    Relaciones:
    - Muchos a Uno con Producto (una reseña pertenece a un producto)
    - Muchos a Uno con Usuario (una reseña es creada por un usuario)
    - Muchos a Uno con Usuario (moderador que aprobó/rechazó)
    """
    __tablename__ = 'resenas'

    # Campos originales
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
    
    # ========== CAMPOS DE MODERACIÓN (NUEVOS) ==========
    visible = db.Column(db.Boolean, default=True, server_default=db.text("TRUE"))
    estado = db.Column(db.String(20), default='pendiente', server_default='pendiente')
    motivo_moderacion = db.Column(db.Text)
    num_reportes = db.Column(db.Integer, default=0, server_default='0')
    moderado_por = db.Column(db.BigInteger, db.ForeignKey('usuarios.id', ondelete='SET NULL'), index=True)
    moderado_at = db.Column(db.DateTime)
    # ===================================================
    
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
        foreign_keys=[usuario_id],
        backref='resenas_creadas'
    )
    moderador = db.relationship(
        'Usuario',
        foreign_keys=[moderado_por],
        backref='resenas_moderadas'
    )

    def __repr__(self):
        return f"<Resena {self.id} prod={self.producto_id} user={self.usuario_id}>"

    def to_dict(self) -> Dict[str, Any]:
        """Serializa la reseña para JSON (incluye campos de moderación)"""
        return {
            "id": self.id,
            "producto_id": self.producto_id,
            "producto_nombre": self.producto.nombre if self.producto else None,
            "usuario_id": self.usuario_id,
            "usuario_nombre": self.usuario.nombre_completo if self.usuario else "Usuario",
            "calificacion": self.calificacion,
            "comentario": self.comentario,
            "compra_verificada": self.compra_verificada,
            "visible": self.visible,
            "estado": self.estado,
            "motivo_moderacion": self.motivo_moderacion,
            "num_reportes": self.num_reportes,
            "moderado_por": self.moderado_por,
            "moderado_at": self.moderado_at.isoformat() if self.moderado_at else None,
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


# ===================== CRUD DE RESEÑAS (ORIGINAL) =====================

def crear_resena(
    producto_id: int,
    usuario_id: int,
    calificacion: int,
    comentario: str,
    compra_verificada: bool = False
) -> Optional[Resena]:
    """
    Crea una nueva reseña con estado PENDIENTE (para moderación)
    
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
        
        # Crear reseña con estado PENDIENTE
        nueva_resena = Resena(
            producto_id=producto_id,
            usuario_id=usuario_id,
            calificacion=calificacion,
            comentario=comentario.strip(),
            compra_verificada=compra_verificada,
            estado='pendiente',
            visible=True
        )
        
        db.session.add(nueva_resena)
        db.session.commit()
        
        log_info(
            f"Reseña creada: ID={nueva_resena.id} "
            f"producto={producto_id} usuario={usuario_id} estado=pendiente"
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
    orden: str = 'recientes',
    solo_visibles: bool = True
) -> Tuple[List[Resena], int]:
    """
    Lista las reseñas de un producto con paginación
    ACTUALIZADO: Filtra por visible=True por defecto (solo aprobadas para público)
    
    Args:
        producto_id: ID del producto
        page: Número de página
        per_page: Reseñas por página
        orden: 'recientes', 'antiguas', 'mejor_calificadas', 'peor_calificadas'
        solo_visibles: Si True, solo muestra reseñas aprobadas y visibles
    
    Returns:
        Tupla (lista_resenas, total_count)
    """
    try:
        query = Resena.query.filter_by(producto_id=producto_id)
        
        # Filtrar solo reseñas visibles (aprobadas) para el público
        if solo_visibles:
            query = query.filter_by(visible=True, estado='aprobada')
        
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
            f"page={page} total={total} solo_visibles={solo_visibles}"
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


def obtener_estadisticas_producto(producto_id: int, solo_visibles: bool = True) -> Dict[str, Any]:
    """
    Obtiene estadísticas de reseñas de un producto
    ACTUALIZADO: Por defecto solo cuenta reseñas aprobadas
    
    Args:
        producto_id: ID del producto
        solo_visibles: Si True, solo cuenta reseñas aprobadas
    
    Returns:
        Dict con promedio, total, distribución por estrellas, etc.
    """
    try:
        query = Resena.query.filter_by(producto_id=producto_id)
        
        if solo_visibles:
            query = query.filter_by(visible=True, estado='aprobada')
        
        resenas = query.all()
        
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


# ===================== FUNCIONES DE MODERACIÓN (NUEVAS) =====================

def listar_resenas(
    filtros: Optional[Dict[str, Any]] = None,
    page: int = 1,
    per_page: int = 20
) -> Tuple[List[Resena], int]:
    """
    Lista reseñas con filtros avanzados (para administrador)
    
    Args:
        filtros: Dict con claves: producto_id, estado, visible, q
        page: Número de página
        per_page: Elementos por página
        
    Returns:
        Tupla (lista_resenas, total)
    """
    try:
        filtros = filtros or {}
        query = Resena.query
        
        if 'producto_id' in filtros:
            query = query.filter(Resena.producto_id == filtros['producto_id'])
        
        if 'estado' in filtros and filtros['estado']:
            query = query.filter(Resena.estado == filtros['estado'])
        
        if 'visible' in filtros:
            query = query.filter(Resena.visible == filtros['visible'])
        
        if 'q' in filtros and filtros['q']:
            q = f"%{filtros['q']}%"
            query = query.filter(Resena.comentario.ilike(q))
        
        query = query.order_by(Resena.created_at.desc())
        
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        
        log_info(f"listar_resenas (admin): page={page}, per_page={per_page}, total={total}")
        return items, total
        
    except SQLAlchemyError as e:
        log_error(f"Error en listar_resenas: {str(e)}")
        return [], 0


def aprobar_resena(resena_id: int, moderador_id: int, motivo: Optional[str] = None) -> Optional[Resena]:
    """
    Aprueba una reseña.
    Estado: aprobada, Visible: TRUE
    """
    try:
        resena = db.session.get(Resena, resena_id)
        if not resena:
            log_warning(f"Reseña no encontrada para aprobar: {resena_id}")
            return None
        
        resena.estado = 'aprobada'
        resena.visible = True
        resena.moderado_por = moderador_id
        resena.moderado_at = datetime.utcnow()
        if motivo:
            resena.motivo_moderacion = motivo
        
        db.session.commit()
        log_info(f"Reseña {resena_id} aprobada por usuario {moderador_id}")
        return resena
        
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al aprobar reseña {resena_id}: {str(e)}")
        return None


def rechazar_resena(resena_id: int, moderador_id: int, motivo: Optional[str] = None) -> Optional[Resena]:
    """
    Rechaza una reseña.
    Estado: rechazada, Visible: FALSE
    """
    try:
        resena = db.session.get(Resena, resena_id)
        if not resena:
            log_warning(f"Reseña no encontrada para rechazar: {resena_id}")
            return None
        
        resena.estado = 'rechazada'
        resena.visible = False
        resena.moderado_por = moderador_id
        resena.moderado_at = datetime.utcnow()
        if motivo:
            resena.motivo_moderacion = motivo
        
        db.session.commit()
        log_info(f"Reseña {resena_id} rechazada por usuario {moderador_id}")
        return resena
        
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al rechazar reseña {resena_id}: {str(e)}")
        return None


def ocultar_resena(resena_id: int, moderador_id: int, motivo: Optional[str] = None) -> Optional[Resena]:
    """
    Oculta una reseña.
    Estado: oculta, Visible: FALSE
    """
    try:
        resena = db.session.get(Resena, resena_id)
        if not resena:
            log_warning(f"Reseña no encontrada para ocultar: {resena_id}")
            return None
        
        resena.estado = 'oculta'
        resena.visible = False
        resena.moderado_por = moderador_id
        resena.moderado_at = datetime.utcnow()
        if motivo:
            resena.motivo_moderacion = motivo
        
        db.session.commit()
        log_info(f"Reseña {resena_id} ocultada por usuario {moderador_id}")
        return resena
        
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al ocultar reseña {resena_id}: {str(e)}")
        return None


def restaurar_resena(resena_id: int, moderador_id: int) -> Optional[Resena]:
    """
    Restaura una reseña rechazada u ocultada.
    Estado: aprobada, Visible: TRUE
    """
    try:
        resena = db.session.get(Resena, resena_id)
        if not resena:
            log_warning(f"Reseña no encontrada para restaurar: {resena_id}")
            return None
        
        resena.estado = 'aprobada'
        resena.visible = True
        resena.moderado_por = moderador_id
        resena.moderado_at = datetime.utcnow()
        resena.motivo_moderacion = None
        
        db.session.commit()
        log_info(f"Reseña {resena_id} restaurada por usuario {moderador_id}")
        return resena
        
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al restaurar reseña {resena_id}: {str(e)}")
        return None


def eliminar_resena(resena_id: int, usuario_id: Optional[int] = None) -> bool:
    """
    Elimina permanentemente una reseña de la base de datos.
    Esta operación NO se puede deshacer.
    
    Args:
        resena_id: ID de la reseña
        usuario_id: ID del usuario (para verificar que sea el dueño, opcional)
    
    Returns:
        True si se eliminó, False si no
    """
    try:
        resena = db.session.get(Resena, resena_id)
        if not resena:
            log_warning(f"Reseña no encontrada para eliminar: {resena_id}")
            return False
        
        # Verificar que el usuario sea el dueño de la reseña (si se proporciona)
        if usuario_id is not None and resena.usuario_id != usuario_id:
            log_warning(
                f"eliminar_resena: Usuario {usuario_id} no es dueño de reseña {resena_id}"
            )
            return False
        
        db.session.delete(resena)
        db.session.commit()
        log_info(f"Reseña {resena_id} eliminada permanentemente")
        return True
        
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al eliminar reseña {resena_id}: {str(e)}")
        return False


def to_dict(resena: Resena) -> Dict[str, Any]:
    """
    Convierte una reseña a diccionario para API (alias de to_dict del modelo)
    
    Args:
        resena: Objeto Resena
        
    Returns:
        Diccionario con todos los campos de la reseña
    """
    return resena.to_dict()