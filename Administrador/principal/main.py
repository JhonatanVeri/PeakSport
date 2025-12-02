# -*- coding: utf-8 -*-
from flask import Blueprint
from Administrador.principal.controlador import registrar_rutas

bp_administrador_principal = Blueprint(
    "administrador_principal",
    __name__,
    template_folder="templates",   # relativo a este paquete
    static_folder="static"         # relativo a este paquete
)

# registra TODAS las rutas sobre el blueprint
registrar_rutas(bp_administrador_principal)
