# -*- coding: utf-8 -*-
# Archivo: app.py
# Versión: 2.5.1 (SESIÓN MFA CORREGIDA - VERSION LIMPIA)

import sys
import io

# ============================
# FIX UTF-8 PARA WINDOWS
# ============================
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import re
from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, session, jsonify
from flask_session import Session
from flask.cli import with_appcontext
import click
import traceback

from Log_PeakSport import log_error, log_success, log_info
from extensiones import mail
load_dotenv()

# Importar configuración
from config import (
    SECRET_KEY, FLASK_ENV, DEBUG, SQLALCHEMY_CONFIG, MAIL_DEFAULT_SENDER,
    MAIL_PASSWORD, MAIL_PORT, MAIL_SERVER, MAIL_USE_TLS, MAIL_USERNAME
)

# -----------------------------
# IMPORTAR db (ÚNICA INSTANCIA)
# -----------------------------
from Modelo_de_Datos_PostgreSQL_y_CRUD.conexion_postgres import db

# Importar modelos
from Modelo_de_Datos_PostgreSQL_y_CRUD import (
    Usuarios,
    Productos,
    Producto_Imagenes,
    Categorias,
    Resena,
    Cart,
    CartItem
)
from Modelo_de_Datos_PostgreSQL_y_CRUD.associations import producto_categorias
from Modelo_de_Datos_PostgreSQL_y_CRUD.password_reset import PasswordResetToken

# ============================
# CREAR APP
# ============================

app = Flask(__name__)

# Aplicar configuración de BD
for key, value in SQLALCHEMY_CONFIG.items():
    app.config[key] = value

# ============================
# CONFIGURACIÓN DE SESIÓN - CORREGIDA v2.5.1
# ============================
log_info("⚙️ Configurando sistema de sesiones...")

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = SECRET_KEY

# ✅ CRÍTICO: Configurar sesión permanente
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Configuración adicional de filesystem session
app.config['SESSION_FILE_DIR'] = os.path.join(os.getcwd(), 'flask_session')
app.config['SESSION_FILE_THRESHOLD'] = 500
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'peaksport:'

# Cookie settings - CRÍTICO PARA MFA
app.config['SESSION_COOKIE_NAME'] = 'peaksport_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = FLASK_ENV == 'production'  # HTTPS-only en producción
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Debug mode
app.config['DEBUG'] = DEBUG

# ✅ Inicializar db ANTES de Session
db.init_app(app)

# ✅ Inicializar sesiones CON LA CONFIGURACIÓN CORRECTA
Session(app)

log_success("✅ Sistema de sesiones inicializado correctamente")

# ============================
# CONFIGURACIÓN DE CORREO
# ============================
app.config["MAIL_SERVER"] = MAIL_SERVER
app.config["MAIL_PORT"] = MAIL_PORT
app.config["MAIL_USE_TLS"] = MAIL_USE_TLS
app.config["MAIL_USERNAME"] = MAIL_USERNAME
app.config["MAIL_PASSWORD"] = MAIL_PASSWORD
app.config["MAIL_DEFAULT_SENDER"] = MAIL_DEFAULT_SENDER

mail.init_app(app)

# ============================
# INICIALIZAR EMAIL SERVICE
# ============================
from services.email_service import init_email_service
init_email_service(app)

# ============================
# MENSAJE DE INICIO
# ============================
print("\n" + "="*70)
print("🚀 INICIALIZANDO PEAKSPORT v2.5.1 (MFA FIX)")
print("   - Sistema de Carrito")
print("   - Catálogo de Productos")
print("   - Recuperación de Contraseña")
print("   - ✅ Sesión MFA Corregida")
print("="*70)
print(f"📍 Entorno: {FLASK_ENV}")
print(f"📍 Debug: {DEBUG}")
print(f"📍 Sesión: filesystem (30 min)")
_db_uri = SQLALCHEMY_CONFIG.get('SQLALCHEMY_DATABASE_URI', '')
_db_uri_oculta = re.sub(r'://([^:]+):[^@]+@', r'://\1:***@', _db_uri)
print(f"📍 Base de datos: {_db_uri_oculta[:60]}...")
print("="*70 + "\n")

log_success("✅ Base de datos configurada correctamente")

# ============================
# IMPORTACIÓN DE BLUEPRINTS
# ============================
from login.main import bp_login
from Cliente.principal.main import bp_cliente_principal
from Cliente.producto.main import bp_producto_detalle
from Apis.producto_main import bp_productos
from Apis.resenas_api import bp_resenas_api
from Administrador.principal.main import bp_administrador_principal
from Seguridad.mfa import bp_mfa
from Cliente.Cart.main import bp_cart
from Cliente.Catalogo.main import bp_catalogo
from Apis.password_reset_api import password_reset_bp

# ============================
# REGISTRO DE BLUEPRINTS
# ============================
app.register_blueprint(bp_login, url_prefix='/login')
app.register_blueprint(bp_cliente_principal, url_prefix='/cliente/principal')
app.register_blueprint(bp_producto_detalle)
app.register_blueprint(bp_productos, url_prefix='/api/productos')
app.register_blueprint(bp_resenas_api, url_prefix='/api/resenas')
app.register_blueprint(bp_administrador_principal, url_prefix='/administrador/principal')
app.register_blueprint(bp_mfa, url_prefix='/mfa')
app.register_blueprint(bp_cart, url_prefix='/cart')
app.register_blueprint(bp_catalogo, url_prefix='/catalogo')
app.register_blueprint(password_reset_bp)

log_success("✅ Blueprints registrados correctamente (v2.5.1)")

# ============================
# RUTAS PRINCIPALES
# ============================
@app.route('/')
def pagina_principal():
    """Pantalla pública principal"""
    try:
        logged = bool(session.get('logged_in') or session.get('mfa_verificado'))
        usuario_nombre = session.get('usuario_nombre', 'Invitado') if logged else 'Invitado'
        usuario_email = session.get('usuario_email')
        
        return render_template(
            'pagina_principal.html',
            usuario_autenticado=logged,
            usuario_nombre=usuario_nombre,
            usuario_email=usuario_email
        )
    except Exception as e:
        log_error(f"[public] pagina_principal error: {e}")
        return "<h1>Error cargando la página</h1>", 500


@app.route('/forgot-password')
def forgot_password_page():
    """Página para solicitar recuperación de contraseña"""
    try:
        return render_template('forgot_password.html')
    except Exception as e:
        log_error(f"[public] forgot_password_page error: {e}")
        return "<h1>Error cargando la página</h1>", 500


@app.route('/reset-password')
def reset_password_page():
    """Página para restablecer contraseña con token"""
    try:
        from flask import request
        token = request.args.get('token')
        return render_template('reset_password.html', token=token)
    except Exception as e:
        log_error(f"[public] reset_password_page error: {e}")
        return "<h1>Error cargando la página</h1>", 500


@app.route('/health')
def health_check():
    """Endpoint para verificar salud de la aplicación"""
    try:
        with app.app_context():
            result = db.session.execute(db.text("SELECT 1"))
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'version': '2.5.1',
            'environment': FLASK_ENV,
            'features': [
                'productos', 
                'reseñas', 
                'usuarios', 
                'categorias', 
                'carrito', 
                'catálogo',
                'password_reset',
                'mfa_fixed'
            ]
        }), 200
        
    except Exception as e:
        log_error(f"[health_check] error: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@app.route('/test-db')
def test_db_route():
    """Ruta de diagnóstico de conexión a BD - solo disponible fuera de producción"""
    if FLASK_ENV == 'production':
        return jsonify({'status': 'not_found'}), 404

    try:
        with app.app_context():
            result = db.session.execute(db.text("SELECT version()"))
            version = result.fetchone()[0]

        return jsonify({
            'status': 'success',
            'message': 'Conexión exitosa',
            'version': version.split(',')[0]
        }), 200

    except Exception as e:
        log_error(f"[test_db_route] error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Error de conexión a la base de datos'
        }), 500


# ============================
# MANEJADORES DE ERRORES
# ============================
@app.errorhandler(404)
def pagina_no_encontrada(error):
    """Página 404"""
    try:
        return render_template('404.html'), 404
    except Exception:
        return "<h1>404 - Página no encontrada</h1>", 404


@app.errorhandler(500)
def error_servidor(error):
    """Página 500"""
    log_error(f"[500] Error del servidor: {error}")
    try:
        return render_template('500.html'), 500
    except Exception:
        return "<h1>500 - Error del servidor</h1>", 500


# ============================
# CONTEXTO DE TEMPLATES
# ============================
@app.context_processor
def inject_config():
    """Inyectar variables globales en templates"""
    return {
        'app_name': 'PeakSport',
        'app_version': '2.5.1',
        'logged_in': session.get('logged_in', False) or session.get('mfa_verificado', False),
        'usuario_nombre': session.get('usuario_nombre', ''),
        'usuario_id': session.get('usuario_id'),
        'environment': FLASK_ENV
    }


# ============================
# COMANDOS CLI
# ============================

@app.cli.command('test-conexion')
@with_appcontext
def test_conexion():
    """Comando: flask test-conexion"""
    click.echo("\n🔍 Probando conexión a BD...")
    try:
        result = db.session.execute(db.text("SELECT version()"))
        version = result.fetchone()[0]
        click.echo("✅ Conexión exitosa")
        click.echo(f"   {version.split(',')[0]}")
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        traceback.print_exc()


@app.cli.command('crear-tablas')
@with_appcontext
def crear_tablas():
    """Comando: flask crear-tablas"""
    click.echo("\n📦 Creando tablas en BD...")
    try:
        db.create_all()
        click.echo("✅ Tablas creadas correctamente")
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        traceback.print_exc()


@app.cli.command('limpiar-sesiones')
def limpiar_sesiones():
    """Limpia todas las sesiones almacenadas"""
    click.echo("\n🧹 Limpiando sesiones...")
    try:
        session_dir = app.config['SESSION_FILE_DIR']
        if os.path.exists(session_dir):
            import shutil
            shutil.rmtree(session_dir)
            os.makedirs(session_dir)
            click.echo("✅ Sesiones limpiadas correctamente")
        else:
            click.echo("⚠️ Directorio de sesiones no existe")
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        traceback.print_exc()


# ============================
# INICIO DE LA APLICACIÓN
# ============================
if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 INICIANDO PEAKSPORT v2.5.1 (MFA FIX)")
    print("="*70)
    print(f"📍 Host: 0.0.0.0")
    print(f"📍 Puerto: 2323")
    print(f"📍 Entorno: {FLASK_ENV}")
    print(f"📍 Debug: {DEBUG}")
    print(f"📍 Características: Productos | Reseñas | Usuarios | Categorías")
    print(f"                    Carrito | Catálogo | Password Reset | MFA")
    print("="*70 + "\n")
    
    app.run(
        debug=DEBUG,
        host="0.0.0.0",
        port=2323,
        use_reloader=True
    )