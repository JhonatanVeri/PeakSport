# -*- coding: utf-8 -*-
"""
Autor: PeakSport Team
Descripción: API endpoints para recuperación de contraseña
Archivo: Apis/password_reset_api.py
VERSIÓN: 3.1 - Con imports corregidos
"""

from flask import Blueprint, request, jsonify, url_for
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from Modelo_de_Datos_PostgreSQL_y_CRUD.Usuarios import (
    obtener_usuario_por_correo
)
# 🔧 CORREGIDO: Cambiar "password_reset" → "passwordreset"
from Modelo_de_Datos_PostgreSQL_y_CRUD.password_reset import (
    crear_token_reset, obtener_token_reset, usar_token_reset,
    PasswordResetToken
)
from Modelo_de_Datos_PostgreSQL_y_CRUD.conexion_postgres import db
from services.email_service import email_service
from Log_PeakSport import log_info, log_critical, log_error, log_warning
import re

# Crear blueprint
password_reset_bp = Blueprint(
    'password_reset',
    __name__,
    url_prefix='/api/auth'
)

# Rate limiting simple (usa Redis en producción)
reset_attempts = {}


@password_reset_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Solicita recuperación de contraseña
    POST /api/auth/forgot-password
    Body: { "correo": "usuario@example.com" }
    
    Retorna: { "success": true, "message": "Si existe una cuenta..." }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': True,
                'message': 'Si existe una cuenta con ese correo, recibirás un enlace en minutos'
            }), 200

        correo = data.get('correo', '').lower().strip()

        # Validación básica
        if not correo or '@' not in correo:
            return jsonify({
                'success': True,
                'message': 'Si existe una cuenta con ese correo, recibirás un enlace en minutos'
            }), 200

        # ✅ Rate limiting: máximo 3 intentos por IP/hora
        client_ip = request.remote_addr
        rate_key = f"reset:{client_ip}"

        if rate_key in reset_attempts:
            attempts, first_attempt = reset_attempts[rate_key]
            if datetime.utcnow() - first_attempt < timedelta(hours=1):
                if attempts >= 3:
                    log_warning(f"Rate limit alcanzado para IP {client_ip}")
                    return jsonify({
                        'success': True,
                        'message': 'Si existe una cuenta con ese correo, recibirás un enlace en minutos'
                    }), 200
                reset_attempts[rate_key] = (attempts + 1, first_attempt)
            else:
                reset_attempts[rate_key] = (1, datetime.utcnow())
        else:
            reset_attempts[rate_key] = (1, datetime.utcnow())

        # Buscar usuario (sin revelar si existe)
        log_info(f"Buscando usuario con correo: {correo}")
        usuario = obtener_usuario_por_correo(correo)

        if usuario:
            log_info(f"Usuario obtenido por correo: {usuario.correo}")
            # Crear token
            token_plain, exito = crear_token_reset(usuario.id, client_ip)

            if exito and token_plain:
                log_info(f"Token de reset creado para usuario {usuario.id}")
                # Crear enlace
                reset_link = url_for(
                    'reset_password_page',
                    token=token_plain,
                    _external=True
                )

                # Enviar email
                email_ok, email_msg = email_service.send_password_reset_email(
                    correo=usuario.correo,
                    nombre=usuario.nombre_completo or usuario.correo,
                    reset_link=reset_link
                )

                if email_ok:
                    log_info(f"Email de recuperación enviado a {usuario.correo}")
                else:
                    log_warning(f"Email no enviado para {usuario.correo}: {email_msg}")
            else:
                log_error(f"No se pudo crear token para usuario {usuario.id}")
        else:
            log_warning(f"Usuario no encontrado con correo: {correo}")

        # ✅ IMPORTANTE: Mostrar MISMO MENSAJE siempre (previene account enumeration)
        return jsonify({
            'success': True,
            'message': 'Si existe una cuenta con ese correo, recibirás un enlace en minutos'
        }), 200

    except Exception as e:
        log_critical(f"Error en forgot_password: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error al procesar solicitud'
        }), 500


@password_reset_bp.route('/reset-password/<token>', methods=['GET'])
def reset_password_token_validate(token):
    """
    Valida el token y retorna info de validación
    GET /api/auth/reset-password/<token>
    
    Retorna: { "success": true, "valid": true, "token": "..." }
    """
    try:
        token = token.strip()

        if not token:
            return jsonify({
                'success': False,
                'error': 'Token no proporcionado',
                'valid': False
            }), 400

        # Hashear token
        token_hash = PasswordResetToken.hash_token(token)

        # Buscar y validar
        token_record, is_valid = obtener_token_reset(token_hash)

        if not is_valid:
            error_msg = 'Enlace expirado' if token_record and token_record.is_expired() else 'Enlace inválido'
            return jsonify({
                'success': False,
                'error': error_msg,
                'valid': False
            }), 400

        # Token válido
        return jsonify({
            'success': True,
            'valid': True,
            'token': token
        }), 200

    except Exception as e:
        log_error(f"Error en reset_password_token_validate: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error al validar enlace',
            'valid': False
        }), 500


@password_reset_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Resetea la contraseña con el token
    POST /api/auth/reset-password
    Body: {
        "token": "...",
        "nueva_contrasena": "..."
    }
    
    Retorna: { "success": true, "message": "Contraseña actualizada" }
    """
    try:
        log_info("=" * 70)
        log_info("🔐 INICIANDO PROCESO DE RESET PASSWORD")
        log_info("=" * 70)
        
        data = request.get_json()
        if not data:
            log_warning("❌ Datos JSON no proporcionados")
            return jsonify({
                'success': False,
                'error': 'Datos incompletos'
            }), 400

        token = data.get('token', '').strip()
        nueva_contrasena = data.get('nueva_contrasena', '').strip()
        
        log_info(f"📩 Token recibido (primeros 30 chars): {token[:30]}...")
        log_info(f"🔐 Nueva contraseña recibida: {'*' * len(nueva_contrasena)} (longitud: {len(nueva_contrasena)})")

        # Validaciones
        if not token or not nueva_contrasena:
            log_warning("❌ Token o contraseña vacíos")
            return jsonify({
                'success': False,
                'error': 'Datos incompletos'
            }), 400

        if len(nueva_contrasena) < 8:
            log_warning("❌ Contraseña muy corta")
            return jsonify({
                'success': False,
                'error': 'La contraseña debe tener mínimo 8 caracteres'
            }), 400

        # Validar requisitos de seguridad
        if not re.search(r'[A-Z]', nueva_contrasena):
            log_warning("❌ Contraseña sin mayúscula")
            return jsonify({
                'success': False,
                'error': 'La contraseña debe tener al menos una mayúscula'
            }), 400
        
        if not re.search(r'[0-9]', nueva_contrasena):
            log_warning("❌ Contraseña sin número")
            return jsonify({
                'success': False,
                'error': 'La contraseña debe tener al menos un número'
            }), 400
        
        if not re.search(r'[@$!%*?&]', nueva_contrasena):
            log_warning("❌ Contraseña sin carácter especial")
            return jsonify({
                'success': False,
                'error': 'La contraseña debe tener al menos un carácter especial (@$!%*?&)'
            }), 400

        log_info("✅ Contraseña cumple requisitos de seguridad")

        # Hashear token
        token_hash = PasswordResetToken.hash_token(token)
        log_info(f"🔑 Token hasheado (primeros 20 chars): {token_hash[:20]}...")

        # Validar token
        log_info("🔍 Validando token en BD...")
        token_record, is_valid = obtener_token_reset(token_hash)

        if not is_valid:
            error_msg = 'Enlace expirado' if token_record else 'Enlace inválido'
            log_warning(f"❌ Token inválido: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400

        log_info(f"✅ Token válido. Usuario ID: {token_record.usuario_id}")

        # Obtener usuario
        from Modelo_de_Datos_PostgreSQL_y_CRUD.Usuarios import Usuario
        
        usuario = db.session.get(Usuario, token_record.usuario_id)
        if not usuario:
            log_error(f"❌ Usuario {token_record.usuario_id} no encontrado en BD")
            return jsonify({
                'success': False,
                'error': 'Usuario no encontrado'
            }), 400

        log_info(f"✅ Usuario encontrado: {usuario.correo}")
        log_info(f"📊 Hash actual en BD (primeros 20 chars): {usuario.contrasena[:20]}...")

        # ✅ Actualizar contraseña directamente con hash
        try:
            # Hashear la nueva contraseña
            nuevo_hash = generate_password_hash(nueva_contrasena)
            log_info(f"🔒 Nuevo hash generado (primeros 20 chars): {nuevo_hash[:20]}...")
            
            # Actualizar en el modelo
            usuario.contrasena = nuevo_hash
            
            # Flush para ver el cambio antes del commit
            db.session.flush()
            log_info("✅ Cambio aplicado en sesión (flush)")
            
            # Commit a la base de datos
            db.session.commit()
            log_info("✅ Cambios guardados en BD (commit)")
            
            # Verificar que se guardó correctamente
            db.session.refresh(usuario)
            log_info(f"🔍 Hash verificado en BD (primeros 20 chars): {usuario.contrasena[:20]}...")
            
            # Verificar que el hash funciona
            if check_password_hash(usuario.contrasena, nueva_contrasena):
                log_info("✅ Verificación exitosa: El hash funciona correctamente")
            else:
                log_error("❌ ADVERTENCIA: El hash NO verifica correctamente")
            
            log_info(f"✅ Contraseña actualizada correctamente para usuario {usuario.id} ({usuario.correo})")
            
        except Exception as update_error:
            db.session.rollback()
            log_error(f"❌ Error al actualizar contraseña en BD: {str(update_error)}")
            import traceback
            log_error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': 'Error al actualizar contraseña'
            }), 500

        # Marcar token como usado
        log_info("🔒 Marcando token como usado...")
        usar_token_reset(token_hash)
        log_info("✅ Token marcado como usado")

        log_info("=" * 70)
        log_info("🎉 PROCESO DE RESET PASSWORD COMPLETADO EXITOSAMENTE")
        log_info("=" * 70)

        return jsonify({
            'success': True,
            'message': 'Contraseña actualizada correctamente'
        }), 200

    except Exception as e:
        db.session.rollback()
        log_critical(f"❌ Error crítico en reset_password: {str(e)}")
        import traceback
        log_critical(f"Traceback completo:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Error al procesar solicitud'
        }), 500