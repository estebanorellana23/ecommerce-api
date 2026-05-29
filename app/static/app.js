"use strict";

// Panel de administración mínimo (vanilla JS). Consume la propia API (mismo origen).
const TOKEN_KEY = "ecommerce_admin_token";
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function getToken() { return localStorage.getItem(TOKEN_KEY); }
function setToken(t) { localStorage.setItem(TOKEN_KEY, t); }
function clearToken() { localStorage.removeItem(TOKEN_KEY); }

// --- Cliente HTTP -----------------------------------------------------------

async function api(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && getToken()) headers["Authorization"] = `Bearer ${getToken()}`;
  const res = await fetch(path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) { logout(); throw new Error("Sesión expirada"); }
  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try { detail = (await res.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

// --- Autenticación ----------------------------------------------------------

async function login(email, password) {
  const params = new URLSearchParams({ username: email, password });
  const res = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: params,
  });
  if (!res.ok) throw new Error("Credenciales inválidas");
  const data = await res.json();
  setToken(data.access_token);
}

function logout() {
  clearToken();
  $("#app-view").classList.add("hidden");
  $("#login-view").classList.remove("hidden");
}

async function showApp() {
  const me = await api("/auth/me");
  $("#user-badge").textContent = `${me.name} · ${me.role}`;
  $("#login-view").classList.add("hidden");
  $("#app-view").classList.remove("hidden");
  loadProducts();
}

// --- Productos --------------------------------------------------------------

async function loadProducts() {
  const page = await api("/catalog?size=100", { auth: false });
  const body = $("#products-body");
  body.innerHTML = "";
  page.items.forEach((p) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${p.id}</td>
      <td>${p.sku}</td>
      <td>${p.name}</td>
      <td>${Number(p.price).toFixed(2)}</td>
      <td>${p.category_id}</td>
      <td><span class="pill ${p.is_active ? "on" : "off"}">${p.is_active ? "Sí" : "No"}</span></td>
      <td>
        <button class="link" data-edit="${p.id}">Editar</button>
        <button class="link" data-del="${p.id}">Eliminar</button>
      </td>`;
    body.appendChild(tr);
  });
  body.querySelectorAll("[data-edit]").forEach((b) =>
    b.addEventListener("click", () => openModal(page.items.find((x) => x.id == b.dataset.edit)))
  );
  body.querySelectorAll("[data-del]").forEach((b) =>
    b.addEventListener("click", () => deleteProduct(b.dataset.del))
  );
}

function openModal(product) {
  $("#modal-error").classList.add("hidden");
  $("#modal-title").textContent = product ? "Editar producto" : "Nuevo producto";
  $("#p-id").value = product ? product.id : "";
  $("#p-sku").value = product ? product.sku : "";
  $("#p-name").value = product ? product.name : "";
  $("#p-desc").value = product ? product.description : "";
  $("#p-price").value = product ? product.price : "";
  $("#p-cat").value = product ? product.category_id : 1;
  $("#p-reorder").value = product ? product.reorder_point : 0;
  $("#p-active").checked = product ? product.is_active : true;
  $("#modal").classList.remove("hidden");
}

function closeModal() { $("#modal").classList.add("hidden"); }

async function saveProduct(e) {
  e.preventDefault();
  const id = $("#p-id").value;
  const payload = {
    sku: $("#p-sku").value,
    name: $("#p-name").value,
    description: $("#p-desc").value,
    price: parseFloat($("#p-price").value),
    category_id: parseInt($("#p-cat").value, 10),
    reorder_point: parseInt($("#p-reorder").value, 10) || 0,
    is_active: $("#p-active").checked,
  };
  try {
    if (id) await api(`/admin/products/${id}`, { method: "PUT", body: payload });
    else await api("/admin/products", { method: "POST", body: payload });
    closeModal();
    loadProducts();
  } catch (err) {
    const el = $("#modal-error");
    el.textContent = err.message;
    el.classList.remove("hidden");
  }
}

async function deleteProduct(id) {
  if (!confirm("¿Eliminar este producto? (requiere rol admin)")) return;
  try {
    await api(`/admin/products/${id}`, { method: "DELETE" });
    loadProducts();
  } catch (err) {
    alert(err.message);
  }
}

// --- Inventario -------------------------------------------------------------

async function getStock() {
  const pid = $("#inv-pid").value;
  try {
    const s = await api(`/inventory/${pid}`, { auth: false });
    $("#inv-result").textContent =
      `Disponible: ${s.available} · Reservado: ${s.reserved} · Neto: ${s.net_available}`;
  } catch (err) { $("#inv-result").textContent = err.message; }
}

async function adjustStock() {
  const pid = $("#inv-pid").value;
  const delta = parseInt($("#inv-delta").value, 10);
  try {
    const s = await api(`/inventory/${pid}/adjust`, {
      method: "POST",
      body: { delta, reason: "ajuste desde panel" },
    });
    $("#inv-result").textContent = `OK. Nuevo disponible: ${s.available}`;
  } catch (err) { $("#inv-result").textContent = err.message; }
}

async function lowStockReport() {
  const threshold = $("#low-threshold").value;
  const body = $("#low-body");
  try {
    const rows = await api(`/inventory/reports/low-stock?threshold=${threshold}`);
    body.innerHTML = rows.length
      ? rows.map((r) => `<tr><td>${r.product_id}</td><td>${r.available}</td></tr>`).join("")
      : `<tr><td colspan="2" class="muted">Sin productos bajo el umbral</td></tr>`;
  } catch (err) {
    body.innerHTML = `<tr><td colspan="2" class="error">${err.message}</td></tr>`;
  }
}

// --- Tabs -------------------------------------------------------------------

function switchTab(name) {
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  $("#tab-products").classList.toggle("hidden", name !== "products");
  $("#tab-inventory").classList.toggle("hidden", name !== "inventory");
}

// --- Eventos ----------------------------------------------------------------

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const err = $("#login-error");
  err.classList.add("hidden");
  try {
    await login($("#email").value, $("#password").value);
    await showApp();
  } catch (e2) {
    err.textContent = e2.message;
    err.classList.remove("hidden");
  }
});

$("#logout").addEventListener("click", logout);
$("#new-product").addEventListener("click", () => openModal(null));
$("#modal-cancel").addEventListener("click", closeModal);
$("#product-form").addEventListener("submit", saveProduct);
$("#inv-get").addEventListener("click", getStock);
$("#inv-adjust").addEventListener("click", adjustStock);
$("#low-report").addEventListener("click", lowStockReport);
$$(".tab").forEach((t) => t.addEventListener("click", () => switchTab(t.dataset.tab)));

// --- Arranque ---------------------------------------------------------------

if (getToken()) {
  showApp().catch(() => logout());
}
