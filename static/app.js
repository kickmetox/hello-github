const HEADER = { "X-DocMan": "1" };
const state = {
  user: null,
  meta: { tags: [], correspondents: [], doctypes: [] },
  filters: { q: "", tag_id: "", doctype_id: "", correspondent_id: "", tax_only: false },
  searchQuery: "",
};

const $ = (id) => document.getElementById(id);

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (value == null || value === false) return;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value);
  });
  for (const child of children.flat()) {
    if (child == null) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

function reveal(mode) {
  $("splash").hidden = true;
  $("login-view").hidden = mode !== "login";
  $("app-view").hidden = mode !== "app";
}

function toast(message) {
  const node = el("div", { class: "toast", text: message });
  $("toasts").append(node);
  setTimeout(() => node.remove(), 4200);
}

async function api(path, options = {}) {
  const headers = Object.assign({}, HEADER, options.headers || {});
  const request = { credentials: "same-origin", headers };
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    request.body = JSON.stringify(options.json);
    request.method = options.method || "POST";
  } else {
    request.method = options.method || "GET";
    if (options.body) request.body = options.body;
  }
  const response = await fetch(path, request);
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (response.status === 401 && !path.endsWith("/login")) {
    reveal("login");
    throw new Error("Anmeldung erforderlich.");
  }
  if (!response.ok) {
    const detail = data && data.detail ? data.detail : "Anfrage fehlgeschlagen.";
    throw new Error(detail);
  }
  return data;
}

function formatBytes(size) {
  if (!size) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = size;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(index ? 1 : 0)} ${units[index]}`;
}

function formatDay(iso) {
  if (!iso) return "—";
  const [year, month, day] = iso.slice(0, 10).split("-");
  return `${day}.${month}.${year}`;
}

function formatStamp(iso) {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Europe/Berlin",
  }).format(new Date(iso));
}

function tagChip(tag) {
  return el("span", { class: "tag", text: tag.name, style: `border-color:${tag.color}` });
}

function highlight(text, terms) {
  const fragment = document.createDocumentFragment();
  if (!text) return fragment;
  if (!terms || !terms.length) {
    fragment.append(text);
    return fragment;
  }
  const pattern = new RegExp(`(${terms.map(escapeReg).join("|")})`, "ig");
  text.split(pattern).forEach((part) => {
    if (terms.some((term) => term.toLowerCase() === part.toLowerCase())) fragment.append(el("mark", { text: part }));
    else if (part) fragment.append(part);
  });
  return fragment;
}

function escapeReg(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function setNav(route) {
  document.querySelectorAll("#nav button").forEach((button) => {
    button.classList.toggle("active", button.dataset.route === route);
  });
}

function paintUser() {
  $("user-button").textContent = state.user.display_name || state.user.username;
  const banner = $("banner");
  if (state.user.must_change_password) {
    banner.hidden = false;
    banner.textContent = "Das Startpasswort ist noch aktiv. Bitte jetzt ein eigenes Passwort mit mindestens 8 Zeichen setzen.";
  } else {
    banner.hidden = true;
    banner.textContent = "";
  }
}

async function loadMeta() {
  const [tags, correspondents, doctypes] = await Promise.all([
    api("/api/tags"),
    api("/api/correspondents"),
    api("/api/doctypes"),
  ]);
  state.meta = { tags, correspondents, doctypes };
}

function fillSelect(select, rows, placeholder) {
  select.replaceChildren(el("option", { value: "", text: placeholder }));
  rows.forEach((row) => select.append(el("option", { value: String(row.id), text: row.name })));
}

function currentRoute() {
  const raw = (location.hash || "#/dashboard").replace(/^#\//, "");
  const [name, id] = raw.split("/");
  return { name: name || "dashboard", id: id || "" };
}

async function onHash() {
  const route = currentRoute();
  setNav(route.name === "doc" ? "documents" : route.name);
  const main = $("main");
  main.replaceChildren(el("p", { class: "muted", text: "Wird geladen …" }));
  try {
    if (route.name === "documents") await renderDocuments();
    else if (route.name === "search") await renderSearch();
    else if (route.name === "organize") await renderOrganize();
    else if (route.name === "audit") await renderAudit();
    else if (route.name === "doc" && route.id) await renderDetail(route.id);
    else await renderDashboard();
  } catch (error) {
    main.replaceChildren(el("p", { class: "form-error", text: error.message }));
  }
}

function navigate(route) {
  const next = `#/${route}`;
  if (location.hash === next) onHash();
  else location.hash = next;
}

async function renderDashboard() {
  const data = await api("/api/dashboard");
  const main = $("main");
  const stats = el("section", { class: "stats" }, [
    stat("Dokumente", data.documents),
    stat("Speicher", formatBytes(data.storage_bytes)),
    stat("Steuerrelevant", data.tax_relevant),
    stat("Im Index", data.index_documents),
  ]);
  const recent = el("div", { class: "list" }, data.recent.map(docButton));
  const reminders = el("div", { class: "list" }, data.reminders.length
    ? data.reminders.map((doc) => {
      const button = docButton(doc);
      button.append(el("span", { class: "muted", text: `Wiedervorlage ${formatDay(doc.reminder_date)}` }));
      return button;
    })
    : [el("p", { class: "empty", text: "Keine Wiedervorlage in den nächsten 30 Tagen." })]);
  main.replaceChildren(
    el("section", { class: "page" }, [
      el("header", { class: "page-head" }, [
        el("div", {}, [el("h1", { text: "Übersicht" }), el("p", { class: "lede", text: "Ablage, Fristen und der lokale Suchindex." })]),
      ]),
      stats,
      el("div", { class: "grid-2" }, [
        el("section", { class: "panel" }, [el("h2", { text: "Zuletzt abgelegt" }), recent]),
        el("section", { class: "panel" }, [el("h2", { text: "Wiedervorlage" }), reminders]),
      ]),
    ]),
  );
}

function stat(label, value) {
  return el("article", { class: "card stat" }, [el("span", { text: label }), el("strong", { text: String(value) })]);
}

function docButton(doc) {
  return el("button", { class: "row", type: "button", "data-action": "open-doc", "data-id": String(doc.id) }, [
    el("h3", { text: doc.title }),
    el("div", { class: "tags" }, [
      doc.doctype ? el("span", { class: "badge", text: doc.doctype.name }) : null,
      doc.correspondent ? el("span", { class: "badge", text: doc.correspondent.name }) : null,
      ...doc.tags.map(tagChip),
      doc.is_tax_relevant ? el("span", { class: "badge", text: "Steuer" }) : null,
    ]),
    el("span", { class: "muted", text: `${doc.original_name} · ${formatBytes(doc.size)} · ${formatStamp(doc.created_at)}` }),
  ]);
}

async function renderDocuments() {
  const main = $("main");
  const filters = el("form", { id: "library-filters", class: "filters" }, [
    labeled("Titel oder Text", el("input", { name: "q", value: state.filters.q, placeholder: "Filtern" })),
    labeled("Schlagwort", el("select", { name: "tag_id", id: "filter-tag" })),
    labeled("Dokumenttyp", el("select", { name: "doctype_id", id: "filter-type" })),
    labeled("Korrespondent", el("select", { name: "correspondent_id", id: "filter-corr" })),
  ]);
  const tax = el("label", { class: "check" }, [
    el("input", { type: "checkbox", name: "tax_only" }),
    "Nur steuerrelevante",
  ]);
  filters.append(tax);
  main.replaceChildren(
    el("section", { class: "page" }, [
      el("header", { class: "page-head" }, [
        el("div", {}, [el("h1", { text: "Dokumente" }), el("p", { class: "lede", id: "library-count" })]),
        el("div", { class: "actions" }, [
          el("button", { type: "button", "data-action": "scan-inbox", text: "Posteingang" }),
          el("button", { type: "button", class: "primary", "data-action": "open-upload", text: "Hochladen" }),
        ]),
      ]),
      filters,
      el("div", { id: "library-results", class: "cards" }),
    ]),
  );
  fillSelect($("filter-tag"), state.meta.tags, "Alle Schlagwörter");
  fillSelect($("filter-type"), state.meta.doctypes, "Alle Typen");
  fillSelect($("filter-corr"), state.meta.correspondents, "Alle Korrespondenten");
  $("filter-tag").value = state.filters.tag_id;
  $("filter-type").value = state.filters.doctype_id;
  $("filter-corr").value = state.filters.correspondent_id;
  filters.elements.tax_only.checked = state.filters.tax_only;
  await loadLibrary();
}

async function loadLibrary() {
  const params = new URLSearchParams();
  if (state.filters.q) params.set("q", state.filters.q);
  if (state.filters.tag_id) params.set("tag_id", state.filters.tag_id);
  if (state.filters.doctype_id) params.set("doctype_id", state.filters.doctype_id);
  if (state.filters.correspondent_id) params.set("correspondent_id", state.filters.correspondent_id);
  if (state.filters.tax_only) params.set("tax_only", "true");
  const data = await api(`/api/documents?${params.toString()}`);
  $("library-count").textContent = `${data.total} ${data.total === 1 ? "Dokument" : "Dokumente"}`;
  const host = $("library-results");
  host.replaceChildren(...(data.documents.length
    ? data.documents.map((doc) => el("div", { class: "doc-card" }, [docButton(doc)]))
    : [el("p", { class: "empty", text: "Keine Dokumente für diesen Filter. Dateien können hierher gezogen werden." })]));
}

async function renderSearch() {
  const main = $("main");
  main.replaceChildren(
    el("section", { class: "page" }, [
      el("header", { class: "page-head" }, [
        el("div", {}, [
          el("h1", { text: "Suche" }),
          el("p", { class: "lede", text: "Ranking nach TF-IDF und Kosinusähnlichkeit. Füllwörter werden ignoriert." }),
        ]),
        el("button", { type: "button", "data-action": "reindex", text: "Index neu aufbauen" }),
      ]),
      el("form", { id: "search-form", class: "filters" }, [
        labeled("Suchbegriff", el("input", { name: "q", value: state.searchQuery, placeholder: "z. B. Kündigung Mietvertrag" })),
        el("button", { class: "primary", type: "submit", text: "Suchen" }),
      ]),
      el("div", { id: "search-results", class: "list" }),
    ]),
  );
  if (state.searchQuery) await runSearch(state.searchQuery);
}

async function runSearch(query) {
  const host = $("search-results");
  if (!query) {
    host.replaceChildren(el("p", { class: "empty", text: "Suchbegriff eingeben." }));
    return;
  }
  const data = await api(`/api/search?q=${encodeURIComponent(query)}`);
  if (!data.terms.length) {
    host.replaceChildren(el("p", { class: "empty", text: "Die Anfrage enthält nur Füllwörter oder keine verwertbaren Begriffe." }));
    return;
  }
  if (!data.results.length) {
    host.replaceChildren(el("p", { class: "empty", text: "Keine passenden Dokumente im Index." }));
    return;
  }
  host.replaceChildren(...data.results.map((hit) => {
    const percent = Math.round(hit.score * 100);
    return el("article", { class: "row" }, [
      el("div", { class: "doc-card" }, [
        el("button", { class: "row", type: "button", "data-action": "open-doc", "data-id": String(hit.document.id) }, [
          el("h3", { text: hit.document.title }),
          el("div", { class: "snippet" }, [highlight(hit.snippet, hit.terms)]),
        ]),
        el("div", { class: "score" }, [
          el("b", { text: hit.score.toFixed(3) }),
          el("div", { class: "bar" }, [el("span", { style: `width:${percent}%` })]),
        ]),
      ]),
    ]);
  }));
}

async function renderOrganize() {
  await loadMeta();
  const main = $("main");
  main.replaceChildren(
    el("section", { class: "page" }, [
      el("header", { class: "page-head" }, [
        el("div", {}, [el("h1", { text: "Stammdaten" }), el("p", { class: "lede", text: "Schlagwörter, Korrespondenten und Dokumenttypen." })]),
      ]),
      el("div", { class: "cards" }, [
        namePanel("Schlagwort", "tag-form", state.meta.tags, "delete-tag", true),
        namePanel("Korrespondent", "corr-form", state.meta.correspondents, "delete-corr", false),
        namePanel("Dokumenttyp", "type-form", state.meta.doctypes, "delete-type", false),
      ]),
      el("section", { class: "panel", id: "users-panel" }),
    ]),
  );
  if (state.user.is_admin) await renderUsers();
}

function namePanel(title, formId, rows, action, withColor) {
  const form = el("form", { id: formId, class: "list" }, [
    labeled("Name", el("input", { name: "name", required: true, maxlength: "120" })),
  ]);
  if (withColor) form.append(labeled("Farbe", el("input", { name: "color", type: "color", value: "#7c9cff" })));
  form.append(el("button", { class: "primary", type: "submit", text: "Hinzufügen" }));
  const list = el("div", { class: "list" }, rows.map((row) => el("div", { class: "doc-card" }, [
    el("strong", { text: row.name }),
    el("button", { type: "button", class: "ghost", "data-action": action, "data-id": String(row.id), text: "Entfernen" }),
  ])));
  return el("section", { class: "panel" }, [el("h2", { text: title }), form, list]);
}

async function renderUsers() {
  const users = await api("/api/users");
  const form = el("form", { id: "user-form", class: "filters" }, [
    labeled("Benutzername", el("input", { name: "username", required: true })),
    labeled("Anzeigename", el("input", { name: "display_name" })),
    labeled("Passwort", el("input", { name: "password", type: "password", required: true, minlength: "8" })),
    el("label", { class: "check" }, [el("input", { type: "checkbox", name: "is_admin" }), "Administrator"]),
    el("button", { class: "primary", type: "submit", text: "Benutzer anlegen" }),
  ]);
  $("users-panel").replaceChildren(
    el("h2", { text: "Benutzer" }),
    form,
    el("div", { class: "list" }, users.map((user) => el("div", { class: "row" }, [
      el("strong", { text: user.display_name }),
      el("span", { class: "muted", text: `${user.username}${user.is_admin ? " · Administrator" : ""}` }),
    ]))),
  );
}

async function renderAudit() {
  const rows = await api("/api/audit");
  const table = el("table", {}, [
    el("thead", {}, [el("tr", {}, ["Zeit (Berlin)", "Benutzer", "Aktion", "Eintrag"].map((text) => el("th", { text })))]),
    el("tbody", {}, rows.map((row) => el("tr", {}, [
      el("td", { text: formatStamp(row.created_at) }),
      el("td", { text: row.username || "—" }),
      el("td", { text: row.action }),
      el("td", { text: row.message }),
    ]))),
  ]);
  $("main").replaceChildren(el("section", { class: "page" }, [
    el("header", { class: "page-head" }, [el("div", {}, [el("h1", { text: "Protokoll" }), el("p", { class: "lede", text: "Anmeldungen, Ablage, Suche und Löschungen." })])]),
    el("div", { class: "panel" }, [table]),
  ]));
}

async function renderDetail(id) {
  const doc = await api(`/api/documents/${id}`);
  const form = el("form", { id: "detail-form", class: "form-grid detail" }, [
    labeled("Titel", el("input", { name: "title", value: doc.title, required: true })),
    labeled("Dateiname", el("input", { value: doc.original_name, disabled: true })),
    labeled("Dokumentdatum", el("input", { name: "document_date", type: "date", value: doc.document_date || "" })),
    labeled("Wiedervorlage", el("input", { name: "reminder_date", type: "date", value: doc.reminder_date || "" })),
    labeled("Korrespondent", el("select", { name: "correspondent_id", id: "detail-corr" })),
    labeled("Dokumenttyp", el("select", { name: "doctype_id", id: "detail-type" })),
    el("label", { class: "check span-2" }, [
      el("input", { type: "checkbox", name: "is_tax_relevant" }),
      "Steuerrelevant",
    ]),
    labeledSpan("Notizen", el("textarea", { name: "notes", text: doc.notes })),
    el("div", { class: "span-2" }, [el("span", { class: "muted", text: "Schlagwörter" }), el("div", { id: "detail-tags", class: "checks" })]),
    el("div", { class: "actions span-2" }, [
      el("button", { class: "primary", type: "submit", text: "Speichern" }),
      el("a", { class: "button", href: `/api/documents/${doc.id}/file`, text: "Herunterladen" }),
      el("button", { type: "button", class: "danger", "data-action": "delete-doc", "data-id": String(doc.id), text: "Löschen" }),
    ]),
  ]);
  form.elements.is_tax_relevant.checked = doc.is_tax_relevant;
  const preview = buildPreview(doc);
  $("main").replaceChildren(el("section", { class: "page" }, [
    el("header", { class: "page-head" }, [
      el("div", {}, [el("h1", { text: doc.title }), el("p", { class: "lede", text: `${formatBytes(doc.size)} · ${doc.text_status} · ${doc.uploaded_by || "System"}` })]),
    ]),
    el("div", { class: "detail" }, [
      el("div", { class: "panel" }, [form, el("p", { class: "mono", text: doc.sha256 })]),
      el("div", {}, [
        preview,
        doc.text ? el("pre", { class: "text", text: doc.text }) : el("p", { class: "empty", text: textStatusMessage(doc) }),
      ]),
    ]),
  ]));
  fillSelect($("detail-corr"), state.meta.correspondents, "Kein Korrespondent");
  fillSelect($("detail-type"), state.meta.doctypes, "Kein Dokumenttyp");
  if (doc.correspondent) $("detail-corr").value = String(doc.correspondent.id);
  if (doc.doctype) $("detail-type").value = String(doc.doctype.id);
  const selected = new Set(doc.tags.map((tag) => tag.id));
  $("detail-tags").replaceChildren(...state.meta.tags.map((tag) => el("label", { class: "check" }, [
    el("input", { type: "checkbox", name: "tag_ids", value: String(tag.id), checked: selected.has(tag.id) ? "checked" : null }),
    tag.name,
  ])));
}

function labeled(caption, field) {
  return el("label", {}, [caption, field]);
}

function labeledSpan(caption, field) {
  return el("label", { class: "span-2" }, [caption, field]);
}

function textStatusMessage(doc) {
  if (doc.text_status === "binary") return "Bild ohne Textebene. Die Suche nutzt Titel, Notiz und Stammdaten.";
  if (doc.text_status === "failed") return "Text konnte nicht gelesen werden.";
  return "Kein extrahierbarer Text.";
}

function buildPreview(doc) {
  const inline = `/api/documents/${doc.id}/file?inline=1`;
  if ([".png", ".jpg", ".jpeg", ".webp", ".gif"].includes(doc.extension)) {
    return el("div", { class: "preview" }, [el("img", { src: inline, alt: doc.title })]);
  }
  if (doc.extension === ".pdf") {
    return el("div", { class: "preview" }, [el("iframe", { src: inline, title: doc.title })]);
  }
  return null;
}

function openModal(card) {
  const root = $("modal-root");
  root.className = "modal-root";
  root.replaceChildren(card);
  root.hidden = false;
}

function closeModal() {
  const root = $("modal-root");
  root.replaceChildren();
  root.className = "";
}

function openUpload(fileList) {
  const form = el("form", { id: "upload-form", class: "list" }, [
    el("div", { class: "drop", id: "drop-zone", text: "Dateien hierher ziehen oder auswählen. PDF, Text, CSV, JSON, DOCX und Bilder, bis 25 MB." }),
    el("input", { name: "files", type: "file", multiple: true }),
    labeled("Titel bei genau einer Datei", el("input", { name: "title" })),
    labeled("Notizen", el("textarea", { name: "notes" })),
    labeled("Dokumentdatum", el("input", { name: "document_date", type: "date" })),
    labeled("Wiedervorlage", el("input", { name: "reminder_date", type: "date" })),
    labeled("Korrespondent", el("select", { name: "correspondent_id", id: "upload-corr" })),
    labeled("Dokumenttyp", el("select", { name: "doctype_id", id: "upload-type" })),
    el("label", { class: "check" }, [el("input", { type: "checkbox", name: "is_tax_relevant" }), "Steuerrelevant"]),
    el("div", { id: "upload-tags", class: "checks" }),
    el("div", { class: "actions" }, [
      el("button", { class: "primary", type: "submit", text: "Ins Archiv legen" }),
      el("button", { type: "button", "data-action": "close-modal", text: "Abbrechen" }),
    ]),
  ]);
  openModal(el("div", { class: "modal-card" }, [el("h2", { text: "Hochladen" }), form]));
  fillSelect($("upload-corr"), state.meta.correspondents, "Kein Korrespondent");
  fillSelect($("upload-type"), state.meta.doctypes, "Kein Dokumenttyp");
  $("upload-tags").replaceChildren(...state.meta.tags.map((tag) => el("label", { class: "check" }, [
    el("input", { type: "checkbox", name: "tag_ids", value: String(tag.id) }),
    tag.name,
  ])));
  if (fileList && fileList.length) {
    const input = form.elements.files;
    const transfer = new DataTransfer();
    Array.from(fileList).forEach((file) => transfer.items.add(file));
    input.files = transfer.files;
  }
}

function openPassword() {
  const form = el("form", { id: "password-form", class: "list" }, [
    labeled("Aktuelles Passwort", el("input", { name: "current_password", type: "password", required: true })),
    labeled("Neues Passwort", el("input", { name: "new_password", type: "password", required: true, minlength: "8" })),
    el("div", { class: "actions" }, [
      el("button", { class: "primary", type: "submit", text: "Speichern" }),
      el("button", { type: "button", "data-action": "close-modal", text: "Abbrechen" }),
    ]),
  ]);
  openModal(el("div", { class: "modal-card" }, [el("h2", { text: "Passwort ändern" }), form]));
}

async function submitUpload(form) {
  const body = new FormData();
  const files = form.elements.files.files;
  if (!files.length) throw new Error("Bitte mindestens eine Datei wählen.");
  Array.from(files).forEach((file) => body.append("files", file));
  ["title", "notes", "document_date", "reminder_date", "correspondent_id", "doctype_id"].forEach((name) => {
    body.append(name, form.elements[name].value || "");
  });
  body.append("is_tax_relevant", form.elements.is_tax_relevant.checked ? "1" : "0");
  const tags = Array.from(form.querySelectorAll("input[name=tag_ids]:checked")).map((node) => node.value);
  body.append("tag_ids", tags.join(","));
  const data = await api("/api/documents", { method: "POST", body });
  if (data.errors && data.errors.length) {
    toast(data.errors.map((item) => `${item.file}: ${item.detail}`).join(" "));
  }
  toast(`${data.documents.length} Dokument übernommen.`);
  closeModal();
  if (data.documents.length === 1) navigate(`doc/${data.documents[0].id}`);
  else navigate("documents");
}

async function submitDetail(form) {
  const id = currentRoute().id;
  const tags = Array.from(form.querySelectorAll("input[name=tag_ids]:checked")).map((node) => Number(node.value));
  await api(`/api/documents/${id}`, {
    method: "PATCH",
    json: {
      title: form.elements.title.value,
      notes: form.elements.notes.value,
      document_date: form.elements.document_date.value || null,
      reminder_date: form.elements.reminder_date.value || null,
      is_tax_relevant: form.elements.is_tax_relevant.checked,
      correspondent_id: form.elements.correspondent_id.value ? Number(form.elements.correspondent_id.value) : null,
      doctype_id: form.elements.doctype_id.value ? Number(form.elements.doctype_id.value) : null,
      tag_ids: tags,
    },
  });
  toast("Gespeichert.");
  await loadMeta();
  await renderDetail(id);
}

function bind() {
  document.body.addEventListener("click", async (event) => {
    const target = event.target.closest("[data-action]");
    if (!target) return;
    const action = target.dataset.action;
    try {
      if (action === "navigate") navigate(target.dataset.route);
      else if (action === "open-doc") navigate(`doc/${target.dataset.id}`);
      else if (action === "open-upload") openUpload();
      else if (action === "open-password") openPassword();
      else if (action === "close-modal") closeModal();
      else if (action === "logout") {
        await api("/api/auth/logout", { method: "POST", json: {} });
        state.user = null;
        reveal("login");
      } else if (action === "delete-doc") {
        if (!window.confirm("Dokument und Datei wirklich löschen?")) return;
        await api(`/api/documents/${target.dataset.id}`, { method: "DELETE" });
        toast("Gelöscht.");
        navigate("documents");
      } else if (action === "delete-tag" || action === "delete-corr" || action === "delete-type") {
        const path = action === "delete-tag" ? "tags" : action === "delete-corr" ? "correspondents" : "doctypes";
        await api(`/api/${path}/${target.dataset.id}`, { method: "DELETE" });
        await renderOrganize();
      } else if (action === "scan-inbox") {
        const result = await api("/api/inbox/scan", { method: "POST", json: {} });
        toast(`${result.imported.length} aus dem Posteingang, ${result.rejected.length} abgelehnt.`);
        await loadLibrary();
      } else if (action === "reindex") {
        const result = await api("/api/search/reindex", { method: "POST", json: {} });
        toast(`Index enthält ${result.documents} Dokumente.`);
      }
    } catch (error) {
      toast(error.message);
    }
  });

  document.body.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    event.preventDefault();
    try {
      if (form.id === "login-form") {
        state.user = await api("/api/auth/login", {
          json: { username: form.username.value, password: form.password.value },
        });
        $("login-error").hidden = true;
        await loadMeta();
        reveal("app");
        paintUser();
        navigate("dashboard");
      } else if (form.id === "quick-search" || form.id === "search-form") {
        state.searchQuery = form.q ? form.q.value.trim() : $("quick-query").value.trim();
        if (form.id === "quick-search") $("quick-query").value = state.searchQuery;
        if (currentRoute().name !== "search") navigate("search");
        else await runSearch(state.searchQuery);
      } else if (form.id === "upload-form") await submitUpload(form);
      else if (form.id === "detail-form") await submitDetail(form);
      else if (form.id === "password-form") {
        state.user = await api("/api/auth/password", {
          method: "POST",
          json: {
            current_password: form.elements.current_password.value,
            new_password: form.elements.new_password.value,
          },
        });
        paintUser();
        closeModal();
        toast("Passwort geändert.");
      } else if (form.id === "tag-form") {
        await api("/api/tags", { json: { name: form.elements.name.value, color: form.elements.color.value } });
        await renderOrganize();
      } else if (form.id === "corr-form") {
        await api("/api/correspondents", { json: { name: form.elements.name.value } });
        await renderOrganize();
      } else if (form.id === "type-form") {
        await api("/api/doctypes", { json: { name: form.elements.name.value } });
        await renderOrganize();
      } else if (form.id === "user-form") {
        await api("/api/users", {
          json: {
            username: form.elements.username.value,
            display_name: form.elements.display_name.value,
            password: form.elements.password.value,
            is_admin: form.elements.is_admin.checked,
          },
        });
        toast("Benutzer angelegt.");
        await renderUsers();
      }
    } catch (error) {
      if (form.id === "login-form") {
        const box = $("login-error");
        box.hidden = false;
        box.textContent = error.message;
      } else toast(error.message);
    }
  });

  document.body.addEventListener("change", async (event) => {
    const form = event.target.form;
    if (!form || form.id !== "library-filters") return;
    state.filters = {
      q: form.elements.q.value.trim(),
      tag_id: form.elements.tag_id.value,
      doctype_id: form.elements.doctype_id.value,
      correspondent_id: form.elements.correspondent_id.value,
      tax_only: form.elements.tax_only.checked,
    };
    try {
      await loadLibrary();
    } catch (error) {
      toast(error.message);
    }
  });

  let filterTimer = 0;
  document.body.addEventListener("input", (event) => {
    const form = event.target.form;
    if (!form || form.id !== "library-filters" || event.target.name !== "q") return;
    state.filters.q = event.target.value.trim();
    window.clearTimeout(filterTimer);
    filterTimer = window.setTimeout(async () => {
      try {
        await loadLibrary();
      } catch (error) {
        toast(error.message);
      }
    }, 200);
  });

  document.addEventListener("dragover", (event) => {
    if (state.user) event.preventDefault();
  });
  document.addEventListener("drop", (event) => {
    if (!state.user || !event.dataTransfer || !event.dataTransfer.files.length) return;
    event.preventDefault();
    openUpload(event.dataTransfer.files);
  });

  window.addEventListener("hashchange", () => {
    if (state.user) onHash();
  });
}

async function boot() {
  bind();
  try {
    state.user = await api("/api/auth/me");
    await loadMeta();
    reveal("app");
    paintUser();
    if (!location.hash) location.hash = "#/dashboard";
    await onHash();
  } catch (_error) {
    reveal("login");
  }
}

boot();
