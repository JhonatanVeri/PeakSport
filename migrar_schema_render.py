"""
Script para migrar el schema de PeakSport a Render
"""
import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()

# URL de la base de datos en Render, tomada de variables de entorno
RENDER_DATABASE_URL = os.getenv("RENDER_DATABASE_URL") or os.getenv("POSTGRES_URI")
if not RENDER_DATABASE_URL:
    print("❌ Falta RENDER_DATABASE_URL (o POSTGRES_URI) en el entorno/.env")
    sys.exit(1)

# Lee el archivo SQL
with open('DBSPEAKSPORT_CLOUD.sql', 'r', encoding='utf-8') as f:
    sql_script = f.read()

try:
    print("🔄 Conectando a Render...")
    conn = psycopg2.connect(RENDER_DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()
    
    print("✅ Conexión exitosa!")
    print("🔄 Ejecutando schema...")
    
    # Ejecutar el script SQL
    cursor.execute(sql_script)
    
    print("✅ Schema ejecutado exitosamente!")
    print("\n📊 Verificando tablas creadas...")
    
    # Verificar las tablas
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    
    tables = cursor.fetchall()
    print(f"\n✅ Tablas creadas ({len(tables)}):")
    for table in tables:
        print(f"   - {table[0]}")
    
    cursor.close()
    conn.close()
    
    print("\n🎉 ¡Migración completada exitosamente!")
    print("📝 Ahora actualiza tu archivo .env con la nueva URL de Render")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nVerifica que:")
    print("1. La URL de Render esté correcta")
    print("2. El archivo DBSPEAKSPORT_CLOUD.sql esté en la misma carpeta")
    print("3. Tengas conexión a internet")