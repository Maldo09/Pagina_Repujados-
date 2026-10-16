"""
Repujados Bahamón - Catálogo web
Backend en Python (Flask) con base de datos PostgreSQL.

Ejecutar:
    python app.py
y abrir http://127.0.0.1:5000
"""
import os
from datetime import datetime
from functools import wraps
from urllib.parse import quote

from flask import (Flask, Response, abort, flash, redirect, render_template,
                   request, session, url_for)
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def cargar_env(ruta=os.path.join(BASE_DIR, ".env")):
    """Lee el archivo .env (CLAVE=valor) sin librerías extra."""
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                os.environ.setdefault(clave.strip(), valor.strip())


cargar_env()

# ---------------------------------------------------------------- Config ----
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "cambia-esta-clave")

# URL de PostgreSQL:  postgresql+psycopg://usuario:clave@host:puerto/base
db_url = os.getenv("DATABASE_URL")
if not db_url:
    # Respaldo para que la página funcione aunque PostgreSQL no esté listo.
    db_url = "sqlite:///" + os.path.join(BASE_DIR, "repujados.db")
    print("⚠  No hay DATABASE_URL en .env: usando SQLite temporal (repujados.db)")
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # imágenes de máx. 5 MB

WHATSAPP = os.getenv("WHATSAPP", "573148594677")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
EXTENSIONES = {"jpg", "jpeg", "png", "webp"}

db = SQLAlchemy(app)

CATEGORIAS = {
    "galvanizado": "Galvanizado",
    "aluminio": "Aluminio",
    "especial": "Accesorios",
}


# ---------------------------------------------------------------- Tablas ----
class Producto(db.Model):
    __tablename__ = "productos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    categoria = db.Column(db.String(30), nullable=False)   # galvanizado / aluminio / especial
    etiqueta = db.Column(db.String(60), nullable=False)    # texto pequeño sobre el nombre
    descripcion = db.Column(db.Text, default="")
    imagen = db.Column(db.String(200), default="")         # archivo en static/assets
    imagen_datos = db.Column(db.LargeBinary)                 # foto subida desde el panel
    imagen_tipo = db.Column(db.String(40))
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)

    def url_imagen(self):
        """Foto subida (guardada en la BD) o, si no hay, el archivo de static/assets."""
        if self.imagen_datos:
            return url_for("imagen_producto", pid=self.id, v=len(self.imagen_datos))
        return url_for("static", filename="assets/" + (self.imagen or "sin-imagen.svg"))

    def link_whatsapp(self):
        texto = f"Hola Repujados Bahamón, quiero información sobre: {self.nombre} ({self.etiqueta})."
        return f"https://wa.me/{WHATSAPP}?text={quote(texto)}"


class Cotizacion(db.Model):
    __tablename__ = "cotizaciones"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    telefono = db.Column(db.String(30), nullable=False)
    producto = db.Column(db.String(160), default="")
    cantidad = db.Column(db.String(40), default="")
    mensaje = db.Column(db.Text, default="")
    atendida = db.Column(db.Boolean, default=False)
    creada = db.Column(db.DateTime, default=datetime.now)


# -------------------------------------------------------------- Ayudantes ---
@app.context_processor
def variables_globales():
    return {
        "WHATSAPP": WHATSAPP,
        "WHATSAPP_TEXTO": "314 859 4677",
        "CATEGORIAS": CATEGORIAS,
        "anio": datetime.now().year,
        "wa_cotizar": f"https://wa.me/{WHATSAPP}?text="
        + quote("Hola Repujados Bahamón, quiero cotizar un producto."),
    }


def solo_admin(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login", siguiente=request.path))
        return vista(*args, **kwargs)
    return envoltura


def guardar_imagen(producto, archivo):
    """Guarda la foto subida dentro de PostgreSQL (así no se pierde al
    reiniciar el servidor en la nube)."""
    if not archivo or not archivo.filename:
        return False
    ext = archivo.filename.rsplit(".", 1)[-1].lower()
    if ext not in EXTENSIONES:
        flash("Formato de imagen no permitido (usa jpg, png o webp).", "error")
        return False
    producto.imagen_datos = archivo.read()
    producto.imagen_tipo = archivo.mimetype or f"image/{ext}"
    return True


# ---------------------------------------------------------- Página pública --
@app.route("/")
def inicio():
    productos = (Producto.query.filter_by(activo=True)
                 .order_by(Producto.orden, Producto.id).all())
    return render_template("index.html", productos=productos)


@app.route("/img/<int:pid>")
def imagen_producto(pid):
    p = db.get_or_404(Producto, pid)
    if not p.imagen_datos:
        abort(404)
    return Response(p.imagen_datos, mimetype=p.imagen_tipo,
                    headers={"Cache-Control": "public, max-age=86400"})


@app.route("/cotizar", methods=["POST"])
def cotizar():
    nombre = request.form.get("nombre", "").strip()
    telefono = request.form.get("telefono", "").strip()
    if not nombre or not telefono:
        flash("Escribe tu nombre y tu teléfono para poder contactarte.", "error")
        return redirect(url_for("inicio") + "#contacto")

    c = Cotizacion(
        nombre=nombre[:120],
        telefono=telefono[:30],
        producto=request.form.get("producto", "")[:160],
        cantidad=request.form.get("cantidad", "")[:40],
        mensaje=request.form.get("mensaje", "").strip(),
    )
    db.session.add(c)
    db.session.commit()

    # Después de guardar, se abre WhatsApp con el mensaje ya escrito.
    texto = (f"Hola Repujados Bahamón, soy {c.nombre}. Quiero cotizar: "
             f"{c.producto or 'un producto'}"
             + (f" - Cantidad: {c.cantidad}" if c.cantidad else "")
             + (f". {c.mensaje}" if c.mensaje else "."))
    return redirect(f"https://wa.me/{WHATSAPP}?text={quote(texto)}")


# ------------------------------------------------------------------ Admin ---
@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("clave") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(request.args.get("siguiente") or url_for("admin"))
        flash("Clave incorrecta.", "error")
    return render_template("login.html")


@app.route("/admin/salir")
def salir():
    session.clear()
    return redirect(url_for("inicio"))


@app.route("/admin")
@solo_admin
def admin():
    productos = Producto.query.order_by(Producto.orden, Producto.id).all()
    cotizaciones = Cotizacion.query.order_by(Cotizacion.creada.desc()).all()
    pendientes = sum(1 for c in cotizaciones if not c.atendida)
    return render_template("admin.html", productos=productos,
                           cotizaciones=cotizaciones, pendientes=pendientes)


@app.route("/admin/producto/nuevo", methods=["GET", "POST"])
@app.route("/admin/producto/<int:pid>", methods=["GET", "POST"])
@solo_admin
def editar_producto(pid=None):
    p = db.session.get(Producto, pid) if pid else Producto(activo=True)
    if pid and p is None:
        abort(404)

    if request.method == "POST":
        p.nombre = request.form["nombre"].strip()
        p.categoria = request.form["categoria"]
        p.etiqueta = request.form["etiqueta"].strip()
        p.descripcion = request.form.get("descripcion", "").strip()
        p.orden = int(request.form.get("orden") or 0)
        p.activo = "activo" in request.form
        guardar_imagen(p, request.files.get("imagen"))
        if not pid:
            db.session.add(p)
        db.session.commit()
        flash(f"Producto «{p.nombre}» guardado.", "ok")
        return redirect(url_for("admin"))

    return render_template("producto_form.html", p=p)


@app.route("/admin/producto/<int:pid>/eliminar", methods=["POST"])
@solo_admin
def eliminar_producto(pid):
    p = db.get_or_404(Producto, pid)
    db.session.delete(p)
    db.session.commit()
    flash("Producto eliminado.", "ok")
    return redirect(url_for("admin"))


@app.route("/admin/cotizacion/<int:cid>/atendida", methods=["POST"])
@solo_admin
def marcar_atendida(cid):
    c = db.get_or_404(Cotizacion, cid)
    c.atendida = not c.atendida
    db.session.commit()
    return redirect(url_for("admin") + "#cotizaciones")


# --------------------------------------------------------------- Arranque ---
def iniciar_bd():
    """Crea las tablas y, si están vacías, carga el catálogo inicial."""
    from seed import PRODUCTOS_INICIALES
    with app.app_context():
        db.create_all()
        if Producto.query.count() == 0:
            for i, datos in enumerate(PRODUCTOS_INICIALES):
                db.session.add(Producto(orden=i, **datos))
            db.session.commit()
            print(f"✓ Catálogo inicial cargado ({len(PRODUCTOS_INICIALES)} productos)")


iniciar_bd()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
