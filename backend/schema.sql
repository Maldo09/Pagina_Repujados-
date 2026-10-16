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
    activo      BOOLEAN DEFAULT TRUE
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
