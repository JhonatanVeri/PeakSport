# solucionar_dns.py
# Script para resolver problemas de DNS/Firewall

import os
import socket
import subprocess
import sys
from dotenv import load_dotenv

load_dotenv()

print("\n" + "="*70)
print("🚀 SOLUCIONES AVANZADAS PARA DNS/FIREWALL")
print("="*70)

# Solución 1: Forzar DNS específico
print("\n1️⃣  FORZAR RESOLUCIÓN CON DNS PÚBLICO")
print("-" * 70)

import dns.resolver

try:
    # Usar Google DNS directamente
    resolver = dns.resolver.Resolver()
    resolver.nameservers = ['8.8.8.8', '8.8.4.4']
    
    host = "db.isdxcadkundexodzsjfl.supabase.co"
    print(f"Resolviendo {host} con Google DNS...")
    
    answers = resolver.resolve(host, 'A')
    for rdata in answers:
        print(f"✅ RESUELTO: {rdata}")
    
except ImportError:
    print("⚠️  dnspython no instalado")
    print("   Instala con: pip install dnspython")
except Exception as e:
    print(f"❌ Error: {e}")
    print("\n💡 INTENTA ESTO:")
    print("   pip install dnspython")
    print("   python solucionar_dns.py")

# Solución 2: Usar IP directa de Supabase
print("\n2️⃣  PROBANDO CON IP DIRECTA DE SUPABASE")
print("-" * 70)

print("Las IPs conocidas de Supabase son:")
supabase_ips = [
    "34.149.242.64",
    "34.149.242.65",
    "34.149.243.0"
]

for ip in supabase_ips:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((ip, 5432))
        sock.close()
        
        if result == 0:
            print(f"✅ IP {ip}:5432 ACCESIBLE")
        else:
            print(f"❌ IP {ip}:5432 NO accesible")
    except Exception as e:
        print(f"⚠️  Error con {ip}: {e}")

# Solución 3: Actualizar credenciales
print("\n3️⃣  VERIFICAR CREDENCIALES EN .env")
print("-" * 70)

postgres_uri = os.getenv('POSTGRES_URI')

if postgres_uri:
    print("✅ POSTGRES_URI encontrada:")
    
    # Verificar componentes
    if 'sslmode=require' in postgres_uri:
        print("   ✅ SSL requerido")
    else:
        print("   ❌ SSL NO configurado (agrega ?sslmode=require)")
    
    if 'jhonatan2.007' in postgres_uri:
        print("   ✅ Contraseña correcta")
    else:
        print("   ⚠️  Contraseña diferente - verifica")
    
    if 'db.isdxcadkundexodzsjfl.supabase.co' in postgres_uri:
        print("   ✅ Host correcto")
    else:
        print("   ❌ Host incorrecto")
else:
    print("❌ POSTGRES_URI no está configurada")

# Solución 4: Alternativa con retry
print("\n4️⃣  CONFIGURACIÓN CON REINTENTOS")
print("-" * 70)

print("Crea un archivo 'conexion_con_retry.py' con esto:")
print("""
import time
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

def conectar_con_reintentos(max_intentos=5):
    uri = os.getenv('POSTGRES_URI')
    
    for intento in range(max_intentos):
        try:
            print(f"Intento {intento + 1}/{max_intentos}...")
            engine = create_engine(uri, pool_pre_ping=True)
            
            with engine.connect() as conn:
                conn.execute("SELECT 1")
                print("✅ ¡CONECTADO!")
                return engine
                
        except Exception as e:
            print(f"❌ Intento {intento + 1} falló: {str(e)[:50]}")
            if intento < max_intentos - 1:
                time.sleep(2 ** intento)  # Espera exponencial
    
    print("❌ No se pudo conectar después de todos los intentos")
    return None

if __name__ == '__main__':
    engine = conectar_con_reintentos()
""")

# Solución 5: Verificar si es VPN/Proxy
print("\n5️⃣  VERIFICAR VPN/PROXY")
print("-" * 70)

try:
    result = subprocess.run(
        ["ipconfig", "/all"],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    output = result.stdout.lower()
    
    if 'pppoe' in output or 'vpn' in output:
        print("⚠️  Parece que tienes VPN/Proxy activo")
        print("   Desactívalo e intenta de nuevo")
    elif 'proxy' in output:
        print("⚠️  Proxy detectado en tu red")
        print("   Configúralo en Flask si es necesario")
    else:
        print("✅ No se detectó VPN/Proxy")
        
except Exception as e:
    print(f"⚠️  No se pudo verificar: {e}")

# Solución 6: Crear conexión alternativa
print("\n6️⃣  ALTERNATIVA: USAR SQLITE LOCALMENTE")
print("-" * 70)

print("""
Si Supabase no funciona, puedes usar SQLite localmente:

1. Cambia el .env:
   FLASK_ENV=development
   DATABASE_URL=sqlite:///peaksport.db

2. Actualiza app.py:
   app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///peaksport.db')

3. Crea las tablas:
   python -c "from app import db; db.create_all()"

Esto te permite trabajar localmente mientras resuelves el problema de Supabase.
""")

print("\n" + "="*70)
print("📋 PRÓXIMOS PASOS")
print("="*70)
print("""
1. Instala dnspython:
   pip install dnspython

2. Ejecuta este script de nuevo:
   python solucionar_dns.py

3. Si aún no funciona, prueba:
   - Cambiar de red (móvil hotspot)
   - Contactar a tu ISP
   - Usar SQLite localmente (mientras resuelves)

4. Si logras conectarte desde otra red:
   - El problema es tu WiFi/Firewall
   - Reinicia el router o contacta a TI
""")
print("="*70)