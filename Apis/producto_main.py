from flask import Blueprint
from Apis.producto_controlador import registrar_rutas

bp_productos = Blueprint(
    'productos', 
    __name__
    )

registrar_rutas(bp_productos)