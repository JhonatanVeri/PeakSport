# -*- coding: utf-8 -*-
"""
Autor: Jherson Sanchez (ajustado)
Descripción: Modelo y CRUD para la tabla `usuarios` en PostgreSQL con SQLAlchemy.
Alineado con el DDL provisto (nombres snake_case, defaults y constraint de rol).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, func, Index
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash, check_password_hash

from Modelo_de_Datos_PostgreSQL_y_CRUD.conexion_postgres import db
from Log_PeakSport import log_info, log_critical, log_error, log_warning


class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id               = db.Column(db.BigInteger, primary_key=True)
    correo           = db.Column(db.String(255), unique=True, nullable=False, index=True)
    contrasena       = db.Column(db.String(255), nullable=False)
    nombre_completo  = db.Column(db.String(255))
    fecha_nacimiento = db.Column(db.Date)
    verificacion     = db.Column(db.Boolean, nullable=False, server_default=db.text("FALSE"))
    rol              = db.Column(db.String(20), nullable=False, server_default='Cliente')
    created_at       = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at       = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    __table_args__ = (
        CheckConstraint("rol IN ('Administrador','Cliente')", name="chk_usuarios_rol"),
        Index('idx_usuarios_correo', 'correo'),
    )

    # Helpers
    def set_password(self, raw_password: str) -> None:
        self.contrasena = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """
        Soporta transición: intenta validar como hash; si falla, compara plano.
        """
        try:
            return check_password_hash(self.contrasena, raw_password)
        except Exception:
            return self.contrasena == raw_password  # fallback si en DB quedó plano

    def __repr__(self):
        return f"<Usuario {self.correo}>"


# ===================== CRUD =====================

def crear_usuario(
    correo: str,
    contrasena: str,
    nombre_completo: Optional[str] = None,
    fecha_nacimiento: Optional[datetime.date] = None,
    verificacion: bool = False,
    rol: str = 'Cliente',
    usar_hash: bool = True,
) -> Optional[Usuario]:
    try:
        if not correo or not contrasena:
            log_warning("crear_usuario: Correo y contraseña son obligatorios")
            return None

        if rol not in ('Administrador', 'Cliente'):
            log_warning(f"crear_usuario: Rol inválido '{rol}'")
            return None

        if Usuario.query.filter_by(correo=correo).first():
            log_warning(f"crear_usuario: Correo ya registrado {correo}")
            return None

        nuevo = Usuario(
            correo=correo,
            nombre_completo=nombre_completo,
            fecha_nacimiento=fecha_nacimiento,
            verificacion=verificacion,
            rol=rol
        )
        if usar_hash:
            nuevo.set_password(contrasena)
        else:
            nuevo.contrasena = contrasena

        db.session.add(nuevo)
        db.session.commit()
        log_info(f"Usuario creado: {correo}")
        return nuevo
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al crear usuario {correo}: {str(e)}")
        return None


def obtener_usuario_por_id(usuario_id: int) -> Optional[Usuario]:
    try:
        usuario = db.session.get(Usuario, usuario_id)
        if usuario:
            log_info(f"Usuario obtenido por id: {usuario_id}")
        else:
            log_warning(f"Usuario no encontrado con id: {usuario_id}")
        return usuario
    except SQLAlchemyError as e:
        log_error(f"Error al obtener usuario por id {usuario_id}: {str(e)}")
        return None


def obtener_usuario_por_correo(correo: str) -> Optional[Usuario]:
    try:
        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario:
            log_info(f"Usuario obtenido por correo: {correo}")
        else:
            log_warning(f"Usuario no encontrado con correo: {correo}")
        return usuario
    except SQLAlchemyError as e:
        log_error(f"Error al obtener usuario por correo {correo}: {str(e)}")
        return None


def actualizar_usuario(usuario_id: int, **kwargs) -> Optional[Usuario]:
    """
    Campos permitidos: correo, nombre_completo, fecha_nacimiento, verificacion, rol, contrasena
    Si se pasa 'contrasena', se hashea por defecto (usar_hash=True) salvo que se pase usar_hash=False.
    """
    usar_hash = kwargs.pop('usar_hash', True)
    campos_permitidos = {'correo', 'nombre_completo', 'fecha_nacimiento', 'verificacion', 'rol', 'contrasena'}

    try:
        usuario = db.session.get(Usuario, usuario_id)
        if not usuario:
            log_warning(f"Usuario no encontrado para actualizar: {usuario_id}")
            return None

        for key, value in kwargs.items():
            if key not in campos_permitidos:
                log_warning(f"actualizar_usuario: Campo ignorado '{key}'")
                continue
            if key == 'rol' and value not in ('Administrador', 'Cliente'):
                log_warning(f"actualizar_usuario: Rol inválido '{value}'")
                continue
            if key == 'contrasena':
                if usar_hash:
                    usuario.set_password(value)
                else:
                    usuario.contrasena = value
            else:
                setattr(usuario, key, value)

        db.session.commit()
        log_info(f"Usuario actualizado: {usuario_id}")
        return usuario
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al actualizar usuario {usuario_id}: {str(e)}")
        return None


def eliminar_usuario(usuario_id: int) -> bool:
    try:
        usuario = db.session.get(Usuario, usuario_id)
        if not usuario:
            log_warning(f"Usuario no encontrado para eliminar: {usuario_id}")
            return False
        db.session.delete(usuario)
        db.session.commit()
        log_info(f"Usuario eliminado: {usuario_id}")
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al eliminar usuario {usuario_id}: {str(e)}")
        return False


def verificar_credenciales(correo: str, contrasena: str) -> Optional[Usuario]:
    """
    Devuelve el usuario si (correo, contraseña) son correctos. Soporta hash o texto plano.
    """
    try:
        if not correo or not contrasena:
            log_warning("verificar_credenciales: Correo o contraseña no proporcionados")
            return None

        usuario = Usuario.query.filter_by(correo=correo).first()
        if not usuario:
            log_error(f"verificar_credenciales: Usuario no encontrado para correo {correo}")
            return None

        if usuario.check_password(contrasena):
            log_info(f"verificar_credenciales: Usuario autenticado {correo}")
            return usuario

        log_error(f"verificar_credenciales: Contraseña incorrecta para usuario {correo}")
        return None

    except SQLAlchemyError as se:
        log_critical(f"verificar_credenciales: Error de base de datos: {str(se)}")
        return None
    except Exception as e:
        log_critical(f"verificar_credenciales: Error inesperado: {str(e)}")
        return None
