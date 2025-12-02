
-- DROP DATABASE IF EXISTS "PEAKSPORT";

CREATE DATABASE "PEAKSPORT"
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'Spanish_Colombia.1252'
    LC_CTYPE = 'Spanish_Colombia.1252'
    LOCALE_PROVIDER = 'libc'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;

-- ====== USUARIOS ======
CREATE TABLE usuarios (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    correo           VARCHAR(255) NOT NULL UNIQUE,
    contrasena       VARCHAR(255) NOT NULL,
    nombre_completo  VARCHAR(255),
    fecha_nacimiento DATE,
    verificacion     BOOLEAN NOT NULL DEFAULT FALSE,
    rol              VARCHAR(20) NOT NULL DEFAULT 'Cliente',
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_usuarios_rol CHECK (rol IN ('Administrador','Cliente'))
);
-- ====== PRODUCTOS (ACTUALIZADA) ======
CREATE TABLE productos (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre           VARCHAR(255) NOT NULL,
    slug             VARCHAR(255) NOT NULL UNIQUE,
    descripcion      TEXT,
    precio_centavos  BIGINT NOT NULL,
    moneda           CHAR(3) NOT NULL DEFAULT 'COP',
    stock            INTEGER NOT NULL DEFAULT 0,
    sku              VARCHAR(100) UNIQUE NULL,
    activo           BOOLEAN NOT NULL DEFAULT TRUE,
    usuario_id       BIGINT,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_precio_no_negativo CHECK (precio_centavos >= 0),
    CONSTRAINT chk_stock_no_negativo CHECK (stock >= 0),
    CONSTRAINT fk_productos_usuario_id
      FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);
CREATE INDEX idx_productos_nombre ON productos (nombre);
-- ====== CATEGORÍAS ======
CREATE TABLE categorias (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre      VARCHAR(255) NOT NULL,
    slug        VARCHAR(255) NOT NULL UNIQUE,
    descripcion TEXT,
    padre_id    BIGINT,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_categorias_padre_id
      FOREIGN KEY (padre_id) REFERENCES categorias(id) ON DELETE SET NULL
);
CREATE INDEX idx_categorias_nombre ON categorias (nombre);
CREATE INDEX idx_categorias_padre  ON categorias (padre_id);

-- ====== PRODUCTO_CATEGORÍAS (N–N) ======
CREATE TABLE producto_categorias (
    producto_id  BIGINT NOT NULL,
    categoria_id BIGINT NOT NULL,
    PRIMARY KEY (producto_id, categoria_id),
    CONSTRAINT fk_producto_categorias_producto
      FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
    CONSTRAINT fk_producto_categorias_categoria
      FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE
);
CREATE INDEX idx_producto_categorias_categoria ON producto_categorias (categoria_id);

-- ====== PRODUCTO_IMÁGENES ======
CREATE TABLE producto_imagenes (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    producto_id  BIGINT NOT NULL,
    url          TEXT NOT NULL,
    alt          TEXT,
    orden        INTEGER NOT NULL DEFAULT 0,
    es_portada   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_producto_imagenes_producto
      FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
);
CREATE INDEX idx_producto_imagenes_producto ON producto_imagenes (producto_id);

-- (Opcional pero recomendado) 1 sola portada por producto
CREATE UNIQUE INDEX ux_portada_por_producto
  ON producto_imagenes (producto_id)
  WHERE es_portada = TRUE;

-- ====== Trigger para updated_at ======
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := CURRENT_TIMESTAMP;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_usuarios_updated
BEFORE UPDATE ON usuarios
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_productos_updated
BEFORE UPDATE ON productos
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
