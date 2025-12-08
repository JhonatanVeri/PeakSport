# -*- coding: utf-8 -*-
"""
Autor: PeakSport Team
Descripción: Servicio de Email usando SendGrid
"""

from flask import render_template_string
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To
import os
from Log_PeakSport import log_info, log_error, log_critical


class EmailService:
    """
    Servicio de email con SendGrid
    Usa las variables de entorno:
    - MAIL_PASSWORD (API key de SendGrid)
    - MAIL_DEFAULT_SENDER (email de remitente)
    """

    def __init__(self):
        """Inicializa SendGrid con credenciales de variables de entorno"""
        try:
            api_key = os.environ.get('MAIL_PASSWORD')
            if not api_key:
                log_error("MAIL_PASSWORD no configurado en variables de entorno")
                self.sg = None
                return
            
            self.sg = SendGridAPIClient(api_key)
            self.from_email = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@peaksport.com')
            log_info("EmailService inicializado correctamente")
        except Exception as e:
            log_error(f"Error inicializando EmailService: {str(e)}")
            self.sg = None

    def send_password_reset_email(self, correo: str, nombre: str, reset_link: str) -> tuple:
        """
        Envía email de recuperación de contraseña
        Usa la función de utils.py para reutilizar el sistema de emails existente
        
        Args:
            correo: Email del usuario
            nombre: Nombre completo del usuario
            reset_link: Enlace para recuperar contraseña (URL completa)
        
        Retorna: (exito: bool, mensaje: str)
        """
        try:
            from utils import enviar_email_recuperacion_contraseña
            
            exito = enviar_email_recuperacion_contraseña(correo, nombre, reset_link)
            
            if exito:
                log_info(f"Email de recuperación enviado a {correo}")
                return True, "Email enviado correctamente"
            else:
                log_error(f"Error al enviar email a {correo}")
                return False, "Error al enviar email"
                
        except Exception as e:
            log_error(f"Error en send_password_reset_email: {str(e)}")
            return False, f"Error al enviar email: {str(e)}"


# ============================
# INICIALIZACIÓN GLOBAL
# ============================

# Crear instancia global para usar en toda la app
email_service = None

def init_email_service(app):
    """
    Inicializa el servicio de email con la app de Flask
    
    Args:
        app: Aplicación Flask
    
    Retorna: Instancia de EmailService
    """
    global email_service
    email_service = EmailService()
    return email_service