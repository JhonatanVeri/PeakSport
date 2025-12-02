"""
Script para migrar el schema de PeakSport a Render
"""
import psycopg2
from psycopg2 import sql

# URL de tu base de datos en Render (completa con el hostname)
RENDER_DATABASE_URL = "postgresql://peaksport_user:***REMOVED-DB-PASSWORD***@dpg-d44ad83ipnbc73d0dde0-a.oregon-postgres.render.com/peaksport_t81b"

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