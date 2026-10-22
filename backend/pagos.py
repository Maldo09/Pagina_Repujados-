"""
Integración con Wompi (pasarela de pagos de Bancolombia).

Cómo funciona:
1. La página crea el pedido y manda al cliente al "Web Checkout" de Wompi
   con el valor y una firma de integridad (para que nadie cambie el precio).
2. El cliente paga en Wompi (tarjeta, PSE, Nequi, Bancolombia...).
3. Wompi lo devuelve a /pedido/resultado?id=<transacción> y además avisa
   al servidor por /wompi/eventos. Con cualquiera de los dos se actualiza
   el estado del pedido; el aviso por eventos es el que manda.

Variables de entorno (Wompi → Desarrolladores → Secretos para integración técnica):
    WOMPI_PUBLIC_KEY        pub_test_...  (pruebas)  o  pub_prod_...  (real)
    WOMPI_INTEGRITY_SECRET  test_integrity_...  o  prod_integrity_...
    WOMPI_EVENTS_SECRET     test_events_...     o  prod_events_...
"""
import hashlib
import hmac
import json
import os
import urllib.request
from urllib.parse import urlencode

CHECKOUT_URL = "https://checkout.wompi.co/p/"


def llave_publica():
    return os.getenv("WOMPI_PUBLIC_KEY", "").strip()


def configurado():
    """True cuando hay llaves de Wompi; si no, el carrito cierra por WhatsApp."""
    return bool(llave_publica() and os.getenv("WOMPI_INTEGRITY_SECRET", "").strip())


def modo_pruebas():
    return llave_publica().startswith("pub_test_")


def api_base():
    return ("https://sandbox.wompi.co/v1" if modo_pruebas()
            else "https://production.wompi.co/v1")


def firma_integridad(referencia, monto_centavos, moneda="COP"):
    """SHA-256 de <referencia><monto><moneda><secreto de integridad>."""
    secreto = os.getenv("WOMPI_INTEGRITY_SECRET", "").strip()
    texto = f"{referencia}{monto_centavos}{moneda}{secreto}"
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def url_checkout(pedido, redirect_url):
    """Dirección del Web Checkout de Wompi con el pedido ya cargado."""
    centavos = pedido.total * 100
    params = {
        "public-key": llave_publica(),
        "currency": "COP",
        "amount-in-cents": centavos,
        "reference": pedido.referencia,
        "signature:integrity": firma_integridad(pedido.referencia, centavos),
        "redirect-url": redirect_url,
        "customer-data:full-name": pedido.nombre,
        "customer-data:phone-number": "".join(c for c in pedido.telefono if c.isdigit()),
    }
    if pedido.email:
        params["customer-data:email"] = pedido.email
    return CHECKOUT_URL + "?" + urlencode(params)


def consultar_transaccion(transaccion_id):
    """Pregunta a Wompi el estado real de una transacción (no se confía en la URL)."""
    url = f"{api_base()}/transactions/{transaccion_id}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)["data"]


def _valor(datos, ruta):
    for parte in ruta.split("."):
        datos = datos[parte]
    return datos


def evento_valido(cuerpo):
    """Verifica la firma (checksum) que Wompi pone en cada evento."""
    secreto = os.getenv("WOMPI_EVENTS_SECRET", "").strip()
    try:
        firma = cuerpo["signature"]
        valores = "".join(str(_valor(cuerpo["data"], p)) for p in firma["properties"])
        texto = f"{valores}{cuerpo['timestamp']}{secreto}"
        calculado = hashlib.sha256(texto.encode("utf-8")).hexdigest()
        return bool(secreto) and hmac.compare_digest(calculado.lower(),
                                                    str(firma["checksum"]).lower())
    except (KeyError, TypeError):
        return False
