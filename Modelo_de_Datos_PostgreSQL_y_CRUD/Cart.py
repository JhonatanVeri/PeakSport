# Modelo_de_Datos_PostgreSQL_y_CRUD/Cart.py
# -- coding: utf-8 --
"""
Modelo y CRUD para el carrito de compras
Soporta carritos para usuarios autenticados y sesiones temporales
"""

from typing import Optional, List, Dict, Any
from sqlalchemy import CheckConstraint, func
from sqlalchemy.exc import SQLAlchemyError

from Modelo_de_Datos_PostgreSQL_y_CRUD.conexion_postgres import db
from Log_PeakSport import log_info, log_error, log_warning


class Cart(db.Model):
    """
    Carrito de compras principal.
    Puede estar asociado a un usuario (persistente) o a una sesión (temporal)
    """
    __tablename__ = 'carts'

    id = db.Column(db.BigInteger, primary_key=True)
    usuario_id = db.Column(db.BigInteger, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=True, index=True)
    session_id = db.Column(db.String(255), nullable=True, index=True)
    activo = db.Column(db.Boolean, nullable=False, server_default=db.text("TRUE"))
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relaciones
    usuario = db.relationship('Usuario', backref=db.backref('carts', lazy='dynamic'))
    # ✅ CAMBIADO: lazy='select' en lugar de lazy='dynamic'
    items = db.relationship('CartItem', back_populates='cart', cascade='all, delete-orphan', lazy='select')

    def __repr__(self):
        return f"<Cart {self.id} usuario={self.usuario_id} session={self.session_id}>"

    def to_dict(self, include_items=False):
        """Serializa el carrito a diccionario"""
        data = {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'session_id': self.session_id,
            'activo': self.activo,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_items:
            # ✅ CORREGIDO: Acceso directo sin .all()
            items_list = list(self.items)
            data['items'] = [item.to_dict() for item in items_list]
            data['total_items'] = sum(item.cantidad for item in items_list)
            data['subtotal'] = sum(item.cantidad * item.precio_unitario for item in items_list)
        
        return data


class CartItem(db.Model):
    """
    Item individual dentro de un carrito.
    Almacena el precio al momento de agregar para mantener histórico
    """
    __tablename__ = 'cart_items'

    id = db.Column(db.BigInteger, primary_key=True)
    cart_id = db.Column(db.BigInteger, db.ForeignKey('carts.id', ondelete='CASCADE'), nullable=False, index=True)
    producto_id = db.Column(db.BigInteger, db.ForeignKey('productos.id', ondelete='CASCADE'), nullable=False, index=True)
    cantidad = db.Column(db.Integer, nullable=False, server_default='1')
    precio_unitario = db.Column(db.BigInteger, nullable=False)  # Precio en centavos al agregar
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    __table_args__ = (
        CheckConstraint("cantidad > 0", name="chk_cantidad_positiva"),
        CheckConstraint("precio_unitario >= 0", name="chk_precio_unitario_no_negativo"),
    )

    # Relaciones
    cart = db.relationship('Cart', back_populates='items')
    producto = db.relationship('Producto', backref=db.backref('cart_items', lazy='dynamic'))

    def __repr__(self):
        return f"<CartItem {self.id} cart={self.cart_id} producto={self.producto_id} cantidad={self.cantidad}>"

    def to_dict(self):
        """Serializa el item a diccionario con información del producto"""
        data = {
            'id': self.id,
            'cart_id': self.cart_id,
            'producto_id': self.producto_id,
            'cantidad': self.cantidad,
            'precio_unitario': self.precio_unitario / 100,  # Convertir a decimal
            'subtotal': (self.cantidad * self.precio_unitario) / 100,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        # Incluir información del producto si está disponible
        if self.producto:
            data['producto'] = {
                'id': self.producto.id,
                'nombre': self.producto.nombre,
                'slug': self.producto.slug,
                'descripcion': self.producto.descripcion,
                'precio_actual': self.producto.precio_centavos / 100,
                'stock': self.producto.stock,
                'activo': self.producto.activo,
                'moneda': self.producto.moneda,
            }
            
            # ✅ CORREGIDO: Acceso correcto a imagenes
            imagenes_list = list(self.producto.imagenes) if hasattr(self.producto, 'imagenes') else []
            portada = next((img for img in imagenes_list if img.es_portada), None)
            if portada:
                data['producto']['imagen'] = portada.to_dict()
            elif imagenes_list:
                data['producto']['imagen'] = imagenes_list[0].to_dict()
        
        return data


# ===================== CRUD =====================

def obtener_o_crear_carrito(usuario_id: Optional[int] = None, session_id: Optional[str] = None) -> Optional[Cart]:
    """
    Obtiene el carrito activo del usuario o sesión, o crea uno nuevo si no existe
    
    Args:
        usuario_id: ID del usuario autenticado (opcional)
        session_id: ID de sesión para usuarios no autenticados (opcional)
    
    Returns:
        Cart o None si hay error
    """
    try:
        if not usuario_id and not session_id:
            log_warning("obtener_o_crear_carrito: se requiere usuario_id o session_id")
            return None

        # Buscar carrito existente
        query = Cart.query.filter_by(activo=True)
        
        if usuario_id:
            query = query.filter_by(usuario_id=usuario_id)
        else:
            query = query.filter_by(session_id=session_id)
        
        cart = query.first()
        
        if cart:
            log_info(f"Carrito encontrado: {cart.id}")
            return cart
        
        # Crear nuevo carrito
        cart = Cart(usuario_id=usuario_id, session_id=session_id, activo=True)
        db.session.add(cart)
        db.session.commit()
        
        log_info(f"Carrito creado: {cart.id} (usuario={usuario_id}, session={session_id})")
        return cart
        
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error en obtener_o_crear_carrito: {str(e)}")
        return None


def agregar_item_carrito(
    cart_id: int,
    producto_id: int,
    cantidad: int = 1
) -> Optional[CartItem]:
    """
    Agrega un producto al carrito o actualiza la cantidad si ya existe
    
    Args:
        cart_id: ID del carrito
        producto_id: ID del producto a agregar
        cantidad: Cantidad a agregar (default: 1)
    
    Returns:
        CartItem o None si hay error
    """
    try:
        from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import Producto
        
        # Validar carrito
        cart = db.session.get(Cart, cart_id)
        if not cart:
            log_warning(f"agregar_item_carrito: carrito no encontrado {cart_id}")
            return None
        
        # Validar producto
        producto = db.session.get(Producto, producto_id)
        if not producto:
            log_warning(f"agregar_item_carrito: producto no encontrado {producto_id}")
            return None
        
        if not producto.activo:
            log_warning(f"agregar_item_carrito: producto inactivo {producto_id}")
            return None
        
        # Validar stock
        if producto.stock < cantidad:
            log_warning(f"agregar_item_carrito: stock insuficiente. Disponible: {producto.stock}, solicitado: {cantidad}")
            return None
        
        # Verificar si el item ya existe en el carrito
        existing_item = CartItem.query.filter_by(
            cart_id=cart_id,
            producto_id=producto_id
        ).first()
        
        if existing_item:
            # Actualizar cantidad
            nueva_cantidad = existing_item.cantidad + cantidad
            
            if producto.stock < nueva_cantidad:
                log_warning(f"agregar_item_carrito: stock insuficiente para cantidad total")
                return None
            
            existing_item.cantidad = nueva_cantidad
            db.session.commit()
            log_info(f"Item actualizado en carrito: producto={producto_id}, nueva cantidad={nueva_cantidad}")
            return existing_item
        
        # Crear nuevo item
        item = CartItem(
            cart_id=cart_id,
            producto_id=producto_id,
            cantidad=cantidad,
            precio_unitario=producto.precio_centavos
        )
        
        db.session.add(item)
        db.session.commit()
        
        log_info(f"Item agregado al carrito: {item.id} (producto={producto_id}, cantidad={cantidad})")
        return item
        
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error en agregar_item_carrito: {str(e)}")
        return None


def actualizar_cantidad_item(item_id: int, cantidad: int) -> Optional[CartItem]:
    """
    Actualiza la cantidad de un item en el carrito
    
    Args:
        item_id: ID del item
        cantidad: Nueva cantidad
    
    Returns:
        CartItem actualizado o None si hay error
    """
    try:
        item = db.session.get(CartItem, item_id)
        if not item:
            log_warning(f"actualizar_cantidad_item: item no encontrado {item_id}")
            return None
        
        if cantidad <= 0:
            log_warning(f"actualizar_cantidad_item: cantidad inválida {cantidad}")
            return None
        
        # Validar stock
        if item.producto.stock < cantidad:
            log_warning(f"actualizar_cantidad_item: stock insuficiente. Disponible: {item.producto.stock}")
            return None
        
        item.cantidad = cantidad
        db.session.commit()
        
        log_info(f"Cantidad actualizada: item={item_id}, nueva cantidad={cantidad}")
        return item
        
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error en actualizar_cantidad_item: {str(e)}")
        return None


def eliminar_item_carrito(item_id: int) -> bool:
    """
    Elimina un item del carrito
    
    Args:
        item_id: ID del item a eliminar
    
    Returns:
        True si se eliminó correctamente, False si hubo error
    """
    try:
        item = db.session.get(CartItem, item_id)
        if not item:
            log_warning(f"eliminar_item_carrito: item no encontrado {item_id}")
            return False
        
        db.session.delete(item)
        db.session.commit()
        
        log_info(f"Item eliminado del carrito: {item_id}")
        return True
        
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error en eliminar_item_carrito: {str(e)}")
        return False


def vaciar_carrito(cart_id: int) -> bool:
    """
    Elimina todos los items de un carrito
    
    Args:
        cart_id: ID del carrito
    
    Returns:
        True si se vació correctamente, False si hubo error
    """
    try:
        cart = db.session.get(Cart, cart_id)
        if not cart:
            log_warning(f"vaciar_carrito: carrito no encontrado {cart_id}")
            return False
        
        CartItem.query.filter_by(cart_id=cart_id).delete()
        db.session.commit()
        
        log_info(f"Carrito vaciado: {cart_id}")
        return True
        
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error en vaciar_carrito: {str(e)}")
        return False


def migrar_carrito_sesion_a_usuario(session_id: str, usuario_id: int) -> bool:
    """
    Migra el carrito de una sesión temporal a un usuario autenticado
    Útil cuando un usuario inicia sesión después de agregar productos
    
    Args:
        session_id: ID de la sesión
        usuario_id: ID del usuario autenticado
    
    Returns:
        True si se migró correctamente
    """
    try:
        # Buscar carrito de sesión
        session_cart = Cart.query.filter_by(session_id=session_id, activo=True).first()
        if not session_cart or len(session_cart.items) == 0:
            log_info(f"No hay carrito de sesión para migrar: {session_id}")
            return True
        
        # Buscar o crear carrito de usuario
        user_cart = Cart.query.filter_by(usuario_id=usuario_id, activo=True).first()
        if not user_cart:
            user_cart = Cart(usuario_id=usuario_id, activo=True)
            db.session.add(user_cart)
            db.session.flush()
        
        # Migrar items
        for session_item in session_cart.items:
            # Verificar si el producto ya existe en el carrito del usuario
            existing_item = CartItem.query.filter_by(
                cart_id=user_cart.id,
                producto_id=session_item.producto_id
            ).first()
            
            if existing_item:
                # Sumar cantidades
                existing_item.cantidad += session_item.cantidad
            else:
                # Transferir item
                session_item.cart_id = user_cart.id
        
        # Marcar carrito de sesión como inactivo
        session_cart.activo = False
        
        db.session.commit()
        log_info(f"Carrito migrado de sesión {session_id} a usuario {usuario_id}")
        return True
        
    except SQLAlchemyError as e:
        db.session.rollback()
        log_error(f"Error en migrar_carrito_sesion_a_usuario: {str(e)}")
        return False


def calcular_totales_carrito(cart_id: int) -> Dict[str, Any]:
    """
    Calcula todos los totales del carrito
    
    Args:
        cart_id: ID del carrito
    
    Returns:
        Diccionario con subtotal, impuestos, envío y total
    """
    try:
        cart = db.session.get(Cart, cart_id)
        if not cart:
            return {
                'subtotal': 0,
                'impuestos': 0,
                'envio': 0,
                'total': 0,
                'total_items': 0,
                'envio_gratis': False
            }
        
        # ✅ CORREGIDO: Acceso directo sin .all()
        items_list = list(cart.items)
        subtotal = sum(item.cantidad * item.precio_unitario for item in items_list)
        total_items = sum(item.cantidad for item in items_list)
        
        # Impuestos (10%)
        impuestos = subtotal * 0.1
        
        # Envío (gratis si supera 100000 centavos = $1000)
        envio = 0 if subtotal >= 100000 else 1500  # $15 de envío
        
        total = subtotal + impuestos + envio
        
        return {
            'subtotal': subtotal / 100,  # Convertir a decimal
            'impuestos': impuestos / 100,
            'envio': envio / 100,
            'total': total / 100,
            'total_items': total_items,
            'envio_gratis': subtotal >= 100000
        }
        
    except Exception as e:
        log_error(f"Error en calcular_totales_carrito: {str(e)}")
        return {
            'subtotal': 0,
            'impuestos': 0,
            'envio': 0,
            'total': 0,
            'total_items': 0,
            'envio_gratis': False
        }