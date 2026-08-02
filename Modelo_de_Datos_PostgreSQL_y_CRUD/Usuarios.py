# -*- coding: utf-8 -*-
"""
Autor: Jherson Sanchez (ajustado)
Descripción: Modelo y CRUD para la tabla `usuarios` en PostgreSQL con SQLAlchemy.
Alineado con el DDL provisto (nombres snake_case, defaults y constraint de rol).
Actualizado v2.5.0: Incluye relación con password_reset_tokens
CORREGIDO: check_password ahora valida correctamente hashes
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, func
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

    # 🆕 NUEVO: Relación con tokens de recuperación de contraseña
    password_reset_tokens = db.relationship(
        'PasswordResetToken',
        backref='usuario',
        lazy=True,
        cascade='all, delete-orphan',
        foreign_keys='PasswordResetToken.usuario_id'
    )

    __table_args__ = (
        CheckConstraint("rol IN ('Administrador','Cliente')", name="chk_usuarios_rol"),
        # Nota: no se agrega índice extra sobre 'correo' aquí porque la columna
        # ya lo declara vía unique=True, index=True (evita índice duplicado).
    )

    # Helpers
    def set_password(self, raw_password: str) -> None:
        """Hashea y guarda la contraseña"""
        self.contrasena = generate_password_hash(raw_password)
        log_info(f"Contraseña hasheada para usuario {self.correo}")

    def check_password(self, raw_password: str) -> bool:
        """
        Verifica la contraseña contra el hash almacenado.
        
        IMPORTANTE: 
        - Intenta validar con check_password_hash (para hashes scrypt/pbkdf2)
        - Si falla, SOLO como último recurso compara en texto plano
        - Registra todos los intentos para debug
        """
        try:
            # ✅ PRIMERO: Intentar con check_password_hash
            if not self.contrasena:
                log_error(f"check_password: {self.correo} - Contraseña vacía en BD")
                return False
            
            resultado = check_password_hash(self.contrasena, raw_password)
            
            if resultado:
                log_info(f"check_password: ✅ Contraseña válida para {self.correo} (hash verificado)")
            else:
                log_warning(f"check_password: ❌ Contraseña inválida para {self.correo} (hash no coincide)")
            
            return resultado
            
        except Exception as hash_error:
            # ⚠️ Fallback SOLO si el hash está corrupto (nunca debería ocurrir en producción)
            log_warning(f"check_password: Exception al validar hash para {self.correo}: {str(hash_error)}")
            
            # Fallback: comparación de texto plano (solo si está mal guardado)
            if self.contrasena == raw_password:
                log_warning(f"check_password: ⚠️ Contraseña validada como TEXTO PLANO (mala práctica) para {self.correo}")
                return True
            
            log_error(f"check_password: ❌ Ambas validaciones fallaron para {self.correo}")
            return False

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
    """
    Crea un nuevo usuario
    
    Args:
        correo: Email único del usuario
        contrasena: Contraseña (se hashea por defecto)
        nombre_completo: Nombre completo (opcional)
        fecha_nacimiento: Fecha de nacimiento (opcional)
        verificacion: Si está verificado (default False)
        rol: 'Cliente' o 'Administrador' (default 'Cliente')
        usar_hash: Si hashear la contraseña (default True)
    
    Retorna: Usuario creado o None si hay error
    """
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
    """
    Obtiene un usuario por ID
    
    Args:
        usuario_id: ID del usuario
    
    Retorna: Usuario o None
    """
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
    """
    Obtiene un usuario por correo
    
    Args:
        correo: Email del usuario
    
    Retorna: Usuario o None
    """
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
    Actualiza un usuario
    
    Args:
        usuario_id: ID del usuario a actualizar
        **kwargs: Campos a actualizar (correo, nombre_completo, fecha_nacimiento, 
                 verificacion, rol, contrasena)
                 Si se pasa 'contrasena', se hashea por defecto (usar_hash=True) 
                 salvo que se pase usar_hash=False
    
    Retorna: Usuario actualizado o None
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
    """
    Elimina un usuario
    
    Args:
        usuario_id: ID del usuario a eliminar
    
    Retorna: True si se eliminó, False si hay error
    """
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
    Verifica las credenciales de un usuario (email y contraseña)
    
    Args:
        correo: Email del usuario
        contrasena: Contraseña a verificar
    
    Retorna: Usuario si credenciales son correctas, None si son incorrectas
    """
    try:
        if not correo or not contrasena:
            log_warning("verificar_credenciales: Correo o contraseña no proporcionados")
            return None

        usuario = Usuario.query.filter_by(correo=correo).first()
        if not usuario:
            log_error(f"verificar_credenciales: Usuario no encontrado para correo {correo}")
            return None

        log_info(f"verificar_credenciales: Verificando contraseña para {correo}")
        
        if usuario.check_password(contrasena):
            log_info(f"✅ verificar_credenciales: Usuario autenticado {correo}")
            return usuario

        log_warning(f"❌ verificar_credenciales: Contraseña incorrecta para usuario {correo}")
        return None

    except SQLAlchemyError as se:
        log_critical(f"verificar_credenciales: Error de base de datos: {str(se)}")
        return None
    except Exception as e:
        log_critical(f"verificar_credenciales: Error inesperado: {str(e)}")
        return None


def obtener_todos_usuarios(limite: int = 100, offset: int = 0) -> list:
    """
    Obtiene todos los usuarios con paginación
    
    Args:
        limite: Cantidad máxima de usuarios a retornar (default 100)
        offset: Número de usuarios a saltar (default 0)
    
    Retorna: Lista de usuarios
    """
    try:
        usuarios = Usuario.query.limit(limite).offset(offset).all()
        log_info(f"Obtenidos {len(usuarios)} usuarios")
        return usuarios
    except SQLAlchemyError as e:
        log_error(f"Error al obtener usuarios: {str(e)}")
        return []


def contar_usuarios() -> int:
    """
    Cuenta el total de usuarios en la BD
    
    Retorna: Cantidad de usuarios
    """
    try:
        cantidad = Usuario.query.count()
        log_info(f"Total de usuarios: {cantidad}")
        return cantidad
    except SQLAlchemyError as e:
        log_error(f"Error al contar usuarios: {str(e)}")
        return 0


def obtener_usuarios_por_rol(rol: str) -> list:
    """
    Obtiene todos los usuarios de un rol específico
    
    Args:
        rol: 'Cliente' o 'Administrador'
    
    Retorna: Lista de usuarios con ese rol
    """
    try:
        if rol not in ('Administrador', 'Cliente'):
            log_warning(f"obtener_usuarios_por_rol: Rol inválido '{rol}'")
            return []
        
        usuarios = Usuario.query.filter_by(rol=rol).all()
        log_info(f"Obtenidos {len(usuarios)} usuarios con rol '{rol}'")
        return usuarios
    except SQLAlchemyError as e:
        log_error(f"Error al obtener usuarios por rol: {str(e)}")
        return []


def cambiar_rol_usuario(usuario_id: int, nuevo_rol: str) -> Optional[Usuario]:
    """
    Cambia el rol de un usuario
    
    Args:
        usuario_id: ID del usuario
        nuevo_rol: Nuevo rol ('Cliente' o 'Administrador')
    
    Retorna: Usuario actualizado o None
    """
    try:
        if nuevo_rol not in ('Administrador', 'Cliente'):
            log_warning(f"cambiar_rol_usuario: Rol inválido '{nuevo_rol}'")
            return None
        
        usuario = db.session.get(Usuario, usuario_id)
        if not usuario:
            log_warning(f"cambiar_rol_usuario: Usuario no encontrado {usuario_id}")
            return None
        
        usuario.rol = nuevo_rol
        db.session.commit()
        log_info(f"Rol del usuario {usuario_id} cambiado a '{nuevo_rol}'")
        return usuario
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al cambiar rol del usuario {usuario_id}: {str(e)}")
        return None


def verificar_usuario(usuario_id: int) -> Optional[Usuario]:
    """
    Marca un usuario como verificado
    
    Args:
        usuario_id: ID del usuario
    
    Retorna: Usuario actualizado o None
    """
    try:
        usuario = db.session.get(Usuario, usuario_id)
        if not usuario:
            log_warning(f"verificar_usuario: Usuario no encontrado {usuario_id}")
            return None
        
        usuario.verificacion = True
        db.session.commit()
        log_info(f"Usuario {usuario_id} verificado")
        return usuario
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error al verificar usuario {usuario_id}: {str(e)}")
        return None


def buscar_usuarios_por_nombre(nombre: str) -> list:
    """
    Busca usuarios por nombre completo (búsqueda parcial)
    
    Args:
        nombre: Nombre a buscar
    
    Retorna: Lista de usuarios que coinciden
    """
    try:
        usuarios = Usuario.query.filter(
            Usuario.nombre_completo.ilike(f"%{nombre}%")
        ).all()
        log_info(f"Encontrados {len(usuarios)} usuarios con nombre '{nombre}'")
        return usuarios
    except SQLAlchemyError as e:
        log_error(f"Error al buscar usuarios por nombre: {str(e)}")
        return []
    
    