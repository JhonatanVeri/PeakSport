from app import app, db
from Modelo_de_Datos_PostgreSQL_y_CRUD.Usuarios import Usuario
from Modelo_de_Datos_PostgreSQL_y_CRUD.Categorias import Categoria
from Modelo_de_Datos_PostgreSQL_y_CRUD.Productos import Producto
from Modelo_de_Datos_PostgreSQL_y_CRUD.Producto_Imagenes import ProductoImagen
from Modelo_de_Datos_PostgreSQL_y_CRUD.associations import producto_categorias

with app.app_context():
    try:
        print("🔄 Sincronizando base de datos (creando solo tablas faltantes)...")

        # Esto crea únicamente tablas que no existan
        db.create_all()

        print("✅ Tablas faltantes creadas correctamente.")
        print("📌 Ningún dato existente fue borrado.")
    except Exception as e:
        print("❌ Error durante la sincronización:", str(e))
