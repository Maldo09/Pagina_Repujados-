// Filtros del catálogo
const filtros = document.querySelectorAll('.filter');
const tarjetas = document.querySelectorAll('.card');
filtros.forEach(btn => btn.addEventListener('click', () => {
  filtros.forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const f = btn.dataset.filter;
  tarjetas.forEach(c => {
    c.style.display = (f === 'all' || c.dataset.category === f) ? 'flex' : 'none';
  });
}));

// Animación al hacer scroll
const io = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) e.target.classList.add('show');
}), { threshold: .08 });
document.querySelectorAll('.reveal').forEach(e => io.observe(e));

// Menú en celular
const menu = document.getElementById('menu');
document.getElementById('menuBtn').addEventListener('click', () => menu.classList.toggle('abierto'));
menu.querySelectorAll('a').forEach(a => a.addEventListener('click', () => menu.classList.remove('abierto')));

// "Cotizar →" llena el formulario con el producto elegido
const selector = document.getElementById('producto');
document.querySelectorAll('[data-producto]').forEach(a => a.addEventListener('click', () => {
  selector.value = a.dataset.producto;
  setTimeout(() => document.getElementById('nombre').focus(), 600);
}));

// Visor de imágenes ampliadas
const visor = document.getElementById('visor');
const visorImg = visor.querySelector('img');
document.querySelectorAll('.photo img').forEach(img => img.addEventListener('click', () => {
  visorImg.src = img.src; visorImg.alt = img.alt; visor.classList.add('abierto');
}));
visor.addEventListener('click', e => { if (e.target !== visorImg) visor.classList.remove('abierto'); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') visor.classList.remove('abierto'); });
