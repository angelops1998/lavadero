// Editor de líneas del pedido: agrega prendas/servicios y suma el total en vivo.
(function () {
    const cont = document.getElementById('items-container');
    if (!cont) return;
    const totalEl = document.getElementById('total-live');
    const btnManual = document.getElementById('add-manual');
    const descEl = document.getElementById('descuento');
    const recEl = document.getElementById('recargo');

    function fmtBs(n) {
        if (isNaN(n)) n = 0;
        const s = n.toFixed(2);                       // "1234.50"
        let [ent, dec] = s.split('.');
        ent = ent.replace(/\B(?=(\d{3})+(?!\d))/g, '.'); // miles con punto
        return 'Bs ' + ent + ',' + dec;
    }

    function parseNum(v) {
        const n = parseFloat(String(v).replace(',', '.'));
        return isNaN(n) ? 0 : n;
    }

    // Unidades de cobro: etiqueta inline junto a la cantidad, sufijo de precio y paso.
    const UNIDADES = {
        prenda: { cant: 'Cant.',  u: '',    per: '',     step: '1' },
        kg:     { cant: 'Kg',     u: 'kg',  per: '/kg',  step: '0.5' },
        metro:  { cant: 'Metros', u: 'm',   per: '/m',   step: '0.5' },
        par:    { cant: 'Pares',  u: 'par', per: '/par', step: '1' },
    };
    const uni = u => UNIDADES[u] || UNIDADES.prenda;

    function recalcRow(row) {
        const cant = parseNum(row.querySelector('.item-cant').value);
        const precio = parseNum(row.querySelector('.item-precio').value);
        const sub = cant * precio;
        row.querySelector('.item-subtotal').textContent = fmtBs(sub);
        return sub;
    }

    function recalcTotal() {
        let sub = 0;
        cont.querySelectorAll('.item-row').forEach(r => { sub += recalcRow(r); });
        const desc = descEl ? Math.max(0, parseNum(descEl.value)) : 0;
        const rec = recEl ? Math.max(0, parseNum(recEl.value)) : 0;
        let total = sub - desc + rec;
        if (total < 0) total = 0;
        if (totalEl) totalEl.textContent = fmtBs(total);
    }

    function addRow(data) {
        data = data || {};
        const u = uni(data.unidad);
        const desc = (data.descripcion || '').replace(/"/g, '&quot;');
        const row = document.createElement('div');
        row.className = 'item-row';
        row.innerHTML = `
            <div class="item-head">
                <input type="text" name="item_descripcion" class="item-desc input"
                       placeholder="Prenda o servicio" value="${desc}">
                <button type="button" class="item-del" title="Quitar">✕</button>
            </div>
            <input type="hidden" name="item_servicio_id" value="${data.servicio_id || ''}">
            <input type="hidden" name="item_unidad" value="${data.unidad || 'prenda'}">
            <div class="item-calc">
                <input type="number" name="item_cantidad" class="item-cant input" aria-label="${u.cant}"
                       inputmode="decimal" min="0" step="${u.step}" value="${data.cantidad ?? 1}">
                ${u.u ? `<span class="u">${u.u}</span>` : ''}
                <span class="mul">×</span>
                <span class="cur">Bs</span>
                <input type="number" name="item_precio" class="item-precio input" aria-label="Precio unitario"
                       inputmode="decimal" min="0" step="0.5" value="${data.precio ?? 0}">
                <span class="item-subtotal">Bs 0,00</span>
            </div>`;
        cont.appendChild(row);

        row.querySelectorAll('.item-cant, .item-precio').forEach(inp => {
            inp.addEventListener('input', recalcTotal);
        });
        row.querySelector('.item-del').addEventListener('click', () => {
            row.remove();
            recalcTotal();
        });
        recalcTotal();
        return row;
    }

    // ── Buscador de servicios (autocompletado + selección múltiple) ──
    const search = document.getElementById('serv-search');
    const input = document.getElementById('serv-input');
    const list = document.getElementById('serv-list');

    function norm(s) {
        // minúsculas y sin acentos, para que "edredon" encuentre "Edredón".
        return String(s).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    }

    let servicios = [];
    const servTag = document.getElementById('servicios-data');
    if (servTag) {
        try { servicios = JSON.parse(servTag.textContent) || []; } catch (e) { servicios = []; }
    }

    if (search && input && list) {
        let activo = -1;   // opción resaltada
        let visibles = []; // servicios que coinciden con la búsqueda

        function resaltar(nombre, q) {
            if (!q) return nombre;
            const i = norm(nombre).indexOf(norm(q));
            if (i < 0) return nombre;
            const a = nombre.slice(0, i), b = nombre.slice(i, i + q.length), c = nombre.slice(i + q.length);
            const esc = t => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            return esc(a) + '<mark>' + esc(b) + '</mark>' + esc(c);
        }

        function cerrar() {
            list.hidden = true;
            list.innerHTML = '';
            activo = -1;
            input.setAttribute('aria-expanded', 'false');
        }

        function elegir(s) {
            addRow({ descripcion: s.nombre, precio: s.precio, servicio_id: s.id, unidad: s.unidad, cantidad: 1 });
            input.value = '';
            cerrar();
            input.focus(); // seguir agregando sin levantar el dedo
        }

        function render(q) {
            const nq = norm(q).trim();
            visibles = nq ? servicios.filter(s => norm(s.nombre).includes(nq)) : servicios.slice();
            list.innerHTML = '';
            activo = -1;

            if (!servicios.length) {
                list.innerHTML = '<li class="serv-empty">No hay servicios cargados. <a href="/servicios">Agregar servicios</a></li>';
            } else if (!visibles.length) {
                list.innerHTML = '<li class="serv-empty">Sin coincidencias. Usá «➕ Agregar otra prenda» para algo fuera del catálogo.</li>';
            } else {
                visibles.forEach((s, i) => {
                    const li = document.createElement('li');
                    li.className = 'serv-opt';
                    li.setAttribute('role', 'option');
                    li.dataset.i = i;
                    li.innerHTML = '<span class="nom">' + resaltar(s.nombre, q.trim()) +
                        '</span><span class="pr">' + fmtBs(parseNum(s.precio)) + uni(s.unidad).per + '</span>';
                    li.addEventListener('mousedown', e => { e.preventDefault(); elegir(s); });
                    li.addEventListener('mouseover', () => setActivo(i));
                    list.appendChild(li);
                });
            }
            list.hidden = false;
            input.setAttribute('aria-expanded', 'true');
        }

        function setActivo(i) {
            const opts = list.querySelectorAll('.serv-opt');
            opts.forEach(o => o.classList.remove('active'));
            activo = i;
            if (i >= 0 && opts[i]) {
                opts[i].classList.add('active');
                opts[i].scrollIntoView({ block: 'nearest' });
            }
        }

        input.addEventListener('focus', () => render(input.value));
        input.addEventListener('input', () => render(input.value));

        input.addEventListener('keydown', e => {
            if (list.hidden && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
                render(input.value); return;
            }
            if (e.key === 'ArrowDown') { e.preventDefault(); if (visibles.length) setActivo((activo + 1) % visibles.length); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); if (visibles.length) setActivo((activo - 1 + visibles.length) % visibles.length); }
            else if (e.key === 'Enter') {
                e.preventDefault();
                if (activo >= 0 && visibles[activo]) elegir(visibles[activo]);
                else if (visibles.length === 1) elegir(visibles[0]);
                else if (input.value.trim()) {
                    // texto libre que no está en el catálogo → prenda manual
                    const row = addRow({ descripcion: input.value.trim(), precio: 0, cantidad: 1 });
                    input.value = ''; cerrar();
                    row.querySelector('.item-precio').focus();
                }
            } else if (e.key === 'Escape') { cerrar(); }
        });

        // Cerrar al tocar fuera del buscador.
        document.addEventListener('click', e => { if (!search.contains(e.target)) cerrar(); });
    }

    // Línea manual (prenda que no está en el catálogo).
    if (btnManual) {
        btnManual.addEventListener('click', () => {
            const row = addRow({ descripcion: '', precio: 0, cantidad: 1 });
            row.querySelector('.item-desc').focus();
        });
    }

    // Recalcular el total cuando cambian descuento/recargo.
    [descEl, recEl].forEach(el => { if (el) el.addEventListener('input', recalcTotal); });

    // "Pagó el total" desactiva el campo de seña.
    const pagoTotal = document.getElementById('pago_total');
    const senaGroup = document.getElementById('sena-group');
    const senaInput = document.getElementById('sena');
    function syncPago() {
        if (!pagoTotal) return;
        const full = pagoTotal.checked;
        if (senaInput) { senaInput.disabled = full; if (full) senaInput.value = ''; }
        if (senaGroup) senaGroup.style.opacity = full ? '.5' : '';
    }
    if (pagoTotal) { pagoTotal.addEventListener('change', syncPago); syncPago(); }

    // Cargar líneas iniciales (edición o reintento tras error).
    const dataTag = document.getElementById('items-data');
    let iniciales = [];
    if (dataTag) {
        try { iniciales = JSON.parse(dataTag.textContent) || []; } catch (e) { iniciales = []; }
    }
    iniciales.forEach(addRow);
    recalcTotal();
})();
