# -*- coding: utf-8 -*-
# Archivo: app.py
# Versión: 2.5.0 (Con Sistema de Carrito, Catálogo y Password Reset)

import sys
import io

# ============================
# FIX UTF-8 PARA WINDOWS
# ============================
# Configurar UTF-8 para la salida estándar (soluciona problemas con emojis en Windows)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
from dotenv import load_dotenv
from flask import Flask, render_template, session, jsonify
from flask_session import Session
from flask.cli import with_appcontext
import click
import traceback

from Log_PeakSport import log_error, log_success
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

# Importar modelos (incluyendo los nuevos modelos de carrito y password reset)
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

# 🆕 NUEVO: Importar modelo de password reset
from Modelo_de_Datos_PostgreSQL_y_CRUD.password_reset import PasswordResetToken

# ============================
# CREAR APP
# ============================

app = Flask(__name__)

# Aplicar configuración de BD
for key, value in SQLALCHEMY_CONFIG.items():
    app.config[key] = value

# ============================
# CONFIGURACIÓN DE SESIÓN
# ============================
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutos
app.config['DEBUG'] = DEBUG

# Configuración adicional de filesystem session
app.config['SESSION_FILE_DIR'] = os.path.join(os.getcwd(), 'flask_session')
app.config['SESSION_FILE_THRESHOLD'] = 500

# Inicializar db
db.init_app(app)

# Inicializar sesiones
Session(app)

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
# 🆕 NUEVO: Inicializar servicio de email (Gmail local + SendGrid producción)
from services.email_service import init_email_service
init_email_service(app)

# ============================
# MENSAJE DE INICIO
# ============================
print("\n" + "="*70)
print("🚀 INICIALIZANDO PEAKSPORT v2.5.0")
print("   - Sistema de Carrito")
print("   - Catálogo de Productos")
print("   - Recuperación de Contraseña")
print("="*70)
print(f"📍 Entorno: {FLASK_ENV}")
print(f"📍 Debug: {DEBUG}")
print(f"📍 Base de datos: {SQLALCHEMY_CONFIG.get('SQLALCHEMY_DATABASE_URI', '')[:50]}...")
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

# 🆕 NUEVO: Importar blueprint de password reset
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

# 🆕 NUEVO: Registrar blueprint de password reset
app.register_blueprint(password_reset_bp)

log_success("✅ Blueprints registrados correctamente (v2.5.0)")

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


# 🆕 NUEVO: Rutas HTML para password reset
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
        # Verificar conexión a BD
        with app.app_context():
            result = db.session.execute(db.text("SELECT 1"))
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'version': '2.5.0',
            'environment': FLASK_ENV,
            'features': [
                'productos', 
                'reseñas', 
                'usuarios', 
                'categorias', 
                'carrito', 
                'catálogo',
                'password_reset'  # 🆕 NUEVO
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
    """Ruta para probar conexión a BD"""
    try:
        with app.app_context():
            result = db.session.execute(db.text("SELECT version()"))
            version = result.fetchone()[0]
        
        return jsonify({
            'status': 'success',
            'message': 'Conexión a Railway/Render exitosa',
            'version': version.split(',')[0]
        }), 200
            
    except Exception as e:
        log_error(f"[test_db_route] error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
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
        'app_version': '2.5.0',
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
    """Comando: flask test-conexion - Prueba conexión a BD"""
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
    """Comando: flask crear-tablas - Crea todas las tablas en BD"""
    click.echo("\n📦 Creando tablas en BD...")
    try:
        db.create_all()
        click.echo("✅ Tablas creadas correctamente")
        click.echo("   Incluye: usuarios, productos, carrito, password_reset_tokens")
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        traceback.print_exc()


@app.cli.command('verificar-modelos')
@with_appcontext
def verificar_modelos():
    """Verifica que todos los modelos estén cargados"""
    click.echo("\n🔍 Verificando modelos...")
    try:
        modelos = [
            ('Usuarios', Usuarios),
            ('Productos', Productos),
            ('ProductoImagenes', Producto_Imagenes),
            ('Categorias', Categorias),
            ('Resenas', Resena),
            ('Cart', Cart),
            ('CartItem', CartItem),
            ('PasswordResetToken', PasswordResetToken),  # 🆕 NUEVO
        ]
        
        for nombre, modelo in modelos:
            tabla = getattr(modelo, "__tablename__", repr(modelo))
            click.echo(f"   ✓ {nombre}: {tabla}")
        
        click.echo("\n✅ Todos los modelos están correctamente importados")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        traceback.print_exc()


@app.cli.command('inspeccionar-bd')
@with_appcontext
def inspeccionar_bd():
    """Inspecciona metadata y tablas existentes en la BD"""
    click.echo("\n=== MODELOS REGISTRADOS ===\n")
    try:
        for table_name in db.metadata.tables.keys():
            click.echo(f"✓ {table_name}")
        
        click.echo("\n=== VERIFICANDO TABLAS EN BD ===\n")
        inspector = db.inspect(db.engine)
        tablas_bd = inspector.get_table_names()
        
        for tabla in tablas_bd:
            columnas = [col['name'] for col in inspector.get_columns(tabla)]
            click.echo(f"\n📋 {tabla}:")
            click.echo(f"   Columnas: {', '.join(columnas)}")
        
        # Verificar tablas importantes
        if 'carts' in tablas_bd:
            click.echo("\n✅ Tabla 'carts' existe")
        else:
            click.echo("\n❌ Tabla 'carts' NO existe")
        
        if 'password_reset_tokens' in tablas_bd:  # 🆕 NUEVO
            click.echo("✅ Tabla 'password_reset_tokens' existe")
        else:
            click.echo("❌ Tabla 'password_reset_tokens' NO existe")
            
    except Exception as e:
        click.echo(f"❌ Error inspeccionando BD: {e}")
        traceback.print_exc()


@app.cli.command('test-producto')
@with_appcontext
def test_producto():
    """Prueba cargar un producto con todas sus relaciones."""
    click.echo("\n🔧 test-producto")
    try:
        Producto = None
        try:
            from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import Producto as P1
            Producto = P1
        except Exception:
            try:
                from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import Productos as P2
                Producto = P2
            except Exception:
                Producto = None

        if Producto is None:
            click.echo("❌ No se pudo importar la clase Producto")
            return

        producto = Producto.query.first()
        
        if not producto:
            click.echo("❌ No hay productos en la BD")
            return
        
        click.echo(f"\n✅ Producto: {getattr(producto, 'nombre', 'N/A')}")
        click.echo(f"   ID: {getattr(producto, 'id', 'N/A')}")
        
        try:
            imgs = list(getattr(producto, 'imagenes', []))
            click.echo(f"   Imágenes: {len(imgs)}")
        except Exception as e:
            click.echo(f"   ❌ Error en imágenes: {e}")
        
        try:
            cats = list(getattr(producto, 'categorias', []))
            click.echo(f"   Categorías: {len(cats)}")
        except Exception as e:
            click.echo(f"   ❌ Error en categorías: {e}")
            
    except Exception as e:
        click.echo(f"❌ Error general: {str(e)}")
        traceback.print_exc()


@app.cli.command('test-carrito')
@with_appcontext
def test_carrito():
    """Prueba crear un carrito de prueba."""
    click.echo("\n🔧 test-carrito")
    try:
        from Modelo_de_Datos_PostgreSQL_y_CRUD.Cart import Cart as CartModel, CartItem as CartItemModel
        
        Producto = None
        try:
            from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import Producto as P1
            Producto = P1
        except Exception:
            try:
                from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import Productos as P2
                Producto = P2
            except Exception:
                Producto = None

        session_id = 'test-session-123'
        cart = CartModel.query.filter_by(session_id=session_id).first()
        
        if not cart:
            cart = CartModel(session_id=session_id)
            db.session.add(cart)
            db.session.commit()
            click.echo(f"✅ Carrito creado: ID {cart.id}")
        else:
            click.echo(f"✅ Carrito existente: ID {cart.id}")
        
        if Producto:
            producto = Producto.query.first()
            if producto:
                item = CartItemModel.query.filter_by(
                    cart_id=cart.id,
                    producto_id=getattr(producto, 'id', None)
                ).first()
                
                if not item:
                    item = CartItemModel(
                        cart_id=cart.id,
                        producto_id=getattr(producto, 'id', None),
                        cantidad=1,
                        precio_unitario_centavos=getattr(producto, 'precio_centavos', 0)
                    )
                    db.session.add(item)
                    db.session.commit()
                    click.echo(f"✅ Producto agregado: {getattr(producto, 'nombre', 'N/A')}")
                else:
                    click.echo(f"✅ Item ya existe: {getattr(producto, 'nombre', 'N/A')}")
        
        items = CartItemModel.query.filter_by(cart_id=cart.id).all()
        click.echo(f"\n📦 Items en carrito: {len(items)}")
        
        for item in items:
            prod_name = getattr(getattr(item, 'producto', None), 'nombre', 'N/A')
            click.echo(f"   - {prod_name} x{getattr(item, 'cantidad', 0)}")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        traceback.print_exc()


# ============================
# INICIO DE LA APLICACIÓN
# ============================
if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 INICIANDO PEAKSPORT v2.5.0")
    print("="*70)
    print(f"📍 Host: 0.0.0.0")
    print(f"📍 Puerto: 2323")
    print(f"📍 Entorno: {FLASK_ENV}")
    print(f"📍 Debug: {DEBUG}")
    print(f"📍 Características: Productos | Reseñas | Usuarios | Categorías")
    print(f"                    Carrito | Catálogo | Password Reset")
    print("="*70 + "\n")
    
    app.run(
        debug=DEBUG,
        host="0.0.0.0",
        port=2323,
        use_reloader=True
    )