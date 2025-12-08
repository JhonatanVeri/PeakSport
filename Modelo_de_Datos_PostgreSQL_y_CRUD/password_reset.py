# -*- coding: utf-8 -*-
"""
Autor: PeakSport Team
Descripción: Modelo y CRUD para recuperación de contraseña en PostgreSQL con SQLAlchemy.
Tabla: password_reset_tokens
VERSIÓN: 3.0 - CORREGIDO - Optimizado para transacciones
"""

from datetime import datetime, timedelta
import secrets
import hashlib
from sqlalchemy import func, Index
from sqlalchemy.exc import SQLAlchemyError

from Modelo_de_Datos_PostgreSQL_y_CRUD.conexion_postgres import db
from Log_PeakSport import log_info, log_critical, log_error, log_warning


class PasswordResetToken(db.Model):
    """
    Tokens para recuperación de contraseña
    Tabla: password_reset_tokens
    """
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.BigInteger, primary_key=True)
    usuario_id = db.Column(
        db.BigInteger,
        db.ForeignKey('usuarios.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used = db.Column(db.Boolean, default=False, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    ip_address = db.Column(db.String(45), nullable=True)

    __table_args__ = (
        Index('idx_password_reset_tokens_usuario_id', 'usuario_id'),
        Index('idx_password_reset_tokens_token_hash', 'token_hash'),
        Index('idx_password_reset_tokens_expires_at', 'expires_at'),
    )

    def is_expired(self) -> bool:
        """Verifica si el token expiró"""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Verifica si el token es válido para usar"""
        return not self.used and not self.is_expired()

    @staticmethod
    def generate_token() -> str:
        """Genera un token seguro"""
        return secrets.token_urlsafe(64)

    @staticmethod
    def hash_token(token: str) -> str:
        """Hashea el token antes de guardarlo"""
        return hashlib.sha256(token.encode()).hexdigest()

    def __repr__(self):
        return f"<PasswordResetToken usuario_id={self.usuario_id} expires_at={self.expires_at}>"


# ===================== CRUD =====================

def crear_token_reset(usuario_id: int, ip_address: str = None) -> tuple:
    """
    Crea un nuevo token de reset
    Args:
        usuario_id: ID del usuario
        ip_address: Dirección IP del cliente (opcional)
    
    Retorna: (token_sin_hashear, exito: bool)
    """
    try:
        log_info(f"🔑 Creando token reset para usuario {usuario_id}")
        
        # Verificar que usuario existe
        from Modelo_de_Datos_PostgreSQL_y_CRUD.Usuarios import Usuario
        usuario = db.session.get(Usuario, usuario_id)
        if not usuario:
            log_warning(f"❌ crear_token_reset: Usuario no encontrado {usuario_id}")
            return None, False

        log_info(f"✅ Usuario {usuario_id} encontrado: {usuario.correo}")

        # Eliminar tokens antiguos sin usar
        tokens_eliminados = PasswordResetToken.query.filter_by(
            usuario_id=usuario_id,
            used=False
        ).delete()
        
        if tokens_eliminados > 0:
            log_info(f"🗑️ {tokens_eliminados} token(s) antiguo(s) eliminado(s)")

        # Generar token
        token_plain = PasswordResetToken.generate_token()
        token_hashed = PasswordResetToken.hash_token(token_plain)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        log_info(f"🔐 Token generado (primeros 30 chars): {token_plain[:30]}...")
        log_info(f"🔒 Token hasheado (primeros 20 chars): {token_hashed[:20]}...")
        log_info(f"⏰ Expira en: {expires_at}")

        # Crear registro
        nuevo_token = PasswordResetToken(
            usuario_id=usuario_id,
            token_hash=token_hashed,
            expires_at=expires_at,
            ip_address=ip_address
        )

        db.session.add(nuevo_token)
        db.session.commit()
        
        log_info(f"✅ Token de reset creado exitosamente (ID: {nuevo_token.id})")
        return token_plain, True

    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"❌ Error SQLAlchemy al crear token reset para usuario {usuario_id}: {str(e)}")
        return None, False
    except Exception as e:
        db.session.rollback()
        log_error(f"❌ Error general al crear token reset para usuario {usuario_id}: {str(e)}")
        return None, False


def obtener_token_reset(token_hash: str) -> tuple:
    """
    Obtiene y valida un token de reset
    Args:
        token_hash: Hash del token
    
    Retorna: (token_record, valido: bool)
    """
    try:
        log_info(f"🔍 Buscando token en BD (hash primeros 20 chars): {token_hash[:20]}...")
        
        token = PasswordResetToken.query.filter_by(
            token_hash=token_hash,
            used=False
        ).first()

        if not token:
            log_warning("❌ obtener_token_reset: Token no encontrado o ya usado")
            return None, False

        log_info(f"✅ Token encontrado (ID: {token.id}, Usuario ID: {token.usuario_id})")
        log_info(f"⏰ Expira en: {token.expires_at}")
        log_info(f"🕐 Hora actual: {datetime.utcnow()}")

        if token.is_expired():
            log_warning(f"❌ Token expirado (expiró: {token.expires_at})")
            return token, False

        log_info("✅ Token válido y no expirado")
        return token, True

    except SQLAlchemyError as e:
        log_error(f"❌ Error SQLAlchemy al obtener token reset: {str(e)}")
        return None, False
    except Exception as e:
        log_error(f"❌ Error general al obtener token reset: {str(e)}")
        return None, False


def usar_token_reset(token_hash: str) -> bool:
    """
    🔧 DEPRECADO: Esta función ya no se usa directamente.
    El token ahora se marca como usado en la misma transacción
    que actualiza la contraseña (ver password_reset_api.py).
    
    Se mantiene para compatibilidad con código existente.
    
    Args:
        token_hash: Hash del token
    
    Retorna: bool
    """
    try:
        log_warning("⚠️ usar_token_reset() llamado - considerar usar transacción única")
        log_info(f"🔒 Marcando token como usado (hash primeros 20 chars): {token_hash[:20]}...")
        
        token = PasswordResetToken.query.filter_by(token_hash=token_hash).first()
        if not token:
            log_warning("❌ usar_token_reset: Token no encontrado")
            return False

        token.used = True
        token.used_at = datetime.utcnow()
        db.session.commit()

        log_info(f"✅ Token marcado como usado (ID: {token.id}, Usuario: {token.usuario_id})")
        return True

    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"❌ Error SQLAlchemy al marcar token como usado: {str(e)}")
        return False
    except Exception as e:
        db.session.rollback()
        log_error(f"❌ Error general al marcar token como usado: {str(e)}")
        return False


def limpiar_tokens_expirados() -> int:
    """
    Limpia tokens expirados hace más de 24 horas
    Retorna cantidad de registros eliminados
    """
    try:
        log_info("🧹 Limpiando tokens expirados...")
        
        result = PasswordResetToken.query.filter(
            PasswordResetToken.expires_at < datetime.utcnow() - timedelta(days=1)
        ).delete()
        
        db.session.commit()
        log_info(f"✅ {result} token(s) expirado(s) eliminado(s)")
        return result

    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"❌ Error SQLAlchemy al limpiar tokens expirados: {str(e)}")
        return 0
    except Exception as e:
        db.session.rollback()
        log_error(f"❌ Error general al limpiar tokens expirados: {str(e)}")
        return 0


def obtener_token_por_usuario(usuario_id: int) -> PasswordResetToken:
    """
    Obtiene el token activo de un usuario
    """
    try:
        token = PasswordResetToken.query.filter_by(
            usuario_id=usuario_id,
            used=False
        ).first()
        
        if token and not token.is_expired():
            log_info(f"✅ Token activo encontrado para usuario {usuario_id}")
            return token
        
        log_info(f"ℹ️ No hay token activo para usuario {usuario_id}")
        return None
        
    except SQLAlchemyError as e:
        log_error(f"❌ Error SQLAlchemy al obtener token del usuario {usuario_id}: {str(e)}")
        return None
    except Exception as e:
        log_error(f"❌ Error general al obtener token del usuario {usuario_id}: {str(e)}")
        return None