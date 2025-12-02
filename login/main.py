
from flask import Blueprint
from login.controlador import registrar_rutas
 
bp_login = Blueprint(
    'login',
    __name__,
    template_folder='templates',
    static_folder='static'
)
registrar_rutas(bp_login)
 