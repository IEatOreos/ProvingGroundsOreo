/* The Service Record's emblem editor (custom, Nov 18, the owner: an emblem editor for each bot "like MCC's own", in
   edit mode only). The owner's editor serves this file (tools/service_record_edit.py /api/emblem-editor.js); the built
   site does not have it, so a copy of the site elsewhere has no editor. It picks MCC's own parts (a foreground, a
   background, the primary, secondary and background colours, the secondary part on or off: maps/_looks/
   mcc_emblems.json), draws them live as MCC layers them (brain/emblems.py compose: background, then secondary, then
   primary, each layer's shape tinted with its colour) and saves them for the bot (POST /api/bot-emblem). MCC shows a
   saved emblem from the bot's next lobby or match. */
(function () {
  "use strict";
  const SIZE = 128;
  const HEAD = { "Content-Type": "application/json", "X-Service-Record-Edit": "1" };

  function el(tag, attrs, ...kids) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === false || v == null) continue;
      if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat(Infinity)) if (kid != null && kid !== false) node.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    return node;
  }
  async function getJSON(url, opts) {
    const r = await fetch(url, Object.assign({ cache: "no-store" }, opts || {}));
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || "error");
    return d;
  }
  const failed = (e, what) => (e instanceof TypeError ? what + ": the editor is not running." : what + ": " + e.message);

  let catalog = null;
  const catalogOnce = () => catalog || (catalog = getJSON("/api/emblem-catalog").catch((e) => { catalog = null; throw e; }));
  const art = (layer) => "/api/emblem-art/" + encodeURIComponent(layer) + ".png";

  // each layer's shape as alpha (its grey: brain/emblems.py compose's convert("L")), SIZE x SIZE, loaded once
  const shapes = new Map();
  function shape(layer) {
    if (!shapes.has(layer)) {
      shapes.set(layer, new Promise((ok, no) => {
        const img = new Image();
        img.onload = () => {
          const c = document.createElement("canvas");
          c.width = c.height = SIZE;
          const g = c.getContext("2d");
          g.imageSmoothingQuality = "high";
          g.drawImage(img, 0, 0, SIZE, SIZE);
          const d = g.getImageData(0, 0, SIZE, SIZE).data, a = new Float32Array(SIZE * SIZE);
          for (let i = 0; i < a.length; i++) a[i] = d[i * 4] / 255;
          ok(a);
        };
        img.onerror = () => { shapes.delete(layer); no(new Error("its art is not on this PC")); };
        img.src = art(layer);
      }));
    }
    return shapes.get(layer);
  }
  // the emblem as MCC layers it, onto a canvas
  async function paint(canvas, e, cat) {
    const f = cat.fg.find((x) => x[0] === e.fg), b = cat.bg.find((x) => x[0] === e.bg);
    if (!f || !b) return;
    const parts = [[b[1], e.background], [f[2], e.secondary], [f[1], e.primary]];
    const alphas = await Promise.all(parts.map(([layer]) => shape(layer)));
    const out = new Float32Array(SIZE * SIZE * 4);
    parts.forEach(([, c], n) => {
      const rgb = cat.colours[String(c)];
      if (!rgb) return;                                     // (the transparent colour: that layer is off)
      const a = alphas[n];
      for (let i = 0; i < a.length; i++) {
        const k = a[i], j = i * 4;
        out[j] = out[j] * (1 - k) + rgb[0] * k;
        out[j + 1] = out[j + 1] * (1 - k) + rgb[1] * k;
        out[j + 2] = out[j + 2] * (1 - k) + rgb[2] * k;
        out[j + 3] = out[j + 3] * (1 - k) + 255 * k;
      }
    });
    const img = new ImageData(SIZE, SIZE);
    for (let i = 0; i < out.length; i++) img.data[i] = Math.round(out[i]);
    canvas.getContext("2d").putImageData(img, 0, 0);
  }

  function style() {
    if (document.getElementById("emblem-editor-style")) return;
    document.head.append(el("style", { id: "emblem-editor-style" }, `
.emb-ed { flex-basis: 100%; display: grid; grid-template-columns: auto minmax(0, 1fr); gap: var(--s-3) var(--s-4); margin-top: var(--s-2); padding: var(--s-3); border: 1px dashed var(--gold); border-radius: var(--radius); background: rgba(4, 10, 18, 0.82); text-shadow: none; }
.emb-ed .emb-side { display: grid; justify-items: center; align-content: start; gap: var(--s-2); }
.emb-ed canvas { width: 160px; height: 160px; border-radius: var(--radius); border: 1px solid var(--line-2); background: repeating-conic-gradient(#0d1a29 0 25%, #12233a 0 50%) 0 0 / 16px 16px; image-rendering: auto; }
.emb-ed .emb-was { display: flex; align-items: center; gap: var(--s-2); color: var(--ink-3); font-size: var(--t-xs); }
.emb-ed .emb-was canvas { width: 40px; height: 40px; }
.emb-ed .emb-state { color: var(--gold); font-size: var(--t-xs); text-transform: uppercase; letter-spacing: 0.05em; }
.emb-ed .emb-acts { display: grid; gap: var(--s-2); width: 100%; }
.emb-ed button { font: inherit; font-size: var(--t-sm); color: var(--ink); background: rgba(232, 178, 60, 0.15); border: 1px solid var(--gold); border-radius: var(--radius); padding: var(--s-1) var(--s-3); min-height: 34px; cursor: pointer; }
.emb-ed button:hover { background: rgba(232, 178, 60, 0.3); }
.emb-ed .emb-msg { color: var(--ink-2); font-size: var(--t-xs); max-width: 12rem; text-align: center; }
.emb-ed .emb-main { min-width: 0; display: grid; gap: var(--s-2); align-content: start; }
.emb-ed .emb-tabs { display: flex; flex-wrap: wrap; gap: 4px; }
.emb-ed .emb-tabs button { background: rgba(9, 20, 34, 0.6); border-color: var(--line-2); color: var(--ink-2); text-transform: uppercase; letter-spacing: 0.05em; font-size: var(--t-xs); }
.emb-ed .emb-tabs button[aria-selected="true"] { color: var(--ink); border-color: var(--gold); background: rgba(232, 178, 60, 0.18); }
.emb-ed .emb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(52px, 1fr)); gap: 4px; max-height: 300px; overflow-y: auto; padding: 2px; }
.emb-ed .emb-grid button { position: relative; padding: 3px; min-height: 0; aspect-ratio: 1; background: #050b14; border-color: var(--line); }
.emb-ed .emb-grid button[aria-pressed="true"] { border-color: var(--gold); box-shadow: 0 0 0 2px var(--gold) inset; }
.emb-ed .emb-grid img { position: absolute; inset: 3px; width: calc(100% - 6px); height: calc(100% - 6px); }
.emb-ed .emb-grid img + img { mix-blend-mode: screen; opacity: 0.55; }
.emb-ed .emb-row { display: grid; gap: 4px; }
.emb-ed .emb-row > span { color: var(--gold); font-size: var(--t-xs); text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: var(--s-3); }
.emb-ed .emb-row label { color: var(--ink-2); text-transform: none; letter-spacing: 0; display: inline-flex; align-items: center; gap: 4px; }
.emb-ed .emb-sw { display: grid; grid-template-columns: repeat(auto-fill, minmax(28px, 1fr)); gap: 4px; max-width: 30rem; }
.emb-ed .emb-sw button { min-height: 28px; aspect-ratio: 1; padding: 0; border: 1px solid rgba(255, 255, 255, 0.25); }
.emb-ed .emb-sw button[aria-pressed="true"] { box-shadow: 0 0 0 2px #050b14, 0 0 0 4px var(--gold); }
.emb-ed .emb-sw button:disabled { opacity: 0.25; cursor: not-allowed; }
.emb-ed .emb-name { color: var(--ink-2); font-size: var(--t-xs); min-height: 1.2em; }
@media (max-width: 760px) { .emb-ed { grid-template-columns: minmax(0, 1fr); } .emb-ed .emb-msg { max-width: none; } }
`));
  }

  // the editor for one bot, into `host`; onSaved(emblem) after a save (the site rebuilds and reloads itself)
  async function open(host, name, onSaved) {
    style();
    const box = el("div", { class: "emb-ed", role: "group", "aria-label": "Emblem editor for " + name }, el("span", { class: "emb-msg" }, "Loading the emblems…"));
    host.replaceChildren(box);
    let cat, now;
    try { [cat, now] = await Promise.all([catalogOnce(), getJSON("/api/bot-emblem?name=" + encodeURIComponent(name))]); }
    catch (e) { box.replaceChildren(el("span", { class: "emb-msg" }, failed(e, "Not loaded"))); return; }
    if (!cat.art) { box.replaceChildren(el("span", { class: "emb-msg" }, "The emblems' art is not on this PC (tools/emblems.py extract makes it).")); return; }
    const e = Object.assign({}, now.emblem), rolled = now.rolled;
    let lastSecondary = e.secondary === cat.off ? Object.keys(cat.colours).map(Number).find((c) => c !== e.primary) : e.secondary;
    const big = el("canvas", { width: SIZE, height: SIZE, role: "img", "aria-label": "Emblem preview" });
    const was = el("canvas", { width: SIZE, height: SIZE, role: "img", "aria-label": "Its rolled emblem" });
    const state = el("span", { class: "emb-state" });
    const msg = el("span", { class: "emb-msg", "aria-live": "polite" });
    const label = el("div", { class: "emb-name", "aria-live": "polite" });
    let drawing = 0;
    const redraw = () => {
      const mine = ++drawing;
      const c = document.createElement("canvas");
      c.width = c.height = SIZE;
      paint(c, e, cat).then(() => {                        // (cleared first: drawImage blends over what was there)
        if (mine !== drawing) return;
        const g = big.getContext("2d");
        g.clearRect(0, 0, SIZE, SIZE);
        g.drawImage(c, 0, 0);
      })
        .catch((err) => { msg.textContent = "Not drawn: " + err.message; });
      const same = ["fg", "bg", "primary", "secondary", "background"].every((k) => e[k] === now.emblem[k]);
      state.textContent = (now.custom ? "Custom emblem" : "Rolled emblem") + (same ? "" : " · not saved");
    };
    paint(was, rolled, cat).catch(() => {});

    // the parts: a grid of thumbnails each (the foreground's two layers, the background's one)
    const grid = (items, key, layersOf, title) => {
      const g = el("div", { class: "emb-grid", role: "group", "aria-label": title });
      const buttons = items.map((x) => el("button", { type: "button", title: x[x.length - 1] || "#" + x[0], "aria-label": (x[x.length - 1] || title) + " (" + x[0] + ")",
        "aria-pressed": String(e[key] === x[0]), onclick: () => { e[key] = x[0]; buttons.forEach((b, i) => b.setAttribute("aria-pressed", String(items[i][0] === e[key]))); label.textContent = x[x.length - 1] || ""; redraw(); } },
        layersOf(x).map((l) => el("img", { src: art(l), alt: "", loading: "lazy", width: 48, height: 48 }))));
      g.append(...buttons);
      return g;
    };
    const fgGrid = grid(cat.fg, "fg", (x) => [x[1], x[2]], "Foregrounds");
    const bgGrid = grid(cat.bg, "bg", (x) => [x[1]], "Backgrounds");
    // the colours: MCC's 30, three rows; the secondary row's switch turns that part off (MCC's transparent colour)
    const ids = Object.keys(cat.colours).map(Number).sort((a, b) => a - b);
    const rows = {};
    const swatches = (key, title) => {
      const s = el("div", { class: "emb-sw", role: "group", "aria-label": title + " colour" });
      const buttons = ids.map((c) => el("button", { type: "button", style: "background: rgb(" + cat.colours[String(c)].join(",") + ")", title: title + " colour " + c,
        "aria-label": title + " colour " + c, "aria-pressed": String(e[key] === c),
        onclick: () => { e[key] = c; if (key === "secondary") lastSecondary = c; sync(); redraw(); } }));
      s.append(...buttons);
      rows[key] = buttons;
      return s;
    };
    const on = el("input", { type: "checkbox", checked: e.secondary !== cat.off, "aria-label": "Secondary part on" });
    on.addEventListener("change", () => { e.secondary = on.checked ? lastSecondary : cat.off; sync(); redraw(); });
    const sync = () => {
      for (const [key, buttons] of Object.entries(rows)) buttons.forEach((b, i) => {
        b.setAttribute("aria-pressed", String(e[key] === ids[i]));
        if (key === "secondary") b.disabled = !on.checked;
      });
      on.checked = e.secondary !== cat.off;
    };
    const colours = el("div", { class: "emb-colours", role: "group", "aria-label": "Colours" },
      el("div", { class: "emb-row" }, el("span", null, "Primary"), swatches("primary", "Primary")),
      el("div", { class: "emb-row" }, el("span", null, "Secondary", el("label", null, on, "On")), swatches("secondary", "Secondary")),
      el("div", { class: "emb-row" }, el("span", null, "Background"), swatches("background", "Background")));
    sync();
    const panes = { Foreground: fgGrid, Background: bgGrid, Colours: colours };
    const slot = el("div");
    const tabs = el("div", { class: "emb-tabs", role: "tablist" });
    const show = (k) => { slot.replaceChildren(panes[k]); [...tabs.children].forEach((t) => t.setAttribute("aria-selected", String(t.textContent === k))); };
    tabs.append(...Object.keys(panes).map((k) => el("button", { type: "button", role: "tab", onclick: () => show(k) }, k)));
    show("Foreground");
    const fgName = cat.fg.find((x) => x[0] === e.fg);
    label.textContent = fgName ? fgName[3] || "" : "";

    const send = async (body, done) => {
      msg.textContent = "Saving…";
      try {
        const d = await getJSON("/api/bot-emblem", { method: "POST", headers: HEAD, body: JSON.stringify(Object.assign({ name }, body)) });
        now = { emblem: d.emblem, custom: d.custom };
        Object.assign(e, d.emblem);
        sync();
        redraw();
        msg.textContent = done;
        if (onSaved) onSaved(d.emblem);
      } catch (err) { msg.textContent = failed(err, "Not saved"); }
    };
    box.replaceChildren(
      el("div", { class: "emb-side" }, big, state, el("div", { class: "emb-was" }, was, "Its rolled emblem"),
        el("div", { class: "emb-acts" },
          el("button", { type: "button", onclick: () => send({ fg: e.fg, bg: e.bg, primary: e.primary, secondary: e.secondary, background: e.background },
            "Saved. MCC shows it from " + name + "'s next lobby or match; the page reloads with the new build.") }, "Save emblem"),
          el("button", { type: "button", onclick: () => send({ reset: true }, "Back to its rolled emblem. The page reloads with the new build.") }, "Back to its rolled emblem")),
        msg),
      el("div", { class: "emb-main" }, tabs, label, slot));
    redraw();
  }

  window.SREmblemEditor = { open };
})();
