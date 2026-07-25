// Menú móvil
const navToggle = document.getElementById('navToggle');
const navLinks = document.querySelector('.nav-links');
const navOverlay = document.getElementById('navOverlay');

function closeNav() {
    navLinks?.classList.remove('open');
    navOverlay?.classList.remove('open');
}
if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => {
        const opening = !navLinks.classList.contains('open');
        navLinks.classList.toggle('open');
        navOverlay?.classList.toggle('open', opening);
    });
    navOverlay?.addEventListener('click', closeNav);
}

// Mostrar / ocultar contraseña
document.querySelectorAll('.toggle-password').forEach(btn => {
    btn.addEventListener('click', () => {
        const input = document.getElementById(btn.dataset.target);
        if (!input) return;
        input.type = input.type === 'password' ? 'text' : 'password';
        btn.textContent = input.type === 'password' ? '👁' : '🙈';
    });
});

// Auto-cerrar mensajes flash
document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => {
        el.style.transition = 'opacity .4s';
        el.style.opacity = '0';
        setTimeout(() => el.remove(), 400);
    }, 4500);
});

// Confirmar acciones peligrosas (formularios con data-confirm)
document.querySelectorAll('form[data-confirm]').forEach(f => {
    f.addEventListener('submit', e => {
        if (!confirm(f.dataset.confirm)) e.preventDefault();
    });
});
