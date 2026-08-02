# -*- coding: utf-8 -*-
"""
Seguridad/mfa.py - Blueprint MFA CORREGIDO v2.3.0
Autenticación multifactor obligatoria.
FIX: Persistencia de sesión después de verificar MFA
"""

from flask import Blueprint, render_template, session, request, redirect, url_for, flash
import random
import datetime
from collections import defaultdict

from utils import enviar_codigo_verificacion
from Log_PeakSport import log_info, log_warning, log_error, log_critical, log_success


# =========================
# RATE LIMITING
# =========================
INTENTOS_MFA = defaultdict(lambda: {"count": 0, "timestamp": None})
MAX_INTENTOS = 5
TIMEOUT_INTENTOS = 300  # 5 minutos


def _verificar_rate_limit(identifier: str) -> tuple[bool, str]:
    """Verifica si el usuario ha excedido el límite de intentos"""
    ahora = datetime.datetime.now()
    data = INTENTOS_MFA[identifier]
    
    # Reset si pasó el timeout
    if data["timestamp"] and (ahora - data["timestamp"]).seconds > TIMEOUT_INTENTOS:
        data["count"] = 0
        data["timestamp"] = None
    
    if data["count"] >= MAX_INTENTOS:
        tiempo_restante = TIMEOUT_INTENTOS - (ahora - data["timestamp"]).seconds
        return False, f"Demasiados intentos. Intenta en {tiempo_restante}s"
    
    data["count"] += 1
    data["timestamp"] = ahora
    return True, ""


# =========================
# Blueprint
# =========================
bp_mfa = Blueprint(
    "mfa",
    __name__,
    template_folder="templates",
    static_folder="static"
)


@bp_mfa.route("/verificar-codigo", methods=["GET", "POST"])
def verificar_codigo():
    """
    GET: Genera código y envía por correo
    POST: Valida código y marca MFA como verificado
    """
    
    # ========== VALIDAR SESIÓN EXISTENTE ==========
    usuario_correo = session.get("usuario_correo")
    usuario_nombre = session.get("usuario_nombre")
    usuario_id = session.get("usuario_id")
    usuario_rol = session.get("usuario_rol")
    
    log_info(f"[MFA] verificar_codigo método={request.method}")
    log_info(f"[MFA] Session state: correo={usuario_correo}, id={usuario_id}, rol={usuario_rol}")
    log_info(f"[MFA] logged_in={session.get('logged_in')}, mfa_verificado={session.get('mfa_verificado')}")
    
    if not usuario_correo or not usuario_id:
        log_warning("[MFA] ❌ Acceso sin sesión válida (correo o id faltante)")
        flash("❌ Sesión inválida. Por favor, inicia sesión nuevamente.", "alert")
        return redirect(url_for("login.vista_pantalla_login"))
    
    if not session.get("logged_in"):
        log_warning(f"[MFA] ❌ logged_in=False para {usuario_correo}")
        flash("❌ Sesión no autenticada. Inicia sesión nuevamente.", "alert")
        return redirect(url_for("login.vista_pantalla_login"))


    # ========== POST: VALIDAR CÓDIGO INGRESADO ==========
    if request.method == "POST":
        codigo_ingresado = request.form.get("codigo", "").strip()
        codigo_esperado = session.get("codigo_mfa")
        vencimiento = session.get("mfa_expira")
        
        log_info(f"[MFA] 🔐 POST - Validando código para {usuario_correo}")
        
        # Rate limiting
        ok_rate, msg_rate = _verificar_rate_limit(str(usuario_id))
        if not ok_rate:
            log_warning(f"[MFA] 🚫 Rate limit excedido para {usuario_correo}: {msg_rate}")
            flash(f"❌ {msg_rate}", "alert")
            return render_template("verificar_codigo.html")
        
        # Validación de formato
        if not codigo_ingresado or len(codigo_ingresado) != 6 or not codigo_ingresado.isdigit():
            log_warning(f"[MFA] ❌ Código inválido (formato) para {usuario_correo}")
            flash("❌ Código debe ser de 6 dígitos numéricos", "alert")
            return render_template("verificar_codigo.html")
        
        # Verificar código
        if codigo_ingresado != codigo_esperado:
            log_warning(f"[MFA] ❌ Código incorrecto para {usuario_correo}")
            flash("❌ Código incorrecto", "alert")
            return render_template("verificar_codigo.html")
        
        # Verificar expiración
        ahora = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        
        if not vencimiento or ahora >= vencimiento:
            log_warning(f"[MFA] ⏰ Código expirado para {usuario_correo}")
            flash("❌ Código expirado. Por favor, solicita uno nuevo", "alert")
            session.pop("codigo_mfa", None)
            session.pop("mfa_expira", None)
            session.modified = True
            return redirect(url_for("mfa.verificar_codigo"))
        
        # ✅ ============ CÓDIGO VÁLIDO ============
        log_success(f"[MFA] ✅ Código VÁLIDO para {usuario_correo}")
        
        # ✅ MARCAR MFA COMO VERIFICADO
        session['mfa_verificado'] = True
        
        # ✅ LIMPIAR DATOS TEMPORALES DE MFA
        session.pop("codigo_mfa", None)
        session.pop("mfa_expira", None)
        
        # ✅ FORZAR GUARDADO DE SESIÓN
        session.permanent = True  # Asegurar que la sesión persista
        session.modified = True
        
        # Limpiar rate limiting
        INTENTOS_MFA.pop(str(usuario_id), None)
        
        log_success(f"✅ [MFA] Usuario {usuario_correo} verificado completamente")
        log_info(f"[MFA] Estado final: logged_in={session.get('logged_in')}, mfa_verificado={session.get('mfa_verificado')}")
        
        flash("✅ Verificación exitosa. ¡Bienvenido!", "success")
        
        # ========== REDIRECCIÓN INTELIGENTE ==========
        destino = session.pop("destino_post_mfa", None)
        
        if destino and isinstance(destino, dict):
            ruta = destino.get("ruta", "/")
            params = destino.get("params", {})
            
            if params:
                query_string = "&".join([f"{k}={v}" for k, v in params.items()])
                url_destino = f"{ruta}?{query_string}"
            else:
                url_destino = ruta
                
            log_info(f"[MFA] 🎯 Redirigiendo a destino guardado: {url_destino}")
            return redirect(url_destino)
        
        # Fallback: dashboard según rol
        log_info(f"[MFA] 🏠 Redirigiendo a dashboard (rol={usuario_rol})")
        
        if usuario_rol == "Administrador":
            return redirect(url_for("administrador_principal.vista_listado_productos"))
        else:
            return redirect(url_for("cliente_principal.vista_cliente_principal"))


    # ========== GET: GENERAR Y ENVIAR CÓDIGO ==========
    log_info(f"[MFA] 📧 GET - Generando código para {usuario_correo}")
    
    # Generar código aleatorio
    codigo = f"{random.randint(100000, 999999)}"
    
    # Calcular vencimiento (5 minutos)
    ahora = datetime.datetime.now(datetime.timezone.utc)
    vencimiento = (ahora + datetime.timedelta(minutes=5)).replace(tzinfo=None)
    
    # Guardar en sesión
    session["codigo_mfa"] = codigo
    session["mfa_expira"] = vencimiento
    session.modified = True
    
    log_info(f"[MFA] Código generado para {usuario_correo}, vence: {vencimiento}")
    
    try:
        # Enviar correo
        enviar_codigo_verificacion(usuario_correo, codigo, usuario_nombre)
        log_success(f"📧 [MFA] Código enviado exitosamente a {usuario_correo}")
    except Exception as e:
        log_error(f"❌ [MFA] Error enviando correo a {usuario_correo}: {e}")
        flash("⚠️ Error enviando código. Por favor, intenta nuevamente.", "alert")
        return redirect(url_for("login.vista_pantalla_login"))
    
    return render_template("verificar_codigo.html")


@bp_mfa.route("/acceso-no-autorizado", methods=["GET"])
def acceso_no_autorizado():
    """Página cuando acceso es denegado"""
    return render_template("acceso_no_autorizado.html"), 403