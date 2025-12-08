# -*- coding: utf-8 -*-
"""
utils.py - VERSIÓN 2.5.0 (CON PASSWORD RESET)
Funciones auxiliares: MFA, validaciones, renderizado, password reset

CAMBIOS v2.5.0:
1. ✅ Decorador @requiere_mfa (flujo correcto sin bucles)
2. ✅ renderizar_vista_protegida simplificado
3. ✅ 🆕 Envío de email para recuperación de contraseña
4. ✅ 🆕 Correos unificados con mismo diseño
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
# PLANTILLA HTML UNIFICADA
# =====================

def _obtener_html_email_peaksport(primer_nombre, contenido_principal, tipo=""):
    """
    Genera HTML unificado para todos los correos de PeakSport.
    
    Args:
        primer_nombre (str): Primer nombre del usuario
        contenido_principal (str): HTML del contenido específico
        tipo (str): "mfa" o "reset" (para logging)
    
    Retorna: HTML completo para el email
    """
    # Determinar colores según tipo de email
    if tipo == "reset":
        bg_body = "#ffffff"
        bg_container = "#ffffff"
        border_color = "rgba(220, 38, 38, 0.15)"
        text_primary = "#000000"
        text_secondary = "#1f2937"
        text_tertiary = "#374151"
        instruction_color = "#1f2937"
        footer_color = "#374151"
    else:
        bg_body = "#0f172a"
        bg_container = "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)"
        border_color = "rgba(220, 38, 38, 0.2)"
        text_primary = "#e5e7eb"
        text_secondary = "#d1d5db"
        text_tertiary = "#9ca3af"
        instruction_color = "#e5e7eb"
        footer_color = "#9ca3af"
    
    html_body = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Seguridad - PeakSport</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Poppins', sans-serif;
                background-color: {bg_body};
                margin: 0;
                padding: 0;
            }}
            
            .email-container {{
                max-width: 600px;
                margin: 20px auto;
                background: {bg_container};
                border-radius: 20px;
                overflow: hidden;
                border: 1px solid {border_color};
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }}
            
            .gradient-header {{
                background: linear-gradient(135deg, #dc2626 0%, #000000 100%);
                padding: 40px 30px;
                text-align: center;
            }}
            
            .header-text h1 {{
                font-size: 32px;
                font-weight: 800;
                color: white;
                margin: 0;
            }}
            
            .header-text p {{
                font-size: 12px;
                color: #e5e7eb;
                margin-top: 8px;
            }}
            
            .security-badge {{
                background-color: rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 12px;
                margin-top: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                color: white;
                font-size: 14px;
                font-weight: 600;
            }}
            
            .email-body {{
                padding: 40px 30px;
            }}
            
            .greeting h2 {{
                font-size: 24px;
                font-weight: 700;
                color: {text_primary};
                margin-bottom: 16px;
            }}
            
            .greeting p {{
                font-size: 16px;
                color: {text_secondary};
                line-height: 1.6;
                margin-bottom: 24px;
            }}
            
            .security-icon {{
                display: flex;
                justify-content: center;
                margin-bottom: 24px;
            }}
            
            .icon-circle {{
                width: 80px;
                height: 80px;
                background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
                font-size: 40px;
            }}
            
            .instruction {{
                text-align: center;
                font-size: 16px;
                color: {instruction_color};
                margin-bottom: 24px;
                font-weight: 600;
            }}
            
            .code-box {{
                background: rgba(220, 38, 38, 0.1);
                border: 2px solid rgba(220, 38, 38, 0.3);
                border-radius: 12px;
                padding: 30px;
                margin: 30px 0;
                text-align: center;
            }}
            
            .code-text {{
                font-size: 42px;
                font-weight: 800;
                color: #dc2626;
                letter-spacing: 8px;
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            }}
            
            .code-expiry {{
                color: {text_tertiary};
                font-weight: 600;
                margin-top: 12px;
                font-size: 14px;
            }}
            
            .button-container {{
                text-align: center;
                margin: 30px 0;
            }}
            
            .button {{
                background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
                color: #ffffff !important;
                padding: 14px 32px;
                border-radius: 10px;
                text-decoration: none;
                font-weight: bold;
                display: inline-block;
                transition: transform 0.3s;
                font-size: 16px;
            }}
            
            .button:hover {{
                transform: scale(1.05);
            }}
            
            .link-copy {{
                background: rgba(0, 0, 0, 0.1);
                padding: 12px;
                border-radius: 8px;
                word-break: break-all;
                color: #dc2626;
                font-family: monospace;
                font-size: 11px;
                margin-top: 12px;
                line-height: 1.4;
                border: 1px solid rgba(220, 38, 38, 0.2);
            }}
            
            .info-box {{
                background: rgba(220, 38, 38, 0.08);
                border-left: 4px solid #dc2626;
                border-radius: 0 8px 8px 0;
                padding: 16px;
                margin: 24px 0;
            }}
            
            .info-box p {{
                font-size: 14px;
                color: {text_primary};
                font-weight: 600;
                margin-bottom: 8px;
            }}
            
            .info-box ul {{
                list-style: none;
                font-size: 14px;
                color: {text_secondary};
            }}
            
            .info-box li {{
                margin-bottom: 6px;
                line-height: 1.5;
            }}
            
            .divider {{
                border-top: 1px solid rgba(220, 38, 38, 0.2);
                margin: 24px 0;
            }}
            
            .email-footer {{
                text-align: center;
                color: {footer_color};
                font-size: 14px;
            }}
            
            .footer-brand {{
                color: {text_primary};
                font-weight: 600;
            }}
            
            .email-bottom {{
                background: linear-gradient(to right, #1a1f2e, #0f172a);
                padding: 20px 30px;
                text-align: center;
                border-top: 1px solid rgba(220, 38, 38, 0.1);
            }}
            
            .email-bottom p {{
                font-size: 12px;
                color: #6b7280;
                margin: 0;
            }}
        </style>
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
                {contenido_principal}
                
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
    
    return html_body


# =====================
# FUNCIONES DE CORREO - MFA
# =====================

def enviar_codigo_verificacion(destinatario, codigo, nombre_usuario="Usuario"):
    """
    Envía un código de verificación al correo del usuario con diseño profesional.
    
    Args:
        destinatario (str): Correo electrónico del usuario.
        codigo (str): Código de verificación MFA (6 dígitos).
        nombre_usuario (str): Nombre completo del usuario.
    """
    
    primer_nombre = (nombre_usuario.split()[0] if nombre_usuario else "Usuario").capitalize()
    
    # Contenido específico para MFA
    contenido_mfa = f"""
    <div class="greeting">
        <h2>Hola {primer_nombre},</h2>
        <p>Recibimos una solicitud para acceder a tu cuenta de <strong>PeakSport</strong>.</p>
    </div>
    
    <div class="security-icon">
        <div class="icon-circle">🔐</div>
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
    """
    
    html_body = _obtener_html_email_peaksport(primer_nombre, contenido_mfa, tipo="mfa")
    
    try:
        asunto = "🔐 Verificación de acceso - PeakSport"
        
        mensaje = Message(
            subject=asunto,
            recipients=[destinatario],
            html=html_body
        )
        mail.send(mensaje)
        log_success(f"✅ Código MFA enviado a {destinatario} ({primer_nombre})")
        
    except Exception as e:
        log_error(f"❌ Error enviando código MFA a {destinatario}: {str(e)}")
        raise


# =====================
# FUNCIONES DE CORREO - PASSWORD RESET
# =====================

def enviar_email_recuperacion_contraseña(destinatario, nombre_usuario, enlace_reset):
    """
    Envía email de recuperación de contraseña
    
    Args:
        destinatario (str): Email del usuario
        nombre_usuario (str): Nombre completo del usuario
        enlace_reset (str): Enlace para resetear contraseña (URL completa)
    
    Retorna: True si se envió correctamente, False si hay error
    """
    try:
        primer_nombre = (nombre_usuario.split()[0] if nombre_usuario else "Usuario").capitalize()
        
        # Contenido específico para Password Reset
        contenido_reset = f"""
        <div class="greeting">
            <h2>Recupera tu contraseña</h2>
            <p>Recibimos una solicitud para restablecer tu contraseña en <strong>PeakSport</strong>.</p>
        </div>
        
        <div class="security-icon">
            <div class="icon-circle">🔑</div>
        </div>
        
        <p class="instruction">Haz clic en el botón de abajo para crear una nueva contraseña:</p>
        
        <div class="button-container">
            <a href="{enlace_reset}" class="button">Restablecer contraseña</a>
        </div>
        
        <p style="text-align: center; color: #888888; font-size: 12px; margin-top: 16px;">
            O copia este enlace:<br>
            <span class="link-copy">{enlace_reset}</span>
        </p>
        
        <div class="info-box">
            <p>⏱️ Importante:</p>
            <ul>
                <li>• Este enlace expira en <strong>1 hora</strong></li>
                <li>• Si no solicitaste cambiar tu contraseña, ignora este correo</li>
                <li>• Tu contraseña no será modificada hasta que confirmes en el enlace</li>
            </ul>
        </div>
        """
        
        html_body = _obtener_html_email_peaksport(primer_nombre, contenido_reset, tipo="reset")
        
        asunto = "🔐 Recupera tu contraseña en PeakSport"
        
        mensaje = Message(
            subject=asunto,
            recipients=[destinatario],
            html=html_body
        )
        mail.send(mensaje)
        log_success(f"✅ Email de recuperación enviado a {destinatario}")
        return True
        
    except Exception as e:
        log_error(f"❌ Error enviando email de recuperación a {destinatario}: {str(e)}")
        return False


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