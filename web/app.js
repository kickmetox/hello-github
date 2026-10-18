const $ = (id) => document.getElementById(id);
let status = null;
let browseParent = null;
let selectedSnapshot = null;

async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}
function post(path, body) {
  return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}
function showError(target, error) { $(target).textContent = error.message || String(error); }

async function refreshStatus() {
  status = await api("/api/status");
  $("world-pill").textContent = "läuft unter " + status.world;
  $("vault-line").textContent = "Vault " + status.vault;
  $("home-linux").value = status.homes.linux;
  $("home-windows").value = status.homes.windows;
  $("vault-path").value = status.vault;
  const select = $("pkg-manager");
  const target = status.world === "linux" ? "windows" : "linux";
  select.replaceChildren();
  for (const name of status.managers[target]) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name + " (" + target + ")";
    select.appendChild(option);
  }
}

async function loadBrowse(path) {
  const data = await api("/api/browse?path=" + encodeURIComponent(path || ""));
  browseParent = data.parent;
  $("browse-path").value = data.path;
  const list = $("browser");
  list.replaceChildren();
  for (const entry of data.entries) {
    const item = document.createElement("li");
    const label = document.createElement("button");
    label.type = "button";
    label.className = "ghost";
    label.textContent = (entry.kind === "dir" ? "▸ " : "· ") + entry.name;
    label.onclick = () => { if (entry.kind === "dir") loadBrowse(entry.path).catch((error) => showError("backup-result", error)); };
    const add = document.createElement("button");
    add.type = "button";
    add.className = "mini";
    add.textContent = entry.kind === "dir" ? "Ordner sichern" : "Datei sichern";
    add.onclick = () => addSelection(entry.path, entry.kind);
    item.append(label, add);
    list.appendChild(item);
  }
}

async function loadSelection() {
  const data = await api("/api/selection");
  $("selection").replaceChildren();
  $("world-items").replaceChildren();
  if (!data.items.length) {
    const empty = document.createElement("li");
    empty.textContent = "Noch nichts ausgewählt.";
    $("selection").appendChild(empty);
  }
  for (const item of data.items) {
    const row = document.createElement("li");
    const text = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = item.label;
    const canonical = document.createElement("div");
    canonical.className = "path";
    canonical.textContent = item.canonical;
    text.append(title, canonical);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "mini";
    remove.textContent = "Entfernen";
    remove.onclick = async () => { await post("/api/selection/remove", { id: item.id }); await loadSelection(); };
    row.append(text, remove);
    $("selection").appendChild(row);
    const world = document.createElement("li");
    const block = document.createElement("div");
    const worldTitle = document.createElement("strong");
    worldTitle.textContent = item.label;
    const worldPath = document.createElement("div");
    worldPath.className = "path";
    worldPath.textContent = "Linux: " + (item.paths.linux || "—") + "\nWindows: " + (item.paths.windows || "—");
    block.append(worldTitle, worldPath);
    world.appendChild(block);
    $("world-items").appendChild(world);
  }
}

async function addSelection(path, kind) {
  try {
    await post("/api/selection", { path, kind });
    await loadSelection();
    $("backup-result").textContent = "Aufgenommen: " + path;
  } catch (error) { showError("backup-result", error); }
}

async function loadSnapshots() {
  const data = await api("/api/snapshots");
  const list = $("snapshots");
  list.replaceChildren();
  if (!data.snapshots.length) {
    const empty = document.createElement("li");
    empty.textContent = "Noch keine Sicherung.";
    list.appendChild(empty);
    return;
  }
  for (const snap of data.snapshots) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "ghost";
    button.textContent = snap.id + " · " + snap.source_world + " · " + snap.files + " Dateien";
    button.onclick = async () => {
      selectedSnapshot = snap.id;
      const full = await api("/api/snapshots/" + encodeURIComponent(snap.id));
      $("restore-result").textContent = full.entries.map((entry) => entry.kind + "  " + entry.canonical).join("\n");
    };
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "mini";
    remove.textContent = "Löschen";
    remove.onclick = async () => {
      await post("/api/snapshots/delete", { id: snap.id });
      if (selectedSnapshot === snap.id) selectedSnapshot = null;
      await loadSnapshots();
    };
    item.append(button, remove);
    list.appendChild(item);
  }
}

function drawCurve(curve) {
  const points = curve.map(([temp, duty]) => (20 + (temp / 110) * 280) + "," + (120 - (duty / 100) * 100)).join(" ");
  $("curve").innerHTML = '<polyline fill="none" stroke="#3aa0ff" stroke-width="3" points="' + points + '" />';
}

async function loadHardware() {
  const data = await api("/api/hardware");
  $("hw-note").textContent = data.probe.note || "";
  $("hw-probe").textContent = JSON.stringify(data.probe, null, 2);
  const wrap = $("profiles");
  wrap.replaceChildren();
  for (const [name, profile] of Object.entries(data.store.profiles)) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "profile" + (name === data.store.active ? " active" : "");
    const strong = document.createElement("strong");
    strong.textContent = name;
    const meta = document.createElement("div");
    meta.className = "path";
    meta.textContent = "CPU " + profile.cpu_max_pct + "% · Laden bis " + profile.charge_stop + "%";
    button.append(strong, meta);
    button.onclick = async () => { await post("/api/hardware/active", { name }); drawCurve(profile.curve); await loadHardware(); };
    wrap.appendChild(button);
    if (name === data.store.active) drawCurve(profile.curve);
  }
}

document.querySelector("#nav").onclick = (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  for (const item of document.querySelectorAll("#nav button")) item.classList.toggle("active", item === button);
  for (const panel of document.querySelectorAll(".panel")) panel.classList.toggle("active", panel.id === "panel-" + button.dataset.panel);
};

$("browse-go").onclick = () => loadBrowse($("browse-path").value).catch((error) => showError("backup-result", error));
$("browse-up").onclick = () => { if (browseParent) loadBrowse(browseParent).catch((error) => showError("backup-result", error)); };
$("do-backup").onclick = async () => {
  try {
    const snap = await post("/api/backup", {});
    $("backup-result").textContent = "Sicherung " + snap.id + " mit " + snap.entries.length + " Einträgen.";
    await loadSnapshots();
  } catch (error) { showError("backup-result", error); }
};
$("do-restore").onclick = async () => {
  try {
    if (!selectedSnapshot) throw new Error("Zuerst eine Sicherung auswählen");
    const body = { id: selectedSnapshot, overwrite: $("restore-overwrite").checked, translate_paths: $("restore-translate").checked };
    if ($("restore-dest").value.trim()) body.destination = $("restore-dest").value.trim();
    $("restore-result").textContent = JSON.stringify(await post("/api/restore", body), null, 2);
  } catch (error) { showError("restore-result", error); }
};
$("do-export").onclick = async () => {
  try {
    if (!selectedSnapshot) throw new Error("Zuerst eine Sicherung auswählen");
    const result = await post("/api/export", { id: selectedSnapshot, path: $("export-path").value.trim() });
    $("restore-result").textContent = "Exportiert nach " + result.path;
  } catch (error) { showError("restore-result", error); }
};
$("do-import").onclick = async () => {
  try {
    const result = await post("/api/import", { path: $("import-path").value.trim() });
    $("restore-result").textContent = "Importiert: " + result.id;
    await loadSnapshots();
  } catch (error) { showError("restore-result", error); }
};
$("save-homes").onclick = async () => {
  await post("/api/homes", { homes: { linux: $("home-linux").value.trim(), windows: $("home-windows").value.trim() } });
  await refreshStatus();
};
$("save-vault").onclick = async () => {
  await post("/api/vault", { path: $("vault-path").value.trim() });
  await refreshStatus();
  await loadSelection();
  await loadSnapshots();
};
$("detect-apps").onclick = async () => { $("app-names").value = (await api("/api/apps/detect")).installed.join("\n"); };
$("plan-apps").onclick = async () => {
  try {
    const plan = await post("/api/apps/plan", { names: $("app-names").value, manager: $("pkg-manager").value, target: status.world === "linux" ? "windows" : "linux" });
    $("app-plan").textContent = JSON.stringify(plan, null, 2);
  } catch (error) { showError("app-plan", error); }
};
$("load-bashrc").onclick = async () => { $("tr-in").value = (await api("/api/examples/bashrc.sample")).text; };
$("do-translate").onclick = async () => {
  try {
    const result = await post("/api/translate", { text: $("tr-in").value, source: $("tr-source").value, target: $("tr-target").value });
    $("tr-out").textContent = result.text + (result.reg ? "\n\n" + result.reg : "");
  } catch (error) { showError("tr-out", error); }
};
$("do-shortcut").onclick = async () => {
  try { $("shortcut-out").textContent = JSON.stringify(await post("/api/shortcuts", { shortcut: $("shortcut").value }), null, 2); }
  catch (error) { showError("shortcut-out", error); }
};
$("do-gestures").onclick = async () => {
  const result = await post("/api/gestures", { settings: { natural_scroll: $("natural-scroll").checked, tap_to_click: $("tap-click").checked } });
  $("theme-out").textContent = result.primary;
};
$("do-theme").onclick = async () => {
  try {
    const result = await post("/api/theme", { theme: { mode: "schedule", accent: "#0078D4", dark_from: "19:00", light_from: "07:00" } });
    $("theme-out").textContent = result.primary;
  } catch (error) { showError("theme-out", error); }
};
$("load-event").onclick = async () => { $("log-in").value = (await api("/api/examples/event.log")).text; };
$("load-dmesg").onclick = async () => { $("log-in").value = (await api("/api/examples/dmesg.log")).text; };
$("do-diagnose").onclick = async () => {
  try {
    const result = await post("/api/diagnose", { text: $("log-in").value });
    const wrap = $("findings");
    wrap.replaceChildren();
    for (const finding of result.findings) {
      const block = document.createElement("article");
      block.className = "finding";
      const sev = document.createElement("p");
      sev.className = "sev";
      sev.textContent = finding.severity + " · " + finding.risk;
      const heading = document.createElement("h3");
      heading.textContent = finding.title;
      const explanation = document.createElement("p");
      explanation.textContent = finding.explanation;
      const cause = document.createElement("p");
      cause.textContent = finding.cause;
      block.append(sev, heading, explanation, cause);
      if (finding.script) {
        const pre = document.createElement("pre");
        pre.className = "out";
        pre.textContent = finding.script;
        block.appendChild(pre);
      }
      wrap.appendChild(block);
    }
  } catch (error) { $("findings").textContent = error.message; }
};
$("do-fs").onclick = async () => {
  try {
    const result = await post("/api/filesystem", { world: $("fs-world").value, filesystem: $("fs-type").value, device: $("fs-device").value });
    $("fs-out").textContent = result.summary + "\n\n" + result.commands.join("\n");
  } catch (error) { showError("fs-out", error); }
};

refreshStatus().then(() => loadBrowse(status.home)).then(loadSelection).then(loadSnapshots).then(loadHardware).catch((error) => {
  $("backup-result").textContent = error.message;
});
