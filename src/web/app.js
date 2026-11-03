"use strict";
/* NovaRent · interfaz web. Sin dependencias: habla con la API REST (docs/api/contrato.md).
   Todo el texto que viene del servidor se inserta como texto (nunca como HTML). */

const CAT = { ECONOMICO: "Económico", COMPACTO: "Compacto", SUV: "SUV", PREMIUM: "Premium" };
const ORDEN = ["ECONOMICO", "COMPACTO", "SUV", "PREMIUM"];
const CONCEPTO = {
  RETRASO: "Retraso en la devolución", KILOMETRAJE: "Kilometraje excedido",
  COMBUSTIBLE: "Combustible faltante", DANOS: "Daños nuevos",
};
const ESTADO_AUTO = { DISPONIBLE: "Disponibles", RENTADO: "Rentados", EN_LIMPIEZA: "En limpieza" };
const ESTADO_RENTA = { PENDIENTE: "Por entregar", ENTREGADO: "En renta", DEVUELTO: "Devueltas" };
const mxn = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

/* ---------- utilidades ---------- */
const dinero = (v) => mxn.format(Number(v));
const centavos = (v) => Math.round(Number(v) * 100);
const nombreCat = (c) => CAT[c] || c;

function fecha(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" });
}
function aISO(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
const hoyISO = () => aISO(new Date());
function sumarDias(iso, n) {
  const [y, m, d] = iso.split("-").map(Number);
  return aISO(new Date(y, m - 1, d + n));
}
function diasEntre(a, b) {
  const [y1, m1, d1] = a.split("-").map(Number);
  const [y2, m2, d2] = b.split("-").map(Number);
  return Math.round((Date.UTC(y2, m2 - 1, d2) - Date.UTC(y1, m1 - 1, d1)) / 86400000);
}
function plural(n, uno, varios) { return `${n} ${n === 1 ? uno : varios}`; }

function guardado(clave, valor) {
  try {
    if (valor === undefined) return sessionStorage.getItem(clave);
    sessionStorage.setItem(clave, valor);
  } catch { /* el navegador puede bloquear el almacenamiento */ }
  return null;
}

/* h("div", {class: "x", onclick: fn}, hijos...) */
function h(tag, props, ...hijos) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "dataset") Object.assign(el.dataset, v);
    else if (k in el && k !== "list") el[k] = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  el.append(...hijos.flat().filter((x) => x != null && x !== false));
  return el;
}

function toast(texto, error) {
  const t = h("div", { class: error ? "toast error" : "toast" }, texto);
  document.getElementById("toasts").append(t);
  setTimeout(() => t.remove(), 4500);
}

/* ---------- API ---------- */
class ApiError extends Error {
  constructor(mensaje, status, faltantes) {
    super(mensaje);
    this.status = status;
    this.faltantes = faltantes || [];
  }
}
async function api(ruta, opciones = {}) {
  let res;
  try {
    res = await fetch(ruta, {
      method: opciones.method || "GET",
      headers: opciones.body ? { "Content-Type": "application/json" } : undefined,
      body: opciones.body ? JSON.stringify(opciones.body) : undefined,
    });
  } catch {
    throw new ApiError("No pudimos conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.", 0);
  }
  let datos = null;
  try { datos = await res.json(); } catch { /* sin cuerpo JSON */ }
  if (!res.ok) {
    throw new ApiError((datos && datos.mensaje) || "Algo salió mal. Inténtalo de nuevo.", res.status, datos && datos.faltantes);
  }
  return datos;
}
const post = (ruta, body) => api(ruta, { method: "POST", body: body || {} });

function bloqueError(e) {
  const conLista = e.faltantes && e.faltantes.length;
  // con lista de faltantes, el mensaje se queda en su primera frase para no repetir lo mismo dos veces
  const texto = conLista ? e.message.split(". ")[0].replace(/\.?$/, ".") : e.message;
  const caja = h("div", { class: "error", role: "alert" }, h("span", {}, texto));
  if (conLista) caja.append(h("ul", {}, e.faltantes.map((f) => h("li", {}, f))));
  return caja;
}

/* Ejecuta una acción deshabilitando el botón mientras espera */
async function conEspera(boton, textoEspera, accion) {
  const original = boton.textContent;
  boton.disabled = true;
  boton.textContent = textoEspera;
  try { return await accion(); } finally { boton.disabled = false; boton.textContent = original; }
}

/* ---------- navegación ---------- */
const VISTAS = { reservar: vistaReservar, renta: vistaRenta, sucursal: vistaSucursal, indicadores: vistaIndicadores };
let limpiarVista = null;

function render() {
  const tab = VISTAS[location.hash.slice(1)] ? location.hash.slice(1) : "reservar";
  document.querySelectorAll("#nav a").forEach((a) => {
    if (a.dataset.tab === tab) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  if (limpiarVista) { limpiarVista(); limpiarVista = null; }
  const main = document.getElementById("main");
  main.replaceChildren();
  limpiarVista = VISTAS[tab](main) || null;
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", render);
window.addEventListener("DOMContentLoaded", render);

function irA(tab, folio) {
  if (folio) guardado("folio", folio);
  if (location.hash === `#${tab}`) render(); else location.hash = tab;
}

/* =====================================================================
   RESERVAR
   ===================================================================== */
function vistaReservar(root) {
  const hoy = hoyISO();
  const est = { suc: "", inicio: hoy, fin: sumarDias(hoy, 3), opciones: [], elegida: null, pedido: 0 };

  const selSuc = h("select", { id: "suc" });
  const inInicio = h("input", { type: "date", id: "inicio", min: hoy, value: est.inicio });
  const inFin = h("input", { type: "date", id: "fin", min: sumarDias(hoy, 1), value: est.fin });
  const dias = h("div", { class: "dias", "aria-live": "polite" });
  const aviso = h("div", { class: "aviso-fechas", "aria-live": "polite" });
  const resultados = h("div", { "aria-live": "polite" });
  const dock = h("div");

  root.append(
    h("h1", {}, "Reserva tu auto"),
    h("p", { class: "lead" }, "Elige sucursal y fechas. Te mostramos solo lo que hay disponible, con el precio final."),
    h("div", { class: "busqueda" },
      h("div", {}, h("label", { for: "suc" }, "Sucursal"), selSuc),
      h("div", {}, h("label", { for: "inicio" }, "Recoger"), inInicio),
      h("div", {}, h("label", { for: "fin" }, "Devolver"), inFin),
      dias),
    aviso, resultados, dock);

  let temporizador = null;
  const programar = () => { clearTimeout(temporizador); temporizador = setTimeout(buscar, 250); };
  [selSuc, inInicio, inFin].forEach((el) => el.addEventListener("change", () => {
    est.suc = selSuc.value; est.inicio = inInicio.value; est.fin = inFin.value;
    if (est.inicio && est.fin && est.fin <= est.inicio && el === inInicio) {
      est.fin = sumarDias(est.inicio, 1); inFin.value = est.fin;
    }
    if (est.inicio) inFin.min = sumarDias(est.inicio, 1);
    programar();
  }));

  async function buscar() {
    const mio = ++est.pedido;
    est.elegida = null; dock.replaceChildren(); aviso.replaceChildren();
    if (!est.suc || !est.inicio || !est.fin) { resultados.replaceChildren(); dias.textContent = ""; return; }
    const n = diasEntre(est.inicio, est.fin);
    if (n < 1) {
      dias.textContent = "";
      resultados.replaceChildren();
      aviso.append(h("div", { class: "error", role: "alert" }, "La fecha de devolución debe ser posterior a la de recogida."));
      return;
    }
    if (est.inicio < hoy) {
      resultados.replaceChildren();
      aviso.append(h("div", { class: "error", role: "alert" }, "La fecha de recogida no puede ser anterior a hoy."));
      return;
    }
    dias.textContent = plural(n, "día", "días");
    resultados.replaceChildren(h("div", { class: "opciones", "aria-busy": "true" }, h("div", { class: "esqueleto" }), h("div", { class: "esqueleto" }), h("div", { class: "esqueleto" })));
    try {
      const lista = await api(`/api/disponibilidad?sucursal_id=${encodeURIComponent(est.suc)}&inicio=${est.inicio}&fin=${est.fin}`);
      if (mio !== est.pedido) return;
      est.opciones = lista.sort((a, b) => ORDEN.indexOf(a.categoria) - ORDEN.indexOf(b.categoria));
      pintar();
    } catch (e) {
      if (mio !== est.pedido) return;
      resultados.replaceChildren(bloqueError(e));
    }
  }

  function pintar() {
    if (!est.opciones.length) {
      resultados.replaceChildren(h("div", { class: "opciones" },
        h("p", { class: "vacio-msg" }, "No quedan autos en esas fechas. Prueba otra sucursal o cambia las fechas.")));
      return;
    }
    const grupo = h("div", { class: "opciones", role: "radiogroup", "aria-label": "Categorías disponibles" },
      est.opciones.map((o) => {
        const puntos = h("span", { class: "puntos", "aria-hidden": "true" },
          Array.from({ length: Math.min(o.lugares, 5) }, () => h("i")));
        const texto = o.lugares === 1 ? "Última unidad" : `${o.lugares} disponibles`;
        const b = h("button", {
          type: "button", class: "opcion", role: "radio", "aria-checked": "false", dataset: { cat: o.categoria },
          onclick: () => elegir(o.categoria),
        },
        h("div", {}, h("div", { class: "nombre" }, nombreCat(o.categoria)),
          h("div", { class: "disp" }, puntos, h("span", {}, texto))),
        h("div", { class: "precio" }, h("div", { class: "total num" }, dinero(o.total)),
          h("div", { class: "dia num" }, `${dinero(o.tarifa_diaria)} por día`)));
        return b;
      }));
    resultados.replaceChildren(grupo);
  }

  function elegir(cat) {
    est.elegida = cat;
    resultados.querySelectorAll(".opcion").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.cat === cat)));
    const o = est.opciones.find((x) => x.categoria === cat);
    const nombre = h("input", { type: "text", id: "cliente", autocomplete: "name", maxLength: 80, placeholder: "Nombre y apellido" });
    const msg = h("div");
    const boton = h("button", { type: "submit", class: "btn" }, `Reservar por ${dinero(o.total)}`);
    const form = h("form", { class: "reserva", novalidate: true, onsubmit: async (ev) => {
      ev.preventDefault();
      msg.replaceChildren();
      if (!nombre.value.trim()) {
        msg.append(h("div", { class: "error", role: "alert" }, "Escribe el nombre del cliente."));
        nombre.focus();
        return;
      }
      try {
        const r = await conEspera(boton, "Reservando…", () => post("/api/reservaciones", {
          cliente: nombre.value.trim(), sucursal_id: est.suc, categoria: cat, inicio: est.inicio, fin: est.fin,
        }));
        confirmacion(r);
      } catch (e) {
        if (e.status === 409) {           // la disponibilidad cambió: se actualiza la lista y se explica
          await buscar();
          aviso.replaceChildren(bloqueError(e));
        } else msg.append(bloqueError(e));
      }
    } },
    h("div", { class: "resumen" }, h("b", {}, nombreCat(cat)), ` · ${plural(diasEntre(est.inicio, est.fin), "día", "días")} · del ${fecha(est.inicio)} al ${fecha(est.fin)}`),
    h("div", {}, h("label", { for: "cliente" }, "Nombre del cliente"), nombre),
    boton, msg);
    dock.replaceChildren(form);
    form.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function confirmacion(r) {
    guardado("folio", r.folio);
    root.replaceChildren(h("section", { class: "confirmacion" },
      h("h1", {}, "¡Reserva confirmada!"),
      h("p", { class: "muted" }, "Guarda tu folio: lo necesitas para recoger el auto y consultar tu renta."),
      h("div", { class: "folio", "aria-label": `Folio ${r.folio}` }, r.folio),
      h("p", {}, `${nombreCat(r.categoria)} · ${fecha(r.inicio)} al ${fecha(r.fin)} · `, h("b", { class: "num" }, dinero(r.total))),
      h("p", { class: "muted" }, r.mensaje || ""),
      h("div", { class: "acciones" },
        h("button", { type: "button", class: "btn", onclick: () => irA("renta", r.folio) }, "Ver mi renta"),
        h("button", { type: "button", class: "btn sec", onclick: async (ev) => {
          try { await navigator.clipboard.writeText(r.folio); toast("Folio copiado"); } catch { toast("No se pudo copiar. Anótalo manualmente.", true); }
          ev.target.blur();
        } }, "Copiar folio"),
        h("button", { type: "button", class: "btn sec", onclick: () => irA("reservar") }, "Hacer otra reserva"))));
    root.querySelector(".confirmacion h1").setAttribute("tabindex", "-1");
    root.querySelector(".confirmacion h1").focus();
  }

  (async () => {
    try {
      const sucs = await api("/api/sucursales");
      selSuc.replaceChildren(...sucs.map((s) => h("option", { value: s.id }, s.nombre)));
      est.suc = selSuc.value;
      buscar();
    } catch (e) { resultados.replaceChildren(bloqueError(e)); }
  })();
  return () => clearTimeout(temporizador);
}

/* =====================================================================
   MI RENTA (cliente)  y  SUCURSAL (personal): comparten el panel de seguimiento
   ===================================================================== */
function vistaRenta(root) {
  const entrada = h("input", { type: "text", id: "folio", placeholder: "Por ejemplo, F-1A2B3C4D", autocomplete: "off", autocapitalize: "characters", spellcheck: false });
  const salida = h("div", { "aria-live": "polite" });
  const buscar = async () => {
    const folio = entrada.value.trim().toUpperCase();
    if (!folio) { salida.replaceChildren(h("div", { class: "error", role: "alert" }, "Escribe tu folio para buscar tu renta.")); return; }
    guardado("folio", folio);
    await panelFolio(salida, folio, "cliente");
  };
  root.append(
    h("h1", {}, "Mi renta"),
    h("p", { class: "lead" }, "Consulta el estado de tu renta, extiéndela o revisa tus cargos con tu folio."),
    h("form", { class: "buscador", onsubmit: (ev) => { ev.preventDefault(); buscar(); } },
      h("div", {}, h("label", { for: "folio" }, "Folio de reserva"), entrada),
      h("button", { type: "submit", class: "btn" }, "Buscar")),
    salida);
  const previo = guardado("folio");
  if (previo) { entrada.value = previo; buscar(); } else entrada.focus();
}

async function cargarFolio(folio) {
  const reserva = await api(`/api/reservaciones/${encodeURIComponent(folio)}`);
  const rentas = await api("/api/rentas");
  return { reserva, renta: rentas.find((r) => r.folio === reserva.folio) || null };
}

let alCambiarPersonal = null;   // la vista Sucursal registra aquí cómo actualizar la lista de limpieza

async function panelFolio(contenedor, folio, modo) {
  contenedor.replaceChildren(h("div", { class: "panel" }, h("div", { class: "esqueleto" })));
  const refrescar = () => {
    panelFolio(contenedor, folio, modo);
    if (modo === "personal" && alCambiarPersonal) alCambiarPersonal();
  };
  try {
    const { reserva, renta } = await cargarFolio(folio);
    contenedor.replaceChildren(...resumenRenta(reserva, renta, modo, refrescar));
  } catch (e) {
    contenedor.replaceChildren(bloqueError(e));
  }
}

function pasoActual(renta) {
  if (!renta || renta.estado === "PENDIENTE") return 0;
  return renta.estado === "ENTREGADO" ? 1 : 2;
}

function mensajeEstado(reserva, renta) {
  if (!renta) return "Tu reserva está confirmada. Presenta tu folio en la sucursal para recoger tu auto.";
  if (renta.estado === "PENDIENTE") return "Tu contrato está listo. Pasa a la sucursal con tus documentos para recoger tu auto.";
  if (renta.estado === "ENTREGADO") return `Disfruta tu renta. Devuélvela el ${fecha(renta.fin)}; después de esa fecha se cobra retraso por hora.`;
  return "Gracias por rentar con NovaRent. Aquí está el detalle final de tu renta.";
}

function resumenRenta(reserva, renta, modo, refrescar) {
  const paso = pasoActual(renta);
  const base = renta || reserva;
  const catAsignada = renta ? renta.categoria_asignada : reserva.categoria;
  const upgrade = renta && renta.categoria_asignada !== renta.categoria_reservada;
  const estadoTxt = !renta ? "Reserva confirmada" : { PENDIENTE: "Por entregar", ENTREGADO: "En renta", DEVUELTO: "Devuelta" }[renta.estado];

  const cerrada = renta && renta.estado === "DEVUELTO";   // en la última etapa todo queda completado
  const etapas = ["Reservada", "En renta", "Devuelta"].map((t, i) =>
    h("li", { class: i < paso || (cerrada && i === paso) ? "hecho" : i === paso ? "actual" : "", "aria-current": i === paso && !cerrada ? "step" : null }, t));

  const total = renta ? renta.total_renta : (centavos(reserva.tarifa_diaria) * reserva.dias) / 100;
  const panel = h("section", { class: "panel" },
    h("div", { class: "panel-cab" },
      h("div", { class: "folio-chico" }, reserva.folio),
      h("span", { class: renta && renta.estado === "DEVUELTO" ? "etiqueta ok" : "etiqueta" }, estadoTxt)),
    h("p", { class: "muted" }, `A nombre de ${reserva.cliente_id}`),
    h("ol", { class: "ruta", "aria-label": "Avance de la renta" }, etapas),
    h("p", {}, mensajeEstado(reserva, renta)),
    h("dl", { class: "datos" },
      dato("Categoría", nombreCat(catAsignada) + (upgrade ? ` (upgrade desde ${nombreCat(renta.categoria_reservada)})` : "")),
      dato("Recoger", fecha(base.inicio)),
      dato("Devolver", fecha(base.fin)),
      dato("Tarifa por día", dinero(base.tarifa_diaria)),
      renta && renta.vehiculo_id ? dato("Vehículo", renta.vehiculo_id) : null,
      dato("Renta total", dinero(total))));

  const bloques = [panel];
  if (renta && renta.estado === "DEVUELTO") bloques.push(panelCargos(renta));
  if (modo === "cliente" && renta && renta.estado === "ENTREGADO") bloques.push(formExtension(renta, refrescar));
  if (modo === "personal") bloques.push(...accionesPersonal(reserva, renta, refrescar));
  return bloques;
}
const dato = (t, v) => h("div", {}, h("dt", {}, t), h("dd", {}, v));

function panelCargos(renta) {
  const cab = h("h2", {}, "Cargos de la devolución");
  const filas = renta.cargos.map((c) => h("tr", {}, h("td", {}, CONCEPTO[c.concepto] || c.concepto, h("div", { class: "muted" }, c.detalle)), h("td", { class: "der" }, dinero(c.monto))));
  const totalFinal = (centavos(renta.total_renta) + centavos(renta.total_cargos)) / 100;
  const tabla = renta.cargos.length
    ? h("table", {},
      h("thead", {}, h("tr", {}, h("th", {}, "Concepto"), h("th", { class: "der" }, "Importe"))),
      h("tbody", {}, filas),
      h("tfoot", {}, h("tr", {}, h("td", {}, "Total de cargos"), h("td", { class: "der" }, dinero(renta.total_cargos)))))
    : h("div", { class: "exito" }, "Sin cargos adicionales: devolviste el auto en las condiciones acordadas.");
  const cmp = renta.comparacion;
  const resumen = cmp ? h("dl", { class: "datos" },
    dato("Kilómetros recorridos", `${cmp.km_recorridos.toLocaleString("es-MX")} km`),
    dato("Combustible faltante", cmp.octavos_faltantes ? `${cmp.octavos_faltantes}/8 de tanque` : "Ninguno"),
    dato("Daños nuevos", cmp.danos_nuevos.length ? cmp.danos_nuevos.join(", ") : "Ninguno")) : null;
  return h("section", { class: "panel" }, cab, tabla, resumen,
    h("p", { class: "num", style: "margin-top:14px;font-weight:700" }, `Total de la renta con cargos: ${dinero(totalFinal)}`));
}

function formExtension(renta, refrescar) {
  const min = sumarDias(renta.fin, 1);
  const nueva = h("input", { type: "date", id: "nueva-fin", min, value: min });
  const msg = h("div");
  const boton = h("button", { type: "submit", class: "btn" }, "Extender renta");
  return h("form", { class: "panel", novalidate: true, onsubmit: async (ev) => {
    ev.preventDefault(); msg.replaceChildren();
    try {
      const r = await conEspera(boton, "Extendiendo…", () => post(`/api/rentas/${renta.id_renta}/extension`, { nueva_fin: nueva.value }));
      toast(`Renta extendida hasta el ${fecha(r.fin)}`);
      refrescar();
    } catch (e) { msg.append(bloqueError(e)); }
  } },
  h("h2", {}, "¿Necesitas más días?"),
  h("p", { class: "muted" }, "Elige la nueva fecha de devolución. La extensión depende de que haya lugar en tu categoría."),
  h("div", { class: "campo", style: "max-width:260px" }, h("label", { for: "nueva-fin" }, "Nueva fecha de devolución"), nueva),
  boton, msg);
}

/* =====================================================================
   SUCURSAL (personal)
   ===================================================================== */
function vistaSucursal(root) {
  const entrada = h("input", { type: "text", id: "folio-s", placeholder: "Folio del cliente", autocomplete: "off", autocapitalize: "characters", spellcheck: false });
  const salida = h("div", { "aria-live": "polite" });
  const lista = h("div");
  const atender = () => {
    const folio = entrada.value.trim().toUpperCase();
    if (!folio) { salida.replaceChildren(h("div", { class: "error", role: "alert" }, "Escribe el folio del cliente.")); return; }
    guardado("folio", folio);
    panelFolio(salida, folio, "personal");
  };
  root.append(
    h("h1", {}, "Sucursal"),
    h("p", { class: "lead" }, "Atiende a un cliente con su folio: abre el contrato, entrega el auto y regístralo al devolverlo."),
    h("form", { class: "buscador", onsubmit: (ev) => { ev.preventDefault(); atender(); } },
      h("div", {}, h("label", { for: "folio-s" }, "Folio de reserva"), entrada),
      h("button", { type: "submit", class: "btn" }, "Atender")),
    salida, h("hr", { class: "separador" }), lista);
  const previo = guardado("folio");
  if (previo) entrada.value = previo;
  alCambiarPersonal = () => panelLimpieza(lista);
  panelLimpieza(lista);
  return () => { alCambiarPersonal = null; };
}

async function panelLimpieza(lista) {
  const refrescar = () => panelLimpieza(lista);
  try {
    const autos = await api("/api/limpieza");
    lista.replaceChildren(h("section", { class: "panel" },
      h("h2", {}, "Autos en limpieza"),
      autos.length ? h("ul", { class: "lista-limpieza" }, autos.map((v) => h("li", {},
        h("div", {}, h("b", {}, v.id), h("div", { class: "muted" }, `${nombreCat(v.categoria)} · ${v.sucursal_id}`)),
        h("button", { type: "button", class: "btn chico", onclick: async (ev) => {
          try {
            await conEspera(ev.currentTarget, "Guardando…", () => post(`/api/vehiculos/${encodeURIComponent(v.id)}/limpieza-terminada`));
            toast(`${v.id} está disponible`);
            refrescar();
          } catch (e) { toast(e.message, true); }
        } }, "Marcar disponible"))))
        : h("p", { class: "muted" }, "No hay autos en limpieza. Cuando se devuelva uno, aparecerá aquí.")));
  } catch (e) { lista.replaceChildren(bloqueError(e)); }
}

/* Captura del estado físico del auto (combustible, kilometraje, daños) */
function camposFisico(prefijo, { combustible = 8, km = "", minKm = 0 } = {}) {
  const rango = h("input", { type: "range", id: `${prefijo}-comb`, min: 0, max: 8, step: 1, value: combustible });
  const salida = h("output", { for: `${prefijo}-comb` }, `${combustible}/8`);
  rango.addEventListener("input", () => { salida.textContent = `${rango.value}/8`; });
  const inKm = h("input", { type: "number", id: `${prefijo}-km`, min: minKm, step: 1, inputMode: "numeric", value: km, placeholder: "Por ejemplo, 12500" });
  const danos = [];
  const chips = h("div", { class: "chips" });
  const inDano = h("input", { type: "text", id: `${prefijo}-dano`, maxLength: 60, placeholder: "Por ejemplo, rayón en puerta" });
  const pintar = () => chips.replaceChildren(...danos.map((d, i) => h("span", { class: "chip" }, d,
    h("button", { type: "button", "aria-label": `Quitar ${d}`, onclick: () => { danos.splice(i, 1); pintar(); } }, "×"))));
  const agregar = () => {
    const t = inDano.value.trim();
    if (t && !danos.includes(t)) { danos.push(t); pintar(); }
    inDano.value = ""; inDano.focus();
  };
  inDano.addEventListener("keydown", (ev) => { if (ev.key === "Enter") { ev.preventDefault(); agregar(); } });
  const el = h("div", {},
    h("div", { class: "campo" }, h("label", { for: `${prefijo}-comb` }, "Combustible (octavos de tanque)"),
      h("div", { class: "combustible" }, rango, salida)),
    h("div", { class: "campo" }, h("label", { for: `${prefijo}-km` }, "Kilometraje"), inKm),
    h("div", { class: "campo" }, h("label", { for: `${prefijo}-dano` }, "Daños visibles (opcional)"),
      h("div", { class: "agregar" }, inDano, h("button", { type: "button", class: "btn sec", onclick: agregar }, "Agregar")), chips));
  return { el, valores: () => ({ combustible_octavos: Number(rango.value), kilometraje: inKm.value === "" ? null : Number(inKm.value), danos: danos.slice() }) };
}

function accionesPersonal(reserva, renta, refrescar) {
  if (!renta) {
    if (reserva.estado !== "CONFIRMADA") return [h("div", { class: "info" }, "Esta reserva no está confirmada, así que todavía no se puede abrir el contrato.")];
    const msg = h("div");
    const boton = h("button", { type: "button", class: "btn", onclick: async () => {
      msg.replaceChildren();
      try { await conEspera(boton, "Abriendo…", () => post("/api/rentas", { folio: reserva.folio })); toast("Contrato abierto"); refrescar(); }
      catch (e) { msg.append(bloqueError(e)); }
    } }, "Abrir contrato");
    return [h("section", { class: "panel" }, h("h2", {}, "Siguiente paso"), h("p", { class: "muted" }, "El cliente llegó con su reserva. Abre el contrato para registrar la entrega."), boton, msg)];
  }
  if (renta.estado === "PENDIENTE") return [formEntrega(renta, refrescar)];
  if (renta.estado === "ENTREGADO") return [formDevolucion(renta, refrescar)];
  return [h("div", { class: "info" }, "La renta ya está cerrada. El auto pasó a limpieza y volverá a estar disponible cuando termine.")];
}

function formEntrega(renta, refrescar) {
  const ident = h("input", { type: "checkbox", id: "e-ident" });
  const lic = h("input", { type: "checkbox", id: "e-lic" });
  const tarjeta = h("input", { type: "text", id: "e-tarjeta", inputMode: "numeric", autocomplete: "off", maxLength: 19, placeholder: "Tarjeta para el depósito" });
  const fisico = camposFisico("e");
  const msg = h("div"); const extra = h("div");
  const boton = h("button", { type: "submit", class: "btn" }, "Registrar entrega");
  return h("form", { class: "panel", novalidate: true, onsubmit: async (ev) => {
    ev.preventDefault(); msg.replaceChildren(); extra.replaceChildren();
    const f = fisico.valores();
    const cuerpo = { identificacion_valida: ident.checked, licencia_vigente: lic.checked, tarjeta: tarjeta.value.trim() };
    if (f.kilometraje !== null) Object.assign(cuerpo, f);
    try {
      const r = await conEspera(boton, "Registrando…", () => post(`/api/rentas/${renta.id_renta}/entrega`, cuerpo));
      toast(`Entrega registrada · ${r.vehiculo_id}`);
      refrescar();
    } catch (e) {
      msg.append(bloqueError(e));
      if (e.status === 409 && /upgrade/i.test(e.message)) extra.append(ofertaUpgrade(renta, refrescar));
    }
  } },
  h("h2", {}, "Entrega del auto"),
  h("p", { class: "muted" }, "Sin identificación, licencia, pago y checklist inicial, la entrega se bloquea y te decimos qué falta."),
  h("label", { class: "check" }, ident, "Identificación oficial verificada"),
  h("label", { class: "check" }, lic, "Licencia de conducir vigente"),
  h("div", { class: "campo" }, h("label", { for: "e-tarjeta" }, "Tarjeta (se simula el depósito; no se guarda)"), tarjeta),
  h("hr", { class: "separador" }),
  h("h2", {}, "Checklist inicial"),
  fisico.el, boton, msg, extra);
}

function ofertaUpgrade(renta, refrescar) {
  const superiores = ORDEN.slice(ORDEN.indexOf(renta.categoria_reservada) + 1);
  const sel = h("select", { id: "up-cat", "aria-label": "Categoría superior" }, superiores.map((c) => h("option", { value: c }, nombreCat(c))));
  const msg = h("div");
  const boton = h("button", { type: "button", class: "btn", onclick: async () => {
    msg.replaceChildren();
    try {
      await conEspera(boton, "Aplicando…", () => post(`/api/rentas/${renta.id_renta}/upgrade`, { categoria_destino: sel.value }));
      toast("Upgrade aplicado sin costo extra. Ahora registra la entrega.");
      refrescar();
    } catch (e) { msg.append(bloqueError(e)); }
  } }, "Autorizar upgrade sin costo");
  return h("div", { class: "info" },
    h("b", {}, "No hay unidades de la categoría reservada."),
    h("p", { style: "margin:6px 0 10px" }, "Puedes entregar una categoría superior conservando la tarifa original."),
    superiores.length ? h("div", { class: "agregar" }, sel, boton) : h("p", {}, "No hay una categoría superior disponible."),
    msg);
}

function formDevolucion(renta, refrescar) {
  const ini = renta.checklist_inicial || { combustible_octavos: 8, kilometraje: 0 };
  const fisico = camposFisico("d", { combustible: ini.combustible_octavos, km: "", minKm: ini.kilometraje });
  const hora = h("input", { type: "datetime-local", id: "d-hora" });
  const msg = h("div");
  const boton = h("button", { type: "submit", class: "btn" }, "Registrar devolución");
  return h("form", { class: "panel", novalidate: true, onsubmit: async (ev) => {
    ev.preventDefault(); msg.replaceChildren();
    const f = fisico.valores();
    if (f.kilometraje === null) { msg.append(h("div", { class: "error", role: "alert" }, "Captura el kilometraje final del vehículo.")); return; }
    const cuerpo = { ...f };
    if (hora.value) cuerpo.fecha_hora = hora.value;
    try {
      const r = await conEspera(boton, "Registrando…", () => post(`/api/rentas/${renta.id_renta}/devolucion`, cuerpo));
      toast(r.cargos.length ? `Devolución registrada con ${plural(r.cargos.length, "cargo", "cargos")}` : "Devolución registrada sin cargos");
      refrescar();
    } catch (e) { msg.append(bloqueError(e)); }
  } },
  h("h2", {}, "Devolución del auto"),
  h("p", { class: "muted" }, `Entrega: ${ini.combustible_octavos}/8 de combustible y ${Number(ini.kilometraje).toLocaleString("es-MX")} km. Al registrar la devolución se calculan los cargos automáticamente.`),
  fisico.el,
  h("div", { class: "campo", style: "max-width:300px" }, h("label", { for: "d-hora" }, "Fecha y hora de devolución (opcional, por defecto ahora)"), hora),
  boton, msg);
}

/* =====================================================================
   INDICADORES
   ===================================================================== */
function vistaIndicadores(root) {
  const zona = h("div", { "aria-live": "polite" });
  const boton = h("button", { type: "button", class: "btn sec chico", onclick: () => cargar() }, "Actualizar");
  root.append(h("h1", {}, "Indicadores"),
    h("p", { class: "lead" }, "Así va la operación: sin sobreventas, devoluciones más rápidas y cobros claros."), zona);
  zona.append(h("div", { class: "tablero" }, h("div", { class: "esqueleto" })));
  const cabecera = h("div", { class: "acciones", style: "margin:0 0 14px" }, boton);
  root.insertBefore(cabecera, zona);

  async function cargar() {
    try {
      const k = await api("/api/kpis");
      zona.replaceChildren(tablero(k));
    } catch (e) { zona.replaceChildren(bloqueError(e)); }
  }
  cargar();
  const reloj = setInterval(cargar, 15000);
  return () => clearInterval(reloj);
}

function barras(obj, etiquetas) {
  const claves = Object.keys(etiquetas);
  const max = Math.max(1, ...claves.map((c) => obj[c] || 0));
  return h("div", { class: "barras" }, claves.map((c) => h("div", { class: "barra" },
    h("span", {}, etiquetas[c]),
    h("div", { class: "pista" }, h("div", { class: "relleno", style: `width:${((obj[c] || 0) / max) * 100}%` })),
    h("b", {}, String(obj[c] || 0)))));
}

function tablero(k) {
  const min = k.minutos_devolucion_a_disponible;
  const cargos = Object.entries(k.cargos_por_concepto);
  return h("div", { class: "tablero" },
    h("div", { class: "dato" },
      h("div", { class: "valor" }, String(k.sobreventas)),
      h("div", {}, "Sobreventas"),
      h("div", { class: "nota" }, k.sobreventas === 0 ? "Cumple la meta: cero sobreventas." : "Hay más reservas que autos: hay que revisar el inventario.")),
    h("div", { class: "dato" },
      h("div", { class: "valor" }, min == null ? "Sin datos" : `${min.toLocaleString("es-MX")} min`),
      h("div", {}, "Devolución a disponible"),
      h("div", { class: "nota" }, "Tiempo promedio entre que se devuelve un auto y queda listo para rentar.")),
    h("div", { class: "dato" },
      h("div", { class: "valor num" }, dinero(k.cobros_por_danos.total)),
      h("div", {}, "Cobros por daños"),
      h("div", { class: "nota" }, `${plural(k.cobros_por_danos.cantidad, "cobro registrado", "cobros registrados")}, cada uno con su detalle.`)),
    h("div", { class: "dato" }, h("div", {}, "Rentas por estado"), barras(k.rentas_por_estado, ESTADO_RENTA)),
    h("div", { class: "dato" }, h("div", {}, "Autos por estado"), barras(k.vehiculos_por_estado, ESTADO_AUTO)),
    h("div", { class: "dato ancho" }, h("div", {}, "Cargos por concepto"),
      cargos.length ? h("table", {}, h("tbody", {}, cargos.map(([c, v]) => h("tr", {}, h("td", {}, CONCEPTO[c] || c, h("div", { class: "muted" }, plural(v.cantidad, "cargo", "cargos"))), h("td", { class: "der" }, dinero(v.total))))))
        : h("p", { class: "nota" }, "Todavía no hay cargos registrados.")));
}
