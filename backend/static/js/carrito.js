// Carrito de compras: se guarda en el navegador del cliente.
// El precio que se cobra lo calcula siempre el servidor, no este archivo.
const Carrito = (() => {
  const CLAVE = 'rb_carrito';

  function leer() {
    try { return JSON.parse(localStorage.getItem(CLAVE)) || []; } catch (e) { return []; }
  }
  function guardar(items) {
    try { localStorage.setItem(CLAVE, JSON.stringify(items)); } catch (e) { /* modo privado */ }
    pintarContador();
  }
  function agregar(id, cantidad = 1) {
    const items = leer();
    const it = items.find(i => i.id === id);
    if (it) it.cantidad = Math.min(999, it.cantidad + cantidad);
    else items.push({ id, cantidad });
    guardar(items);
  }
  function cambiar(id, cantidad) {
    let items = leer();
    if (cantidad <= 0) items = items.filter(i => i.id !== id);
    else items.forEach(i => { if (i.id === id) i.cantidad = Math.min(999, cantidad); });
    guardar(items);
  }
  function vaciar() { guardar([]); }
  function unidades() { return leer().reduce((s, i) => s + i.cantidad, 0); }
  function pintarContador() {
    document.querySelectorAll('[data-contador]').forEach(el => {
      const n = unidades();
      el.textContent = n;
      el.hidden = n === 0;
    });
  }
  return { leer, guardar, agregar, cambiar, vaciar, pintarContador };
})();

const pesos = v => '$' + Math.round(v).toLocaleString('es-CO');

function aviso(texto) {
  let t = document.getElementById('toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'toast'; t.className = 'toast'; t.setAttribute('role', 'status');
    document.body.appendChild(t);
  }
  t.innerHTML = texto;
  t.classList.add('visible');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('visible'), 2600);
}

document.addEventListener('DOMContentLoaded', () => {
  Carrito.pintarContador();

  // Botones "Agregar al carrito" del catálogo
  document.querySelectorAll('[data-agregar]').forEach(btn => btn.addEventListener('click', () => {
    Carrito.agregar(Number(btn.dataset.agregar), 1);
    aviso(`Agregado: <strong>${btn.dataset.nombre}</strong> · <a href="/carrito">Ver carrito →</a>`);
  }));

  // Página del carrito
  const app = document.getElementById('carritoApp');
  if (!app) return;
  const precios = JSON.parse(document.getElementById('precios').textContent);
  const lista = document.getElementById('lista');
  const total = document.getElementById('total');
  const campo = document.getElementById('carritoCampo');
  const pago = document.getElementById('pago');

  function render() {
    // quitar productos que ya no existen o no tienen precio
    const items = Carrito.leer().filter(i => precios[i.id]);
    Carrito.guardar(items);
    app.classList.toggle('vacio', items.length === 0);
    lista.innerHTML = '';
    let suma = 0;
    items.forEach(i => {
      const p = precios[i.id];
      suma += p.precio * i.cantidad;
      const fila = document.createElement('div');
      fila.className = 'linea';
      fila.innerHTML = `
        <img src="${p.imagen}" alt="">
        <div class="linea-info"><strong></strong><span></span><em>${pesos(p.precio)} c/u</em></div>
        <div class="cantidad">
          <button type="button" aria-label="Quitar uno">−</button>
          <input type="number" min="1" max="999" value="${i.cantidad}" aria-label="Cantidad">
          <button type="button" aria-label="Agregar uno">+</button>
        </div>
        <div class="linea-sub">${pesos(p.precio * i.cantidad)}</div>
        <button type="button" class="quitar" aria-label="Eliminar">×</button>`;
      fila.querySelector('strong').textContent = p.nombre;
      fila.querySelector('span').textContent = p.etiqueta;
      const [menos, mas] = fila.querySelectorAll('.cantidad button');
      const input = fila.querySelector('input');
      menos.onclick = () => { Carrito.cambiar(i.id, i.cantidad - 1); render(); };
      mas.onclick = () => { Carrito.cambiar(i.id, i.cantidad + 1); render(); };
      input.onchange = () => { Carrito.cambiar(i.id, parseInt(input.value, 10) || 0); render(); };
      fila.querySelector('.quitar').onclick = () => { Carrito.cambiar(i.id, 0); render(); };
      lista.appendChild(fila);
    });
    total.textContent = pesos(suma);
    campo.value = JSON.stringify(items);
    if (pago) pago.disabled = items.length === 0;
  }
  render();

  document.getElementById('formPedido').addEventListener('submit', () => {
    campo.value = JSON.stringify(Carrito.leer());
    if (pago) { pago.disabled = true; pago.textContent = 'Procesando…'; }
  });
});
