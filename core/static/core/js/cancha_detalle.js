(function(){
  // Helpers
  const $  = (sel, ctx=document) => ctx.querySelector(sel);
  const $$ = (sel, ctx=document) => Array.from(ctx.querySelectorAll(sel));
  const parseISO = s => new Date(s);
  const sameInstant = (a,b) => a.toISOString() === b.toISOString();
  const consecutivos = (a,b) => sameInstant(a.fin, b.inicio);
  const fmt = d => d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});

  // Elementos
  const grid       = $("#grid-tramos");
  const form       = $("#form-carrito");
  const selInicio  = $("#sel-inicio");
  const selFin     = $("#sel-fin");
  const selTexto   = $("#sel-texto");
  const selPrecio  = $("#sel-precio");
  const btnAdd     = $("#btn-add");
  const btnLimpiar = $("#btn-limpiar");

  // Modal Bootstrap
  const modalEl = $("#modalAddToCart");
  let modal = null;
  if (modalEl && window.bootstrap) {
    modal = new bootstrap.Modal(modalEl, {backdrop: 'static'});
  }
  const modalRango = $("#modal-rango");
  const modalTotal = $("#modal-precio");

  // Estado
  let seleccion = []; // máx 2 tramos

  function render(){
    if (seleccion.length === 0){
      if (selInicio) selInicio.value = "";
      if (selFin) selFin.value = "";
      if (selTexto) selTexto.textContent = "—";
      if (selPrecio) selPrecio.textContent = "";
      if (btnAdd) btnAdd.disabled = true;
      return;
    }
    const ini = seleccion[0].inicio;
    const fin = seleccion[seleccion.length - 1].fin;

    if (selInicio) selInicio.value = ini.toISOString();
    if (selFin) selFin.value = fin.toISOString();
    if (selTexto) selTexto.textContent = `${fmt(ini)} – ${fmt(fin)}`;

    const total = seleccion.reduce((acc, x) => acc + (Number(x.precio)||0), 0);
    if (selPrecio) selPrecio.textContent = total ? `Total: $${Math.round(total).toLocaleString('es-CL')}` : "";

    if (btnAdd) btnAdd.disabled = false;
  }

  function toggle(btn){
    const seg = {
      inicio: parseISO(btn.dataset.inicio),
      fin: parseISO(btn.dataset.fin),
      precio: btn.dataset.precio || 0,
      label: btn.dataset.label || "",
      btn: btn
    };

    const idx = seleccion.findIndex(x => sameInstant(x.inicio, seg.inicio) && sameInstant(x.fin, seg.fin));
    if (idx >= 0){
      // deseleccionar
      seleccion[idx].btn.classList.remove("active");
      seleccion.splice(idx,1);
      render();
      return;
    }

    if (seleccion.length === 0){
      seleccion = [seg];
      btn.classList.add("active");
    } else if (seleccion.length === 1){
      const unico = seleccion[0];
      if (consecutivos(unico, seg) || consecutivos(seg, unico)){
        seleccion.push(seg);
        btn.classList.add("active");
        seleccion.sort((a,b) => a.inicio - b.inicio);
      } else {
        // reemplazar
        unico.btn.classList.remove("active");
        seleccion = [seg];
        btn.classList.add("active");
      }
    } else {
      // ya hay 2 -> reemplazar por nuevo
      seleccion.forEach(x => x.btn.classList.remove("active"));
      seleccion = [seg];
      btn.classList.add("active");
    }
    render();
  }

  // Listeners tramos
  if (grid){
    $$(".tramo-btn", grid).forEach(b => b.addEventListener("click", () => toggle(b)));
  }

  // Limpiar
  if (btnLimpiar){
    btnLimpiar.addEventListener("click", () => {
      seleccion.forEach(x => x.btn.classList.remove("active"));
      seleccion = [];
      render();
    });
  }

  // Abrir modal al añadir
  if (btnAdd && form && modal){
    btnAdd.addEventListener("click", (e) => {
      // por si el botón es submit
      e.preventDefault();
      if (!selInicio.value || !selFin.value) return;

      // Copiar resumen al modal
      if (modalRango) modalRango.textContent = selTexto ? selTexto.textContent : "";
      if (modalTotal) modalTotal.textContent = selPrecio ? selPrecio.textContent : "";

      modal.show();
    });
  }

  // Confirmar en modal -> enviar form
  const btnConfirmAdd = $("#btn-confirm-add");
  if (btnConfirmAdd && form && modal){
    btnConfirmAdd.addEventListener("click", () => {
      modal.hide();
      form.submit();
    });
  }

  // Date min hoy + auto-submit en cambio (si tu template tiene #fecha y #form-fecha)
  const fecha = document.getElementById('fecha');
  if (fecha) {
    const hoy = new Date();
    const pad = n => String(n).padStart(2,'0');
    const min = `${hoy.getFullYear()}-${pad(hoy.getMonth()+1)}-${pad(hoy.getDate())}`;
    if (!fecha.min || fecha.min < min) fecha.min = min;

    const formFecha = document.getElementById('form-fecha');
    if (formFecha) {
      fecha.addEventListener('change', () => formFecha.submit());
    }
  }
    // ===== Confirmación de eliminación en carrito (no rompe nada existente) =====
  const delModalEl = document.getElementById('modalConfirmDelete');
  let delModal = null;
  if (delModalEl && window.bootstrap) {
    delModal = new bootstrap.Modal(delModalEl, { backdrop: 'static' });
  }

  const lblCancha  = document.getElementById('del-cancha');
  const lblFecha   = document.getElementById('del-fecha');
  const lblHorario = document.getElementById('del-horario');
  const btnConfirmDelete = document.getElementById('btn-confirm-delete');

  let formToSubmit = null;

  // Intercepta el submit solo si hay modal disponible; si no, deja fluir el submit normal.
  $$(".js-delete-form").forEach(f => {
    f.addEventListener("submit", (e) => {
      if (!delModal) return; // sin Bootstrap o sin modal -> comportamiento actual

      e.preventDefault();
      formToSubmit = f;

      // Toma datos de la fila para mostrar en la modal (no rompe estructura actual)
      const row = f.closest("tr");
      const cancha  = row?.querySelector("td:first-child .fw-semibold")?.textContent?.trim() || "la cancha";
      const fecha   = row?.children?.[1]?.textContent?.trim() || "—";
      const horario = row?.children?.[2]?.textContent?.trim() || "—";

      if (lblCancha)  lblCancha.textContent  = cancha;
      if (lblFecha)   lblFecha.textContent   = fecha;
      if (lblHorario) lblHorario.textContent = horario;

      delModal.show();
    });
  });

  if (btnConfirmDelete) {
    btnConfirmDelete.addEventListener("click", () => {
      if (formToSubmit) {
        delModal?.hide();
        formToSubmit.submit(); // ejecuta el submit original
        formToSubmit = null;
      }
    });
  }


})();


 