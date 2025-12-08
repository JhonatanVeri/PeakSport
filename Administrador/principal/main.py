# -*- coding: utf-8 -*-
"""
Archivo: Administrador/principal/__init__.py
Blueprint del módulo de Administración Principal
"""

from flask import Blueprint
from Administrador.principal.controlador import registrar_rutas

# Crear el Blueprint con la configuración correcta
bp_administrador_principal = Blueprint(
    "administrador_principal",
    __name__,
    template_folder="templates",      # Carpeta de templates: Administrador/principal/templates/
    static_folder="static",           # Carpeta de statics: Administrador/principal/static/
    static_url_path="/administrador/principal/static",  # URL para los statics
    url_prefix="/administrador/principal"   # Prefijo de URL para todas las rutas
)

# Registrar todas las rutas desde el controlador
registrar_rutas(bp_administrador_principal)