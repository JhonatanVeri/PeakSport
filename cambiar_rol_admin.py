#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para cambiar el rol de un usuario a Administrador
"""

from app import app
from Modelo_de_Datos_PostgreSQL_y_CRUD.Usuarios import obtener_usuario_por_correo, actualizar_usuario

def cambiar_a_administrador(correo: str):
    """
    Cambia el rol de un usuario a Administrador basado en su correo
    """
    with app.app_context():
        print(f"\n🔍 Buscando usuario con correo: {correo}")
        
        # Obtener el usuario
        usuario = obtener_usuario_por_correo(correo)
        
        if not usuario:
            print(f"❌ No se encontró usuario con correo: {correo}")
            return False
        
        print(f"✅ Usuario encontrado:")
        print(f"   - Correo: {usuario.correo}")
        print(f"   - Nombre: {usuario.nombre_completo}")
        print(f"   - Rol actual: {usuario.rol}")
        
        # Cambiar el rol a Administrador
        if usuario.rol == 'Administrador':
            print(f"⚠️  El usuario ya es Administrador")
            return True
        
        print(f"\n🔄 Cambiando rol a Administrador...")
        usuario_actualizado = actualizar_usuario(usuario.id, rol='Administrador')
        
        if usuario_actualizado:
            print(f"✅ Rol actualizado exitosamente!")
            print(f"   - Nuevo rol: {usuario_actualizado.rol}")
            return True
        else:
            print(f"❌ Error al actualizar el rol")
            return False


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("\n📋 USO:")
        print("   python cambiar_rol_admin.py <correo@ejemplo.com>")
        print("\n📝 EJEMPLO:")
        print("   python cambiar_rol_admin.py usuario@gmail.com")
        print("\n")
        sys.exit(1)
    
    correo = sys.argv[1]
    cambiar_a_administrador(correo)