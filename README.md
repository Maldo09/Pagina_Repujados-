# Repujados Bahamón — Catálogo web

Página web con catálogo, formulario de cotización y panel de administración.
Backend en **Python (Flask)** y base de datos **PostgreSQL**.

```
Pagina_Repujados-/
├── frontend/index.html        ← versión estática original (Live Server)
└── backend/                   ← versión terminada (Python)
    ├── app.py                 ← servidor, rutas y tablas
    ├── seed.py                ← catálogo inicial (se carga la 1.ª vez)
    ├── schema.sql             ← las tablas en SQL, para practicar
    ├── requirements.txt
    ├── .env.example           ← copiar como .env
    ├── templates/             ← HTML (index, panel admin)
    └── static/                ← css, js y assets (imágenes)
```

---

## 1. ¿Qué es PostgreSQL y para qué sirve aquí?

PostgreSQL es una **base de datos**: un programa que guarda información en
**tablas** (como hojas de Excel con columnas fijas) y que se consulta con el
lenguaje **SQL**.

Antes, los productos estaban escritos a mano dentro del HTML. Ahora viven en
la tabla `productos`, y Python los lee para armar la página. Así la cliente
puede agregar, editar u ocultar productos desde `/admin` **sin tocar código**.
Las solicitudes del formulario se guardan en la tabla `cotizaciones`.

```
Navegador ──► Flask (app.py) ──► PostgreSQL
   ▲              │  lee productos / guarda cotizaciones
   └── HTML ◄─────┘
```

> **Live Server vs. Flask:** Live Server solo sirve archivos HTML estáticos;
> no puede hablar con una base de datos. Para esta versión ya no usas Live
> Server: ejecutas `python app.py` y abres `http://127.0.0.1:5000`.

## 2. Instalar PostgreSQL (Windows)

1. Descarga el instalador en **postgresql.org/download/windows** (EDB).
2. En el asistente deja marcados *PostgreSQL Server*, *pgAdmin 4* y
   *Command Line Tools*.
3. Te pedirá una **contraseña para el usuario `postgres`**. Anótala: es la
   que va en el `.env`.
4. Deja el puerto **5432**.

## 3. Crear la base de datos

**Opción A – pgAdmin (visual):** abre pgAdmin → Servers → PostgreSQL →
clic derecho en *Databases* → *Create* → *Database…* → nombre `repujados` → Save.

**Opción B – consola (SQL Shell / psql):**

```sql
CREATE DATABASE repujados;
\l              -- lista las bases de datos
\c repujados    -- conectarse a ella
\dt             -- ver tablas (aparecerán después de correr app.py)
\q              -- salir
```

## 4. Ejecutar el proyecto

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # en Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt

copy .env.example .env          # en Mac/Linux: cp .env.example .env
# edita .env y pon tu contraseña de postgres y una clave de admin

python app.py
```

Abre **http://127.0.0.1:5000** — la página.
Abre **http://127.0.0.1:5000/admin** — el panel (clave = `ADMIN_PASSWORD`).

La primera vez, `app.py` crea las tablas y carga los 12 productos solo.
Si no hay `DATABASE_URL`, usa SQLite temporal para que igual funcione.

## 5. Practicar SQL con tus datos

En pgAdmin: clic derecho en `repujados` → *Query Tool*. Prueba:

```sql
SELECT * FROM productos ORDER BY orden;
SELECT * FROM cotizaciones WHERE atendida = FALSE;
UPDATE productos SET descripcion = 'Texto nuevo' WHERE id = 1;
SELECT categoria, COUNT(*) FROM productos GROUP BY categoria;
```

Refresca la página y verás los cambios. Más consultas en `schema.sql`.

## 6. Imágenes

Las imágenes de `static/assets/` son **provisionales**. Reemplázalas por las
fotos reales con **el mismo nombre** (`galv_4.jpg`, `alu_3.jpg`, `hero.jpg`,
`logo.png`, …) o súbelas desde el panel al editar cada producto. Las fotos
subidas desde el panel se guardan dentro de PostgreSQL, así no se pierden
cuando el servidor se reinicia.

## 7. Publicarla en internet con Render (gratis)

El archivo `render.yaml` ya trae toda la configuración: servidor Python,
base de datos PostgreSQL y variables.

1. Entra a **render.com** y crea una cuenta con tu GitHub.
2. **New → Blueprint** y elige el repositorio `Pagina_Repujados-`.
3. Render pide `ADMIN_PASSWORD`: escribe la clave del panel → **Apply**.
4. Espera unos minutos. Te queda una dirección tipo
   `https://repujados-bahamon.onrender.com` (y `/admin` para el panel).

Cada `git push` a GitHub vuelve a publicar la página sola.

**Límites del plan gratis:** la página se "duerme" tras 15 minutos sin
visitas (la siguiente visita tarda cerca de un minuto en cargar) y la base
de datos gratuita vence a los 30 días. Para dejarla en producción con la
cliente, pasa la base de datos y el servicio a un plan pago desde Render.
