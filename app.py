# -- coding: utf-8 --
# Archivo: app.py
# Versión: 2.4.0 (Con Sistema de Carrito de Compras) - LIMPIO Y ORDENADO

import os
from dotenv import load_dotenv
from flask import Flask, render_template, session, jsonify
from flask_session import Session
from flask.cli import with_appcontext
import click
import traceback

from Log_PeakSport import log_error, log_success
from extensiones import mail  # extiende mail (no contiene la instancia db en este proyecto)
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

# Importar modelos (incluyendo los nuevos modelos de carrito)
from Modelo_de_Datos_PostgreSQL_y_CRUD import (
    Usuarios,
    Productos,
    Producto_Imagenes,
    Categorias,
    Resena,
    Cart,       # 🆕 NUEVO
    CartItem    # 🆕 NUEVO
)
from Modelo_de_Datos_PostgreSQL_y_CRUD.associations import producto_categorias

# ============================
# CREAR APP
# ============================

app = Flask(__name__)  # ✅ CORREGIDO: __name__ (doble guion bajo)

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

# Inicializar db (la instancia viene de conexion_postgres)
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
# MENSAJE DE INICIO
# ============================
print("\n" + "="*70)
print("🚀 INICIALIZANDO PEAKSPORT CON SISTEMA DE CARRITO")
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

# 🆕 NUEVO: Importar blueprint del carrito
from Cliente.Cart.main import bp_cart

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

# 🆕 NUEVO: Registrar blueprint del carrito
app.register_blueprint(bp_cart, url_prefix='/cart')

log_success("✅ Blueprints registrados correctamente (incluye carrito de compras)")

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
            'version': '2.4.0',
            'environment': FLASK_ENV,
            'features': ['productos', 'reseñas', 'usuarios', 'categorias', 'carrito']
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
        'app_version': '2.4.0',
        'logged_in': session.get('logged_in', False) or session.get('mfa_verificado', False),
        'usuario_nombre': session.get('usuario_nombre', ''),
        'usuario_id': session.get('usuario_id'),
        'environment': FLASK_ENV
    }


# ============================
# COMANDOS CLI (UNIFICADOS, SIN DUPLICADOS)
# ============================

@app.cli.command('test-conexion')
@with_appcontext
def test_conexion():
    """Comando: flask test-conexion - Prueba conexión a Railway/Render"""
    click.echo("\n🔍 Probando conexión a Railway/Render...")
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
    """Comando: flask crear-tablas - Crea todas las tablas en Railway/Render"""
    click.echo("\n📦 Creando tablas en Railway/Render...")
    try:
        db.create_all()
        click.echo("✅ Tablas creadas correctamente (incluye tablas de carrito)")
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
            ('Cart', Cart),          # 🆕 NUEVO
            ('CartItem', CartItem)   # 🆕 NUEVO
        ]
        
        for nombre, modelo in modelos:
            # Intentamos leer __tablename__ si existe, si no mostramos repr del modelo
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
        
        # Verificar específicamente el carrito
        if 'carts' in tablas_bd or 'cart' in tablas_bd:
            click.echo("\n✅ Tabla 'carts' existe")
        else:
            click.echo("\n❌ Tabla 'carts' NO existe")
        
        if 'cart_items' in tablas_bd or 'cart_item' in tablas_bd:
            click.echo("✅ Tabla 'cart_items' existe")
        else:
            click.echo("❌ Tabla 'cart_items' NO existe")
    except Exception as e:
        click.echo(f"❌ Error inspeccionando BD: {e}")
        traceback.print_exc()


@app.cli.command('test-producto')
@with_appcontext
def test_producto():
    """Prueba cargar un producto con todas sus relaciones."""
    click.echo("\n🔧 test-producto")
    try:
        # Intentamos localizar la clase Producto de forma flexible
        Producto = None
        try:
            # si tu módulo Productos define la clase Producto o Productos, probamos ambas
            from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import Producto as P1
            Producto = P1
        except Exception:
            try:
                from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import Productos as P2
                Producto = P2
            except Exception:
                Producto = None

        if Producto is None:
            click.echo("❌ No se pudo importar la clase Producto. Revisa Modelo_de_Datos_PostgreSQL_y_CRUD.Productos")
            return

        producto = Producto.query.first()
        
        if not producto:
            click.echo("❌ No hay productos en la BD")
            return
        
        click.echo(f"\n✅ Producto: {getattr(producto, 'nombre', 'N/A')}")
        click.echo(f"   ID: {getattr(producto, 'id', 'N/A')}")
        precio_centavos = getattr(producto, 'precio_centavos', None)
        if precio_centavos is not None:
            try:
                click.echo(f"   Precio: {precio_centavos / 100}")
            except Exception:
                click.echo(f"   Precio: {precio_centavos} (no divisible por 100)")
        click.echo(f"   Stock: {getattr(producto, 'stock', 'N/A')}")
        
        # Test imagenes
        try:
            imgs = list(getattr(producto, 'imagenes', []))
            click.echo(f"   Imágenes: {len(imgs)}")
        except Exception as e:
            click.echo(f"   ❌ Error en imágenes: {e}")
        
        # Test categorias
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
        # Import de modelos usando las rutas del paquete
        from Modelo_de_Datos_PostgreSQL_y_CRUD.Cart import Cart as CartModel, CartItem as CartItemModel
        # Producto puede venir de distinto nombre; intentamos importarlo como en test-producto
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
        
        # Agregar producto de prueba si existe
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
        
        # Mostrar contenido
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
    print("🚀 INICIANDO PEAKSPORT")
    print("="*70)
    print(f"📍 Host: 0.0.0.0")
    print(f"📍 Puerto: 2323")
    print(f"📍 Entorno: {FLASK_ENV}")
    print(f"📍 Debug: {DEBUG}")
    print("="*70 + "\n")
    
    app.run(
        debug=DEBUG,
        host="0.0.0.0",
        port=2323,
        use_reloader=True
    )
