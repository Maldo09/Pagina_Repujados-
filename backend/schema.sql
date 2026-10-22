-- Tablas que crea app.py automáticamente (aquí solo como referencia y práctica).
-- Puedes ejecutarlo en psql o pgAdmin si quieres crearlas a mano.

CREATE TABLE IF NOT EXISTS productos (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(120) NOT NULL,
    categoria   VARCHAR(30)  NOT NULL,     -- galvanizado | aluminio | especial
    etiqueta    VARCHAR(60)  NOT NULL,
    descripcion TEXT,
    imagen      VARCHAR(200),
    orden       INTEGER DEFAULT 0,
    activo      BOOLEAN DEFAULT TRUE,
    precio      INTEGER            -- pesos; NULL = a consultar
);

CREATE TABLE IF NOT EXISTS cotizaciones (
    id        SERIAL PRIMARY KEY,
    nombre    VARCHAR(120) NOT NULL,
    telefono  VARCHAR(30)  NOT NULL,
    producto  VARCHAR(160),
    cantidad  VARCHAR(40),
    mensaje   TEXT,
    atendida  BOOLEAN DEFAULT FALSE,
    creada    TIMESTAMP DEFAULT NOW()
);

-- Consultas útiles para practicar:
-- SELECT * FROM productos ORDER BY orden;
-- SELECT * FROM productos WHERE categoria = 'aluminio';
-- SELECT nombre, telefono, producto, creada FROM cotizaciones WHERE atendida = FALSE;
-- UPDATE productos SET descripcion = 'Nuevo texto' WHERE id = 3;
-- SELECT categoria, COUNT(*) FROM productos GROUP BY categoria;

-- Tienda
CREATE TABLE IF NOT EXISTS pedidos (
    id SERIAL PRIMARY KEY, referencia VARCHAR(40) UNIQUE NOT NULL,
    nombre VARCHAR(120) NOT NULL, telefono VARCHAR(30) NOT NULL, email VARCHAR(120),
    direccion VARCHAR(200), ciudad VARCHAR(80), notas TEXT,
    total INTEGER NOT NULL, estado VARCHAR(20) DEFAULT 'PENDIENTE',
    wompi_id VARCHAR(60), metodo_pago VARCHAR(40), enviado BOOLEAN DEFAULT FALSE,
    creado TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS pedido_items (
    id SERIAL PRIMARY KEY, pedido_id INTEGER NOT NULL REFERENCES pedidos(id),
    producto_id INTEGER, nombre VARCHAR(200) NOT NULL,
    precio INTEGER NOT NULL, cantidad INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS ajustes (clave VARCHAR(40) PRIMARY KEY, valor TEXT);

-- Ventas pagadas por día:
-- SELECT DATE(creado), COUNT(*), SUM(total) FROM pedidos WHERE estado='APPROVED' GROUP BY 1 ORDER BY 1 DESC;
-- Productos más vendidos:
-- SELECT nombre, SUM(cantidad) FROM pedido_items GROUP BY nombre ORDER BY 2 DESC;
