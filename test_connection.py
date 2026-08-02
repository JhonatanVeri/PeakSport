# test_connection.py
# Script para verificar la conexión a Supabase

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect

# Cargar variables del .env
load_dotenv()

def test_supabase_connection():
    """Prueba la conexión a Supabase"""
    
    print("=" * 60)
    print("🔍 PRUEBA DE CONEXIÓN A SUPABASE")
    print("=" * 60)
    
    # Obtener URI
    uri = os.getenv('POSTGRES_URI')
    
    if not uri:
        print("❌ ERROR: No se encontró POSTGRES_URI en .env")
        return False
    
    # Ocultar contraseña en el log
    uri_oculta = uri.replace(uri.split(':')[1].split('@')[0], '***')
    print(f"\n📍 Conectando a: {uri_oculta}")
    
    try:
        # Crear engine
        engine = create_engine(uri, echo=False)
        
        # Conectar
        with engine.connect() as conn:
            print("\n✅ CONEXIÓN ESTABLECIDA")
            
            # Información de PostgreSQL
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"\n📊 PostgreSQL: {version.split(',')[0]}")
            
            # Obtener tablas
            inspector = inspect(engine)
            tablas = inspector.get_table_names()
            
            print(f"\n📦 TABLAS ENCONTRADAS ({len(tablas)}):")
            for tabla in tablas:
                columnas = inspector.get_columns(tabla)
                print(f"\n   📋 {tabla}")
                for col in columnas:
                    print(f"      • {col['name']}: {col['type']}")
            
            # Prueba de lectura
            print("\n" + "=" * 60)
            print("📝 PRUEBAS DE LECTURA")
            print("=" * 60)
            
            # Contar registros en cada tabla
            for tabla in tablas:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {tabla}"))
                    count = result.fetchone()[0]
                    print(f"✓ {tabla}: {count} registros")
                except Exception as e:
                    print(f"✗ {tabla}: Error - {e}")
            
            print("\n" + "=" * 60)
            print("✅ ¡TODAS LAS PRUEBAS PASARON!")
            print("=" * 60)
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR DE CONEXIÓN:")
        print(f"   {type(e).__name__}: {e}")
        print("\n⚠️  VERIFICAR:")
        print("   1. ¿La URI en .env es correcta?")
        print("   2. ¿Incluye ?sslmode=require?")
        print("   3. ¿Tienes conexión a internet?")
        print("   4. ¿El proyecto en Supabase está activo?")
        return False


def test_flask_app():
    """Prueba la app Flask con Supabase"""
    
    print("\n" + "=" * 60)
    print("🚀 PRUEBA CON FLASK")
    print("=" * 60)
    
    try:
        from app import app, db
        from Modelo_de_Datos_PostgreSQL_y_CRUD import Usuario, Producto, Categoria

        with app.app_context():
            print("\n✅ App Flask creada exitosamente")

            # Verificar conexión
            db.session.execute(text("SELECT 1"))
            print("✅ SQLAlchemy conectado a Supabase")

            # Contar registros
            usuarios = Usuario.query.count()
            productos = Producto.query.count()
            categorias = Categoria.query.count()
            
            print(f"\n📊 DATOS EN SUPABASE:")
            print(f"   • Usuarios: {usuarios}")
            print(f"   • Productos: {productos}")
            print(f"   • Categorías: {categorias}")
            
            print("\n✅ ¡La app está lista para usar Supabase!")
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR CON FLASK:")
        print(f"   {type(e).__name__}: {e}")
        print("\n⚠️  VERIFICAR:")
        print("   1. ¿Todos los modelos están importados?")
        print("   2. ¿Las tablas existen en Supabase?")
        return False


if __name__ == '__main__':
    # Prueba 1: Conexión directa
    resultado1 = test_supabase_connection()
    
    # Prueba 2: Con Flask
    resultado2 = test_flask_app()
    
    # Resultado final
    print("\n" + "=" * 60)
    if resultado1 and resultado2:
        print("🎉 ¡TODO ESTÁ CONFIGURADO CORRECTAMENTE!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("⚠️  HAY PROBLEMAS - REVISA ARRIBA")
        print("=" * 60)
        sys.exit(1)