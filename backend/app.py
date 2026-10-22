"""
Repujados Bahamón - Catálogo web
Backend en Python (Flask) con base de datos PostgreSQL.

Ejecutar:
    python app.py
y abrir http://127.0.0.1:5000
"""
import json
import os
import secrets
from datetime import datetime
from functools import wraps
from urllib.parse import quote

from flask import (Flask, Response, abort, flash, redirect, render_template,
                   request, session, url_for)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.middleware.proxy_fix import ProxyFix

import pagos

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
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # Render usa https por delante
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
    precio = db.Column(db.Integer)                           # pesos COP; vacío = "a consultar"

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


class Pedido(db.Model):
    __tablename__ = "pedidos"

    ESTADOS = {
        "PENDIENTE": "Esperando pago",
        "POR_CONFIRMAR": "Esperando transferencia",
        "APPROVED": "Pagado",
        "DECLINED": "Rechazado",
        "VOIDED": "Anulado",
        "ERROR": "Error en el pago",
    }

    id = db.Column(db.Integer, primary_key=True)
    referencia = db.Column(db.String(40), unique=True, nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    telefono = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(120), default="")
    direccion = db.Column(db.String(200), default="")
    ciudad = db.Column(db.String(80), default="")
    notas = db.Column(db.Text, default="")
    total = db.Column(db.Integer, nullable=False)            # pesos COP
    estado = db.Column(db.String(20), default="PENDIENTE")
    wompi_id = db.Column(db.String(60), default="")
    metodo_pago = db.Column(db.String(40), default="")
    enviado = db.Column(db.Boolean, default=False)
    creado = db.Column(db.DateTime, default=datetime.now)
    items = db.relationship("PedidoItem", backref="pedido", cascade="all, delete-orphan")

    @property
    def estado_texto(self):
        return self.ESTADOS.get(self.estado, self.estado)

    def resumen(self):
        return ", ".join(f"{i.cantidad} x {i.nombre}" for i in self.items)


class PedidoItem(db.Model):
    __tablename__ = "pedido_items"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=False)
    producto_id = db.Column(db.Integer)
    nombre = db.Column(db.String(200), nullable=False)        # copia: si el producto cambia, el pedido no
    precio = db.Column(db.Integer, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)

    @property
    def subtotal(self):
        return self.precio * self.cantidad


class Ajuste(db.Model):
    """Textos que la dueña cambia desde el panel (ej. datos de pago)."""
    __tablename__ = "ajustes"

    clave = db.Column(db.String(40), primary_key=True)
    valor = db.Column(db.Text, default="")


def ajuste(clave, defecto=""):
    a = db.session.get(Ajuste, clave)
    return a.valor if a and a.valor else defecto


# -------------------------------------------------------------- Ayudantes ---
@app.template_filter("pesos")
def formato_pesos(valor):
    """12500 -> $12.500"""
    return "$" + f"{int(valor or 0):,}".replace(",", ".")


def actualizar_pago(pedido, transaccion):
    """Aplica a un pedido el estado que informó Wompi (si el monto coincide)."""
    if int(transaccion.get("amount_in_cents", -1)) != pedido.total * 100:
        return False
    pedido.wompi_id = transaccion.get("id", pedido.wompi_id) or ""
    pedido.metodo_pago = transaccion.get("payment_method_type", pedido.metodo_pago) or ""
    estado = transaccion.get("status", "")
    if estado in Pedido.ESTADOS and pedido.estado != "APPROVED":
        pedido.estado = estado
    return True

@app.context_processor
def variables_globales():
    return {
        "WHATSAPP": WHATSAPP,
        "WHATSAPP_TEXTO": "314 859 4677",
        "CATEGORIAS": CATEGORIAS,
        "PAGO_EN_LINEA": pagos.configurado(),
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


@app.route("/salud")
def salud():
    """Respuesta mínima para el servicio que mantiene la página despierta."""
    return "ok", 200, {"Cache-Control": "no-store"}


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


# ------------------------------------------------------- Carrito y pedidos --
def _leer_carrito(crudo):
    """Convierte el carrito que manda el navegador en (producto, cantidad),
    tomando SIEMPRE el precio de la base de datos, nunca del navegador."""
    try:
        datos = json.loads(crudo or "[]")
    except ValueError:
        return []
    cantidades = {}
    for item in datos if isinstance(datos, list) else []:
        try:
            pid, cant = int(item["id"]), int(item["cantidad"])
        except (KeyError, TypeError, ValueError):
            continue
        if 1 <= cant <= 999:
            cantidades[pid] = min(999, cantidades.get(pid, 0) + cant)
    if not cantidades:
        return []
    productos = Producto.query.filter(Producto.id.in_(cantidades), Producto.activo.is_(True),
                                      Producto.precio.isnot(None)).all()
    return [(p, cantidades[p.id]) for p in productos if p.precio > 0]


@app.route("/carrito")
def carrito():
    productos = Producto.query.filter(Producto.activo.is_(True),
                                      Producto.precio.isnot(None)).all()
    precios = {p.id: {"nombre": p.nombre, "etiqueta": p.etiqueta, "precio": p.precio,
                      "imagen": p.url_imagen()} for p in productos}
    return render_template("carrito.html", precios=precios)


@app.route("/pedido/crear", methods=["POST"])
def crear_pedido():
    lineas = _leer_carrito(request.form.get("carrito"))
    f = {k: request.form.get(k, "").strip() for k in
         ("nombre", "telefono", "email", "direccion", "ciudad", "notas")}
    if not lineas:
        flash("Tu carrito está vacío o los productos ya no están disponibles.", "error")
        return redirect(url_for("carrito"))
    if not f["nombre"] or not f["telefono"] or not f["direccion"] or not f["ciudad"]:
        flash("Completa nombre, teléfono, dirección y ciudad para el envío.", "error")
        return redirect(url_for("carrito"))

    pedido = Pedido(
        referencia="RB-" + datetime.now().strftime("%y%m%d") + "-" + secrets.token_hex(3).upper(),
        nombre=f["nombre"][:120], telefono=f["telefono"][:30], email=f["email"][:120],
        direccion=f["direccion"][:200], ciudad=f["ciudad"][:80], notas=f["notas"][:1000],
        total=sum(p.precio * c for p, c in lineas),
        estado="PENDIENTE" if pagos.configurado() else "POR_CONFIRMAR",
    )
    for p, c in lineas:
        pedido.items.append(PedidoItem(producto_id=p.id, precio=p.precio, cantidad=c,
                                       nombre=f"{p.nombre} ({p.etiqueta})"))
    db.session.add(pedido)
    db.session.commit()

    if pagos.configurado():
        destino = url_for("resultado_pedido", ref=pedido.referencia, _external=True)
        return redirect(pagos.url_checkout(pedido, destino))
    return redirect(url_for("resultado_pedido", ref=pedido.referencia))


@app.route("/pedido/<ref>")
def resultado_pedido(ref):
    pedido = Pedido.query.filter_by(referencia=ref).first_or_404()
    tid = request.args.get("id", "").strip()
    if tid and pagos.configurado() and pedido.estado != "APPROVED":
        try:
            t = pagos.consultar_transaccion(tid)
            if t.get("reference") == pedido.referencia and actualizar_pago(pedido, t):
                db.session.commit()
        except Exception as e:                      # Wompi no respondió: el evento lo actualizará
            app.logger.warning("No se pudo consultar Wompi: %s", e)
    texto = (f"Hola Repujados Bahamón, soy {pedido.nombre}. Pedido {pedido.referencia}: "
             f"{pedido.resumen()}. Total {formato_pesos(pedido.total)}. "
             f"Envío a {pedido.direccion}, {pedido.ciudad}.")
    return render_template("pedido.html", pedido=pedido,
                           datos_pago=ajuste("datos_pago"),
                           wa_pedido=f"https://wa.me/{WHATSAPP}?text={quote(texto)}")


@app.route("/wompi/eventos", methods=["POST"])
def wompi_eventos():
    """Aviso de Wompi cuando cambia el estado de un pago."""
    cuerpo = request.get_json(silent=True) or {}
    if not pagos.evento_valido(cuerpo):
        return "firma inválida", 400
    if cuerpo.get("event") == "transaction.updated":
        t = cuerpo["data"]["transaction"]
        pedido = Pedido.query.filter_by(referencia=t.get("reference")).first()
        if pedido and actualizar_pago(pedido, t):
            db.session.commit()
    return "ok", 200


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
    pedidos = Pedido.query.order_by(Pedido.creado.desc()).limit(200).all()
    por_enviar = sum(1 for p in pedidos
                     if p.estado in ("APPROVED", "POR_CONFIRMAR") and not p.enviado)
    return render_template("admin.html", productos=productos, cotizaciones=cotizaciones,
                           pendientes=pendientes, pedidos=pedidos, por_enviar=por_enviar,
                           pago_en_linea=pagos.configurado(),
                           datos_pago=ajuste("datos_pago"),
                           modo_pruebas=pagos.modo_pruebas())


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
        precio = "".join(c for c in request.form.get("precio", "") if c.isdigit())
        p.precio = int(precio) if precio else None
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


@app.route("/admin/datos-pago", methods=["POST"])
@solo_admin
def guardar_datos_pago():
    a = db.session.get(Ajuste, "datos_pago") or Ajuste(clave="datos_pago")
    a.valor = request.form.get("datos_pago", "").strip()[:2000]
    db.session.add(a)
    db.session.commit()
    flash("Datos de pago guardados.", "ok")
    return redirect(url_for("admin") + "#pagos")


@app.route("/admin/pedido/<int:pid>/pagado", methods=["POST"])
@solo_admin
def marcar_pagado(pid):
    p = db.get_or_404(Pedido, pid)
    if p.estado == "POR_CONFIRMAR":
        p.estado = "APPROVED"           # la dueña verificó la transferencia
    elif p.estado == "APPROVED" and not p.wompi_id:
        p.estado = "POR_CONFIRMAR"      # deshacer un clic por error
    db.session.commit()
    return redirect(url_for("admin") + "#pedidos")


@app.route("/admin/pedido/<int:pid>/enviado", methods=["POST"])
@solo_admin
def marcar_enviado(pid):
    p = db.get_or_404(Pedido, pid)
    p.enviado = not p.enviado
    db.session.commit()
    return redirect(url_for("admin") + "#pedidos")


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
        # Agrega columnas nuevas a tablas que ya existían (sin borrar datos).
        columnas = {c["name"] for c in inspect(db.engine).get_columns("productos")}
        if "precio" not in columnas:
            with db.engine.begin() as con:
                con.execute(text("ALTER TABLE productos ADD COLUMN precio INTEGER"))
            print("✓ Columna 'precio' agregada a productos")
        if Producto.query.count() == 0:
            for i, datos in enumerate(PRODUCTOS_INICIALES):
                db.session.add(Producto(orden=i, **datos))
            db.session.commit()
            print(f"✓ Catálogo inicial cargado ({len(PRODUCTOS_INICIALES)} productos)")


iniciar_bd()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
