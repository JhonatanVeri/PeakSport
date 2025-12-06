# -*- coding: utf-8 -*-
"""
Cliente/catalogo/controlador.py
Controlador del Catálogo - Integrado con modelos reales de PeakSport
Usa: Producto, ProductoImagen, Categoria, Resena
"""

from flask import request
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.exc import SQLAlchemyError

from Modelo_de_Datos_PostgreSQL_y_CRUD.conexion_postgres import db
from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import Producto, listar_productos
from Modelo_de_Datos_PostgreSQL_y_CRUD.Producto_Imagenes import ProductoImagen
from Modelo_de_Datos_PostgreSQL_y_CRUD.Categorias import Categoria
from Modelo_de_Datos_PostgreSQL_y_CRUD.Resenas import obtener_estadisticas_producto
from Log_PeakSport import log_info, log_error, log_warning


class CatalogoControlador:
    """
    Controlador principal del catálogo
    Usa los modelos reales de la BD: Producto, Categoria, ProductoImagen, Resena
    """
    
    def __init__(self):
        """Inicializar el controlador"""
        log_info("✅ CatalogoControlador inicializado")
    
    # ==================== PRODUCTOS ====================
    
    def obtener_todos_productos(self, 
                                page: int = 1, 
                                per_page: int = 12,
                                filtros: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Obtiene todos los productos activos con paginación
        
        Args:
            page: Número de página (default: 1)
            per_page: Productos por página (default: 12)
            filtros: Dict con filtros {'activo': True, 'q': 'búsqueda', 'categoria_id': 1}
        
        Returns:
            Dict con productos, total, página, etc.
        """
        try:
            filtros = filtros or {}
            # Por defecto solo productos activos
            if 'activo' not in filtros:
                filtros['activo'] = True
            
            productos, total = listar_productos(
                filtros=filtros,
                page=page,
                per_page=per_page
            )
            
            return {
                'success': True,
                'productos': [self._producto_a_dict(p) for p in productos],
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
        except Exception as e:
            log_error(f"Error en obtener_todos_productos: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'productos': [],
                'total': 0
            }
    
    def obtener_producto(self, producto_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene un producto específico con toda su información
        
        Args:
            producto_id: ID del producto
        
        Returns:
            Dict con datos del producto o None
        """
        try:
            producto = db.session.get(Producto, producto_id)
            if not producto:
                log_warning(f"Producto no encontrado: {producto_id}")
                return None
            
            return self._producto_a_dict(producto, incluir_completo=True)
        except Exception as e:
            log_error(f"Error en obtener_producto {producto_id}: {str(e)}")
            return None
    
    def obtener_producto_por_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un producto por su slug
        
        Args:
            slug: Slug del producto (ej: 'zapatillas-nike-deportivas')
        
        Returns:
            Dict con datos del producto o None
        """
        try:
            producto = Producto.query.filter_by(slug=slug, activo=True).first()
            if not producto:
                log_warning(f"Producto no encontrado con slug: {slug}")
                return None
            
            return self._producto_a_dict(producto, incluir_completo=True)
        except Exception as e:
            log_error(f"Error en obtener_producto_por_slug {slug}: {str(e)}")
            return None
    
    def buscar_productos(self, 
                        q: str, 
                        page: int = 1, 
                        per_page: int = 12) -> Dict[str, Any]:
        """
        Busca productos por nombre o descripción
        
        Args:
            q: Término de búsqueda
            page: Número de página
            per_page: Productos por página
        
        Returns:
            Dict con productos encontrados
        """
        try:
            if not q or len(q.strip()) < 2:
                return {'success': False, 'error': 'Búsqueda muy corta', 'productos': []}
            
            filtros = {'activo': True, 'q': q.strip()}
            return self.obtener_todos_productos(page=page, per_page=per_page, filtros=filtros)
        except Exception as e:
            log_error(f"Error en buscar_productos: {str(e)}")
            return {'success': False, 'error': str(e), 'productos': []}
    
    def obtener_productos_por_categoria(self, 
                                       categoria_id: int,
                                       page: int = 1,
                                       per_page: int = 12) -> Dict[str, Any]:
        """
        Obtiene productos de una categoría específica
        
        Args:
            categoria_id: ID de la categoría
            page: Número de página
            per_page: Productos por página
        
        Returns:
            Dict con productos de la categoría
        """
        try:
            categoria = db.session.get(Categoria, categoria_id)
            if not categoria:
                log_warning(f"Categoría no encontrada: {categoria_id}")
                return {'success': False, 'error': 'Categoría no encontrada', 'productos': []}
            
            filtros = {'activo': True, 'categoria_id': categoria_id}
            resultado = self.obtener_todos_productos(page=page, per_page=per_page, filtros=filtros)
            resultado['categoria'] = {
                'id': categoria.id,
                'nombre': categoria.nombre,
                'slug': categoria.slug,
                'descripcion': categoria.descripcion
            }
            return resultado
        except Exception as e:
            log_error(f"Error en obtener_productos_por_categoria: {str(e)}")
            return {'success': False, 'error': str(e), 'productos': []}
    
    # ==================== CATEGORÍAS ====================
    
    def obtener_categorias(self) -> List[Dict[str, Any]]:
        """
        Obtiene todas las categorías principales (sin padre)
        
        Returns:
            Lista de categorías
        """
        try:
            categorias = Categoria.query.filter_by(padre_id=None).order_by(Categoria.nombre).all()
            return [self._categoria_a_dict(c) for c in categorias]
        except Exception as e:
            log_error(f"Error en obtener_categorias: {str(e)}")
            return []
    
    def obtener_categorias_con_productos(self) -> List[Dict[str, Any]]:
        """
        Obtiene categorías con conteo de productos
        
        Returns:
            Lista de categorías con su conteo
        """
        try:
            categorias = Categoria.query.filter_by(padre_id=None).all()
            resultado = []
            
            for cat in categorias:
                resultado.append({
                    'id': cat.id,
                    'nombre': cat.nombre,
                    'slug': cat.slug,
                    'descripcion': cat.descripcion,
                    'cantidad_productos': cat.productos.count()
                })
            
            return resultado
        except Exception as e:
            log_error(f"Error en obtener_categorias_con_productos: {str(e)}")
            return []
    
    # ==================== FILTROS ====================
    
    def filtrar_productos(self) -> Dict[str, Any]:
        """
        Aplica filtros desde los query parameters
        Soporta: categoria_id, marca (si existe), precio_min, precio_max, q
        
        Returns:
            Dict con productos filtrados
        """
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 12, type=int)
            categoria_id = request.args.get('categoria_id', type=int)
            precio_min = request.args.get('precio_min', type=int)
            precio_max = request.args.get('precio_max', type=int)
            q = request.args.get('q', '').strip()
            
            filtros = {'activo': True}
            
            # Aplicar filtros
            if categoria_id:
                filtros['categoria_id'] = categoria_id
            if q:
                filtros['q'] = q
            
            # Filtro por rango de precio (en centavos)
            query = Producto.query.filter_by(activo=True)
            
            if categoria_id:
                query = query.join(Producto.categorias).filter(Categoria.id == categoria_id)
            if q:
                query = query.filter(Producto.nombre.ilike(f"%{q}%"))
            if precio_min:
                query = query.filter(Producto.precio_centavos >= precio_min * 100)
            if precio_max:
                query = query.filter(Producto.precio_centavos <= precio_max * 100)
            
            total = query.count()
            productos = (
                query.order_by(Producto.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            
            return {
                'success': True,
                'productos': [self._producto_a_dict(p) for p in productos],
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
        except Exception as e:
            log_error(f"Error en filtrar_productos: {str(e)}")
            return {'success': False, 'error': str(e), 'productos': []}
    
    def ordenar_productos(self, criterio: str) -> List[Dict[str, Any]]:
        """
        Ordena productos según criterio
        Soporta: nombre, precio_asc, precio_desc, rating, popular, recientes
        
        Args:
            criterio: Criterio de ordenamiento
        
        Returns:
            Lista de productos ordenados
        """
        try:
            query = Producto.query.filter_by(activo=True)
            
            if criterio == 'nombre':
                query = query.order_by(Producto.nombre.asc())
            elif criterio == 'precio_asc':
                query = query.order_by(Producto.precio_centavos.asc())
            elif criterio == 'precio_desc':
                query = query.order_by(Producto.precio_centavos.desc())
            elif criterio == 'rating':
                # Requeriría join con reseñas, por ahora solo disponible
                query = query.order_by(Producto.created_at.desc())
            elif criterio == 'popular':
                # Aquí podrías agregar lógica de popularidad
                query = query.order_by(Producto.created_at.desc())
            elif criterio == 'recientes':
                query = query.order_by(Producto.created_at.desc())
            else:
                query = query.order_by(Producto.created_at.desc())
            
            productos = query.limit(20).all()
            return [self._producto_a_dict(p) for p in productos]
        except Exception as e:
            log_error(f"Error en ordenar_productos: {str(e)}")
            return []
    
    # ==================== MÉTODOS PRIVADOS ====================
    
    def _producto_a_dict(self, 
                        producto: Producto, 
                        incluir_completo: bool = False) -> Dict[str, Any]:
        """
        Convierte un objeto Producto a diccionario
        
        Args:
            producto: Objeto Producto de la BD
            incluir_completo: Si True incluye reseñas, imágenes adicionales, etc.
        
        Returns:
            Dict con datos del producto
        """
        try:
            # Obtener portada
            portada = ProductoImagen.query.filter_by(
                producto_id=producto.id,
                es_portada=True
            ).first()
            
            imagen_dict = None
            if portada:
                imagen_dict = portada.to_dict()
            else:
                # Obtener primera imagen si no hay portada
                primera_img = ProductoImagen.query.filter_by(
                    producto_id=producto.id
                ).order_by(ProductoImagen.orden).first()
                if primera_img:
                    imagen_dict = primera_img.to_dict()
            
            # Datos básicos
            data = {
                'id': producto.id,
                'nombre': producto.nombre,
                'slug': producto.slug,
                'descripcion': producto.descripcion,
                'precio_centavos': producto.precio_centavos,
                'precio_actual': producto.precio_centavos / 100,  # En decimal
                'moneda': producto.moneda,
                'stock': producto.stock,
                'activo': producto.activo,
                'sku': producto.sku,
                'imagen': imagen_dict,
                'created_at': producto.created_at.isoformat() if producto.created_at else None,
            }
            
            # Si es vista completa
            if incluir_completo:
                # Categorías
                categorias = []
                for cat in producto.categorias.all():
                    categorias.append(self._categoria_a_dict(cat))
                data['categorias'] = categorias
                
                # Todas las imágenes
                imagenes = []
                for img in ProductoImagen.query.filter_by(producto_id=producto.id).order_by(ProductoImagen.orden).all():
                    imagenes.append(img.to_dict())
                data['imagenes'] = imagenes
                
                # Estadísticas de reseñas
                stats = obtener_estadisticas_producto(producto.id)
                data['resenas'] = {
                    'total': stats.get('total', 0),
                    'promedio': stats.get('promedio', 0),
                    'distribucion': stats.get('distribucion', {})
                }
            
            return data
        except Exception as e:
            log_error(f"Error en _producto_a_dict: {str(e)}")
            return {}
    
    def _categoria_a_dict(self, categoria: Categoria) -> Dict[str, Any]:
        """
        Convierte una Categoría a diccionario
        
        Args:
            categoria: Objeto Categoria
        
        Returns:
            Dict con datos de la categoría
        """
        return {
            'id': categoria.id,
            'nombre': categoria.nombre,
            'slug': categoria.slug,
            'descripcion': categoria.descripcion,
            'padre_id': categoria.padre_id
        }