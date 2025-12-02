# -*- coding: utf-8 -*-
"""
Blueprint: cliente_principal
Pantalla principal del CLIENTE (dashboard/landing autenticada).
- GET /cliente/                 -> vista_cliente_principal (protegida por sesión, rol Cliente)
- GET /cliente/recomendados     -> JSON con productos recomendados (opcional)
- GET /cliente/home-publica     -> portada pública (sin login), reutiliza mismo template con flags
"""

from functools import wraps
from flask import render_template, session, redirect, url_for
from utils import renderizar_vista_entorno_desarrollo_y_produccion


# --- Helper opcional: proteger rutas que requieren sesión ---
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('logged_in'):
            # si no hay sesión, va al login del blueprint "login"
            return redirect(url_for('login.vista_pantalla_login'))
        return view(*args, **kwargs)
    return wrapped

def registrar_rutas(bp):
    """
    Registra las rutas del blueprint.
    Llamar desde app.py tras registrar el blueprint.
    """

    # --- Home del cliente ---
    @bp.get('/')
    def vista_cliente_principal():
        """
        Página principal reutilizable para invitados o logueados.
        - Si hay sesión, se muestra el nombre y habilitas carrito, perfil, etc.
        - Si no, se muestra CTA para iniciar sesión.
        """
        """
        logged = bool(session.get('logged_in'))
        usuario_nombre = session.get('usuario_nombre')  # puede ser None

        return render_template(
            'pagina_principal.html',   # la plantilla que ya tienes separada
            logged_in=logged,
            usuario_nombre=usuario_nombre
        )"""
        return renderizar_vista_entorno_desarrollo_y_produccion(
            'pagina_principal.html'
        )
    

    # Si quisieras una sección que SÍ exija estar logueado (opcional)
    @bp.get('/perfil')
    @login_required
    def vista_perfil():
        return render_template(
            'perfil.html',
            logged_in=True,
            usuario_nombre=session.get('usuario_nombre')
        )