# -*- coding: utf-8 -*-
"""
Blueprint: login - VERSIÓN CORREGIDA
Rutas de autenticación (login/logout) y vista de login.

CAMBIO CRÍTICO: Remover session.regenerate() - NO soportado en filesystem
"""

from flask import render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash
from functools import wraps
import re
from datetime import datetime

from Modelo_de_Datos_PostgreSQL_y_CRUD.Usuarios import (
    verificar_credenciales, obtener_usuario_por_id, crear_usuario
)
from Log_PeakSport import log_info, log_error, log_critical, log_warning
# Al inicio de login/controlador.py
from utils import requiere_mfa  # ← Agregar esta línea

# =========================
# CONSTANTES DE SEGURIDAD
# =========================
MIN_PASSWORD_LENGTH = 8
ALLOWED_ROLES = {'Administrador', 'Cliente'}
VALID_EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
MAX_LOGIN_ATTEMPTS = 5
SESSION_TIMEOUT = 1800  # 30 minutos


# =========================
# Helpers de validación
# =========================
def _validar_email(email: str) -> bool:
    """Valida formato de email con regex"""
    if not email or len(email) > 255:
        return False
    return bool(re.match(VALID_EMAIL_REGEX, email))


def _validar_contraseña(password: str) -> tuple[bool, str]:
    """
    Valida fortaleza de contraseña.
    Retorna (es_válida, mensaje_error)
    """
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres"
    
    if not any(c.isupper() for c in password):
        return False, "Contraseña debe contener al menos una mayúscula"
    
    if not any(c.islower() for c in password):
        return False, "Contraseña debe contener al menos una minúscula"
    
    if not any(c.isdigit() for c in password):
        return False, "Contraseña debe contener al menos un número"
    
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        return False, "Contraseña debe contener al menos un carácter especial"
    
    return True, ""


def _validar_edad(fecha_nacimiento_str: str) -> tuple[bool, str]:
    """
    Valida que el usuario sea mayor de 18 años.
    fecha_nacimiento_str debe estar en formato YYYY-MM-DD
    """
    try:
        birth_date = datetime.strptime(fecha_nacimiento_str, '%Y-%m-%d').date()
        today = datetime.today().date()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        
        if age < 18:
            return False, "Debes ser mayor de 18 años para registrarte"
        
        if age > 120:
            return False, "Fecha de nacimiento inválida"
        
        return True, ""
    except ValueError:
        return False, "Formato de fecha inválido (esperado YYYY-MM-DD)"


def _payload_json():
    """Normaliza el payload aceptando ambas convenciones"""
    data = request.get_json(silent=True) or {}
    correo = data.get('correo') or data.get('Correo')
    contrasena = data.get('contrasena') or data.get('Contrasena')
    return correo, contrasena


def _redir_por_rol(rol: str):
    """Devuelve la URL de destino según el rol del usuario"""
    if rol == 'Administrador':
        return url_for('administrador_principal.vista_listado_productos')
    return url_for('cliente_principal.vista_cliente_principal')




# =========================
# Rutas
# =========================
def registrar_rutas(bp):
    """Registra las rutas del blueprint de login"""
    
    @bp.get('/')
    def vista_pantalla_login():
        """Renderiza el formulario de login/registro"""
        try:
            # ✅ Si ya está logueado Y verificado, redirige al dashboard
            if session.get('logged_in') and session.get('mfa_verificado'):
                rol = session.get('usuario_rol')
                if rol == 'Administrador':
                    return redirect(url_for('administrador_principal.vista_listado_productos'))
                return redirect(url_for('cliente_principal.vista_cliente_principal'))
            
            # ✅ Si está logueado pero NO verificado, enviar a MFA
            if session.get('logged_in') and not session.get('mfa_verificado'):
                return redirect(url_for('mfa.verificar_codigo'))
            
            # ✅ Si no está logueado, mostrar formulario
            return render_template('loginFormulario.html')
            
        except Exception as e:
            log_critical(f"[login] vista_pantalla_login: Error inesperado: {e}")
            return "<h1>Error cargando la pantalla de login</h1>", 500


    @bp.post('/auth/login')
    def login_usuario_route():
        """
        CORREGIDO: Ahora FUERZA MFA antes de redirigir al dashboard
        
        Flujo:
        1. Verifica credenciales
        2. Guarda usuario en sesión
        3. REDIRIGE A MFA (/mfa/verificar-codigo)
        4. MFA verifica código
        5. LUEGO redirige al dashboard real
        """
        try:
            correo, contrasena = _payload_json()

            # Validaciones
            if not correo or not contrasena:
                log_warning("[login] Faltan credenciales")
                return jsonify({'ok': False, 'error': 'Correo y contraseña son obligatorios'}), 400

            if not _validar_email(correo):
                log_warning(f"[login] Email inválido: {correo}")
                return jsonify({'ok': False, 'error': 'Formato de email inválido'}), 400

            # Verificar credenciales
            usuario = verificar_credenciales(correo, contrasena)
            if not usuario:
                log_warning(f"[login] Credenciales inválidas para {correo}")
                return jsonify({'ok': False, 'error': 'Credenciales inválidas'}), 401

            # ✅ LIMPIAR SESIÓN COMPLETAMENTE
            session.clear()

            # Guardar datos en sesión (PERO sin verificación aún)
            session['usuario_id'] = usuario.id
            session['usuario_correo'] = usuario.correo
            session['usuario_nombre'] = usuario.nombre_completo
            session['usuario_rol'] = usuario.rol
            session['logged_in'] = True
            session['mfa_verificado'] = False  # ✅ CRÍTICO: Aún NO verificado
            session.permanent = True

            log_info(f"[login] Credenciales válidas para {correo}, enviando a MFA")

            # ✅ REDIRIGE A MFA, NO al dashboard
            return jsonify({
                'ok': True,
                'redirect': url_for('mfa.verificar_codigo')  # CAMBIO CRÍTICO
            }), 200

        except Exception as e:
            log_critical(f"[login] login_usuario_route: Error inesperado: {e}")
            return jsonify({'ok': False, 'error': 'Error interno del servidor'}), 500


    @bp.post('/auth/register')
    def registrar_usuario_route():
        """
        Crea usuario con validaciones BACKEND completas
        """
        try:
            data = request.get_json(silent=True) or {}
            
            nombre = (data.get('Nombre_Completo') or '').strip()
            correo = (data.get('Correo') or '').strip().lower()
            fecha_nac = data.get('Fecha_Nacimiento')
            contrasena = data.get('Contrasena')

            # Validaciones
            if not all([nombre, correo, fecha_nac, contrasena]):
                return jsonify({'error': 'Faltan campos obligatorios'}), 400

            if len(nombre) < 3 or len(nombre) > 255:
                return jsonify({'error': 'Nombre debe tener entre 3 y 255 caracteres'}), 400

            if not _validar_email(correo):
                return jsonify({'error': 'Email inválido'}), 400

            # ✅ Validar edad (NUEVO)
            es_válida, msg = _validar_edad(fecha_nac)
            if not es_válida:
                return jsonify({'error': msg}), 400

            # ✅ Validar contraseña (NUEVO)
            es_válida, msg = _validar_contraseña(contrasena)
            if not es_válida:
                return jsonify({'error': msg}), 400

            # Crear usuario con hash de contraseña
            nuevo = crear_usuario(
                correo=correo,
                contrasena=contrasena,
                nombre_completo=nombre,
                fecha_nacimiento=fecha_nac,
                verificacion=False,
                rol='Cliente',
                usar_hash=True  # ✅ Asegura que se hashea
            )
            
            if not nuevo:
                return jsonify({'error': 'No se pudo crear el usuario (posiblemente duplicado)'}), 400

            log_info(f"[login] Usuario registrado: {correo}")
            return jsonify({'mensaje': 'Usuario creado exitosamente', 'id': nuevo.id}), 201

        except Exception as e:
            log_critical(f"[login] registrar_usuario_route: Error: {e}")
            return jsonify({'error': 'Error interno del servidor'}), 500


    @bp.post('/auth/logout')
    def logout_usuario_route():
        """
        CORREGIDO: Limpia sesión correctamente y registra audit log
        """
        try:
            usuario_correo = session.get('usuario_correo', 'desconocido')
            
            # Limpiar sesión
            session.clear()
            
            log_info(f"[login] Logout exitoso para {usuario_correo}")
            
            return jsonify({
                "ok": True,
                "redirect": url_for('login.vista_pantalla_login')
            }), 200
            
        except Exception as e:
            log_error(f"[login] logout_usuario_route: {e}")
            return jsonify({
                "ok": False,
                "redirect": url_for('login.vista_pantalla_login')
            }), 200


    @bp.get('/auth/me')
    def quien_soy():
        """Endpoint para consultar estado de sesión"""
        try:
            # ✅ Requiere AMBAS condiciones
            if not session.get('logged_in') or not session.get('mfa_verificado'):
                return jsonify({'logged_in': False, 'mfa_verificado': False}), 200
            
            return jsonify({
                'logged_in': True,
                'mfa_verificado': True,
                'usuario_id': session.get('usuario_id'),
                'correo': session.get('usuario_correo'),
                'nombre': session.get('usuario_nombre'),
                'rol': session.get('usuario_rol')
            }), 200
        except Exception as e:
            log_error(f"[login] quien_soy: {e}")
            return jsonify({'logged_in': False}), 200


    @bp.get('/dashboard')
    @requiere_mfa  # ✅ Decorador que verifica MFA
    def dashboard():
        """
        Redirige al dashboard correspondiente según el rol.
        SOLO accesible si está logueado Y MFA verificado
        """
        try:
            destino = _redir_por_rol(session.get('usuario_rol'))
            log_info(f"[login] Dashboard accedido por {session.get('usuario_correo')}")
            return redirect(destino)
        except Exception as e:
            log_critical(f"[login] dashboard: {e}")
            return redirect(url_for('mfa.verificar_codigo'))