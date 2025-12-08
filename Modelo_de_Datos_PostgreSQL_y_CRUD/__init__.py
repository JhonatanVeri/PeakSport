# -*- coding: utf-8 -*-
"""
Inicialización del paquete de modelos
Importa todos los modelos para que estén disponibles
VERSIÓN 2.5.1 - Con Password Reset
"""
from Modelo_de_Datos_PostgreSQL_y_CRUD.conexion_postgres import db

# Importar modelos existentes
from Modelo_de_Datos_PostgreSQL_y_CRUD.Usuarios import Usuario
from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import Producto
from Modelo_de_Datos_PostgreSQL_y_CRUD.Producto_Imagenes import ProductoImagen
from Modelo_de_Datos_PostgreSQL_y_CRUD.Categorias import Categoria
from Modelo_de_Datos_PostgreSQL_y_CRUD.Resenas import Resena

# 🆕 NUEVO: Importar modelos del carrito
from Modelo_de_Datos_PostgreSQL_y_CRUD.Cart import Cart, CartItem

# 🆕 NUEVO: Importar modelo de password reset
# ✅ CORREGIDO: Usando "passwordreset" (sin guion bajo)
from Modelo_de_Datos_PostgreSQL_y_CRUD.password_reset import PasswordResetToken

# Exportar todos los modelos
__all__ = [
    'db',
    'Usuario',
    'Producto',
    'ProductoImagen',
    'Categoria',
    'Resena',
    'Cart',
    'CartItem',
    'PasswordResetToken'  # 🆕 AGREGADO
]