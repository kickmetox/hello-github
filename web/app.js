const $ = (id) => document.getElementById(id);

const titles = {
  overview: ["Modul 00", "Übersicht"],
  migrator: ["Modul 01", "Migrator"],
  diagnose: ["Modul 02", "Diagnose"],
  hardware: ["Modul 03", "Hardware"],
};

document.querySelectorAll("nav button").forEach((button) => {
  button.addEventListener("click", () => showPage(button.dataset.page));
});

function showPage(name) {
  document.querySelectorAll("nav button").forEach((button) => {
    button.classList.toggle("active", button.dataset.page === name);
  });
  for (const key of Object.keys(titles)) {
    document.getElementById(`page-${key}`).classList.toggle("hidden", key !== name);
  }
  $("eyebrow").textContent = titles[name][0];
  $("title").textContent = titles[name][1];
  if (name === "hardware") loadFans();
  if (name === "overview") loadOverview();
}

document.querySelectorAll("#mig-tabs button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("#mig-tabs button").forEach((item) => item.classList.toggle("active", item === button));
    document.querySelectorAll("[data-mig]").forEach((panel) => {
      panel.classList.toggle("hidden", panel.dataset.mig !== button.dataset.tab);
    });
  });
});

async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }
  return data;
}

function post(path, body) {
  return api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function show(id, value) {
  $(id).textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

async function loadOverview() {
  try {
    show("overview-out", await api("/api/overview"));
  } catch (error) {
    show("overview-out", error.message);
  }
}
$("reload-overview").addEventListener("click", loadOverview);

document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", async () => {
    const data = await api(`/api/examples/${button.dataset.example}`);
    $("cfg-text").value = data.text;
  });
});

$("cfg-run").addEventListener("click", async () => {
  try {
    const body = {
      text: $("cfg-text").value,
      target_format: $("cfg-to").value,
      target_os: $("cfg-os").value,
      user: $("cfg-user").value,
    };
    if ($("cfg-from").value) body.source_format = $("cfg-from").value;
    const data = await post("/api/translate", body);
    $("cfg-out").textContent = data.output;
    const rows = (data.changes || []).map((change) => {
      const before = change.before ?? "";
      const after = change.after ?? "";
      return `<tr><td>${escapeHtml(change.kind)}</td><td>${escapeHtml(change.key || "")}</td><td class="mono">${escapeHtml(String(before))}</td><td class="mono">${escapeHtml(String(after))}</td></tr>`;
    }).join("");
    $("cfg-diff").innerHTML = rows
      ? `<table><thead><tr><th>Art</th><th>Schlüssel</th><th>Vorher</th><th>Nachher</th></tr></thead><tbody>${rows}</tbody></table>`
      : "<p class='muted'>Keine Pfad- oder Schlüsseländerung.</p>";
  } catch (error) {
    show("cfg-out", error.message);
  }
});

$("path-run").addEventListener("click", async () => {
  try {
    show("path-out", await post("/api/paths", { path: $("path-in").value, target_os: $("path-os").value, user: "andreas" }));
  } catch (error) {
    show("path-out", error.message);
  }
});

$("apps-run").addEventListener("click", async () => {
  try {
    const apps = $("apps-in").value.split(",").map((item) => item.trim()).filter(Boolean);
    const data = await post("/api/apps/plan", { apps, target_os: $("apps-os").value, detect: $("apps-detect").checked });
    $("apps-out").innerHTML = data.apps.map(renderApp).join("");
  } catch (error) {
    $("apps-out").innerHTML = `<p class="danger">${escapeHtml(error.message)}</p>`;
  }
});

function renderApp(app) {
  const plans = [...(app.target_plans || [])];
  for (const alt of app.alternatives || []) {
    for (const plan of alt.plans || []) plans.push({ ...plan, role: alt.role });
  }
  const commands = plans.map((plan) => `<li><span class="mono">${escapeHtml(plan.shell || "")}</span> ${plan.role ? "· " + escapeHtml(plan.role) : ""} · ${plan.manager_present ? "Manager da" : "Manager fehlt"} · dry-run</li>`).join("");
  const altNotes = (app.alternatives || []).filter((item) => item.note).map((item) => `<p class="muted">${escapeHtml(item.role || "")}: ${escapeHtml(item.note)}</p>`).join("");
  return `<article class="card"><div class="row"><strong>${escapeHtml(app.id)}</strong><span class="tag ${escapeHtml(app.equivalence)}">${escapeHtml(app.equivalence)}</span></div><p>${escapeHtml(app.summary_de)}</p>${app.note ? `<p class="muted">${escapeHtml(app.note)}</p>` : ""}${altNotes}<ul>${commands || "<li>Kein Installationsbefehl. Nur Hinweis.</li>"}</ul></article>`;
}

$("keys-example").addEventListener("click", async () => {
  const data = await api("/api/examples/vscode-keybindings.json");
  $("keys-in").value = data.text;
});

$("keys-run").addEventListener("click", async () => {
  try {
    const raw = $("keys-in").value.trim();
    const target = $("keys-os").value;
    const body = raw.startsWith("[") ? { bindings: JSON.parse(raw), target_os: target } : { shortcut: raw, target_os: target };
    show("keys-out", await post("/api/shortcuts", body));
  } catch (error) {
    show("keys-out", error.message);
  }
});

$("g-run").addEventListener("click", async () => {
  try {
    show("g-out", await post("/api/gestures", {
      profile: {
        natural_scroll: $("g-natural").checked,
        tap_to_click: $("g-tap").checked,
        three_finger: $("g-three").value,
        four_finger: $("g-four").value,
      },
    }));
  } catch (error) {
    show("g-out", error.message);
  }
});

$("t-run").addEventListener("click", async () => {
  try {
    show("t-out", await post("/api/theme", {
      profile: {
        mode: $("t-mode").value,
        accent: $("t-accent").value,
        cursor: $("t-cursor").value,
        wallpaper: $("t-wall").value,
      },
      user: "andreas",
    }));
  } catch (error) {
    show("t-out", error.message);
  }
});

document.querySelectorAll("[data-log]").forEach((button) => {
  button.addEventListener("click", async () => {
    const data = await api(`/api/examples/${button.dataset.log}`);
    $("diag-text").value = data.text;
  });
});

$("diag-run").addEventListener("click", async () => {
  try {
    const data = await post("/api/diagnose", { text: $("diag-text").value, shell: $("diag-shell").value });
    $("diag-out").innerHTML = data.findings.map((finding) => renderFinding(finding, data.shell)).join("");
  } catch (error) {
    $("diag-out").innerHTML = `<p class="danger">${escapeHtml(error.message)}</p>`;
  }
});

function renderFinding(finding, shell) {
  const apply = finding.apply || {};
  const id = `apply-${finding.code}`;
  const button = apply.eligible
    ? `<label class="checks"><input type="checkbox" id="${id}-c"> Ich bestätige die freigegebene Leseaktion ${escapeHtml(apply.action_id)}</label>
       <button type="button" class="btn" data-apply="${escapeHtml(apply.action_id)}" data-box="${id}-c">Ausführen</button>`
    : `<p class="muted">${escapeHtml(apply.reason_de || "")}</p>`;
  return `<article class="panel card"><div class="kicker">${escapeHtml(finding.code)}</div><h2>${escapeHtml(finding.title)}</h2><p>${escapeHtml(finding.plain_de)}</p><pre>${escapeHtml(finding.script || "")}</pre>${button}<pre id="result-${escapeHtml(finding.code)}"></pre></article>`;
}

document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-apply]");
  if (!button) return;
  const box = document.getElementById(button.dataset.box);
  if (!box || !box.checked) {
    alert("Bestätigung fehlt.");
    return;
  }
  try {
    const data = await post("/api/repair/apply", { action_id: button.dataset.apply, confirm: true });
    const slot = document.getElementById(`result-${button.closest("article").querySelector(".kicker").textContent}`);
    if (slot) slot.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    alert(error.message);
  }
});

$("fw-run").addEventListener("click", async () => {
  try { show("fw-out", await api("/api/firmware")); } catch (error) { show("fw-out", error.message); }
});

$("rs-run").addEventListener("click", async () => {
  const host = $("rs-host").value;
  const fs = $("rs-fs").value;
  let device = $("rs-dev").value;
  if (host === "windows" && device.startsWith("/dev")) device = "E:";
  if (host === "linux" && /^[A-Z]:$/.test(device)) device = "/dev/sdb1";
  $("rs-dev").value = device;
  try {
    show("rs-out", await post("/api/rescue", { host_os: host, filesystem: fs, device }));
  } catch (error) {
    show("rs-out", error.message);
  }
});

async function loadFans() {
  if ($("fan-names").dataset.ready === "1") return;
  const data = await api("/api/hardware/fans");
  $("fan-names").innerHTML = data.profiles.map((profile, index) =>
    `<button type="button" data-fan="${profile.name}" class="${index === 0 ? "active" : ""}">${profile.name}</button>`
  ).join("");
  $("fan-names").dataset.ready = "1";
  $("fan-names").querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      $("fan-names").querySelectorAll("button").forEach((item) => item.classList.toggle("active", item === button));
      const profile = data.profiles.find((item) => item.name === button.dataset.fan);
      drawFan(profile);
    });
  });
  drawFan(data.profiles[0]);
  const power = await api("/api/hardware/power");
  $("pwr-out").innerHTML = `<table><thead><tr><th>Plan</th><th>Windows</th><th>ppd</th><th>TLP AC/BAT</th><th></th></tr></thead><tbody>${
    power.plans.map((plan) => `<tr><td>${escapeHtml(plan.id)}</td><td class="mono">${escapeHtml(plan.windows_guid)}</td><td>${escapeHtml(plan.ppd)}</td><td class="mono">${escapeHtml(plan.tlp_governor_ac)} / ${escapeHtml(plan.tlp_governor_bat)}</td><td><button type="button" class="btn-ghost" data-power="${escapeHtml(plan.id)}">Anwenden</button></td></tr>`).join("")
  }</tbody></table><p class="muted">powerprofilesctl: ${power.powerprofilesctl || "nicht vorhanden"}</p>`;
}

function drawFan(profile) {
  const points = profile.points;
  const w = 680, h = 230, l = 40, b = 28, t = 16, r = 12;
  const x = (temp) => l + (temp / 110) * (w - l - r);
  const y = (duty) => t + (1 - duty / 100) * (h - t - b);
  const poly = points.map((point) => `${x(point.temp_c)},${y(point.duty_percent)}`).join(" ");
  const dots = points.map((point) => `<circle cx="${x(point.temp_c)}" cy="${y(point.duty_percent)}" r="3.5" fill="#dff24a"/>`).join("");
  const labels = points.map((point) => `<text x="${x(point.temp_c)}" y="${h - 8}" text-anchor="middle" fill="#a4aa90" font-size="11" font-family="IBM Plex Mono, monospace">${point.temp_c}°</text>`).join("");
  $("fan-svg").innerHTML = `<svg class="fan" viewBox="0 0 ${w} ${h}" role="img" aria-label="Lüfterkurve ${profile.name}"><line x1="${l}" y1="${t}" x2="${l}" y2="${h - b}" stroke="#343b2a"/><line x1="${l}" y1="${h - b}" x2="${w - r}" y2="${h - b}" stroke="#343b2a"/><polyline fill="none" stroke="#dff24a" stroke-width="2" points="${poly}"/>${dots}${labels}</svg>`;
  $("fan-out").textContent = JSON.stringify({ linux: profile.linux.points, windows: profile.windows.points, applied: profile.applied }, null, 2);
}

document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-power]");
  if (!button) return;
  try {
    const data = await post("/api/hardware/power", { id: button.dataset.power, confirm: $("pwr-confirm").checked });
    alert(data.reason_de || (data.executed ? "Gesetzt." : "Plan, nicht ausgeführt."));
  } catch (error) {
    alert(error.message);
  }
});

$("hw-probe").addEventListener("click", async () => {
  try { show("hw-probe-out", await api("/api/hardware/probe")); } catch (error) { show("hw-probe-out", error.message); }
});

$("bat-range").addEventListener("input", () => { $("bat-label").textContent = $("bat-range").value; });
$("bat-run").addEventListener("click", async () => {
  try {
    show("bat-out", await post("/api/hardware/battery", {
      stop_percent: Number($("bat-range").value),
      confirm: $("bat-confirm").checked,
    }));
  } catch (error) {
    show("bat-out", error.message);
  }
});

$("uv-run").addEventListener("click", async () => {
  try {
    show("uv-out", await post("/api/hardware/undervolt", {
      cpu: { vendor: $("uv-cpu").value, core_offset_mv: Number($("uv-core").value), cache_offset_mv: Number($("uv-cache").value) },
      gpu: { vendor: $("uv-gpu").value, offset_mv: Number($("uv-gmv").value), core_clock_mhz: Number($("uv-gcore").value), mem_clock_mhz: 0 },
    }));
  } catch (error) {
    show("uv-out", error.message);
  }
});

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
}

loadOverview();
