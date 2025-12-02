# -*- coding: utf-8 -*-
"""
Controlador de Cliente (Principal)
Vista personalizada para clientes autenticados usando el template público.
"""

from flask import session, render_template
from utils import requiere_mfa
from Log_PeakSport import log_info, log_debug

def registrar_rutas(bp):
    """Registra las rutas del blueprint de cliente principal"""
    
    @bp.route('/home')
    @requiere_mfa
    def vista_cliente_principal():
        """
        Vista principal para clientes autenticados.
        Reutiliza el template público pero con información personalizada.
        """
        # Obtener datos de sesión
        usuario_email = session.get('usuario_email')
        usuario_nombre = session.get('usuario_nombre')
        usuario_rol = session.get('usuario_rol')
        
        # Logs de auditoría
        log_info(f'✅ [Cliente Home] Acceso exitoso para {usuario_email}')
        log_debug(f'✅ Renderizando pagina_principal.html para {usuario_email}')
        
        # ✅ Usar el template público con contexto personalizado
        # El template detecta automáticamente si hay usuario autenticado
        return render_template(
            'pagina_principal.html',
            usuario_nombre=usuario_nombre,
            usuario_email=usuario_email,
            usuario_rol=usuario_rol,
            usuario_autenticado=True,
            es_cliente=True
        )