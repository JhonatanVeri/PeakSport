# -*- coding: utf-8 -*-
"""
Archivo: conexion_postgres.py

Clase para manejar la conexión a PostgreSQL/Supabase
utilizando SQLAlchemy dentro de una aplicación Flask.

Características:
- Soporte para Supabase con Connection Pooling
- Configuración automática de SSL
- Reintentos automáticos de conexión
- Optimizado para desarrollo y producción

Autor: Carlos Andrés Jiménez Sarmiento (CJ)
Versión: 2.1.0 (Supabase)
"""

import os
import time
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, exc
from sqlalchemy.pool import Pool
from Log_PeakSport import log_success, log_error, log_critical, log_documentacion

# Instancia global
db = SQLAlchemy()


class PostgreSQLConnection:
    """
    Clase para inicializar y configurar la conexión a PostgreSQL/Supabase
    mediante SQLAlchemy en el contexto de Flask.
    
    Soporta:
    - Conexión directa a PostgreSQL
    - Connection pooling de Supabase
    - Reintentos automáticos
    - SSL requerido para Supabase
    """

    def __init__(self, app=None):
        """
        Constructor de la clase.

        Args:
            app (Flask): instancia opcional de la app Flask.
        """
        self.db = db
        self.app = app
        self.engine = None
        
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        Configura la app de Flask con SQLAlchemy.

        Args:
            app (Flask): instancia de la app Flask.
        """
        try:
            # Importar config aquí para evitar circular imports
            from config import SQLALCHEMY_CONFIG, POSTGRES_URI, FLASK_ENV
            
            if not POSTGRES_URI:
                log_critical("❌ POSTGRES_URI no definida en .env")
                raise ValueError("POSTGRES_URI no definida en .env")
            
            # Aplicar configuración de SQLAlchemy
            for key, value in SQLALCHEMY_CONFIG.items():
                app.config[key] = value
            
            app.config["SQLALCHEMY_DATABASE_URI"] = POSTGRES_URI

            # Inicializar SQLAlchemy
            self.db.init_app(app)
            
            # Guardar referencia a la app para usar el contexto después
            self.app = app
            
            # Configurar listeners para reconexión automática
            with app.app_context():
                self._setup_listeners()
            
            log_success("✅ Conexión a PostgreSQL/Supabase inicializada correctamente.")
            
            # Log del entorno
            if FLASK_ENV == 'production':
                log_documentacion("📍 Usando Connection Pool (Puerto 6543)")
            else:
                log_documentacion("📍 Usando conexión directa (Puerto 5432)")
                
        except Exception as e:
            log_error(f"⚠️ Error al inicializar PostgreSQL: {str(e)}")
            raise

    def _setup_listeners(self):
        """
        Configura listeners para manejar errores de conexión
        y reconexión automática.
        """
        
        @event.listens_for(Pool, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Se ejecuta cuando se crea una nueva conexión"""
            log_documentacion("🔗 Nueva conexión a la base de datos establecida")
        
        @event.listens_for(Pool, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Se ejecuta cuando se obtiene una conexión del pool"""
            # Verificar que la conexión sigue activa
            try:
                dbapi_conn.isolation_level
            except Exception as e:
                log_error(f"⚠️ Conexión perdida, reconectando: {str(e)[:50]}")
                # Retornar False fuerza una nueva conexión
                raise exc.DisconnectionError()

    def test_connection(self):
        """
        Prueba la conexión a la base de datos.
        
        Returns:
            bool: True si la conexión es exitosa, False si falla
        """
        try:
            with self.app.app_context():
                with self.db.engine.connect() as conn:
                    conn.execute("SELECT 1")
                    log_success("✅ Conexión a base de datos verificada")
                    return True
        except Exception as e:
            log_error(f"❌ Error al verificar conexión: {str(e)}")
            return False

    def reconnect_with_retries(self, max_retries=5, delay=2):
        """
        Intenta reconectar a la base de datos con reintentos exponenciales.
        
        Args:
            max_retries (int): Número máximo de reintentos
            delay (int): Retraso inicial en segundos
            
        Returns:
            bool: True si se reconecta, False si falla
        """
        for attempt in range(max_retries):
            try:
                log_documentacion(f"🔄 Intento de reconexión {attempt + 1}/{max_retries}...")
                
                if self.test_connection():
                    log_success("✅ Reconexión exitosa")
                    return True
                    
            except Exception as e:
                wait_time = delay ** attempt
                log_error(f"❌ Intento {attempt + 1} falló: {str(e)[:50]}")
                
                if attempt < max_retries - 1:
                    log_documentacion(f"⏳ Esperando {wait_time}s antes de reintentar...")
                    time.sleep(wait_time)
        
        log_critical(f"❌ No se pudo reconectar después de {max_retries} intentos")
        return False

    def get_db_info(self):
        """
        Obtiene información de la conexión a la base de datos.
        
        Returns:
            dict: Información de la BD
        """
        try:
            with self.db.engine.connect() as conn:
                result = conn.execute("SELECT version()")
                version = result.fetchone()[0]
                
                return {
                    'status': 'connected',
                    'version': version.split(',')[0],
                    'engine': 'PostgreSQL'
                }
        except Exception as e:
            return {
                'status': 'disconnected',
                'error': str(e)
            }