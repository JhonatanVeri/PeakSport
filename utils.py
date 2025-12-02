# -*- coding: utf-8 -*-
"""
utils.py - VERSIÓN CORRECTA (SIN BUCLE)
Funciones auxiliares: MFA, validaciones, renderizado

CAMBIOS CRÍTICOS:
1. ✅ Decorador @requiere_mfa corregido (no redirige a MFA cuando debe ir a login)
2. ✅ renderizar_vista_protegida simplificado (no duplica lógica del decorador)
"""

from flask import render_template, request, redirect, url_for, session, flash
from flask_mail import Message
from extensiones import mail
import re
from datetime import datetime
from functools import wraps

from Log_PeakSport import log_info, log_error, log_warning, log_debug, log_success


# =====================
# DECORADOR DE MFA - CORREGIDO
# =====================
def requiere_mfa(fn):
    """
    Decorador que verifica MFA antes de permitir acceso.
    Debe usarse en TODAS las rutas protegidas.
    
    FLUJO CORRECTO:
    1. Si NO está logged_in → redirige a /login
    2. Si está logged_in pero NO mfa_verificado → redirige a /mfa/verificar-codigo
    3. Si ambos están OK → permite acceso
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # ✅ PASO 1: Verificar si está logueado
        if not session.get("logged_in"):
            log_warning(f"[MFA] Acceso rechazado: No logged_in. Redirigiendo a LOGIN")
            # Guardar destino para después
            session["destino_post_login"] = {
                "ruta": request.path,
                "params": request.args.to_dict()
            }
            session.modified = True
            # ✅ CRÍTICO: Redirigir a LOGIN, NO a MFA
            return redirect(url_for("login.vista_pantalla_login"))
        
        # ✅ PASO 2: Verificar MFA
        if not session.get("mfa_verificado"):
            log_warning(f"[MFA] MFA no verificado para {session.get('usuario_correo')}. Redirigiendo a MFA")
            # Guardar destino para después del MFA
            session["destino_post_mfa"] = {
                "ruta": request.path,
                "params": request.args.to_dict()
            }
            session.modified = True
            return redirect(url_for("mfa.verificar_codigo"))
        
        # ✅ PASO 3: Ambas validaciones pasaron
        log_debug(f"[MFA] ✅ Acceso permitido a {request.path} para {session.get('usuario_correo')}")
        return fn(*args, **kwargs)
    
    return wrapper


# =====================
# FUNCIONES DE CORREO
# =====================

def enviar_codigo_verificacion(destinatario, codigo, nombre_usuario="Usuario"):
    """
    Envía un código de verificación al correo del usuario con diseño profesional.
    
    Args:
        destinatario (str): Correo electrónico del usuario.
        codigo (str): Código de verificación MFA (6 dígitos).
        nombre_usuario (str): Nombre completo del usuario.
    """
    
    # Estilos CSS
    estilos_css = """
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
    
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    body {
        font-family: 'Poppins', sans-serif;
        background-color: #f7f7f7;
    }
    
    .email-container {
        max-width: 600px;
        margin: 40px auto;
        background-color: #ffffff;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        overflow: hidden;
    }
    
    .gradient-header {
        background: linear-gradient(135deg, #dc2626 0%, #7f1d1d 50%, #1a1a1a 100%);
        padding: 40px 30px;
        text-align: center;
    }
    
    .header-text h1 {
        font-size: 32px;
        font-weight: 700;
        color: white;
    }
    
    .header-text p {
        font-size: 12px;
        color: #d1d5db;
        margin-top: 4px;
    }
    
    .security-badge {
        background-color: rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 12px;
        margin-top: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        color: white;
    }
    
    .email-body {
        padding: 32px;
    }
    
    .greeting h2 {
        font-size: 24px;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 8px;
    }
    
    .greeting p {
        font-size: 16px;
        color: #4b5563;
        line-height: 1.6;
    }
    
    .security-icon {
        display: flex;
        justify-content: center;
        margin-bottom: 24px;
    }
    
    .icon-circle {
        width: 80px;
        height: 80px;
        background: #dc2626;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(220,38,38,0.3);
    }
    
    .lock-icon {
        font-size: 40px;
        color: white;
    }
    
    .instruction {
        text-align: center;
        font-size: 16px;
        color: #1f2937;
        margin-bottom: 16px;
        font-weight: 600;
    }
    
    .code-box {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        border: 3px dashed #dc2626;
        border-radius: 12px;
        padding: 30px;
        margin: 30px 0;
        text-align: center;
    }
    
    .code-text {
        font-size: 42px;
        font-weight: 800;
        color: #dc2626;
        letter-spacing: 8px;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    }
    
    .code-expiry {
        color: #7f1d1d;
        font-weight: 600;
        margin-top: 12px;
        font-size: 14px;
    }
    
    .info-box {
        background-color: #f9fafb;
        border-left: 4px solid #dc2626;
        border-radius: 0 8px 8px 0;
        padding: 16px;
        margin-bottom: 24px;
    }
    
    .info-box p {
        font-size: 14px;
        color: #1f2937;
        font-weight: 600;
        margin-bottom: 8px;
    }
    
    .info-box ul {
        list-style: none;
        font-size: 14px;
        color: #4b5563;
    }
    
    .info-box li {
        margin-bottom: 4px;
        line-height: 1.5;
    }
    
    .divider {
        border-top: 2px solid #e5e7eb;
        margin: 24px 0;
    }
    
    .email-footer {
        text-align: center;
    }
    
    .email-footer p {
        font-size: 14px;
        color: #6b7280;
        margin-bottom: 4px;
    }
    
    .footer-brand {
        color: #1f2937;
        font-weight: 600;
    }
    
    .email-bottom {
        background: linear-gradient(to right, #1f2937, #000000);
        padding: 16px 32px;
        text-align: center;
    }
    
    .email-bottom p {
        font-size: 12px;
        color: #9ca3af;
    }
    """
    
    # HTML
    primer_nombre = (nombre_usuario.split()[0] if nombre_usuario else "Usuario").capitalize()
    
    html_body = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verificación de Acceso - PeakSport</title>
        <style>{estilos_css}</style>
    </head>
    <body>
        <div class="email-container">
            <div class="gradient-header">
                <div class="header-text">
                    <h1>PEAKSPORT</h1>
                    <p>Excellence in Motion</p>
                </div>
                <div class="security-badge">
                    <span>🔒</span>
                    <span>Verificación de Seguridad</span>
                </div>
            </div>
            
            <div class="email-body">
                <div class="greeting">
                    <h2>Hola {primer_nombre},</h2>
                    <p>Recibimos una solicitud para acceder a tu cuenta de <strong>PeakSport</strong>.</p>
                </div>
                
                <div class="security-icon">
                    <div class="icon-circle">
                        <span class="lock-icon">🔐</span>
                    </div>
                </div>
                
                <p class="instruction">Por seguridad, verifica tu identidad ingresando el siguiente código:</p>
                
                <div class="code-box">
                    <div class="code-text">{codigo}</div>
                    <p class="code-expiry">⏱️ Este código expirará en 5 minutos</p>
                </div>
                
                <div class="info-box">
                    <p>ℹ️ Información importante:</p>
                    <ul>
                        <li>• Nunca compartas este código con nadie</li>
                        <li>• PeakSport nunca te pedirá este código por teléfono o email</li>
                        <li>• Si no realizaste esta solicitud, cambia tu contraseña inmediatamente</li>
                    </ul>
                </div>
                
                <div class="divider"></div>
                
                <div class="email-footer">
                    <p>Equipo de Seguridad<br><span class="footer-brand">PeakSport</span></p>
                </div>
            </div>
            
            <div class="email-bottom">
                <p>🔒 Este es un correo automático. Por favor no respondas a este mensaje.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        asunto = "🔐 Verificación de acceso - PeakSport"
        
        mensaje = Message(
            subject=asunto,
            recipients=[destinatario],
            html=html_body
        )
        mail.send(mensaje)
        log_success(f"✅ Código enviado a {destinatario} ({primer_nombre})")
        
    except Exception as e:
        log_error(f"❌ Error enviando correo a {destinatario}: {str(e)}")
        raise  # Re-lanzar para que MFA pueda manejarlo


# =====================
# RENDERIZADOR DE VISTAS - SIMPLIFICADO
# =====================

def renderizar_vista_protegida(
    template: str,
    correos_permitidos=None,
    mantenimiento: bool = False,
    **context
):
    """
    Renderiza vista protegida.
    
    IMPORTANTE: Esta función NO debe duplicar la lógica de @requiere_mfa
    Solo agrega datos de sesión al contexto del template.
    
    Args:
        template (str): Nombre del template
        correos_permitidos (list): Email whitelist (opcional)
        mantenimiento (bool): Muestra página de mantenimiento
        **context: Variables para el template
    """
    nombre_usuario = session.get("usuario_nombre", "Usuario")
    correo_usuario = session.get("usuario_correo", "")
    logueado = session.get("logged_in", False)
    mfa_verificado = session.get("mfa_verificado", False)

    # =====================
    # MODO MANTENIMIENTO
    # =====================
    if mantenimiento:
        if correo_usuario and correo_usuario.lower() == "admin@peaksport.com":
            log_info(f"🛠 Acceso a mantenimiento: {correo_usuario}")
        else:
            log_info(f"🚧 Modo mantenimiento. Acceso denegado: {correo_usuario}")
            return render_template("modo_mantenimiento.html"), 503

    # =====================
    # FILTRO POR CORREOS (opcional)
    # =====================
    if correos_permitidos:
        lista_normalizada = [c.lower() for c in correos_permitidos]
        if not correo_usuario or correo_usuario.lower() not in lista_normalizada:
            log_warning(f"🔒 Acceso denegado. Email no autorizado: {correo_usuario}")
            return render_template("acceso_no_autorizado.html"), 403

    # =====================
    # RENDERIZADO FINAL
    # =====================
    # Agregar datos de sesión al contexto
    context.setdefault("logged_in", logueado)
    context.setdefault("usuario_nombre", nombre_usuario)
    context.setdefault("usuario_correo", correo_usuario)
    context.setdefault("usuario_rol", session.get("usuario_rol", "Cliente"))
    context.setdefault("usuario_id", session.get("usuario_id"))
    context.setdefault("mfa_verificado", mfa_verificado)

    log_debug(f"✅ Renderizando {template} para {correo_usuario}")
    
    return render_template(template, **context)


# =====================
# ALIAS POR COMPATIBILIDAD
# =====================
renderizar_vista_entorno_desarrollo_y_produccion = renderizar_vista_protegida