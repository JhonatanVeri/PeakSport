# Modelo_de_Datos_PostgreSQL_y_CRUD/associations.py
# -*- coding: utf-8 -*-
from Modelo_de_Datos_PostgreSQL_y_CRUD.conexion_postgres import db

producto_categorias = db.Table(
    'producto_categorias',
    db.Column('producto_id', db.BigInteger,
              db.ForeignKey('productos.id', ondelete='CASCADE'),
              primary_key=True),
    db.Column('categoria_id', db.BigInteger,
              db.ForeignKey('categorias.id', ondelete='CASCADE'),
              primary_key=True)
)
