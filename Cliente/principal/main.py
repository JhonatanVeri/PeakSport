# -*- coding: utf-8 -*-
"""
Blueprint de Cliente Principal
Maneja la vista principal para clientes autenticados.
"""

from flask import Blueprint
from Cliente.principal.controlador import registrar_rutas

# ✅ NO necesita template_folder porque usa el template principal de la app
bp_cliente_principal = Blueprint(
    'cliente_principal',
    __name__
)

# Registrar las rutas del blueprint
registrar_rutas(bp_cliente_principal)