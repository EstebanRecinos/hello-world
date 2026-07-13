/* ORBITA-LINK — portal cliente (SPA sin framework).
   Habla con /api/v1; el borrador se guarda en el servidor desde el paso 1. */

"use strict";

const API = "/api/v1";

/* ── sesión ──────────────────────────────────────────────────────────── */

const session = {
  get token() { return sessionStorage.getItem("token"); },
  get name() { return sessionStorage.getItem("name"); },
  set({ token, name }) { sessionStorage.setItem("token", token); sessionStorage.setItem("name", name); },
  clear() { sessionStorage.clear(); },
};

async function api(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (session.token) headers.Authorization = `Bearer ${session.token}`;
  const resp = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const data = resp.status === 204 ? null : await resp.json().catch(() => null);
  if (!resp.ok) throw { status: resp.status, detail: data && data.detail };
  return data;
}

/* ── utilidades ──────────────────────────────────────────────────────── */

const $ = (sel, el = document) => el.querySelector(sel);
const view = $("#view");

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.hidden = true; }, 6000);
}

function money(cents) {
  return new Intl.NumberFormat("es", { style: "currency", currency: "USD", maximumFractionDigits: 0 })
    .format(cents / 100);
}

function fecha(iso) {
  return new Date(iso).toLocaleDateString("es", { day: "numeric", month: "long", year: "numeric" });
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

let pendingDirection = 0; // -1 atrás, 0 sin animación, 1 adelante

function render(html) {
  view.classList.remove("view-fwd", "view-back");
  if (pendingDirection !== 0) {
    void view.offsetWidth; // reinicia la animación
    view.classList.add(pendingDirection > 0 ? "view-fwd" : "view-back");
  }
  pendingDirection = 0;
  view.innerHTML = html;
  const h1 = $("h1", view);
  if (h1) { h1.setAttribute("tabindex", "-1"); h1.focus(); }
  updateChrome();
}

/* Ilustraciones ligeras (SVG inline) — todas variaciones del arco del logo. */
const ILLOS = {
  // sin cargas: la trayectoria lista, la carga aún no sale
  vacio: `<svg viewBox="0 0 64 64" aria-hidden="true">
    <path d="M 48.97 15.03 A 24 24 0 1 0 56 32" fill="none" stroke="currentColor"
          stroke-width="3.5" stroke-linecap="round" stroke-dasharray="2 7"/>
    <circle class="dot" cx="32" cy="32" r="5"/></svg>`,
  // sin vuelos: el punto espera fuera del arco
  sinVuelos: `<svg viewBox="0 0 64 64" aria-hidden="true">
    <path d="M 48.97 15.03 A 24 24 0 1 0 56 32" fill="none" stroke="currentColor"
          stroke-width="3.5" stroke-linecap="round"/>
    <circle class="dot" cx="10" cy="10" r="5"/>
    <path d="M 17 17 L 24 24" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-dasharray="1 5"/></svg>`,
  // sin conexión: el arco cortado
  sinConexion: `<svg viewBox="0 0 64 64" aria-hidden="true">
    <path d="M 48.97 15.03 A 24 24 0 0 0 10 20" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"/>
    <path d="M 12 46 A 24 24 0 0 0 56 32" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"/>
    <circle class="dot" cx="55.9" cy="21.4" r="5.5"/></svg>`,
  // enlace inválido: el punto con interrogación
  noEncontrado: `<svg viewBox="0 0 64 64" aria-hidden="true">
    <path d="M 48.97 15.03 A 24 24 0 1 0 56 32" fill="none" stroke="currentColor"
          stroke-width="3.5" stroke-linecap="round"/>
    <text x="32" y="39" text-anchor="middle" font-size="20" font-weight="700" fill="currentColor">?</text></svg>`,
};

function emptyState(illo, title, body, cta) {
  return `<div class="empty">${ILLOS[illo]}<h2>${title}</h2><p>${body}</p>
    ${cta ? `<div class="btnrow" style="justify-content:center">${cta}</div>` : ""}</div>`;
}

function updateChrome() {
  const chip = $("#userchip"), out = $("#logout");
  const logged = Boolean(session.token);
  chip.hidden = out.hidden = !logged;
  if (logged) chip.textContent = session.name;
}

$("#logout").addEventListener("click", () => { session.clear(); location.hash = "#/entrar"; });

const STATE_WORDS = {
  draft: ["Borrador", ""], quoted: ["Con precio", "acc"], booked: ["Reservado", "ok"],
  integrated: ["En el cohete", "ok"], launched: ["Lanzado", "ok"], deployed: ["En órbita", "ok"],
  closed: ["Completado", "ok"], cancelled: ["Cancelado", "warn"],
};

function statePill(status) {
  const [word, cls] = STATE_WORDS[status] || [status, ""];
  return `<span class="pill ${cls}">${word}</span>`;
}

function comparacion(kg) {
  if (kg == null) return "";
  if (kg <= 2) return "como una botella grande de agua";
  if (kg <= 15) return "como una caja de zapatos grande llena de libros";
  if (kg <= 60) return "como una maleta grande de viaje";
  if (kg <= 200) return "como un refrigerador";
  return "como un piano pequeño";
}

const STEP_TITLES = [
  "¿Cómo se llama tu carga?",
  "¿Cuánto pesa y cuánto mide?",
  "¿A dónde va?",
  "Tres preguntas de seguridad",
  "¿Tienes permiso para lanzarla?",
  "Revisa y confirma",
];

const FIELD_STEP = {
  mass_kg: 2, length_m: 2, width_m: 2, height_m: 2,
  target_orbit_name: 3, target_inclination_deg: 3, target_altitude_km: 3,
};

function progressBar(step) {
  return `<div class="progress">
    <div class="bar" role="progressbar" aria-valuenow="${step}" aria-valuemin="1" aria-valuemax="6"
         aria-label="Paso ${step} de 6"><i style="width:${(step / 6) * 100}%"></i></div>
    <span class="label">Paso ${step} de 6</span></div>`;
}

/* ── vistas ──────────────────────────────────────────────────────────── */

function vEntrar() {
  render(`
    <h1>Envía tu carga al espacio</h1>
    <p class="lead">Te acompañamos paso a paso: registra tu carga, compara vuelos con precio claro y sigue tu envío hasta la órbita. Sin conocimientos técnicos.</p>
    <div class="card">
      <form id="f">
        <div class="field">
          <label for="name">¿Cómo te llamas o cómo se llama tu organización?</label>
          <p class="hint">Versión de prueba: entras solo con un nombre, sin contraseña.</p>
          <input id="name" type="text" required minlength="2" maxlength="60" autocomplete="organization">
        </div>
        <button class="btn" type="submit">Entrar</button>
      </form>
    </div>`);
  $("#f").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = $("#name").value.trim();
    if (!name) return;
    const { access_token } = await api("/auth/dev-token", { method: "POST", body: { subject: name, role: "customer" } });
    session.set({ token: access_token, name });
    location.hash = "#/cargas";
  });
}

async function vCargas() {
  const list = await api("/manifests");
  const rows = list.map(m => `
    <li class="card mrow">
      <div>
        <div class="t">${esc(m.name)}</div>
        ${statePill(m.status)}
        ${m.status === "draft" && !m.is_complete ? '<span class="pill warn">Registro sin terminar</span>' : ""}
        ${m.needs_review ? '<span class="pill acc">Un asesor revisará tus respuestas</span>' : ""}
      </div>
      <div class="btnrow" style="margin:0">
        ${m.status === "draft"
          ? `<a class="btn ghost" href="#/carga/${m.id}/paso/${m.is_complete ? 6 : firstMissingStep(m)}">Continuar</a>`
          : m.status === "quoted"
            ? `<a class="btn ghost" href="#/carga/${m.id}/opciones">Ver opciones</a>`
            : `<a class="btn ghost" href="#/tracking/${m.tracking_token}">Seguir envío</a>`}
      </div>
    </li>`).join("");
  render(`
    <h1>Mis cargas</h1>
    <p class="lead">Aquí están tus envíos. Puedes retomar un registro donde lo dejaste: se guarda solo.</p>
    <ul class="mlist">${rows || ""}</ul>
    ${!rows ? emptyState("vacio", "Tu primera carga te espera",
        "Registrarla toma unos minutos y tu avance se guarda solo.",
        '<a class="btn" href="#/nueva">Registrar mi primera carga</a>') : ""}
    ${rows ? '<div class="btnrow"><a class="btn" href="#/nueva">Registrar una carga nueva</a></div>' : ""}`);
}

function firstMissingStep(m) {
  const steps = (m.missing_fields || []).map(f => FIELD_STEP[f] || 6);
  return steps.length ? Math.min(...steps) : 6;
}

/* paso 1: nombre (crea o renombra el borrador) */
async function vPaso1(id) {
  const m = id ? await api(`/manifests/${id}`) : null;
  render(`
    ${progressBar(1)}
    <h1>${STEP_TITLES[0]}</h1>
    <p class="lead">Un nombre para reconocerla, por ejemplo “Satélite escolar Quetzal-1”.</p>
    <div class="card"><form id="f">
      <div class="field">
        <label for="name">Nombre de tu carga</label>
        <input id="name" type="text" required minlength="1" maxlength="200" value="${esc(m ? m.name : "")}">
      </div>
      <div class="btnrow">
        <a class="btn ghost" href="#/cargas">Atrás</a>
        <button class="btn" type="submit">Continuar</button>
      </div>
    </form></div>
    <p class="hint">Tu avance se guarda automáticamente en cada paso.</p>`);
  $("#f").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = $("#name").value.trim();
    const saved = id
      ? await api(`/manifests/${id}`, { method: "PATCH", body: { name } })
      : await api("/manifests", { method: "POST", body: { name } });
    location.hash = `#/carga/${saved.id}/paso/2`;
  });
}

/* paso 2: peso y medidas */
async function vPaso2(id) {
  const m = await api(`/manifests/${id}`);
  const cm = v => (v == null ? "" : Math.round(v * 100));
  render(`
    ${progressBar(2)}
    <h1>${STEP_TITLES[1]}</h1>
    <div class="card"><form id="f">
      <div class="field">
        <label for="kg">Peso, en kilogramos</label>
        <p class="hint">Aceptamos cargas de hasta 500 kg en este servicio.</p>
        <input id="kg" type="number" required min="0.1" max="500" step="0.1" inputmode="decimal"
               value="${m.mass_kg ?? ""}">
        <p class="field-error" id="kg-err" hidden></p>
      </div>
      <fieldset>
        <legend>Medidas de la caja que la contiene, en centímetros</legend>
        <div class="grid3">
          <div class="field"><label for="l">Largo</label>
            <input id="l" type="number" required min="1" step="1" inputmode="numeric" value="${cm(m.length_m)}"></div>
          <div class="field"><label for="w">Ancho</label>
            <input id="w" type="number" required min="1" step="1" inputmode="numeric" value="${cm(m.width_m)}"></div>
          <div class="field"><label for="h">Alto</label>
            <input id="h" type="number" required min="1" step="1" inputmode="numeric" value="${cm(m.height_m)}"></div>
        </div>
      </fieldset>
      <p class="compare" id="cmp" ${m.mass_kg == null ? "hidden" : ""}>✓ Tu carga: ${m.mass_kg ?? ""} kg, ${comparacion(m.mass_kg)}.</p>
      <div class="btnrow">
        <a class="btn ghost" href="#/carga/${id}/paso/1">Atrás</a>
        <button class="btn" type="submit">Continuar</button>
      </div>
    </form></div>`);

  $("#kg").addEventListener("input", () => {
    const kg = parseFloat($("#kg").value);
    const err = $("#kg-err"), cmp = $("#cmp");
    if (kg > 500) {
      err.textContent = "Ese peso supera los 500 kg de este servicio. Si tu carga pesa más, escríbenos y te conectamos con un lanzamiento dedicado.";
      err.hidden = false; cmp.hidden = true;
    } else {
      err.hidden = true;
      if (kg > 0) { cmp.textContent = `✓ Tu carga: ${kg} kg, ${comparacion(kg)}.`; cmp.hidden = false; }
      else cmp.hidden = true;
    }
  });

  $("#f").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
      mass_kg: parseFloat($("#kg").value),
      length_m: parseFloat($("#l").value) / 100,
      width_m: parseFloat($("#w").value) / 100,
      height_m: parseFloat($("#h").value) / 100,
    };
    await api(`/manifests/${id}`, { method: "PATCH", body });
    location.hash = `#/carga/${id}/paso/3`;
  });
}

/* paso 3: destino */
const DESTINOS = {
  leo: { orbit: "LEO", inc: 51.6, alt: 420 },
  sso: { orbit: "SSO", inc: 97.5, alt: 550 },
};

async function vPaso3(id) {
  const m = await api(`/manifests/${id}`);
  const preset = m.target_orbit_name === "SSO" ? "sso" : m.target_orbit_name === "LEO" ? "leo" : m.target_orbit_name ? "custom" : null;
  render(`
    ${progressBar(3)}
    <h1>${STEP_TITLES[2]}</h1>
    <p class="lead">Elige lo que quieres lograr. Nosotros calculamos la órbita.</p>
    <div class="card"><form id="f">
      <fieldset>
        <legend class="visually-hidden">Destino</legend>
        <div class="optcards">
          <label class="optcard">
            <input type="radio" name="dest" value="leo" ${preset === "leo" ? "checked" : ""} required>
            <span><span class="t">🌍 Cerca de la Tierra</span><br>
            <span class="d">La opción más común y barata. Ideal para experimentos y comunicaciones.</span></span>
          </label>
          <label class="optcard">
            <input type="radio" name="dest" value="sso" ${preset === "sso" ? "checked" : ""}>
            <span><span class="t">📷 Para tomar fotos de la Tierra</span><br>
            <span class="d">Pasa sobre cada lugar a la misma hora del día. La que usan los satélites con cámara.</span></span>
          </label>
          <label class="optcard">
            <input type="radio" name="dest" value="custom" ${preset === "custom" ? "checked" : ""}>
            <span><span class="t">🛠 Ya sé mi órbita exacta</span><br>
            <span class="d">Para quien conoce su inclinación y altitud.</span></span>
          </label>
        </div>
      </fieldset>
      <details id="adv" ${preset === "custom" ? "open" : ""}>
        <summary>Datos de órbita (modo avanzado)</summary>
        <div class="grid2" style="margin-top:12px">
          <div class="field">
            <label for="inc">Inclinación, en grados</label>
            <p class="hint">El ángulo de tu órbita respecto al ecuador.</p>
            <input id="inc" type="number" min="0" max="180" step="0.1" value="${m.target_inclination_deg ?? ""}">
          </div>
          <div class="field">
            <label for="alt">Altitud, en kilómetros</label>
            <p class="hint">Qué tan alto sobre la Tierra.</p>
            <input id="alt" type="number" min="150" max="2000" step="1" value="${m.target_altitude_km ?? ""}">
          </div>
        </div>
      </details>
      <div class="btnrow">
        <a class="btn ghost" href="#/carga/${id}/paso/2">Atrás</a>
        <button class="btn" type="submit">Continuar</button>
      </div>
    </form></div>`);

  view.querySelectorAll('input[name="dest"]').forEach(r => r.addEventListener("change", () => {
    const adv = $("#adv");
    if (r.value === "custom") adv.open = true;
    else {
      const d = DESTINOS[r.value];
      $("#inc").value = d.inc; $("#alt").value = d.alt;
    }
  }));

  $("#f").addEventListener("submit", async (e) => {
    e.preventDefault();
    const dest = view.querySelector('input[name="dest"]:checked');
    if (!dest) return;
    let body;
    if (dest.value === "custom") {
      const inc = parseFloat($("#inc").value), alt = parseFloat($("#alt").value);
      if (Number.isNaN(inc) || Number.isNaN(alt)) { toast("Completa la inclinación y la altitud, o elige una opción guiada."); return; }
      body = { target_orbit_name: "CUSTOM", target_inclination_deg: inc, target_altitude_km: alt };
    } else {
      const d = DESTINOS[dest.value];
      body = { target_orbit_name: d.orbit, target_inclination_deg: d.inc, target_altitude_km: d.alt };
    }
    await api(`/manifests/${id}`, { method: "PATCH", body });
    location.hash = `#/carga/${id}/paso/4`;
  });
}

/* paso 4: seguridad (tri-estado) */
const SAFETY_QS = [
  ["has_propulsion", "¿Tu carga lleva combustible o motores propios?"],
  ["hazardous_materials", "¿Contiene baterías, gases a presión o químicos?"],
  ["needs_early_deploy", "¿Necesita salir del cohete antes que las demás cargas?"],
];

function triRadios(name, current) {
  return `<div class="seg">
    ${[["yes", "Sí"], ["no", "No"], ["unsure", "No estoy segura/o"]].map(([v, t]) => `
      <label><input type="radio" name="${name}" value="${v}" ${current === v ? "checked" : ""} required> ${t}</label>`).join("")}
  </div>`;
}

async function vPaso4(id) {
  const m = await api(`/manifests/${id}`);
  render(`
    ${progressBar(4)}
    <h1>${STEP_TITLES[3]}</h1>
    <p class="lead">Es normal no saberlas todas.</p>
    <div class="card"><form id="f">
      ${SAFETY_QS.map(([field, q]) => `
        <fieldset><legend>${q}</legend>${triRadios(field, m[field + "_answer"])}</fieldset>`).join("")}
      <p class="notice">Si respondes “No estoy segura/o”, seguimos adelante y un asesor lo confirma contigo antes del lanzamiento. Tu precio podría bajar si resulta que no aplica.</p>
      <div class="btnrow">
        <a class="btn ghost" href="#/carga/${id}/paso/3">Atrás</a>
        <button class="btn" type="submit">Continuar</button>
      </div>
    </form></div>`);
  $("#f").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {};
    for (const [field] of SAFETY_QS) {
      const sel = view.querySelector(`input[name="${field}"]:checked`);
      if (!sel) return;
      body[field] = sel.value;
    }
    await api(`/manifests/${id}`, { method: "PATCH", body });
    location.hash = `#/carga/${id}/paso/5`;
  });
}

/* paso 5: permisos */
async function vPaso5(id) {
  const m = await api(`/manifests/${id}`);
  render(`
    ${progressBar(5)}
    <h1>${STEP_TITLES[4]}</h1>
    <p class="lead">Todo lo que va al espacio necesita un permiso de tu país (una licencia). Muchos proyectos pequeños lo tramitan con su universidad o su agencia espacial.</p>
    <div class="card"><form id="f">
      <fieldset>
        <legend>Tu permiso de lanzamiento</legend>
        <div class="optcards">
          <label class="optcard"><input type="radio" name="lic" value="approved" ${m.licensing_status === "approved" ? "checked" : ""} required>
            <span><span class="t">Ya lo tengo aprobado</span></span></label>
          <label class="optcard"><input type="radio" name="lic" value="pending" ${m.licensing_status === "pending" ? "checked" : ""}>
            <span><span class="t">Está en trámite</span><br><span class="d">Aplicamos un recargo del 20% que desaparece cuando se aprueba.</span></span></label>
          <label class="optcard"><input type="radio" name="lic" value="not_required" ${m.licensing_status === "not_required" ? "checked" : ""}>
            <span><span class="t">Mi proyecto no lo necesita</span><br><span class="d">Poco común: confírmalo con tu asesor si tienes dudas.</span></span></label>
        </div>
      </fieldset>
      <fieldset>
        <legend>¿Tu carga usa tecnología de Estados Unidos con restricciones de exportación?</legend>
        <p class="hint">La mayoría de proyectos escolares y comerciales: No.</p>
        ${triRadios("itar_controlled", m.itar_controlled_answer)}
      </fieldset>
      <div class="btnrow">
        <a class="btn ghost" href="#/carga/${id}/paso/4">Atrás</a>
        <button class="btn" type="submit">Continuar</button>
      </div>
    </form></div>`);
  $("#f").addEventListener("submit", async (e) => {
    e.preventDefault();
    const lic = view.querySelector('input[name="lic"]:checked');
    const itar = view.querySelector('input[name="itar_controlled"]:checked');
    if (!lic || !itar) return;
    await api(`/manifests/${id}`, { method: "PATCH", body: { licensing_status: lic.value, itar_controlled: itar.value } });
    location.hash = `#/carga/${id}/paso/6`;
  });
}

/* paso 6: revisión */
async function vPaso6(id) {
  const m = await api(`/manifests/${id}`);
  const dim = v => (v == null ? "—" : Math.round(v * 100) + " cm");
  const tri = v => (v === "yes" ? "Sí" : v === "no" ? "No" : "No estoy segura/o");
  const missing = m.missing_fields || [];
  render(`
    ${progressBar(6)}
    <h1>${STEP_TITLES[5]}</h1>
    <div class="card">
      <div class="qrow"><span>Nombre</span><strong>${esc(m.name)}</strong></div>
      <div class="qrow"><span>Peso</span><strong>${m.mass_kg != null ? m.mass_kg + " kg" : "—"}</strong></div>
      <div class="qrow"><span>Medidas (L×A×A)</span><strong>${dim(m.length_m)} × ${dim(m.width_m)} × ${dim(m.height_m)}</strong></div>
      <div class="qrow"><span>Destino</span><strong>${m.target_orbit_name ? esc(m.target_orbit_name) + ` · ${m.target_inclination_deg}° · ${m.target_altitude_km} km` : "—"}</strong></div>
      <div class="qrow"><span>Combustible propio</span><strong>${tri(m.has_propulsion_answer)}</strong></div>
      <div class="qrow"><span>Baterías / gases / químicos</span><strong>${tri(m.hazardous_materials_answer)}</strong></div>
      <div class="qrow"><span>Salida temprana</span><strong>${tri(m.needs_early_deploy_answer)}</strong></div>
      <div class="qrow"><span>Permiso</span><strong>${{ approved: "Aprobado", pending: "En trámite", not_required: "No necesario" }[m.licensing_status]}</strong></div>
    </div>
    ${m.needs_review ? '<p class="notice">Respondiste “No estoy segura/o” en alguna pregunta: un asesor la confirmará contigo. Mientras tanto el precio incluye un recargo de seguridad que puede desaparecer.</p>' : ""}
    ${missing.length ? `<p class="notice">Te falta completar el paso ${firstMissingStep(m)} para poder ver precios.</p>` : ""}
    <div class="btnrow">
      <a class="btn ghost" href="#/carga/${id}/paso/5">Atrás</a>
      ${missing.length
        ? `<a class="btn" href="#/carga/${id}/paso/${firstMissingStep(m)}">Completar lo que falta</a>`
        : `<a class="btn" href="#/carga/${id}/opciones">Ver opciones de lanzamiento</a>`}
    </div>`);
}

/* opciones (matching) */
function encaje(score) {
  if (score >= 0.95) return ["Encaja perfecto con tu destino", "ok"];
  if (score >= 0.8) return ["Encaja muy bien con tu destino", "ok"];
  return ["Encaja bien con tu destino", "acc"];
}

async function vOpciones(id) {
  let matches;
  try {
    matches = await api(`/manifests/${id}/matches`);
  } catch (err) {
    if (err.status === 409 && err.detail && err.detail.missing_fields) {
      toast("Te faltan algunos datos antes de ver precios. Te llevamos al paso correcto.");
      location.hash = `#/carga/${id}/paso/${Math.min(...err.detail.missing_fields.map(f => FIELD_STEP[f] || 6))}`;
      return;
    }
    throw err;
  }
  const cards = matches.map((x, i) => {
    const w = x.launch_window;
    const [fit, cls] = encaje(x.orbital_score);
    return `<div class="card match">
      <div class="match-head">
        <span class="t">${esc(w.provider)} · ${esc(w.vehicle)}</span>
        <span class="price-num">${money(x.estimated_price.total_cents)}</span>
      </div>
      <div class="meta">Sale el ${fecha(w.launch_date)} · vuelo compartido</div>
      <span class="pill ${cls}">${fit}</span>
      ${i === 0 ? '<span class="pill acc">Recomendado</span>' : ""}
      <details><summary>Ver detalles técnicos</summary>
        <p class="hint">Órbita ${esc(w.orbit_name)} · ${w.inclination_deg}° / ${w.altitude_km} km ·
        diferencia con tu destino: ${x.inclination_delta_deg.toFixed(1)}° y ${x.altitude_delta_km.toFixed(0)} km ·
        puntaje de compatibilidad: ${x.orbital_score}</p>
      </details>
      <div class="btnrow"><button class="btn choose" data-window="${w.id}">Elegir este vuelo</button></div>
    </div>`;
  }).join("");
  render(`
    <h1>Vuelos disponibles para tu carga</h1>
    <p class="lead">Ordenados por lo que mejor encaja con tu destino. El precio ya incluye tus recargos, si aplican.</p>
    ${cards || emptyState("sinVuelos", "Por ahora no hay vuelos para tu destino",
      "Prueba con otra órbita en el paso 3, o escríbenos y te avisamos cuando haya uno.",
      `<a class="btn ghost" href="#/carga/${id}/paso/3">Cambiar destino</a>`)}
    <div class="btnrow"><a class="btn ghost" href="#/carga/${id}/paso/6">Atrás</a></div>`);
  view.querySelectorAll(".choose").forEach(b => b.addEventListener("click", async () => {
    b.disabled = true;
    try {
      const q = await api(`/manifests/${id}/quotes`, { method: "POST", body: { launch_window_id: b.dataset.window } });
      sessionStorage.setItem("quote:" + q.id, JSON.stringify(q));
      location.hash = `#/carga/${id}/cotizacion/${q.id}`;
    } finally { b.disabled = false; }
  }));
}

/* cotización */
const MULT_WORDS = {
  urgency: ["Recargo por salida próxima", "El vuelo sale en menos de 90 días."],
  atypical_volume: ["Recargo por carga voluminosa", "Tu carga ocupa más espacio de lo habitual para su peso."],
  regulatory_risk: ["Recargo de permisos y seguridad (20%)", "Desaparece cuando tu permiso se apruebe o el asesor confirme tus respuestas."],
};

async function vCotizacion(id, qid) {
  const stored = sessionStorage.getItem("quote:" + qid);
  if (!stored) { location.hash = `#/carga/${id}/opciones`; return; }
  const q = JSON.parse(stored);
  const rows = Object.entries(q.multipliers).map(([k, f]) => {
    const [t, why] = MULT_WORDS[k] || [k, ""];
    return `<div class="qrow"><span>${t}<div class="why">${why}</div></span>
      <strong class="price-num">+ ${money(Math.round(q.base_total_cents * (f - 1)))}</strong></div>`;
  }).join("");
  render(`
    <h1>Tu precio</h1>
    <div class="card">
      <div class="qrow"><span>Transporte de tu carga<div class="why">Vuelo compartido</div></span>
        <strong class="price-num">${money(q.base_total_cents)}</strong></div>
      ${rows}
      <div class="qrow total"><span>Total</span><span class="price-num">${money(q.total_cents)}</span></div>
    </div>
    ${q.expires_at ? `<p class="notice">Este precio queda congelado si reservas antes del ${fecha(q.expires_at)}.</p>` : ""}
    <div class="btnrow">
      <a class="btn ghost" href="#/carga/${id}/opciones">Ver otras opciones</a>
      <button class="btn" id="book">Reservar este vuelo</button>
    </div>`);
  $("#book").addEventListener("click", async () => {
    $("#book").disabled = true;
    try {
      await api(`/manifests/${id}/book`, { method: "POST", body: { quote_id: qid } });
      location.hash = `#/carga/${id}/reservado`;
    } catch (err) {
      $("#book").disabled = false;
      if (err.status === 409) {
        toast(typeof err.detail === "string" ? traducir(err.detail) : "No se pudo reservar. Vuelve a pedir el precio.");
        location.hash = `#/carga/${id}/opciones`;
      } else throw err;
    }
  });
}

function traducir(detail) {
  if (/expired/i.test(detail)) return "Ese precio ya venció. Te mostramos las opciones con el precio de hoy.";
  if (/invalidated/i.test(detail)) return "Tu precio cambió tras la revisión del asesor (¡puede haber bajado!). Pide uno nuevo.";
  if (/capacity/i.test(detail)) return "Ese vuelo se llenó. Elige otro de la lista.";
  return detail;
}

/* confirmación */
async function vReservado(id) {
  const m = await api(`/manifests/${id}`);
  const url = `${location.origin}/#/tracking/${m.tracking_token}`;
  render(`
    <svg class="celebrate" viewBox="0 0 64 64" aria-hidden="true">
      <path d="M 48.97 15.03 A 24 24 0 1 0 56 32" fill="none" stroke="currentColor" stroke-width="5.5" stroke-linecap="round"/>
      <g class="orbit-dot"><circle cx="55.9" cy="21.4" r="6.5" fill="var(--accent)"/></g>
    </svg>
    <h1>¡Vuelo reservado!</h1>
    <p class="lead">Tu carga <strong>${esc(m.name)}</strong> tiene lugar asegurado. Te avisaremos de cada paso.</p>
    <h2>Qué sigue</h2>
    <div class="card"><ul class="timeline">
      <li class="now"><div><div class="ev">Reserva confirmada</div><div class="sub">Hoy</div></div></li>
      <li class="future"><div><div class="ev">Entrega tu carga para integrarla al cohete</div><div class="sub">Te escribiremos con la fecha y el lugar. A partir de ahí ya no se puede cancelar.</div></div></li>
      <li class="future"><div><div class="ev">Despegue</div></div></li>
      <li class="future"><div><div class="ev">Tu carga en órbita</div></div></li>
    </ul></div>
    <h2>Comparte el seguimiento</h2>
    <p>Cualquier persona con este enlace puede ver el estado de tu carga (sin precios ni datos personales):</p>
    <p class="share">${url}</p>
    <div class="btnrow">
      <a class="btn" href="#/tracking/${m.tracking_token}">Ver seguimiento</a>
      <a class="btn ghost" href="#/cargas">Ir a mis cargas</a>
    </div>`);
}

/* tracking público */
const EVENT_WORDS = {
  "manifest.created": "Recibimos tu registro",
  "manifest.quoted": "Precio confirmado",
  "manifest.booked": "Vuelo reservado",
  "manifest.review_requested": "Un asesor revisará tus respuestas",
  "manifest.review_resolved": "El asesor confirmó tus respuestas",
  "manifest.cancelled": "Envío cancelado",
};
const STATE_EVENT_WORDS = {
  integrated: ["Tu carga ya está dentro del cohete", "A partir de aquí ya no se puede cancelar."],
  launched: ["¡Despegue!", ""],
  deployed: ["Tu carga está en órbita", ""],
  closed: ["Misión completada", ""],
};
const FUTURE_ORDER = ["booked", "integrated", "launched", "deployed", "closed"];
const FUTURE_WORDS = {
  integrated: "Integración al cohete", launched: "Despegue",
  deployed: "Tu carga en órbita", closed: "Misión completada",
};

async function vTracking(token) {
  let t = null, offlineSince = null;
  try {
    t = await api(`/tracking/${token}`);
    localStorage.setItem("track:" + token, JSON.stringify({ t, ts: Date.now() }));
  } catch (err) {
    if (err && err.status === 404) {
      render(`<h1>No encontramos ese envío</h1>` + emptyState("noEncontrado", "El enlace no funciona",
        "Revisa que esté completo, o pide uno nuevo a quien te lo compartió."));
      return;
    }
    // sin red: último estado conocido, con aviso honesto
    const cached = localStorage.getItem("track:" + token);
    if (cached) {
      const saved = JSON.parse(cached);
      t = saved.t;
      offlineSince = saved.ts;
    } else {
      render(`<h1>Sin conexión</h1>` + emptyState("sinConexion", "No pudimos conectar",
        "Revisa tu internet y vuelve a intentarlo. El seguimiento funciona sin conexión después de abrirlo una vez."));
      return;
    }
  }
  renderTracking(t, offlineSince);
}

function hace(ts) {
  const min = Math.round((Date.now() - ts) / 60000);
  if (min < 2) return "hace un momento";
  if (min < 60) return `hace ${min} minutos`;
  const h = Math.round(min / 60);
  return h === 1 ? "hace 1 hora" : `hace ${h} horas`;
}

function renderTracking(t, offlineSince) {
  const done = t.history
    .filter(e => e.event_type !== "manifest.updated")
    .map((e, i, arr) => {
      const words = e.event_type === "manifest.state_changed"
        ? (STATE_EVENT_WORDS[e.to_state] || [e.to_state, ""])
        : [EVENT_WORDS[e.event_type] || e.event_type, ""];
      const last = i === arr.length - 1;
      return `<li class="${last && !FUTURE_ORDER.slice(FUTURE_ORDER.indexOf(t.status) + 1).length ? "now" : last ? "now" : ""}">
        <div><div class="ev">${words[0]}</div>${words[1] ? `<div class="sub">${words[1]}</div>` : ""}
        <div class="ts">${fecha(e.created_at)}</div></div></li>`;
    }).join("");
  const idx = FUTURE_ORDER.indexOf(t.status);
  const future = (idx >= 0 && t.status !== "cancelled" ? FUTURE_ORDER.slice(idx + 1) : [])
    .map(s => `<li class="future"><div><div class="ev">${FUTURE_WORDS[s]}</div></div></li>`).join("");
  render(`
    <h1>${esc(t.payload_name)} ${statePill(t.status)}</h1>
    <p class="lead">Destino: órbita ${esc(t.target_orbit_name)} · seguimiento público, sin precios ni datos personales.</p>
    ${offlineSince ? `<p class="offline-notice">Sin conexión — mostrando el estado de ${hace(offlineSince)}.</p>` : ""}
    <div class="card"><ul class="timeline">${done}${future}</ul></div>
    <details><summary>Ver detalles técnicos</summary>
      <p class="hint">Estado del sistema: <span class="mono">${t.status}</span> · última actualización ${fecha(t.last_updated)}.</p>
    </details>`);
}

/* ── router ──────────────────────────────────────────────────────────── */

// Rango de cada vista para animar la dirección del avance (wizard y flujo).
function routeRank(parts) {
  if (parts[0] === "entrar") return 0;
  if (parts[0] === "nueva") return 11;
  if (parts[0] === "carga") {
    if (parts[2] === "paso") return 10 + parseInt(parts[3], 10);
    if (parts[2] === "opciones") return 20;
    if (parts[2] === "cotizacion") return 21;
    if (parts[2] === "reservado") return 22;
  }
  return 1; // cargas y tracking: sin dirección fuerte
}

let lastRank = null;

async function route() {
  const h = location.hash || "#/cargas";
  const parts = h.slice(2).split("/");
  const rank = routeRank(parts);
  pendingDirection = lastRank === null || rank === lastRank ? 0 : rank > lastRank ? 1 : -1;
  lastRank = rank;
  try {
    if (parts[0] === "tracking" && parts[1]) return await vTracking(parts[1]);
    if (!session.token) return vEntrar();
    if (parts[0] === "entrar") return vEntrar();
    if (parts[0] === "nueva") return vPaso1(null);
    if (parts[0] === "carga" && parts[1]) {
      const id = parts[1];
      if (parts[2] === "paso") {
        const n = parseInt(parts[3], 10);
        return await [vPaso1, vPaso2, vPaso3, vPaso4, vPaso5, vPaso6][n - 1](id);
      }
      if (parts[2] === "opciones") return await vOpciones(id);
      if (parts[2] === "cotizacion") return await vCotizacion(id, parts[3]);
      if (parts[2] === "reservado") return await vReservado(id);
    }
    return await vCargas();
  } catch (err) {
    if (err && err.status === 401) { session.clear(); return vEntrar(); }
    if (err && err.status === 404) { render(`<h1>No encontramos esa página</h1><p class="lead"><a href="#/cargas">Volver a mis cargas</a></p>`); return; }
    console.error(err);
    if (err && err.status === undefined) {
      render(`<h1>Sin conexión</h1>` + emptyState("sinConexion", "No pudimos conectar",
        "Tus datos guardados están a salvo. Revisa tu internet y vuelve a intentarlo.",
        '<a class="btn ghost" href="#/cargas">Reintentar</a>'));
      return;
    }
    render(`<h1>Algo salió mal</h1><p class="lead">Vuelve a intentarlo en un momento. Si sigue fallando, escríbenos.</p>
      <div class="btnrow"><a class="btn ghost" href="#/cargas">Volver a mis cargas</a></div>`);
  }
}

window.addEventListener("hashchange", route);
route();

/* ── PWA: service worker + instalación no intrusiva ─────────────────── */

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => { /* la app funciona igual sin SW */ });
}

let installEvent = null;
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  if (localStorage.getItem("install-dismissed")) return;
  installEvent = e;
  $("#install-banner").hidden = false;
});
$("#install-yes").addEventListener("click", async () => {
  $("#install-banner").hidden = true;
  if (installEvent) { installEvent.prompt(); installEvent = null; }
});
$("#install-no").addEventListener("click", () => {
  $("#install-banner").hidden = true;
  localStorage.setItem("install-dismissed", "1");
});
