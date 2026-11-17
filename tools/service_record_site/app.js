/* Proving Grounds Service Record: the pages (tools/service_record.py copies this into the built site).
   Everything shown comes from window.SR_DATA (data.js); every number in it was summed by the build, this file only
   lays it out. Text always goes in as text, never as HTML. */
(function () {
  "use strict";
  const D = window.SR_DATA;
  const main = document.getElementById("main");
  const nav = document.getElementById("nav");
  const shell = document.querySelector(".shell");
  const card = document.getElementById("card");
  const gamePick = document.getElementById("game");
  if (!D) {
    main.replaceChildren(el("p", { class: "note" },
      "The stats file (data.js) is missing. Build the site again: python\\python.exe -I tools\\service_record.py"));
    return;
  }

  // ---------------------------------------------------------------- small tools
  function fill(node, attrs, kids) {
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === false || v == null) continue;
      if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat(Infinity)) {
      if (kid == null || kid === false) continue;
      node.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    }
    return node;
  }
  function el(tag, attrs, ...kids) { return fill(document.createElement(tag), attrs, kids); }
  function svg(tag, attrs, ...kids) { return fill(document.createElementNS("http://www.w3.org/2000/svg", tag), attrs, kids); }
  const int = (n) => Number(n || 0).toLocaleString("en-US");
  const dec = (v) => (v == null ? "-" : Number(v).toFixed(2));
  const ordinal = (n) => { const s = ["th", "st", "nd", "rd"], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); };
  const day = (t) => new Date(t * 1000).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  const title = (key) => (key ? key.charAt(0).toUpperCase() + key.slice(1) : "");

  const ZERO = { games: 0, wins: 0, kills: 0, deaths: 0, assists: 0, seconds: 0, detailed: 0, alive: 0, betrayals: 0,
    suicides: 0, medals: 0, kw: 0, kg: 0, km: 0, ko: 0, score: 0, spree: 0,
    r: { kd: 0, kpg: null, dpg: null, apg: null, kph: null, dph: null, mpg: null, mph: null, win: null, playtime: "0d 0h 0m" } };
  const players = new Map(D.players.map((p) => [p.name, p]));
  const gameName = new Map(D.games);
  const catName = new Map(D.cats);
  const RING = ["slayer", "ctf", "koth", "territories", "oddball", "infection", "assault", "invasion"];
  const PAGES = [
    ["Service Record", [["overview", "Overview"], ["placements", "State Placements"], ["history", "Game History"], ["commendations", "Commendations"],
      ["heatmaps", "Heatmaps"], ["achievements", "Achievements"], ["profile", "Profile"]]],
    ["Career Stats", [["summary", "Summary"], ["types", "By Game Type"], ["maps", "By Map"], ["medals", "Medals"],
      ["weapons", "Weapons"], ["enemies", "Enemies"]]],
  ];

  // ---------------------------------------------------------------- where we are (the address after #)
  let route = { parts: [], q: {} };
  function parse() {
    const raw = location.hash.replace(/^#\/?/, "");
    const cut = raw.indexOf("?");
    const path = cut < 0 ? raw : raw.slice(0, cut);
    let parts;
    try { parts = path.split("/").filter(Boolean).map(decodeURIComponent); } catch (e) { parts = ["?"]; }
    const q = Object.fromEntries(new URLSearchParams(cut < 0 ? "" : raw.slice(cut + 1)));
    if (!gameName.has(q.game)) delete q.game;
    return { parts, q };
  }
  function href(parts, q) {
    const all = Object.assign({}, route.q.game ? { game: route.q.game } : {}, q || {});
    for (const k of Object.keys(all)) if (all[k] == null || all[k] === "") delete all[k];
    const qs = new URLSearchParams(all).toString();
    return "#/" + parts.map(encodeURIComponent).join("/") + (qs ? "?" + qs : "");
  }
  const game = () => route.q.game || D.default_game;
  const bucket = (p, cat) => (p.g[game()] && p.g[game()].cats[cat || "all"]) || ZERO;
  const side = (p) => p.g[game()] || null;
  const mapName = (id) => (D.maps && D.maps[id]) || id || "Unknown map";

  // ---------------------------------------------------------------- shared pieces
  function panel(heading, body, extra) {
    return el("section", { class: "panel" }, el("header", null, el("h2", null, heading), extra), body);
  }
  function empty(strong, text) {
    return el("div", { class: "empty" }, el("strong", null, strong), text);
  }
  const noGames = () => empty("No counted matches yet",
    "Nothing has been recorded here for " + gameName.get(game()) + ". This fills in after the next match: " +
    "the site rebuilds itself when a match starts.");

  function emblem(p, small) {
    const size = small ? 28 : 72;
    if (p && p.emblem) return el("img", { class: "emblem" + (small ? " sm" : ""), src: p.emblem, alt: "", width: size, height: size, loading: small ? "lazy" : null });
    return el("span", { class: "emblem none" + (small ? " sm" : ""), "aria-hidden": "true" }, small ? "" : "No emblem");
  }
  // A rank's insignia. Real art made on this PC (ranks/<step>.png) when the build found some; else our own
  // placeholder: a plate with the rank's number and one pip per Grade.
  function insignia(step, small) {
    const cls = "insignia" + (small ? " sm" : "");
    const size = small ? 28 : 56;
    if ((D.rank_art || []).includes(step)) return el("img", { class: cls, src: "ranks/" + step + ".png", alt: "", width: size, height: size });
    const [, , number, grade] = D.ranks[step];
    const pips = [];
    for (let i = 0; i < grade; i++) pips.push(svg("circle", { cx: 24 - (grade - 1) * 4 + i * 8, cy: 37, r: 2.2, fill: "currentColor" }));
    return svg("svg", { class: cls, viewBox: "0 0 48 48", width: size, height: size, "aria-hidden": "true" },
      svg("path", { d: "M24 3 42 13v22L24 45 6 35V13z", fill: "none", stroke: "currentColor", "stroke-width": 2.5, "stroke-linejoin": "round" }),
      svg("text", { x: 24, y: grade ? 29 : 31, "text-anchor": "middle", "font-size": 17, "font-weight": 700, fill: "currentColor", "font-family": "inherit" }, number),
      pips);
  }
  // Line icons, drawn for this site (24 x 24, stroked in the text's colour).
  const ICONS = {
    overview: "M3 11l9-7 9 7v9h-6v-6H9v6H3z",
    placements: "M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11zM12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z",
    history: "M3 12a9 9 0 1 0 2.6-6.4M3 4v4h4M12 7v5l3 3",
    commendations: "M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6-4.5-4.2 6.1-.7z",
    heatmaps: "M12 21c-4 0-6.5-2.6-6.5-6 0-4 3.5-5.5 4-9 2.5 1.5 4 4 4 6 1-.5 1.6-1.6 1.8-3 1.7 1.6 3.2 3.8 3.2 6 0 3.4-2.5 6-6.5 6z",
    achievements: "M12 3l7 4v5c0 4.5-3 7.6-7 9-4-1.4-7-4.5-7-9V7zM9 12l2 2 4-4",
    profile: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5",
    summary: "M5 20v-8M10 20V5M15 20v-6M20 20V9M3 20h18",
    types: "M7 9h10a4 4 0 0 1 4 4v1.5a2.5 2.5 0 0 1-4.5 1.5L15 14H9l-1.5 2A2.5 2.5 0 0 1 3 14.5V13a4 4 0 0 1 4-4zM8 11v3M6.5 12.5h3M15.5 11.5h.01M17.5 13.5h.01",
    maps: "M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2zM9 4v14M15 6v14",
    medals: "M8 3l2.2 5.5M16 3l-2.2 5.5M12 21a6 6 0 1 0 0-12 6 6 0 0 0 0 12zM12 12.5l1 2 2.2.3-1.6 1.5.4 2.2-2-1-2 1 .4-2.2-1.6-1.5 2.2-.3z",
    weapons: "M2.5 9.5h15l2-2h2v4h-4.5l-1.5 1.5h-3l-2.5 4H6.5l1.5-4H4.5l-2-1.5zM10.5 13l.5 2",
    enemies: "M12 3a8 8 0 0 0-8 8c0 2.6 1.2 4.4 3 5.5V20h10v-3.5c1.8-1.1 3-2.9 3-5.5a8 8 0 0 0-8-8zM9 11.5h.01M15 11.5h.01M10 20v-2M14 20v-2",
    back: "M15 5l-7 7 7 7",
    trophy: "M8 4h8v5a4 4 0 0 1-8 0zM8 6H4.5v1.5A3 3 0 0 0 8 10.5M16 6h3.5v1.5A3 3 0 0 1 16 10.5M12 13v4M8.5 20h7M10 17h4",
    film: "M4 5h16v14H4zM4 9h16M4 15h16M8 5v4M8 15v4M16 5v4M16 15v4",
    arrow: "M5 12h14M13 6l6 6-6 6",
    calendar: "M4 6h16v14H4zM4 10h16M8 3v4M16 3v4",
    games: "M7 9h10a4 4 0 0 1 4 4v1.5a2.5 2.5 0 0 1-4.5 1.5L15 14H9l-1.5 2A2.5 2.5 0 0 1 3 14.5V13a4 4 0 0 1 4-4z",
    win: "M8 4h8v5a4 4 0 0 1-8 0zM12 13v4M8.5 20h7M10 17h4",
    kills: "M12 3v4M12 17v4M3 12h4M17 12h4M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z",
    deaths: "M12 3a8 8 0 0 0-8 8c0 2.6 1.2 4.4 3 5.5V20h10v-3.5c1.8-1.1 3-2.9 3-5.5a8 8 0 0 0-8-8zM9 11.5h.01M15 11.5h.01",
    assists: "M4 13l4 4 3-1.5 3 2.5 6-6M4 13l5-5 3 2 3-3 5 5",
    spree: "M13 3L5 13h6l-1 8 8-10h-6z",
    since: "M5 21V4M5 4h11l-2 4 2 4H5",
    scoreboard: "M4 5h16v14H4zM4 10h16M10 10v9",
  };
  // the owner's neon icons (art/icons, cut from his sheets) for the sections and panel headings that have one; the
  // drawn ones below otherwise
  const NEON = { overview: "home", placements: "rising", history: "clock", commendations: "star", heatmaps: "picture",
    profile: "helmet", summary: "bars", types: "s_controller", maps: "pin", medals: "s_perfection", weapons: "s_dmr",
    enemies: "skull", film: "film", achievements: "s_hex",
    // the Overview's stat list and the kills box (his second set); Assists keeps the drawn one
    calendar: "s_calendar", games: "s_controller", win: "s_star", kills: "s_crosshair", deaths: "s_skull",
    "stat-medals": "s_medal", spree: "s_layers", since: "s_clock" };
  function neon(name, size) {
    const src = NEON[name] && D.icons && D.icons[NEON[name] + ".png"];
    if (!src) return icon(name === "stat-medals" ? "medals" : name, size);
    return el("img", { class: "ic neon", src, alt: "", width: size || 22, height: size || 22 });
  }
  function icon(name, size) {
    return svg("svg", { class: "ic", viewBox: "0 0 24 24", width: size || 20, height: size || 20, "aria-hidden": "true" },
      svg("path", { d: ICONS[name] || ICONS.overview, fill: "none", stroke: "currentColor", "stroke-width": 1.7, "stroke-linecap": "round", "stroke-linejoin": "round" }));
  }
  // A game type family's badge: a shield outline with the mode's sign in it (our own drawing).
  const MODE_SIGNS = {
    slayer: "M24 15v5M24 30v5M15 25h5M28 25h5M24 29a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
    ctf: "M19 35V15M19 16h11l-2.5 4 2.5 4H19",
    koth: "M16 31h16M16 31l-1-11 5 4 4-7 4 7 5-4-1 11",
    territories: "M16 17h16v16H16zM24 17v16M16 25h16",
    oddball: "M24 33a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 24h.01M27 24h.01M22 29h4",
    infection: "M24 25a3 3 0 1 0 0-.01M24 22v-6M21.5 26.5l-5 3M26.5 26.5l5 3",
    assault: "M23 33a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM28 20l3-3M31 17l2 0",
    invasion: "M17 30l7-6 7 6M17 23l7-6 7 6",
    rest: "M24 15l2.5 6.5 7 .5-5.4 4.4 1.8 6.8L24 29.4l-5.9 3.8 1.8-6.8-5.4-4.4 7-.5z",
  };
  // a family's icon from the owner's Reach game-type sheet (modes.json), when this PC has it; null otherwise
  const modeIcon = (cat, size) => (D.mode_art && D.mode_art[cat]
    ? el("img", { class: "mode-ic", src: D.mode_art[cat], alt: "", width: size || 18, height: size || 18, loading: "lazy" }) : null);
  // the game type each recorded game type name falls in (its matches say)
  const typeCat = new Map(D.matches.map((m) => [m.type || "Unknown", m.cat]));
  function modeBadge(cat) {
    if (D.mode_art && D.mode_art[cat]) return el("img", { class: "badge", src: D.mode_art[cat], alt: "", width: 52, height: 52 });
    return svg("svg", { class: "badge", viewBox: "0 0 48 48", width: 48, height: 48, "aria-hidden": "true" },
      svg("path", { d: "M24 3 41 9.5v13C41 33 33.5 40.5 24 45 14.5 40.5 7 33 7 22.5v-13z", fill: "none", stroke: "currentColor", "stroke-width": 1.8, "stroke-linejoin": "round" }),
      svg("path", { d: MODE_SIGNS[cat] || MODE_SIGNS.rest, fill: "none", stroke: "currentColor", "stroke-width": 1.8, "stroke-linecap": "round", "stroke-linejoin": "round" }));
  }
  const BADGE_LABEL = { ctf: "CTF", koth: "KOTH", rest: "Other" };
  const FAMILY_LABEL = { ctf: "Capture the Flag", koth: "King of the Hill" };
  const result = (m, me) => (me.won ? "Won" : m.rows.every((r) => r.st === 0) ? "Tied" : "Lost");
  const pad2 = (n) => String(n).padStart(2, "0");
  const dotted = (t) => { const d = new Date(t * 1000); return pad2(d.getMonth() + 1) + "." + pad2(d.getDate()) + "." + d.getFullYear(); };

  // The record's card across the top of every one of its pages: the emblem, the name and clan tag, the rank and its
  // progress, and the three game type families it has played most.
  function recordCard(p) {
    const cur = D.ranks[p.rank], next = D.ranks[p.rank + 1];
    const g = side(p), cats = (g && g.cats) || {};
    const fams = RING.concat(["rest"]).filter((k) => cats[k] && cats[k].games).sort((a, b) => cats[b].games - cats[a].games);
    for (const k of ["slayer", "ctf", "koth"]) if (fams.length < 3 && !fams.includes(k)) fams.push(k);
    return [
      el("div", { class: "em" }, emblem(p)),
      el("div", { class: "id" },
        el("div", { class: "nm" }, insignia(p.rank, true), el("h1", null, p.name), cardBadges(p)),
        cardClan(p),
        editing() && !p.person ? botClanForm(p) : null,   // (a person's tag is their own, set in the game's settings)
        el("div", { class: "rk" }, el("span", null, cur[0]),
          el("span", { class: "nx" }, next ? "Next: " + next[0] + " (" + int(p.cr) + " / " + int(next[1]) + " cR)" : "Highest rank reached (" + int(p.cr) + " cR)")),
        next ? el("progress", { max: next[1] - cur[1], value: p.cr - cur[1], "aria-label": "Progress to " + next[0] })
          : el("progress", { max: 1, value: 1, "aria-label": "Highest rank reached" })),
      el("ul", { class: "modes", "aria-label": "Most played game types" }, fams.slice(0, 3).map((k) => {
        const n = (cats[k] || {}).games || 0;
        return el("li", { class: n ? null : "off", "data-tip": (catName.get(k) || FAMILY_LABEL[k] || title(k)) + ": " + int(n) + (n === 1 ? " game" : " games") },
          el("span", null, BADGE_LABEL[k] || title(k)), modeBadge(k));
      })),
    ];
  }
  // the bot's clan on its card: a quiet line of its own under the name (label, tag, the clan's full name), the clan's page
  function cardClan(p) {
    if (!p.clan || !String(p.clan).trim()) return null;
    const full = (D.clan_names && D.clan_names[clanKey(p.clan)]) || "";
    return el("a", { class: "card-clan", href: href(["clans", clanKey(p.clan)]), "aria-label": "Clan: " + (full ? full + " (" + p.clan + ")" : p.clan) },
      el("span", { class: "lbl" }, "Clan"), el("span", { class: "clan-abbr" }, p.clan), full ? el("span", { class: "full" }, full) : null);
  }
  // a page's own title, under the card (the card itself is drawn once by render)
  function banner() {
    const page = route.parts[2] || "overview";
    const found = PAGES.flatMap((x) => x[1]).find((x) => x[0] === page);
    return el("h1", { class: "page-title" }, found ? found[1] : page === "match" ? "Carnage Report" : "");
  }

  function table(caption, heads, rows, opts) {
    const o = opts || {};
    return el("div", { class: o.fit ? "fit" : "scroll" }, el("table", null, caption && el("caption", null, caption),
      el("thead", null, el("tr", null, heads.map((x) => el("th", { scope: "col", class: x[1] || null }, x[0])))),
      el("tbody", null, rows.length ? rows : el("tr", null, el("td", { class: "l", colspan: heads.length }, o.none || "Nothing recorded yet.")))));
  }
  const td = (v, cls) => el("td", { class: cls || null }, v);

  // the Games Played ring: one segment per game type family, 2px apart; the legend carries every value
  function ring(cats) {
    const order = RING.filter((k) => cats[k] && cats[k].games);
    const parts = order.map((k) => ({ label: catName.get(k) || k, value: cats[k].games, color: "var(--c-" + k + ")" }));
    const rest = Object.keys(cats).filter((k) => k !== "all" && !RING.includes(k) && cats[k].games);
    if (rest.length) {
      parts.push({ label: rest.length === 1 ? (catName.get(rest[0]) || rest[0]) : "Other modes",
        value: rest.reduce((n, k) => n + cats[k].games, 0), color: "var(--c-rest)" });
    }
    const total = parts.reduce((n, x) => n + x.value, 0);
    const R = 62, C = 2 * Math.PI * R, gap = parts.length > 1 ? 2 : 0;
    const marks = [];
    let at = 0;
    for (const x of parts) {
      const len = (x.value / total) * C;
      marks.push(svg("circle", { cx: 84, cy: 84, r: R, fill: "none", stroke: x.color, "stroke-width": 22,
        "stroke-dasharray": Math.max(len - gap, 1) + " " + C, "stroke-dashoffset": -at, transform: "rotate(-90 84 84)",
        "data-tip": x.label + ": " + int(x.value) + (x.value === 1 ? " game" : " games") }));
      at += len;
    }
    const picture = svg("svg", { viewBox: "0 0 168 168", role: "img", "aria-label": "Games played by game type: " + int(total) + " in all" },
      total ? marks : svg("circle", { cx: 84, cy: 84, r: R, fill: "none", stroke: "var(--track)", "stroke-width": 22 }),
      svg("text", { class: "total", x: 84, y: 88, "text-anchor": "middle" }, int(total)),
      svg("text", { class: "unit", x: 84, y: 106, "text-anchor": "middle" }, total === 1 ? "game" : "games"));
    const legend = el("ul", { class: "legend" }, parts.map((x) => el("li", null,
      el("span", { class: "sw", style: "background:" + x.color }), el("span", null, x.label),
      el("span", { class: "v" }, int(x.value)), el("span", { class: "pc" }, Math.round((100 * x.value) / total) + "%"))));
    return el("div", { class: "ring" }, picture, total ? legend : el("p", { class: "note" }, "No games to split yet."));
  }
  function hbars(rows) {
    const max = Math.max(1, ...rows.map((r) => r[1]));
    return el("div", { class: "hbars" }, rows.map(([label, value]) => [
      el("span", { class: "lab" }, label),
      el("span", { class: "trk", "data-tip": label + ": " + int(value) }, el("span", { class: "fill", style: "width:" + (100 * value) / max + "%" })),
      el("span", { class: "val" }, int(value))]));
  }
  function medalTile(id, n) {
    const m = D.medals[id] || { name: "Medal " + id, icon: null };
    const art = m.icon
      ? el("img", { src: m.icon, alt: "", width: 56, height: 56, loading: "lazy" })
      : svg("svg", { viewBox: "0 0 48 48", "aria-hidden": "true" },
        svg("circle", { cx: 24, cy: 24, r: 19, fill: "none", stroke: "currentColor", "stroke-width": 2.5 }),
        svg("path", { d: "M24 13l3.2 6.6 7.3 1-5.3 5.1 1.3 7.2L24 29.5l-6.5 3.4 1.3-7.2-5.3-5.1 7.3-1z", fill: "none", stroke: "currentColor", "stroke-width": 2, "stroke-linejoin": "round" }));
    return el("li", null, art, el("span", { class: "n" }, int(n)), el("span", { class: "t" }, m.name));
  }
  const medalList = (g) => Object.entries((g && g.medals) || {}).sort((a, b) => b[1] - a[1] || a[0] - b[0]);
  function reportNote(s) {
    return s.games && s.detailed < s.games
      ? el("p", { class: "note" }, "Medals, betrayals and kill types come from " + int(s.detailed) + " of " + int(s.games) +
        " games: the others were recorded without MCC's full report.")
      : null;
  }
  const killTypes = (s) => [["Weapon", s.kw], ["Grenade", s.kg], ["Melee", s.km], ["Other", s.ko]];

  // The kill record (tools/kill_record.py): who the game credits with each death, with what, where both stood. Only
  // matches recorded with it count here; a bot with none says "not recorded yet", never a zero.
  const recorded = (g) => !!(g && g.kill_games);
  const weaponName = (key) => (D.weapons && D.weapons[key]) || ["Damage type " + key.split(":").pop(), true];
  const weaponList = (g) => Object.entries((g && g.weapons) || {})
    .sort((a, b) => b[1][0] - a[1][0] || b[1][1] - a[1][1] || weaponName(a[0])[0].localeCompare(weaponName(b[0])[0]));
  // A weapon's picture: MCC's own drawing of it, read from this PC's MCC by tools/service_record_art.py and copied
  // in by the build (weapons/<name>.png); our own plain mark where there is none.
  function weaponPicture(key) {
    const src = D.weapon_art && D.weapon_art[key];
    if (src) return el("img", { src, alt: "", loading: "lazy" });
    return svg("svg", { viewBox: "0 0 96 48", "aria-hidden": "true" },
      svg("circle", { cx: 48, cy: 24, r: 15, fill: "none", stroke: "currentColor", "stroke-width": 2 }),
      svg("path", { d: "M48 3v12M48 33v12M21 24h12M63 24h12", stroke: "currentColor", "stroke-width": 2, "stroke-linecap": "round" }));
  }
  // Weapons as cards, as the old stats pages showed them: the picture, the name, "Kills: N | Deaths: N", and under
  // them this weapon's share of every recorded kill and death (`all` is the bot's whole list, `shown` the cards).
  function weaponCards(shown, all, cls) {
    const kills = all.reduce((n, w) => n + w[1][0], 0), deaths = all.reduce((n, w) => n + w[1][1], 0);
    const pc = (n, of) => (of ? Math.round((100 * n) / of) + "%" : "-");
    return el("ul", { class: "weapons" + (cls ? " " + cls : "") }, shown.map(([key, n]) => {
      const [name, sure] = weaponName(key);
      const shares = pc(n[0], kills) + " of kills, " + pc(n[1], deaths) + " of deaths";
      const used = !!(n[0] || n[1]);
      return el("li", { class: used ? null : "unused" },
        el("div", { class: "pic" }, weaponPicture(key)),
        el("div", { class: "nm" }, name, !sure && used && el("span", { class: "mark", title: "Named from the game's list of damage types; not yet matched to a kill seen live" }, " *")),
        el("div", { class: "kd" }, "Kills: ", el("b", null, int(n[0])), el("span", { class: "sep", "aria-hidden": "true" }, "|"), "Deaths: ", el("b", null, int(n[1]))),
        el("div", { class: "share", "data-tip": name + ": " + shares }, el("span", { style: "width:" + (kills ? (100 * n[0]) / kills : 0) + "%" })),
        el("div", { class: "pc" }, shares));
    }));
  }
  // Every weapon and vehicle of the game shown (D.arsenal, weapons.json), used or not (the owner, Nov 17: "even if the
  // player has no kills with it"), with the bot's kills and deaths, 0 where none; any other way it killed or died (a
  // fall, the Guardians...) with the weapons. Most kills first, then most deaths, then by name.
  const inShownGame = (k) => game() === "all" || k.startsWith(game() + ":");
  function arsenalLists(g) {
    const own = (g && g.weapons) || {};
    const A = D.arsenal || { weapons: [], vehicles: [] };
    const wk = new Set(A.weapons.filter(inShownGame)), vk = new Set(A.vehicles.filter(inShownGame));
    for (const k of Object.keys(own)) (VEHICLES.has(k) ? vk : wk).add(k);
    const order = (keys) => [...keys].map((k) => [k, own[k] || [0, 0]])
      .sort((a, b) => b[1][0] - a[1][0] || b[1][1] - a[1][1] || weaponName(a[0])[0].localeCompare(weaponName(b[0])[0]));
    return [order(wk), order(vk)];
  }
  function killNote(g, s) {
    if (g.kill_games >= s.games) {
      return "From the mod's record of every kill in " + (s.games === 1 ? "the 1 counted match." : "all " + int(s.games) + " counted matches.");
    }
    return "From the mod's record of every kill, kept for " + int(g.kill_games) + " of " + int(s.games) +
      " counted matches: the others were played before it was written.";
  }
  const NO_KILLS = "The mod writes a record of every kill (who the game credits, with what, where) for Reach matches " +
    "recorded from 15 November 2026 on. None of the counted matches here has one yet: it fills in after the next recorded match.";

  // ---------------------------------------------------------------- the leaderboard (the player picker)
  const SORTS = { name: (p) => p.name.toLowerCase(), rank: (p) => p.cr, games: (p) => bucket(p).games,
    wins: (p) => bucket(p).wins, kills: (p) => bucket(p).kills, deaths: (p) => bucket(p).deaths,
    assists: (p) => bucket(p).assists, kd: (p) => bucket(p).r.kd };
  let find = "";
  function leaderboard() {
    const key = SORTS[route.q.sort] ? route.q.sort : "kd";
    const dir = route.q.dir === "asc" || (route.q.dir !== "desc" && key === "name") ? 1 : -1;
    const body = el("tbody");
    const count = el("span", { class: "note", "aria-live": "polite" });
    function draw() {
      const want = find.trim().toLowerCase();
      const rows = D.players.filter((p) => !want || p.name.toLowerCase().includes(want) || (p.clan || "").toLowerCase().includes(want));
      rows.sort((a, b) => {
        const x = SORTS[key](a), y = SORTS[key](b);
        return (x < y ? -1 : x > y ? 1 : 0) * dir || bucket(b).kills - bucket(a).kills || a.name.localeCompare(b.name);
      });
      body.replaceChildren(...(rows.length ? rows.map((p, i) => {
        const s = bucket(p);
        return el("tr", null, td(i + 1, i < 3 && s.games && !want ? "pos lead" : "pos"),
          td(el("span", { class: "cell" }, emblem(p, true), el("a", { href: href(["p", p.name, "overview"]) }, p.name),
            p.clan && el("a", { class: "tag hide-s", href: href(["clans", clanKey(p.clan)]) }, p.clan)), "l"),
          td(el("span", { class: "cell" }, insignia(p.rank, true), D.ranks[p.rank][0]), "l hide-s"),
          td(int(s.games)), td(int(s.wins), "hide-s"), td(int(s.kills)), td(int(s.deaths)), td(int(s.assists), "hide-s"), td(dec(s.r.kd)));
      }) : [el("tr", null, el("td", { class: "l", colspan: 9 }, "Nothing matches “" + find + "”."))]));
      count.textContent = rows.length + " of " + D.players.length + " shown";
    }
    const head = (k, label, cls) => {
      const on = k === key;
      const next = on ? (dir === 1 ? "desc" : "asc") : (k === "name" ? "asc" : "desc");
      return el("th", { scope: "col", class: cls || null, "aria-sort": on ? (dir === 1 ? "ascending" : "descending") : null },
        el("button", { type: "button", onclick: () => { location.hash = href([], { sort: k, dir: next }); } }, label));
    };
    draw();
    const played = D.players.filter((p) => bucket(p).games).length;
    return [
      el("h1", null, "Bot Tracker"), boardTabs(""), editing() ? resetAllForm() : null, podium(),
      el("p", { class: "note" }, played
        ? int(played) + " of " + int(D.players.length) + " have a counted match in " + gameName.get(game()) + ". Choose a name to open its Service Record."
        : "Nobody has a counted match in " + gameName.get(game()) + " yet. Everyone starts at 0; the numbers fill in after the next match."),
      panel("Standings", el("div", { class: "scroll" }, el("table", null,
        el("thead", null, el("tr", null, el("th", { scope: "col" }, "#"), head("name", "Name", "l"), head("rank", "Rank", "l hide-s"),
          head("games", "Games"), head("wins", "Wins", "hide-s"), head("kills", "Kills"), head("deaths", "Deaths"),
          head("assists", "Assists", "hide-s"), head("kd", "K/D"))), body)),
        el("div", { class: "toolbar" }, count,
          el("label", null, "Find a name", el("input", { type: "search", value: find, autocomplete: "off",
            oninput: (e) => { find = e.target.value; draw(); } })))),
    ];
  }

  // ---------------------------------------------------------------- the front page's podium and the Ranks page
  // a bot's figure standing still (the first angle of its turntable, native/figure_snap.exe), else its emblem
  function figureStill(p) {
    const f = p.figure;
    return f ? el("span", { class: "still", role: "img", "aria-label": p.name + " in its armor",
      style: `background-image:url("${f.src}");background-size:${f.n * 100}% 100%;aspect-ratio:${f.w} / ${f.h}` })
      : el("span", { class: "still none" }, emblem(p));
  }
  // the top three by credits (cR, the rank's own formula) in the game shown: second, first, third, on lit rings
  function podium() {
    const top = D.players.filter((p) => bucket(p).games).map((p) => ({ p, v: crOf(bucket(p)) + commCr(p) }))
      .sort((x, y) => y.v - x.v || x.p.name.localeCompare(y.p.name)).slice(0, 3);
    if (!top.length) return null;
    return el("section", { class: "podium", "aria-label": "The top three by credits in " + gameName.get(game()) },
      el("ol", null, [1, 0, 2].filter((i) => top[i]).map((i) => {
        const { p, v } = top[i];
        const link = href(["p", p.name, "overview"]);
        return el("li", { class: "place p" + (i + 1) },
          el("a", { class: "figure-link ringed", href: link, "aria-label": p.name + ", " + ordinal(i + 1) }, figureStill(p)),
          el("span", { class: "plinth" }, el("span", { class: "num" }, ordinal(i + 1))),
          el("a", { class: "nm", href: link }, p.name),
          el("span", { class: "rk" }, insignia(p.rank, true), D.ranks[p.rank][0]),
          el("span", { class: "cr" }, int(v) + " cR"));
      })));
  }
  // every rank of Reach in order, its Grades with their credits, and which bots hold it now (credits come from counted
  // Reach matches only: ranks.json)
  // ---------------------------------------------------------------- clans
  // A clan is its tag (the bots' clan tags: the roster's, else the newest report's), letters alike whatever their case.
  // Its credits are all its members' (each member's own cR, the rank's formula), its rank the players' ladder with
  // every step x10 (D.ranks: the one table, ranks.json).
  const CLAN_SCALE = 10;
  const clanKey = (tag) => String(tag).trim().toLowerCase();
  let clanCache = null;
  function clanList() {
    if (clanCache) return clanCache;
    const by = new Map();
    for (const p of D.players) {
      if (!p.clan || !String(p.clan).trim()) continue;
      const k = clanKey(p.clan);
      if (!by.has(k)) by.set(k, { key: k, tags: new Map(), members: [] });
      const c = by.get(k);
      c.members.push(p);
      c.tags.set(p.clan, (c.tags.get(p.clan) || 0) + 1);
    }
    clanCache = [...by.values()].map((c) => {
      const cr = c.members.reduce((n, p) => n + (p.cr || 0), 0);
      const tag = [...c.tags].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0][0];   // (its most worn spelling)
      c.members.sort((a, b) => (b.cr || 0) - (a.cr || 0) || a.name.localeCompare(b.name));
      const games = c.members.reduce((n, p) => n + ((p.g[D.default_game] && p.g[D.default_game].cats.all) || ZERO).games, 0);
      const name = (D.clan_names && D.clan_names[c.key]) || "";
      const about = (D.clan_about && D.clan_about[c.key]) || "";
      return { key: c.key, tag, name, about, title: name || tag, members: c.members, cr, games, rank: clanRank(cr) };
    }).sort((a, b) => b.cr - a.cr || b.members.length - a.members.length || a.tag.localeCompare(b.tag));
    clanCache.forEach((c, i) => { c.place = i && c.cr === clanCache[i - 1].cr ? clanCache[i - 1].place : i + 1; });
    return clanCache;
  }
  function clanRank(cr) {
    let i = 0;
    while (i + 1 < D.ranks.length && cr >= D.ranks[i + 1][1] * CLAN_SCALE) i++;
    return i;
  }
  function clanRankBlock(c) {
    const cur = D.ranks[c.rank], next = D.ranks[c.rank + 1];
    return el("div", { class: "clan-rank" }, insignia(c.rank),
      el("div", null, el("div", { class: "rk-name" }, cur[0]),
        next ? el("progress", { max: (next[1] - cur[1]) * CLAN_SCALE, value: c.cr - cur[1] * CLAN_SCALE, "aria-label": "Clan progress to " + next[0] })
          : el("progress", { max: 1, value: 1, "aria-label": "Highest clan rank reached" }),
        el("div", { class: "rk-next" }, next ? "Next: " + next[0] + " (" + int(c.cr) + " / " + int(next[1] * CLAN_SCALE) + " cR)" : "Highest rank reached (" + int(c.cr) + " cR)")));
  }
  // ---------------------------------------------------------------- the owner's edit mode
  // Only when the site is served by the owner's editor on this PC (tools/service_record_edit.py answers /api/editor);
  // switched on from the footer, remembered in this browser until switched off (Nov 17, the owner: "a permanent edit
  // button"). Saves go to the editor, which rebuilds the site.
  let editorHere = false;
  const editing = () => { try { return editorHere && localStorage.getItem("sr-edit") === "1"; } catch (e) { return false; } };
  function clanNameForm(c) {
    const input = el("input", { type: "text", value: c.name, maxlength: 40, placeholder: "Full clan name", "aria-label": "Clan name for " + c.tag });
    const about = el("textarea", { maxlength: 280, rows: 3, placeholder: "A short description of the clan", "aria-label": "Description of " + c.tag });
    about.value = c.about;
    const left = el("small", { class: "left" });
    const count = () => { left.textContent = (280 - about.value.length) + " left"; };
    about.addEventListener("input", count);
    count();
    const msg = el("span", { class: "note", "aria-live": "polite" });
    const post = (path, field, value) => fetch(path, { method: "POST", headers: { "Content-Type": "application/json", "X-Service-Record-Edit": "1" },
      body: JSON.stringify({ key: c.key, [field]: value }) }).then((r) => r.json().then((d) => { if (!r.ok) throw new Error(d.error || "error"); return d[field]; }));
    const save = async (name, text) => {
      msg.textContent = "Saving\u2026";
      try {
        D.clan_names = D.clan_names || {};
        D.clan_about = D.clan_about || {};
        if (name !== c.name) { const v = await post("/api/clan-name", "name", name); if (v) D.clan_names[c.key] = v; else delete D.clan_names[c.key]; }
        if (text !== c.about) { const v = await post("/api/clan-about", "about", text); if (v) D.clan_about[c.key] = v; else delete D.clan_about[c.key]; }
        clanCache = null;
        render();
      } catch (e) {
        msg.textContent = e instanceof TypeError ? "Not saved: the editor is not running." : "Not saved: " + e.message;
      }
    };
    return el("form", { class: "edit-form", onsubmit: (e) => { e.preventDefault(); save(input.value, about.value); } },
      el("label", null, "Clan name", input),
      el("label", { class: "wide" }, "Description", about, left),
      el("div", { class: "edit-actions" }, el("button", { type: "submit" }, "Save"),
        c.name || c.about ? el("button", { type: "button", onclick: () => save("", "") }, "Clear both") : null, msg));
  }
  // a bot's clan tag, saved where the game reads it (bot_profiles.ini, by the editor; only while MCC is closed, and worn
  // from MCC's next start): the clans already on the site to pick from, or a new tag
  const CLAN_TAG = /^[^\s,;=\[\]|]{1,4}$/;
  function botClanForm(p) {
    const list = el("datalist", { id: "clan-tags" }, clanList().map((c) => el("option", { value: c.tag }, c.title)));
    const input = el("input", { type: "text", value: p.clan || "", maxlength: 4, list: "clan-tags", class: "tag", placeholder: "None",
      spellcheck: "false", autocomplete: "off", "aria-label": "Clan tag for " + p.name });
    const msg = el("span", { class: "note", "aria-live": "polite" }, "Saved to the game: close MCC first; worn from its next start.");
    const save = async (tag) => {
      tag = tag.trim();
      if (tag && !CLAN_TAG.test(tag)) { msg.textContent = "Up to 4 letters or numbers, no spaces or , ; = [ ] |"; input.focus(); return; }
      if (tag === (p.clan || "")) { msg.textContent = "No change."; return; }
      msg.textContent = "Saving\u2026";
      try {
        const r = await fetch("/api/bot-clan", { method: "POST", headers: { "Content-Type": "application/json", "X-Service-Record-Edit": "1" },
          body: JSON.stringify({ name: p.name, clan: tag }) });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || "error");
        p.clan = d.clan;
        clanCache = null;
        render();
      } catch (e) {
        msg.textContent = e instanceof TypeError ? "Not saved: the editor is not running." : "Not saved: " + e.message;
      }
    };
    return el("form", { class: "edit-form bot-clan", onsubmit: (e) => { e.preventDefault(); save(input.value); } },
      el("label", null, "Clan tag", input), list,
      el("div", { class: "edit-actions" }, el("button", { type: "submit" }, "Save"),
        p.clan ? el("button", { type: "button", onclick: () => save("") }, "Leave clan") : null), msg);
  }
  // Reset all (Nov 17, the owner: "a reset all button so I don't ask you everytime"): everyone's stats from 0, the
  // owner's too, after a second, explicit yes. The editor keeps a copy of the ledger first and refuses while MCC runs.
  function resetAllForm() {
    const msg = el("span", { class: "note", "aria-live": "polite" }, "Every bot and listed player back to 0. Close MCC first.");
    const box = el("div", { class: "edit-actions" });
    const ask = () => {
      msg.textContent = "Start everyone, you included, at 0? Old matches stop counting and leave the site; a copy of the stats is kept on this PC.";
      box.replaceChildren(
        el("button", { type: "button", class: "danger", onclick: go }, "Yes, reset everyone"),
        el("button", { type: "button", onclick: () => render() }, "Cancel"));
      box.firstChild.focus();
    };
    async function go() {
      box.replaceChildren();
      msg.textContent = "Resetting…";
      try {
        const r = await fetch("/api/reset-all", { method: "POST", headers: { "Content-Type": "application/json", "X-Service-Record-Edit": "1" },
          body: JSON.stringify({ confirm: "reset all" }) });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || "error");
        msg.textContent = "Done: everyone starts at 0. The page reloads with the new build.";
      } catch (e) {
        msg.textContent = e instanceof TypeError ? "Not reset: the editor is not running." : "Not reset: " + e.message;
        box.replaceChildren(el("button", { type: "button", class: "danger", onclick: ask }, "Reset all stats"));
      }
    }
    box.append(el("button", { type: "button", class: "danger", onclick: ask }, "Reset all stats"));
    return el("div", { class: "edit-form reset-all" }, el("strong", null, "Reset all stats"), box, msg);
  }
  function editToggle() {
    const foot = document.querySelector(".foot");
    if (!foot || !editorHere || foot.querySelector(".edit-toggle")) return;
    const b = el("button", { type: "button", class: "edit-toggle" });
    const show = () => { b.textContent = editing() ? "Edit mode: on" : "Edit mode"; b.setAttribute("aria-pressed", String(editing())); };
    b.addEventListener("click", () => {
      try { localStorage.setItem("sr-edit", editing() ? "0" : "1"); } catch (e) { /* (not kept) */ }
      document.body.classList.toggle("editing", editing());
      show();
      render();
    });
    show();
    foot.prepend(b);
    document.body.classList.toggle("editing", editing());
  }
  if (location.protocol.startsWith("http")) {
    fetch("/api/editor", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d && d.edit) { editorHere = true; editToggle(); if (editing()) render(); } }).catch(() => {});
  }

  let clanFind = "";
  function clansPage() {
    const list = clanList();
    const body = el("ol", { class: "clans" });
    const count = el("span", { class: "note", "aria-live": "polite" });
    const draw = () => {
      const want = clanFind.trim().toLowerCase();
      const shown = list.filter((c) => !want || c.tag.toLowerCase().includes(want) || c.name.toLowerCase().includes(want) || c.about.toLowerCase().includes(want) ||
        c.members.some((p) => p.name.toLowerCase().includes(want)));
      body.replaceChildren(...(shown.length ? shown.map((c) => el("li", null, el("a", { class: "clan-card", href: href(["clans", c.key]) },
        el("span", { class: "place" + (c.cr && c.place <= 3 ? " lead" : "") }, c.cr ? c.place : "-"),
        el("span", { class: "ins" }, insignia(c.rank)),
        el("span", { class: "who" }, el("b", null, c.title), el("small", null, c.name ? el("span", { class: "clan-abbr" }, c.tag) : null, D.ranks[c.rank][0]),
          c.about ? el("span", { class: "clan-blurb" }, c.about.replace(/\s+/g, " ")) : null),
        el("span", { class: "crew" }, c.members.slice(0, 6).map((p) => emblem(p, true)), c.members.length > 6 ? el("small", null, "+" + (c.members.length - 6)) : null),
        el("span", { class: "nums" }, el("b", null, int(c.cr) + " cR"), el("small", null, c.members.length + (c.members.length === 1 ? " member" : " members")))))) :
        [el("li", { class: "none" }, "No clan or member matches \u201C" + clanFind + "\u201D.")]));
      count.textContent = shown.length + " of " + list.length + " clans";
    };
    draw();
    return [el("h1", null, "Bot Tracker"), boardTabs("clans"),
      el("p", { class: "note" }, "Every clan the bots wear a tag of. A clan's credits are all its members' cR added up, and its rank is the same ladder as a player's with every step \u00D7" + CLAN_SCALE + "."),
      panel("Clans", el("div", { class: "body" },
        el("div", { class: "toolbar" }, count, el("label", null, "Find a clan or member", el("input", { type: "search", value: clanFind, autocomplete: "off",
          oninput: (e) => { clanFind = e.target.value; draw(); } }))),
        list.length ? body : empty("No clans yet", "A clan shows here once a bot wears its tag.")))];
  }
  function clanPage(key) {
    const c = clanList().find((x) => x.key === key);
    const total = c.cr || 1;
    const rows = c.members.map((p, i) => {
      const s = (p.g[D.default_game] && p.g[D.default_game].cats.all) || ZERO;
      return el("tr", null, td(i + 1, i < 3 && p.cr ? "pos lead" : "pos"),
        td(el("span", { class: "cell" }, emblem(p, true), el("a", { href: href(["p", p.name, "overview"]) }, p.name)), "l"),
        td(el("span", { class: "cell" }, insignia(p.rank, true), D.ranks[p.rank][0]), "l hide-s"),
        td(int(p.cr)), td(Math.round((100 * (p.cr || 0)) / total) + "%", "hide-s"), td(int(s.games)), td(dec(s.r.kd), "hide-s"));
    });
    return [el("h1", null, "Bot Tracker"), boardTabs("clans"),
      el("p", null, el("a", { class: "more back-link", href: href(["clans"]) }, "All clans")),
      el("section", { class: "panel clan-head" }, el("div", { class: "body" },
        el("div", { class: "clan-title" }, c.cr ? el("span", { class: "place-big" }, "#" + c.place) : null,
          el("div", null, el("h2", null, c.title), c.name ? el("span", { class: "clan-abbr big" }, c.tag) : null, editing() ? clanNameForm(c) : null)),
        clanRankBlock(c),
        el("ul", { class: "clan-facts" },
          el("li", null, el("b", null, int(c.cr)), el("span", null, "Clan cR")),
          el("li", null, el("b", null, int(c.members.length)), el("span", null, c.members.length === 1 ? "Member" : "Members")),
          el("li", null, el("b", null, int(c.games)), el("span", null, "Games (members' Reach)"))),
        c.about ? el("p", { class: "clan-about" }, c.about) : null,
        // (a placeholder: applying to a clan is not decided yet, the owner, Nov 16)
        el("button", { type: "button", class: "apply-btn", disabled: true, title: "Clan applications are coming soon" }, "Apply", el("small", null, "Coming soon")))),
      panel("Members", table(null, [["#"], ["Member", "l"], ["Rank", "l hide-s"], ["cR"], ["Share", "hide-s"], ["Games"], ["K/D", "hide-s"]], rows))];
  }

  function ranksPage() {
    const groups = [];
    D.ranks.forEach((s, i) => { if (s[3] === 0 || !groups.length) groups.push({ name: s[0], steps: [] }); groups[groups.length - 1].steps.push(i); });
    const at = new Map();
    for (const p of D.players) { if (!at.has(p.rank)) at.set(p.rank, []); at.get(p.rank).push(p); }
    const ranked = D.players.filter((p) => p.cr > 0);
    const best = ranked.slice().sort((x, y) => y.cr - x.cr || x.name.localeCompare(y.name))[0];
    const held = groups.filter((gr) => gr.steps.some((i) => at.has(i))).length;
    const w = D.credits;
    const cards = el("ol", { class: "ranks" }, groups.map((gr) => {
      const first = gr.steps[0], last = gr.steps[gr.steps.length - 1], next = D.ranks[last + 1];
      const here = gr.steps.flatMap((i) => at.get(i) || []).sort((x, y) => y.cr - x.cr || x.name.localeCompare(y.name));
      return el("li", { class: "rank-card" + (here.length ? " held" : "") + (here.length > 9 ? " many" : "") },
        el("div", { class: "ins" }, insignia(first)),
        el("div", { class: "rn" }, el("h3", null, gr.name),
          el("span", { class: "crs" }, int(D.ranks[first][1]) + (next ? " to " + int(next[1] - 1) : " and up") + " cR")),
        gr.steps.length > 1 ? el("ol", { class: "grades", "aria-label": gr.name + "'s grades" }, gr.steps.map((i) =>
          el("li", { "data-tip": D.ranks[i][0] + ": " + int(D.ranks[i][1]) + " cR" }, insignia(i, true),
            el("span", null, D.ranks[i][3] ? "Grade " + D.ranks[i][3] : "Base"), el("small", null, int(D.ranks[i][1]))))) : null,
        here.length ? el("ul", { class: "holders" }, here.map((p) => el("li", null,
          el("a", { href: href(["p", p.name, "profile"]), "data-tip": D.ranks[p.rank][0] + ", " + int(p.cr) + " cR" }, emblem(p, true), p.name))))
          : el("p", { class: "none" }, "No bot here yet"));
    }));
    return [el("h1", null, "Bot Tracker"), boardTabs("ranks"),
      el("p", { class: "note" }, "Reach's ranks, lowest first. A bot's credits (cR) come from its counted Reach matches: " + int(w.game) + " a game, " +
        int(w.win) + " a win, " + int(w.kill) + " a kill, " + int(w.assist) + " an assist and " + int(w.medal) + " a medal, so its rank can always be rebuilt from the record."),
      el("ul", { class: "hero" }, [["Highest rank", best ? D.ranks[best.rank][0] : "-", best ? best.name : ""], ["Bots with credits", int(ranked.length), "of " + int(D.players.length)],
        ["Ranks held", int(held), "of " + int(groups.length)], ["Credits earned", int(D.players.reduce((n, p) => n + p.cr, 0)), "cR in all"]]
        .map(([k, v, sub]) => el("li", null, el("span", { class: "v" }, v), el("span", { class: "k" }, k), sub ? el("span", { class: "sub" }, sub) : null))),
      panel("Ranks", el("div", { class: "body" }, cards))];
  }

  // ---------------------------------------------------------------- state leaderboards
  // Every bot has a home state, picked by the build from its name alone (states.json), so it never moves. A board
  // ranks the bots of one area (nationwide, a census region or a state) by one number; a bot with none of that number
  // is left off the board, never shown at 0. Equal numbers share a place.
  const REGIONS = new Map(D.regions || []);
  const STATES = D.states || {};
  const VEHICLES = new Set(D.vehicles || []);
  const BOARDS = [["overall", "Overall"], ["mode", "Mode"], ["weapon", "Weapon"], ["vehicle", "Vehicle"]];
  const crOf = (s) => { const w = D.credits; return s.games * w.game + s.wins * w.win + s.kills * w.kill + s.assists * w.assist + s.medals * w.medal; };
  // the credits its commendations' tiers add (Reach's, so in Reach and in all games; none by mode)
  const commCr = (p) => ((game() === D.default_game || game() === "all") && D.commendations && D.commendations.credits ? p.comm_cr || 0 : 0);
  const stateName = (code) => (STATES[code] || [code || "Unknown"])[0];
  const regionOf = (p) => (STATES[p.state] || [])[1];
  const areaName = (a) => (!a ? "Nationwide" : REGIONS.has(a) ? REGIONS.get(a) : stateName(a));
  const inArea = (p, a) => !a || p.state === a || regionOf(p) === a;
  const validArea = (a) => (a && (REGIONS.has(a) || STATES[a]) ? a : "");
  function killsWith(p, key) {   // [kills, deaths] with one damage type, or with every vehicle ("all"); null: no kill rows
    const g = side(p);
    if (!recorded(g)) return null;
    if (key !== "all") return g.weapons[key] || [0, 0];
    return Object.entries(g.weapons).filter(([k]) => VEHICLES.has(k)).reduce((n, [, v]) => [n[0] + v[0], n[1] + v[1]], [0, 0]);
  }
  // a board's choices in the game shown: the modes some bot played, the weapons and vehicles some bot has a kill with
  function boardKeys(kind) {
    if (kind === "overall") return [];
    if (kind === "mode") return D.cats.filter(([k]) => D.players.some((p) => bucket(p, k).games));
    const mine = (k) => (game() === "all" || k.startsWith(game() + ":")) && VEHICLES.has(k) === (kind === "vehicle");
    const A = D.arsenal || { weapons: [], vehicles: [] };
    const used = (k) => D.players.some((p) => { const n = killsWith(p, k); return n && n[0]; });
    const keys = [...new Set(A.weapons.concat(A.vehicles).filter(mine).concat(Object.keys(D.weapons || {}).filter((k) => mine(k) && used(k))))]
      .map((k) => [k, weaponName(k)[0]]).sort((a, b) => a[1].localeCompare(b[1]));
    return kind === "vehicle" && keys.length ? [["all", "All vehicles"]].concat(keys) : keys;
  }
  function board(kind, key) {
    if (kind === "overall" || kind === "mode") {
      const cat = kind === "mode" ? key : "all";
      return { kind, key, label: kind === "mode" ? catName.get(key) || key : "Overall", unit: "cR",
        value: (p) => { const s = bucket(p, cat); return s.games ? crOf(s) + (kind === "overall" ? commCr(p) : 0) : null; },
        cols: [["Games"], ["Wins", "hide-s"], ["K/D", "hide-s"]],
        cells: (p) => { const s = bucket(p, cat); return [td(int(s.games)), td(int(s.wins), "hide-s"), td(dec(s.r.kd), "hide-s")]; } };
    }
    return { kind, key, label: key === "all" ? "All vehicles" : weaponName(key)[0], unit: "Kills",
      value: (p) => { const n = killsWith(p, key); return n && n[0] ? n[0] : null; },
      cols: [["Deaths to it", "hide-s"]], cells: (p) => [td(int(killsWith(p, key)[1]), "hide-s")] };
  }
  function standings(b, area) {
    const rows = D.players.filter((p) => inArea(p, area)).map((p) => ({ p, v: b.value(p) })).filter((r) => r.v != null);
    rows.sort((x, y) => y.v - x.v || x.p.name.localeCompare(y.p.name));
    rows.forEach((r, i) => { r.place = i && r.v === rows[i - 1].v ? rows[i - 1].place : i + 1; });
    return rows;
  }
  const boardHref = (b, area) => href(["states"], { board: b.kind === "overall" ? null : b.kind,
    key: b.kind === "overall" ? null : b.key, area: area || null });
  function boardTabs(on) {
    return el("ul", { class: "tabs" }, [["", "Leaderboard", []], ["states", "By state", ["states"]], ["ranks", "Ranks", ["ranks"]], ["clans", "Clans", ["clans"]]].map(([k, label, parts]) =>
      el("li", null, el("a", { href: href(parts), "aria-current": k === on ? "true" : null }, label))));
  }
  function statesPage() {
    const kind = BOARDS.some(([k]) => k === route.q.board) ? route.q.board : "overall";
    const keys = boardKeys(kind);
    const firstUsed = keys.find(([k]) => k === "all" || D.players.some((p) => { const n = killsWith(p, k); return n && n[0]; }));
    const key = kind === "overall" ? "all" : keys.some(([k]) => k === route.q.key) ? route.q.key : (firstUsed || keys[0] || [null])[0];
    const area = validArea(route.q.area);
    const b = key ? board(kind, key) : null;
    const go = (q) => { location.hash = href(["states"], Object.assign({ board: kind === "overall" ? null : kind, key: kind === "overall" ? null : key, area: area || null }, q)); };
    const counted = (a) => D.players.filter((p) => inArea(p, a)).length;
    const homes = [...new Set(D.players.map((p) => p.state).filter((c) => STATES[c]))].sort((x, y) => stateName(x).localeCompare(stateName(y)));
    const kinds = el("ul", { class: "seg", "aria-label": "Board" }, BOARDS.map(([k, label]) => el("li", null,
      el("a", { href: href(["states"], { board: k === "overall" ? null : k, area: area || null }), "aria-current": k === kind ? "true" : null }, label))));
    const keyPick = keys.length ? el("label", null, kind === "mode" ? "Mode" : title(kind),
      el("select", { onchange: (e) => go({ key: e.target.value }) }, keys.map(([k, label]) => el("option", { value: k, selected: k === key }, label)))) : null;
    const areaPick = el("label", null, "Area", el("select", { onchange: (e) => go({ area: e.target.value || null }) },
      el("option", { value: "", selected: !area }, "Nationwide (" + D.players.length + ")"),
      el("optgroup", { label: "Regions" }, [...REGIONS].map(([k, n]) => el("option", { value: k, selected: k === area }, n + " (" + counted(k) + ")"))),
      el("optgroup", { label: "States" }, homes.map((c) => el("option", { value: c, selected: c === area }, stateName(c) + " (" + counted(c) + ")")))));
    const tools = el("div", { class: "toolbar picks" }, kinds, keyPick, areaPick);
    let body;
    if (!b) {
      body = empty("Nothing to rank yet", kind === "mode" ? "Nobody has a counted match in " + gameName.get(game()) + " yet."
        : "No kill with a " + kind + " is recorded in " + gameName.get(game()) + " yet. The mod's kill record fills this board after each recorded match.");
    } else {
      const rows = standings(b, area);
      body = table(null, [["#"], ["Name", "l"], ["State", "l"], ["Region", "l hide-s"], [b.unit]].concat(b.cols),
        rows.map((r) => el("tr", null, td(r.place, r.place <= 3 ? "pos lead" : "pos"),
          td(el("span", { class: "cell" }, emblem(r.p, true), el("a", { href: href(["p", r.p.name, "placements"]) }, r.p.name)), "l"),
          td(el("a", { href: boardHref(b, r.p.state) }, stateName(r.p.state)), "l"),
          td(el("a", { href: boardHref(b, regionOf(r.p)) }, areaName(regionOf(r.p))), "l hide-s"),
          td(int(r.v)), b.cells(r.p))),
        { none: b.unit === "Kills" ? "No kill with " + (key === "all" ? "a vehicle" : "the " + b.label) + " is recorded" + (area ? " in " + areaName(area) : "") + " yet."
          : "Nobody in " + areaName(area) + " is on this board yet." });
    }
    // each state of the area, its bots and its leader on this board (not when one state is shown)
    const inside = b && !STATES[area] ? homes.filter((c) => !area || STATES[c][1] === area)
      .map((c) => [c, standings(b, c)]).filter(([, rows]) => rows.length) : [];
    const leaders = inside.length ? panel("Leaders by state", table(null, [["State", "l"], ["Region", "l hide-s"], ["On the board"], ["Leader", "l"], [b.unit]],
      inside.map(([c, rows]) => el("tr", null, td(el("a", { href: boardHref(b, c) }, stateName(c)), "l"), td(areaName(STATES[c][1]), "l hide-s"),
        td(int(rows.length) + " of " + int(counted(c))),
        td(rows.filter((r) => r.place === 1).map((r, i) => [i ? ", " : null, el("a", { href: href(["p", r.p.name, "placements"]) }, r.p.name)]), "l"),
        td(int(rows[0].v)))))) : null;
    const what = !b ? "" : b.unit === "cR" ? "credits earned in " + (kind === "mode" ? b.label + " matches" : "every counted match") : "kills with " + (key === "all" ? "any vehicle" : "the " + b.label);
    return [el("h1", null, "Bot Tracker"), boardTabs("states"),
      el("p", { class: "note" }, "Every name has a home state, picked from the name the first time it is listed, so it never moves (it is not where anyone lives). " +
        "Each board ranks one area" + (what ? " by " + what : "") + " in " + gameName.get(game()) + "; anyone with none is left off, and equal numbers share a place."),
      panel(b ? b.label + ": " + areaName(area) : "State leaderboards", el("div", null, el("div", { class: "body" }, tools), body)),
      leaders];
  }

  // ---------------------------------------------------------------- commendations
  // Reach's multiplayer commendations (commendations.json): each bot's count (service_record.py commendation_counts),
  // the tier it has reached (Iron ... Onyx, then Max), its way to the next tier and the credits its tiers award.
  const TIER_CLASS = ["none", "iron", "bronze", "silver", "gold", "onyx", "max"];
  function commState(p, c) {
    const n = p.comm ? p.comm[c.key] : null;
    const tier = n == null ? 0 : c.need.filter((x) => n >= x).length;
    const next = tier < c.need.length ? tier : null;
    const from = tier ? c.need[tier - 1] : 0;
    const share = n == null ? 0 : next == null ? 1 : Math.min(1, (n - from) / (c.need[next] - from));
    const earned = c.cr.slice(0, tier).reduce((a, b) => a + b, 0);
    return { n, tier, next, share, earned, whole: n == null ? 0 : Math.min(1, n / c.need[c.need.length - 1]) };
  }
  const tierName = (i) => (i ? D.commendations.tiers[i - 1] : "Not started");
  function commArt(c, tier) {
    // the banner of the tier reached (the owner's emblem of that tier on it: service_record.py tier_banners), else
    // Reach's own 286 x 90 banner (its grey emblem, then the bar)
    const tiered = tier && D.commendations && D.commendations.tier_art && D.commendations.tier_art[c.key];
    const src = (tiered && tiered[tier]) || (D.commendations && D.commendations.art[c.key]);
    if (src) return el("img", { class: "comm-art banner" + (tiered && tiered[tier] ? " framed" : ""), src, alt: "", loading: "lazy" });
    return svg("svg", { class: "comm-art drawn", viewBox: "0 0 64 64", "aria-hidden": "true" },
      svg("path", { d: "M32 4 56 14v20c0 13-10 22-24 27C18 56 8 47 8 34V14z", fill: "none", stroke: "currentColor", "stroke-width": 3, "stroke-linejoin": "round" }),
      svg("path", { d: "M32 18l4.4 9 9.9 1.4-7.2 7 1.7 9.8L32 40.6l-8.8 4.6 1.7-9.8-7.2-7 9.9-1.4z", fill: "currentColor", opacity: tier ? 0.9 : 0.35 }));
  }
  function commBar(st, c) {
    return el("div", { class: "comm-bar", role: "img", "aria-label": tierName(st.tier) + (st.next != null ? ", " + int(st.n || 0) + " of " + int(c.need[st.next]) + " to " + tierName(st.next + 1) : "") },
      c.need.map((x, i) => el("span", { class: "seg " + TIER_CLASS[i + 1] + (i < st.tier ? " on" : i === st.next ? " now" : ""),
        style: i === st.next ? "--fill:" + (100 * st.share).toFixed(1) + "%" : null, "data-tip": tierName(i + 1) + ": " + int(x) + (c.cr[i] ? " (+" + int(c.cr[i]) + " cR)" : "") })));
  }
  const commSource = { kills: "From the kill record (matches since 15 Nov 2026)", report: "From MCC's post-game reports", matches: "From every counted match" };
  function commCard(p, c) {
    const st = commState(p, c);
    const banner = !!(D.commendations && D.commendations.art[c.key]);
    return el("li", { class: "comm t-" + TIER_CLASS[st.tier] + (st.n == null ? " unknown" : "") + (banner ? " has-banner" : "") },
      el("div", { class: "comm-pic" }, commArt(c, st.tier)),
      el("div", { class: "comm-body" },
        el("div", { class: "comm-head" }, el("h3", null, c.name), el("span", { class: "chip " + TIER_CLASS[st.tier] }, tierName(st.tier))),
        el("p", { class: "what" }, c.what),
        commBar(st, c),
        el("p", { class: "comm-nums" }, st.n == null
          ? "Not recorded yet: " + (c.from === "kills" ? "no match of this bot has the kill record." : "MCC's medal list has not been read on this PC.")
          : st.next == null ? int(st.n) + ": every tier reached."
            : int(st.n) + " of " + int(c.need[st.next]) + " for " + tierName(st.next + 1) + (c.cr[st.next] ? " (+" + int(c.cr[st.next]) + " cR)" : "")),
        el("p", { class: "comm-src" }, commSource[c.from] + (st.earned ? " \u00B7 " + int(st.earned) + " cR earned" : ""))));
  }
  function commProgress(p) {
    const list = (D.commendations && D.commendations.list) || [];
    const known = list.map((c) => commState(p, c)).filter((s) => s.n != null);
    return known.length ? (100 * known.reduce((a, s) => a + s.whole, 0)) / list.length : 0;
  }
  // Hometown Hero: the boards this bot leads in its home state, each with at least one other bot of the state on it
  function hometownBoards(p) {
    if (!STATES[p.state]) return [];
    const boards = [board("overall", "all")]
      .concat(boardKeys("mode").map(([k]) => board("mode", k)), boardKeys("weapon").map(([k]) => board("weapon", k)),
        boardKeys("vehicle").map(([k]) => board("vehicle", k)));
    return boards.filter((bd) => { const rows = standings(bd, p.state); return rows.length >= 2 && rows.some((r) => r.p === p && r.place === 1); });
  }
  const badgeOpen = (p, bd) => (bd.maps ? ((p.badges && p.badges[bd.key]) || []).length >= bd.maps.length : bd.key === "hometown_hero" && hometownBoards(p).length > 0);
  // the badges a bot has unlocked, on its player card: each its emblem, a link to it on the Commendations page
  function cardBadges(p) {
    const list = ((D.commendations && D.commendations.badges) || []).filter((bd) => badgeOpen(p, bd));
    if (!list.length) return null;
    return el("ul", { class: "card-badges", "aria-label": "Badges" }, list.map((bd) => {
      const art = D.commendations.badge_art && D.commendations.badge_art[bd.key];
      return el("li", null, el("a", { href: href(["p", p.name, "commendations"], { badge: bd.key }), "data-tip": bd.name + ": " + bd.what, "aria-label": bd.name },
        art ? el("img", { src: art, alt: "" }) : el("span", { class: "card-badge-name" }, bd.name)));
    }));
  }
  function badgeCard(p, bd) {
    const art = D.commendations.art[bd.key];
    let open = false, line = "", extra = null;
    if (bd.maps) {
      const won = new Set((p.badges && p.badges[bd.key]) || []);
      open = won.size >= bd.maps.length;
      line = int(won.size) + " of " + int(bd.maps.length) + " maps won";
      extra = el("ul", { class: "map-chips" }, bd.maps.map((m) => el("li", { class: won.has(m) ? "on" : null, "data-tip": mapName(m) + (won.has(m) ? ": won" : ": no win yet") }, mapName(m))));
    } else if (bd.key === "hometown_hero") {
      const led = hometownBoards(p);
      open = led.length > 0;
      line = open ? "#1 in " + stateName(p.state) + " on " + led.length + (led.length === 1 ? " board" : " boards")
        : STATES[p.state] ? "Not #1 in " + stateName(p.state) + " on any board yet" : "No home state";
      extra = open ? el("ul", { class: "map-chips" }, led.map((x) => el("li", { class: "on" }, el("a", { href: boardHref(x, p.state) }, x.label)))) : null;
    }
    const emblemArt = D.commendations.badge_art && D.commendations.badge_art[bd.key];   // (its own emblem, large)
    return el("li", { id: "badge-" + bd.key, class: "badge-card" + (open ? " open" : "") + (art || emblemArt ? " has-banner" : "") },
      el("div", { class: "comm-pic" }, emblemArt ? el("img", { class: "badge-art", src: emblemArt, alt: "", loading: "lazy" })
        : art ? el("img", { class: "comm-art banner", src: art, alt: "", width: 286, height: 90, loading: "lazy" })
        : svg("svg", { class: "comm-art drawn", viewBox: "0 0 64 64", "aria-hidden": "true" },
          svg("circle", { cx: 32, cy: 32, r: 26, fill: "none", stroke: "currentColor", "stroke-width": 3 }),
          svg("path", { d: open ? "M21 33l7 7 15-16" : "M24 30v-5a8 8 0 0 1 16 0v5M21 30h22v14H21z", fill: "none", stroke: "currentColor", "stroke-width": 3, "stroke-linecap": "round", "stroke-linejoin": "round" }))),
      el("div", { class: "comm-body" },
        el("div", { class: "comm-head" }, el("h3", null, bd.name), el("span", { class: "chip " + (open ? "gold" : "none") }, open ? "Unlocked" : "Locked")),
        el("p", { class: "what" }, bd.what), el("p", { class: "comm-nums" }, line), extra));
  }
  function commendations(p) {
    const list = (D.commendations && D.commendations.list) || [];
    if (!list.length) return [banner(p), panel("Commendations", empty("No commendation list", "tools/service_record_site/commendations.json was not read."))];
    const states = list.map((c) => [c, commState(p, c)]);
    const tiers = states.reduce((a, [, s]) => a + s.tier, 0), most = Math.max(...states.map(([, s]) => s.tier));
    const earned = states.reduce((a, [, s]) => a + s.earned, 0);
    const badges = D.commendations.badges || [];
    const opened = badges.filter((bd) => badgeOpen(p, bd)).length;
    const show = ["", "started", "unknown"].includes(route.q.show) ? route.q.show : "";
    const part = (set) => {
      const shown = states.filter(([c, s]) => c.set === set && (!show || (show === "started" ? s.n : s.n == null)));
      shown.sort((x, y) => y[1].tier - x[1].tier || y[1].share - x[1].share || x[0].name.localeCompare(y[0].name));
      return shown.length ? el("ul", { class: "comms" }, shown.map(([c]) => commCard(p, c))) : el("p", { class: "note" }, "None here.");
    };
    const count = (set) => list.filter((c) => c.set === set).length;
    return [banner(p),
      el("ul", { class: "hero" }, [["Tiers reached", int(tiers), "of " + int(list.length * D.commendations.tiers.length)],
        ["Highest tier", most ? tierName(most) : "None yet", ""], ["Badges", int(opened) + " of " + int(badges.length), "unlocked"],
        ["Credits from them", int(earned) + " cR", D.commendations.credits ? "counted in the rank" : "not counted in the rank"]]
        .map(([k, v, sub]) => el("li", null, el("span", { class: "v" }, v), el("span", { class: "k" }, k), sub ? el("span", { class: "sub" }, sub) : null))),
      el("ul", { class: "seg", "aria-label": "Show" }, [["", "All"], ["started", "Started"], ["unknown", "Not recorded yet"]].map(([k, label]) =>
        el("li", null, el("a", { href: href(["p", p.name, "commendations"], { show: k || null }), "aria-current": k === show ? "true" : null }, label)))),
      panel("Multiplayer Commendations", el("div", { class: "body" }, part("mp"),
        el("p", { class: "note" }, "Reach's " + count("mp") + " multiplayer commendations. Campaign and Firefight ones are left out: the bots play multiplayer only.")),
        el("span", { class: "note" }, count("mp") + " in all")),
      count("pg") ? panel("Proving Grounds Commendations", el("div", { class: "body" }, part("pg"),
        el("p", { class: "note" }, "Our own, counted the same way: first kills, game-winning kills and grudges come from the kill record (games since 15 Nov 2026).")),
        el("span", { class: "note" }, count("pg") + " in all")) : null,
      badges.length ? panel("Badges", el("div", { class: "body" }, el("ul", { class: "comms" }, badges.map((bd) => badgeCard(p, bd))),
        el("p", { class: "note" }, "One-time unlocks: no tiers, no credits.")), el("span", { class: "note" }, opened + " of " + badges.length + " unlocked")) : null,
      el("p", { class: "note" }, "Counted over this bot's counted Reach matches. Each tier reached adds its credits " +
        (D.commendations.credits ? "to the bot's rank, as in Reach." : "(not counted in the rank: ranks.json commendation_credits)."))];
  }

  // ---------------------------------------------------------------- a bot's pages
  // The figure, on a lit ring. Its own (native/figure_snap.exe: the bots panel's 3D view, its own armor pieces and
  // colours) turns: the angles round a turntable side by side in one picture, one shown at a time; drag it, or the
  // arrows (or the keyboard's) turn it a step. Else MCC's drawing of the body it wears in Reach (service_record_art.py
  // pictures), else our own outline. The corner button shows its armor list instead.
  let figureTurn = 0, figureArmor = false;
  function figureCard(p) {
    const looks = p.looks, f = p.figure;
    const body = (looks && looks.body) || "spartan";
    const drawing = D.figure_art && (D.figure_art[body + ".png"] || D.figure_art["spartan.png"]);
    const stage = el("div", { class: "stage" });
    const label = el("span", { class: "view", "aria-live": "polite" });
    let table = null;
    const at = () => ((figureTurn % f.n) + f.n) % f.n;
    const paint = () => {
      if (!table) return;
      const k = at();
      table.style.backgroundPositionX = (f.n > 1 ? (100 * k) / (f.n - 1) : 0) + "%";
      table.setAttribute("aria-label", p.name + " in its armor, turned " + Math.round((360 * k) / f.n) + " degrees");
    };
    const step = (d) => { figureTurn += d; paint(); };
    const figure = () => {
      if (f) {
        table = el("div", { class: "turntable", role: "img", tabindex: 0, title: "Drag to turn",
          style: `background-image:url("${f.src}");background-size:${f.n * 100}% 100%;aspect-ratio:${f.w} / ${f.h}`,
          onkeydown: (e) => { if (e.key === "ArrowLeft" || e.key === "ArrowRight") { step(e.key === "ArrowLeft" ? -1 : 1); e.preventDefault(); } } });
        let x0 = null, t0 = 0;
        table.addEventListener("pointerdown", (e) => { x0 = e.clientX; t0 = figureTurn; table.setPointerCapture(e.pointerId); });
        table.addEventListener("pointermove", (e) => { if (x0 !== null) { figureTurn = t0 + Math.round((x0 - e.clientX) / 14); paint(); } });
        const stop = () => { x0 = null; };
        table.addEventListener("pointerup", stop);
        table.addEventListener("pointercancel", stop);
        paint();
        return el("div", { class: "fig real" }, el("span", { class: "stand ringed" }, table));
      }
      table = null;
      return el("div", { class: "fig" }, drawing ? el("img", { src: drawing, alt: (looks ? looks.species : "Spartan") + " figure" })
        : svg("svg", { viewBox: "0 0 120 240", "aria-hidden": "true" }, svg("path", { d: "M60 10c12 0 20 9 20 21s-8 19-20 19-20-7-20-19 8-21 20-21zM34 58h52l14 70-14 4-6-40-4 70 6 64H66l-6-60-6 60H38l6-64-4-70-6 40-14-4z", fill: "none", stroke: "currentColor", "stroke-width": 2.5, "stroke-linejoin": "round" })));
    };
    const armor = () => looks && looks.pieces.length
      ? el("dl", { class: "armor" }, el("dt", null, "Species"), el("dd", null, looks.species), looks.pieces.map(([k, v]) => [el("dt", null, k), el("dd", null, v)]))
      : el("p", { class: "note" }, "No Reach look on file yet (it is written when the look is rolled).");
    const toggle = el("button", { type: "button", class: "armor-btn", "aria-pressed": "false" });
    const arrows = [el("button", { type: "button", "aria-label": "Turn left", onclick: () => step(-1) }, "\u2190"), label,
      el("button", { type: "button", "aria-label": "Turn right", onclick: () => step(1) }, "\u2192")];
    const turnBar = el("div", { class: "turn" }, arrows);
    const show = () => {
      stage.replaceChildren(figureArmor ? armor() : figure());
      stage.classList.toggle("own", !figureArmor && !!f);   // its own figure brings its own ring
      toggle.textContent = figureArmor ? "Figure" : "Armor";
      toggle.setAttribute("aria-pressed", String(figureArmor));
      label.textContent = f ? "360\u00B0" : figureArmor ? "Armor" : "Figure";
      turnBar.hidden = !f || figureArmor;
    };
    toggle.addEventListener("click", () => { figureArmor = !figureArmor; show(); });
    show();
    return el("section", { class: "panel figure", "aria-label": "Figure" }, toggle, stage, turnBar);
  }
  // the Games Played ring: one segment per game type family, every family listed under it (0 too)
  function donut(cats) {
    const fams = RING.map((k) => [k, (cats[k] || {}).games || 0]);
    const rest = Object.keys(cats).filter((k) => k !== "all" && !RING.includes(k)).reduce((n, k) => n + cats[k].games, 0);
    if (rest) fams.push(["rest", rest]);
    const total = fams.reduce((n, x) => n + x[1], 0);
    const R = 56, C = 2 * Math.PI * R, live = fams.filter((x) => x[1]), gap = live.length > 1 ? 2 : 0;
    let at = 0;
    const marks = live.map(([k, n]) => {
      const len = (n / total) * C;
      const m = svg("circle", { cx: 80, cy: 80, r: R, fill: "none", stroke: "var(--c-" + k + ")", "stroke-width": 20,
        "stroke-dasharray": Math.max(len - gap, 1) + " " + C, "stroke-dashoffset": -at, transform: "rotate(-90 80 80)",
        "data-tip": (catName.get(k) || (k === "rest" ? "Other modes" : title(k))) + ": " + int(n) + (n === 1 ? " game" : " games") });
      at += len;
      return m;
    });
    return el("div", { class: "donut" },
      svg("svg", { viewBox: "0 0 160 160", role: "img", "aria-label": "Games played by game type: " + int(total) + " in all" },
        svg("circle", { cx: 80, cy: 80, r: R, fill: "none", stroke: "var(--track)", "stroke-width": 20 }), marks,
        svg("circle", { cx: 80, cy: 80, r: 44, fill: "var(--panel-2)" }),
        svg("text", { class: "total", x: 80, y: 84, "text-anchor": "middle" }, int(total)),
        svg("text", { class: "unit", x: 80, y: 101, "text-anchor": "middle" }, "Total")),
      el("ul", { class: "legend" }, fams.map(([k, n]) => el("li", null,
        el("span", { class: "dot", style: "background:var(--c-" + k + ")" }),
        el("span", { class: "lbl" }, modeIcon(k, 16), catName.get(k) || (k === "rest" ? "Other modes" : FAMILY_LABEL[k] || title(k))), el("span", { class: "v" }, int(n))))));
  }
  // won or lost, every match oldest first (the newest 40): a bar for a win, a small block for a loss, each run of wins
  // numbered under its last bar
  function streakChart(p, g) {
    const list = g.matches.slice(0, 40).map((i) => D.matches[i]).reverse();
    const won = list.map((m) => !!(m.rows.find((r) => r.n === p.name) || {}).won);
    const step = 22, w = 16, top = 10, base = 96, H = 124, width = Math.max(list.length * step + 8, 240);
    const marks = [];
    let run = 0;
    won.forEach((x, i) => {
      const m = list[i], cx = 4 + i * step;
      const tip = result(m, { won: x }) + ": " + mapName(m.map) + ", " + m.when;
      if (x) {
        run++;
        marks.push(svg("rect", { class: "w", x: cx, y: top, width: w, height: base - top, rx: 2, "data-tip": tip }));
        if (!won[i + 1]) marks.push(svg("text", { x: cx + w / 2, y: base + 18, "text-anchor": "middle" }, run));
      } else {
        run = 0;
        marks.push(svg("rect", { class: "l", x: cx, y: base - 8, width: w, height: 8, rx: 1.5, "data-tip": tip }));
      }
    });
    return svg("svg", { class: "streak", viewBox: `0 0 ${width} ${H}`, preserveAspectRatio: "xMinYMid meet", role: "img",
      "aria-label": "Matches oldest first: " + won.map((x) => (x ? "won" : "lost")).join(", ") },
      svg("line", { x1: 0, x2: width, y1: base + 0.5, y2: base + 0.5 }), marks);
  }
  // a match as a card (Recent Games, Game History): the map's picture (MCC's own preview, read on this PC) with the
  // match's length, the map, the game type and when, how this player did, the carnage report and heatmap links, and
  // its kills
  const clock = (s) => (s == null ? "" : Math.floor(s / 60) + ":" + pad2(Math.floor(s % 60)));
  function gameCard(p, m) {
    const me = m.rows.find((r) => r.n === p.name) || {};
    const pic = D.map_art && D.map_art[m.map];
    const link = href(["p", p.name, "match", m.id]);
    const secs = Math.max(...m.rows.map((r) => r.sec || 0));
    const heatKey = m.heat || m.map;                                   // (a Forge layout's own heatmap: "<map>@<layout>")
    const heat = side(p) && side(p).heat && side(p).heat[heatKey];
    return el("li", null,
      el("a", { class: "thumb", href: link, "aria-label": mapName(m.map) + " carnage report" },
        pic ? el("img", { src: pic, alt: "", loading: "lazy" }) : el("span", { class: "noimg" }, mapName(m.map)),
        el("span", { class: "len" }, "\u25B8 " + clock(secs))),
      el("div", { class: "what" },
        el("a", { class: "t", href: link }, mapName(m.map)),
        el("div", { class: "by" }, modeIcon(m.cat, 16), (m.type || "Unknown game type") + " on ", el("b", null, dotted(m.t))),
        el("div", { class: "res" + (me.won ? " won" : "") }, result(m, me), ", placed " + ordinal((me.st || 0) + 1) + ": " +
          int(me.k) + " kills, " + int(me.d) + " deaths, " + int(me.a) + " assists"),
        el("div", { class: "acts" }, el("a", { href: link }, icon("scoreboard", 18), "Carnage report"),
          heat ? el("a", { href: href(["p", p.name, "heatmaps"], { map: heatKey }) }, icon("heatmaps", 18), "Heatmap") : null)),
      el("div", { class: "box" }, neon("kills", 22), el("b", null, int(me.k)), el("span", null, me.k === 1 ? "Kill" : "Kills")));
  }
  function recentGames(p, g) {
    return el("ul", { class: "games" }, g.matches.slice(0, 5).map((i) => gameCard(p, D.matches[i])));
  }

  function overview(p) {
    const g = side(p), s = bucket(p);
    const row = (ic, label, value, small) => el("li", null, neon(ic, 18), el("span", { class: "k" }, label),
      el("span", { class: "v" }, value, small && el("small", null, " (" + small + ")")));
    const facts = el("section", { class: "panel facts", "aria-label": "Service record" }, el("ul", { class: "list" },
      row("calendar", "Last Played", g ? dotted(g.last) : "-"),
      row("games", "Games Played", int(s.games)),
      row("win", "Wins", int(s.wins), s.r.win != null ? dec(s.r.win) + "%" : null),
      row("kills", "Kills", int(s.kills), dec(s.r.kd) + " K/D"),
      row("deaths", "Deaths", int(s.deaths)),
      row("assists", "Assists", int(s.assists)),
      row("stat-medals", "Medals", int(s.medals)),
      row("spree", "Most Kills in a Row", int(s.spree)),
      row("since", "Playing Since", g ? dotted(g.first) : "-")));
    const played = el("section", { class: "panel played" }, el("header", null, el("h2", null, "Games Played")),
      el("div", { class: "body" }, donut(g ? g.cats : {})));
    const clist = (D.commendations && D.commendations.list) || [];
    const top3 = clist.map((c) => [c, commState(p, c)]).filter(([, s]) => s.n)
      .sort((x, y) => y[1].tier - x[1].tier || y[1].share - x[1].share).slice(0, 3);
    const commend = el("section", { class: "panel commend" },
      el("header", null, el("h2", null, "Top Commendations"), el("span", { class: "prog" }, "Commendation Progress ", el("b", null, commProgress(p).toFixed(1) + "%"))),
      el("div", { class: "body" }, top3.length
        ? el("ul", { class: "top-comms" }, top3.map(([c, st]) => el("li", { class: "t-" + TIER_CLASS[st.tier] + (D.commendations.art[c.key] ? " has-banner" : ""), "data-tip": c.what },
          commArt(c, st.tier), el("div", null, el("b", null, c.name), el("span", { class: "chip " + TIER_CLASS[st.tier] }, tierName(st.tier)), commBar(st, c)))))
        : el("p", { class: "note" }, "No commendation started yet."),
        el("a", { class: "more", href: href(["p", p.name, "commendations"]) }, "All commendations")));
    const streak = g ? g.streak : { current: 0, best: 0 };
    const plural = (n) => int(n) + (n === 1 ? " Win" : " Wins");
    const streaks = el("section", { class: "panel streaks" },
      el("header", null, el("h2", null, icon("trophy", 22), "Victory Streaks"),
        el("a", { class: "go", href: href(["p", p.name, "history"]) }, "View Game History", icon("arrow", 16))),
      el("div", { class: "body" },
        el("div", { class: "runs" },
          el("div", null, el("span", { class: "k" }, "Current Streak"), el("span", { class: "v" }, plural(streak.current))),
          el("div", null, icon("trophy", 18), el("span", { class: "k" }, "Longest Streak"), el("span", { class: "v" }, plural(streak.best)))),
        el("div", { class: "chart" }, el("div", { class: "axis" }, el("span", null, "Won"), el("span", null, "Lost")),
          el("div", { class: "scroll" }, g && g.matches.length ? streakChart(p, g) : el("p", { class: "note" }, "No counted matches yet.")))));
    const games = el("section", { class: "panel recent" },
      el("header", null, el("h2", null, neon("film", 24), "Recent Games"),
        el("a", { class: "go", href: href(["p", p.name, "history"]) }, "View All Games", icon("arrow", 16))),
      g && g.matches.length ? el("div", { class: "body" }, recentGames(p, g),
        el("a", { class: "wide-btn", href: href(["p", p.name, "history"]) }, "See every game in " + gameName.get(game()), icon("arrow", 18)))
        : noGames());
    return [banner(p), el("div", { class: "ov" }, figureCard(p), facts, played, commend), streaks, games];
  }

  // Game History: every counted match as a card, newest first, by mode, map and result; 25 at a time
  let historyShown = 25;
  function history(p) {
    const g = side(p);
    const all = g ? g.matches.map((i) => D.matches[i]) : [];
    const mine = (m) => m.rows.find((r) => r.n === p.name) || {};
    const cats = [...new Set(all.map((m) => m.cat))].sort((x, y) => (catName.get(x) || x).localeCompare(catName.get(y) || y));
    const maps = [...new Set(all.map((m) => m.map))].sort((x, y) => mapName(x).localeCompare(mapName(y)));
    const cat = cats.includes(route.q.cat) ? route.q.cat : "";
    const map = maps.includes(route.q.map) ? route.q.map : "";
    const res = ["Won", "Lost", "Tied"].includes(route.q.res) ? route.q.res : "";
    const list = all.filter((m) => (!cat || m.cat === cat) && (!map || m.map === map) && (!res || result(m, mine(m)) === res));
    const go = (q) => { historyShown = 25; location.hash = href(["p", p.name, "history"], Object.assign({ cat: cat || null, map: map || null, res: res || null }, q)); };
    const tools = el("div", { class: "toolbar picks" },
      el("label", null, "Mode", el("select", { onchange: (e) => go({ cat: e.target.value || null }) },
        el("option", { value: "", selected: !cat }, "All modes"), cats.map((k) => el("option", { value: k, selected: k === cat }, catName.get(k) || title(k))))),
      el("label", null, "Map", el("select", { onchange: (e) => go({ map: e.target.value || null }) },
        el("option", { value: "", selected: !map }, "All maps"), maps.map((k) => el("option", { value: k, selected: k === map }, mapName(k))))),
      el("ul", { class: "seg", "aria-label": "Result" }, [["", "All"], ["Won", "Won"], ["Lost", "Lost"], ["Tied", "Tied"]].map(([k, label]) =>
        el("li", null, el("a", { href: href(["p", p.name, "history"], { cat: cat || null, map: map || null, res: k || null }), "aria-current": k === res ? "true" : null }, label)))));
    const k = list.reduce((n, m) => n + (mine(m).k || 0), 0), d = list.reduce((n, m) => n + (mine(m).d || 0), 0);
    const won = list.filter((m) => mine(m).won).length;
    const cards = el("ul", { class: "games" }, list.slice(0, historyShown).map((m) => gameCard(p, m)));
    const more = list.length > historyShown ? el("button", { type: "button", class: "wide-btn", onclick: () => {
      historyShown += 25;
      cards.replaceChildren(...list.slice(0, historyShown).map((m) => gameCard(p, m)));
      if (list.length <= historyShown) more.remove();
      else more.textContent = "Show more (" + int(list.length - historyShown) + " left)";
    } }, "Show more (" + int(list.length - historyShown) + " left)") : null;
    return [banner(p), panel("Games", el("div", { class: "body" }, tools,
      list.length ? [el("p", { class: "note" }, int(list.length) + (list.length === 1 ? " game" : " games") + ", newest first: " + int(won) + " won, " +
        int(k) + " kills, " + int(d) + " deaths (" + dec(d ? k / d : k) + " K/D). Open one for its carnage report."), cards, more]
        : empty(all.length ? "No games match" : "No counted matches yet", all.length ? "Try another mode, map or result." : "Nothing is recorded for " + gameName.get(game()) + " yet.")),
      el("a", { class: "go", href: href(["p", p.name, "history"], { cat: null, map: null, res: null }) }, "Clear filters", icon("arrow", 16)))];
  }

  // The carnage report: the map's picture across the top with the result, every player's line (team by team, in its
  // colours) with the medals each earned that game, and, for a match recorded with the kill record, its kill feed.
  const TEAMS = ["Red", "Blue", "Green", "Orange", "Purple", "Gold", "Brown", "Pink"];
  const teamOf = (m, name) => { const r = m.rows.find((x) => x.n === name); return r && m.teams ? r.team : null; };
  function medalStrip(medals, max) {
    const list = Object.entries(medals || {}).sort((a, b) => b[1] - a[1] || a[0] - b[0]);
    const shown = list.slice(0, max || 6);
    return el("ul", { class: "mstrip" }, shown.map(([id, n]) => {
      const md = D.medals[id] || { name: "Medal " + id, icon: null };
      return el("li", { "data-tip": md.name + (n > 1 ? " x" + n : "") },
        md.icon ? el("img", { src: md.icon, alt: md.name, width: 26, height: 26, loading: "lazy" }) : el("span", { class: "mdot", "aria-label": md.name }), n > 1 ? el("b", null, n) : null);
    }), list.length > shown.length ? el("li", { class: "rest" }, "+" + (list.length - shown.length)) : null);
  }
  let feedAll = false, feedMine = false;
  function killFeed(p, m) {
    const box = el("div");
    const draw = () => {
      const rows = m.feed.filter((r) => !feedMine || r[1] === p.name || r[2] === p.name);
      const shown = feedAll ? rows : rows.slice(0, 40);
      const who = (name, end) => {                                 // end: "k" the killer (against the weapon), "v" the victim
        const tm = name ? teamOf(m, name) : null;
        return name ? el("span", { class: "who " + end + (tm != null ? " t" + tm : ""), "data-me": name === p.name ? "1" : null }, name) : null;
      };
      box.replaceChildren(
        el("div", { class: "toolbar" }, el("ul", { class: "seg", "aria-label": "Show" }, [[false, "Every kill"], [true, p.name + "'s"]].map(([k, label]) =>
          el("li", null, el("a", { href: "#", "aria-current": k === feedMine ? "true" : null, onclick: (e) => { e.preventDefault(); feedMine = k; draw(); } }, label)))),
          el("span", { class: "note" }, int(rows.length) + (rows.length === 1 ? " death" : " deaths"))),
        el("ol", { class: "feed" }, shown.map(([t, killer, victim, key, kind]) => {
          const [wname] = weaponName(key);
          const art = D.weapon_art && D.weapon_art[key];
          return el("li", { class: kind },
            el("span", { class: "tm" }, clock(t)),
            kind === "death" ? [who(victim, "v"), el("span", { class: "how" }, art ? el("img", { src: art, alt: "", loading: "lazy" }) : null, el("span", null, "died: " + wname))]
              : [who(killer, "k"), el("span", { class: "how", "data-tip": wname }, art ? el("img", { src: art, alt: wname, loading: "lazy" }) : el("span", null, wname)),
                who(victim, "v"), kind === "betrayal" ? el("span", { class: "tag" }, "betrayal") : null]);
        })),
        rows.length > shown.length ? el("button", { type: "button", class: "wide-btn", onclick: () => { feedAll = true; draw(); } }, "Show all " + int(rows.length)) : null);
    };
    draw();
    return box;
  }
  function match(p, id) {
    const m = D.matches.find((x) => x.id === id);
    if (!m) return [banner(p), panel("Carnage Report", empty("Match not found", "This match is not in the record (it may be from before the stats were reset)."))];
    const me = m.rows.find((r) => r.n === p.name) || {};
    const full = m.report;
    const secs = Math.max(...m.rows.map((r) => r.sec || 0));
    const pic = D.map_art && D.map_art[m.map];
    const verdict = result(m, me);
    const teamSum = (t) => m.rows.filter((r) => r.team === t).reduce((n, r) => n + (r.score != null ? r.score : r.k), 0);
    const teams = m.teams ? [...new Set(m.rows.map((r) => r.team))].sort((x, y) => Math.min(...m.rows.filter((r) => r.team === x).map((r) => r.st)) - Math.min(...m.rows.filter((r) => r.team === y).map((r) => r.st))) : [];
    const hero = el("section", { class: "report-hero", style: pic ? `background-image:url("${pic}")` : null },
      el("div", { class: "shade" },
        el("p", { class: "kicker" }, "Carnage Report"),
        el("h2", null, mapName(m.map)),
        el("p", { class: "meta" }, [m.type || "Unknown game type", gameName.get(m.game) || m.game, dotted(m.t) + " " + m.when.slice(11), clock(secs)].join("  \u00B7  ")),
        el("div", { class: "verdict" },
          el("span", { class: "big " + verdict.toLowerCase() }, verdict),
          me.n ? el("span", null, p.name + " placed " + ordinal(me.st + 1) + ": " + int(me.k) + " kills, " + int(me.d) + " deaths, " + int(me.a) + " assists") : null),
        teams.length ? el("ul", { class: "scores" }, teams.map((t) => el("li", { class: "t" + t }, el("span", null, (TEAMS[t] || "Team " + (t + 1)) + " Team"), el("b", null, int(teamSum(t)))))) : null));
    const heads = [["#"], ["Player", "l"]].concat(full ? [["Score", "hide-s"]] : [], [["Kills"], ["Deaths"], ["Assists", "hide-s"], ["K/D"]], full ? [["Medals", "l hide-s"]] : []);
    const line = (r) => el("tr", { class: r.n === p.name ? "me" : null }, td(ordinal(r.st + 1), "pos"),
      td(el("span", { class: "cell" }, players.has(r.n) ? emblem(players.get(r.n), true) : el("span", { class: "emblem none sm" }),
        r.listed && players.has(r.n) ? el("a", { href: href(["p", r.n, "overview"]) }, r.n) : el("span", null, r.n),
        r.clan ? el("span", { class: "tag hide-s" }, r.clan) : null, !r.bot ? el("span", { class: "tag" }, "player") : null), "l"),
      full ? td(int(r.score), "hide-s") : null, td(int(r.k)), td(int(r.d)), td(int(r.a), "hide-s"), td(dec(r.d ? r.k / r.d : r.k)),
      full ? td(medalStrip(r.medals, 6), "l hide-s") : null);
    const boards = teams.length
      ? teams.map((t) => {
        const mine = m.rows.filter((r) => r.team === t);
        const sum = (k) => mine.reduce((n, r) => n + (r[k] || 0), 0);
        return el("section", { class: "panel team-board t" + t },
          el("header", null, el("h2", null, (TEAMS[t] || "Team " + (t + 1)) + " Team", mine.some((r) => r.won) ? el("span", { class: "won-tag" }, "Won") : null),
            el("span", { class: "note" }, int(sum("k")) + " kills, " + int(sum("d")) + " deaths")),
          table(null, heads, mine.map(line)));
      })
      : [panel("Players", table(null, heads, m.rows.map(line)))];
    const feed = m.feed && m.feed.length ? panel("Kill Feed", el("div", { class: "body" }, killFeed(p, m),
      el("p", { class: "note" }, "From the mod's kill record: who the game credits with each death, with what, and when (minutes into the match).")))
      : panel("Kill Feed", empty("Not recorded for this match", "The kill record started on 15 November 2026; this match was played without it."));
    return [banner(p),
      el("p", null, el("a", { class: "more back-link", href: href(["p", p.name, "history"]) }, "Back to Game History")),
      hero, boards, feed,
      full ? null : el("p", { class: "note" }, "MCC's full report for this match was not kept, so only kills, deaths and assists remain.")];
  }

  function summary(p) {
    const g = side(p);
    const have = D.cats.filter(([k]) => g && g.cats[k] && g.cats[k].games);
    const cat = have.some(([k]) => k === route.q.cat) ? route.q.cat : "all";
    const s = bucket(p, cat);
    const tabs = el("ul", { class: "tabs" }, [["all", "All"]].concat(have).map(([k, label]) =>
      el("li", null, el("a", { href: href(["p", p.name, "summary"], { cat: k === "all" ? null : k }), "aria-current": k === cat ? "true" : null }, label))));
    const stats = el("dl", { class: "stats" },
      el("dt", null, "Games"), el("dd", null, int(s.games)),
      el("dt", null, "Wins"), el("dd", null, int(s.wins)),
      el("dt", null, "Playtime"), el("dd", null, s.r.playtime),
      el("dt", null, "Kills"), el("dd", null, int(s.kills)),
      el("dt", null, "Deaths"), el("dd", null, int(s.deaths)),
      el("dt", null, "Assists"), el("dd", null, int(s.assists)),
      el("dt", null, "Kill/Death"), el("dd", null, dec(s.r.kd)),
      el("dt", null, "Kills/Game"), el("dd", null, dec(s.r.kpg)),
      el("dt", null, "Deaths/Game"), el("dd", null, dec(s.r.dpg)),
      el("dt", null, "Kills/Hour"), el("dd", null, dec(s.r.kph)),
      el("dt", null, "Deaths/Hour"), el("dd", null, dec(s.r.dph)),
      el("dt", null, "Medals"), el("dd", null, int(s.medals)),
      el("dt", null, "Medals/Game"), el("dd", null, dec(s.r.mpg)),
      el("dt", null, "Medals/Hour"), el("dd", null, dec(s.r.mph)));
    const top = medalList(g).slice(0, 7);
    return [banner(p), tabs,
      el("div", { class: "grid" },
        panel((cat === "all" ? "All game types" : catName.get(cat)) + ": stats", el("div", null, stats, reportNote(s) && el("div", { class: "body" }, reportNote(s)))),
        panel("Games played", el("div", { class: "body" }, ring(g ? g.cats : {})))),
      panel("Top medals", top.length ? el("div", { class: "body" }, el("ul", { class: "medals" }, top.map(([id, n]) => medalTile(id, n))))
        : empty("No medals yet", "Medals come from MCC's post-game report of each counted match."),
        el("a", { class: "more", href: href(["p", p.name, "medals"]) }, "View all medals")),
      panel("Top weapons", recorded(g)
        ? el("div", { class: "body" }, weaponList(g).some((w) => w[1][0])
          ? weaponCards(weaponList(g).filter((w) => w[1][0]).slice(0, 3), weaponList(g), "best")
          : el("p", { class: "note" }, "No kills in the recorded matches yet."),
          el("p", { class: "note" }, killNote(g, bucket(p))))
        : el("div", { class: "body" },
          el("p", { class: "note" }, "Kills and deaths per weapon are not recorded yet here: MCC's report only splits kills by type."),
          bucket(p).detailed ? hbars(killTypes(bucket(p))) : null),
        el("a", { class: "more", href: href(["p", p.name, "weapons"]) }, "View weapons"))];
  }

  function breakdown(p, heading, group, label, first) {
    const g = side(p);
    const rows = Object.entries((g && g[group]) || {}).sort((a, b) => b[1].games - a[1].games || label(a[0]).localeCompare(label(b[0])))
      .map(([k, s]) => el("tr", null, td(group === "types" && modeIcon(typeCat.get(k))
        ? el("span", { class: "cell" }, modeIcon(typeCat.get(k), 20), label(k)) : label(k), "l wrap"), td(int(s.games)), td(int(s.wins)), td(int(s.kills)), td(int(s.deaths)),
        td(int(s.assists), "hide-s"), td(dec(s.r.kd)), td(dec(s.r.kpg), "hide-s"), td(s.r.playtime, "hide-s")));
    return [banner(p), panel(heading, table(null,
      [[first, "l"], ["Games"], ["Wins"], ["Kills"], ["Deaths"], ["Assists", "hide-s"], ["K/D"], ["Kills/Game", "hide-s"], ["Playtime", "hide-s"]],
      rows, { none: "No counted matches yet for " + gameName.get(game()) + "." }))];
  }

  // Medals by group, as the old service record sorted them (service_record.py medal_group: MCC's own type of each)
  const MEDAL_GROUPS = [["multikill", "Multikills"], ["spree", "Sprees"], ["kill", "Kills"], ["style", "Style"],
    ["assist", "Assists & Support"], ["objective", "Objective"], ["legendary", "Legendary"], ["other", "Other"]];
  function medals(p) {
    const list = medalList(side(p));
    const groupOf = (id) => (D.medals[id] && D.medals[id].cat) || "other";
    const groups = MEDAL_GROUPS.map(([k, label]) => [k, label, list.filter(([id]) => groupOf(id) === k)]).filter((x) => x[2].length);
    const want = groups.some((x) => x[0] === route.q.group) ? route.q.group : "";
    const total = (items) => items.reduce((n, x) => n + x[1], 0);
    const tiles = el("ul", { class: "mgroups" }, groups.map(([k, label, items]) => el("li", null,
      el("a", { href: href(["p", p.name, "medals"], { group: want === k ? null : k }), "aria-current": want === k ? "true" : null },
        el("span", { class: "v" }, int(total(items))), el("span", { class: "k" }, label), el("span", { class: "n" }, items.length + (items.length === 1 ? " kind" : " kinds"))))));
    const shown = groups.filter((x) => !want || x[0] === want);
    return [banner(p),
      list.length ? [tiles, shown.map(([k, label, items]) => panel(label,
        el("div", { class: "body" }, el("ul", { class: "medals" }, items.map(([id, n]) => medalTile(id, n)))),
        el("span", { class: "note" }, int(total(items)) + " earned")))]
        : panel("Medals", empty("No medals yet", "Medals come from MCC's post-game report of each counted match.")),
      list.length ? el("p", { class: "note" }, int(bucket(p).medals) + " medals in all, " + list.length + " kinds. Pick a group to see it alone.") : null,
      !D.medal_art && list.length ? el("p", { class: "note" },
        "Medals show by MCC's number because their names and icons have not been read from this PC's MCC yet: " +
        "python\\python.exe -I tools\\service_record_art.py medals") : null];
  }

  function weapons(p) {
    const s = bucket(p);
    const rows = s.detailed ? killTypes(s).map(([label, n]) => el("tr", null, td(label, "l"), td(int(n)),
      td(s.kills ? Math.round((100 * n) / s.kills) + "%" : "-"))) : [];
    const g = side(p);
    const byType = panel("Kills by type (MCC's report)", el("div", null, table(null, [["Type", "l"], ["Kills"], ["Share of kills"]], rows,
      { none: "No report recorded yet for " + gameName.get(game()) + "." }), reportNote(s) && el("div", { class: "body" }, reportNote(s))));
    const rec = recorded(g);
    const [wl, vl] = arsenalLists(rec ? g : null);
    const all = wl.concat(vl);
    const kills = all.reduce((n, w) => n + w[1][0], 0), deaths = all.reduce((n, w) => n + w[1][1], 0);
    const unchecked = all.some(([key, n]) => (n[0] || n[1]) && !weaponName(key)[1]);
    const count = (list) => { const k = list.filter((w) => w[1][0] || w[1][1]).length; return int(k) + " of " + int(list.length) + " used"; };
    return [banner(p),
      panel("Weapons", el("div", { class: "body" },
        el("p", { class: "note" }, rec ? killNote(g, s) + " Kills are the ones the game credits to " + p.name + " against players of the other team; deaths are every way it died."
          : "Not recorded yet. " + NO_KILLS + " Every weapon is listed at 0 until then; MCC's own report splits kills by type, below."),
        wl.length ? weaponCards(wl, all) : null,
        unchecked && el("p", { class: "note" },
          "* Named from the game's own list of damage types. This name has not yet been matched to a kill seen live.")),
        el("span", { class: "note" }, rec ? int(kills) + (kills === 1 ? " kill, " : " kills, ") + int(deaths) + (deaths === 1 ? " death" : " deaths") + " \u00b7 " + count(wl) : count(wl))),
      vl.length ? panel("Vehicles", el("div", { class: "body" }, weaponCards(vl, all, "vehicles")), el("span", { class: "note" }, count(vl))) : null,
      byType];
  }

  function enemies(p) {
    const g = side(p);
    // (short headers, columns that wrap: the tables fit their panel, never scroll sideways)
    const list = (obj, what) => table("Matches: how often they were " + p.name + "'s " + what + "; Kills: in those matches.",
      [["Opponent", "l"], ["Matches"], ["Kills"]],
      Object.entries(obj || {}).sort((a, b) => b[1][1] - a[1][1] || a[0].localeCompare(b[0])).map(([n, v]) =>
        el("tr", null, td(players.has(n) ? el("a", { href: href(["p", n, "overview"]) }, n) : n, "l wrap"), td(int(v[0])), td(int(v[1])))),
      { none: "No report recorded yet for " + gameName.get(game()) + ".", fit: true });
    const rivals = el("div", { class: "grid" }, panel("Killed most (MCC's report)", list(g && g.killed, "top victim")),
      panel("Killed most by (MCC's report)", list(g && g.killed_by, "top killer")));
    if (!recorded(g)) {
      return [banner(p), panel("Enemies", empty("Full versus table not recorded yet", NO_KILLS +
        " MCC's report names only two rivals per match, below: who " + p.name + " killed most and who killed them most.")), rivals];
    }
    const rows = Object.entries(g.versus).sort((a, b) => (b[1][0] + b[1][1]) - (a[1][0] + a[1][1]) || b[1][0] - a[1][0] || a[0].localeCompare(b[0]))
      .map(([n, v]) => el("tr", null,
        td(players.has(n) ? el("a", { href: href(["p", n, "overview"]) }, n) : n, "l wrap"), td(int(v[0])), td(int(v[1])),
        td((v[0] > v[1] ? "+" : "") + int(v[0] - v[1])), td(v[1] ? dec(v[0] / v[1]) : dec(v[0]))));
    return [banner(p),
      panel("Enemies", table(killNote(g, bucket(p)) + " Every opponent " + p.name + " killed or was killed by.",
        [["Opponent", "l"], ["Kills"], ["Deaths"], ["+/-"], ["K/D"]], rows,
        { none: "No kills either way in the recorded matches yet.", fit: true })),
      rivals];
  }

  // Kills and deaths on a map's top-down picture (maps/<id>.png, copied in by the build with the part of the level it
  // shows). Each spot is a soft glow, so places fought over often grow bright, with a mark on top: a dot where this
  // bot stood for a kill, a cross where it died. Without a picture of the map the spots are plotted on a plain panel.
  // A map tab leaves the view (whole map or zoomed) to the map it opens: its link drops ?view.
  function heatmaps(p) {
    const g = side(p);
    if (!recorded(g)) return [banner(p), panel("Heatmaps", empty("Not recorded yet", NO_KILLS))];
    const count = (m) => (g.heat[m].k.length + g.heat[m].d.length) / 2;
    const ids = Object.keys(g.heat).filter(count).sort((a, b) => count(b) - count(a) || mapName(a).localeCompare(mapName(b)));
    if (!ids.length) return [banner(p), panel("Heatmaps", empty("Nothing to plot yet", killNote(g, bucket(p)) + " No kill or death of " + p.name + " is in them."))];
    const id = ids.includes(route.q.map) ? route.q.map : ids[0];
    const show = ["kills", "deaths"].includes(route.q.show) ? route.q.show : "both";
    const spots = g.heat[id], pic = (D.heat_maps || {})[id];
    const link = (q) => href(["p", p.name, "heatmaps"], Object.assign({ map: id === ids[0] ? null : id, show: show === "both" ? null : show,
      view: route.q.view === "all" ? "all" : null }, q));
    const mapTabs = el("ul", { class: "tabs" }, ids.map((m) => el("li", null,
      el("a", { href: link({ map: m === ids[0] ? null : m, view: null }), "aria-current": m === id ? "true" : null }, mapName(m) + " (" + int(count(m)) + ")"))));
    const showTabs = el("ul", { class: "seg", "aria-label": "Show" }, [["both", "Kills and deaths"], ["kills", "Kills"], ["deaths", "Deaths"]].map(([k, label]) =>
      el("li", null, el("a", { href: link({ show: k === "both" ? null : k }), "aria-current": k === show ? "true" : null }, label))));
    const nk = spots.k.length / 2, nd = spots.d.length / 2;
    const canvas = el("canvas", { role: "img", "aria-label": p.name + " on " + mapName(id) + ": " + int(nk) + " kills, " + int(nd) + " deaths plotted" });
    // What is shown: [x0, y0, width, height] in the level's units. The whole picture, or, when every spot lies in a
    // small part of it (a Forge variant in a corner of Forge World), that part with a margin; without a picture, the
    // spots' own bounds. The picture is drawn into the canvas, cut to the view and dimmed, under the spots.
    const all = spots.k.concat(spots.d), xs = all.filter((_, i) => i % 2 === 0), ys = all.filter((_, i) => i % 2 === 1);
    const bx = Math.min(...xs), by = Math.min(...ys), bw = Math.max(...xs) - bx, bh = Math.max(...ys) - by;
    const pad = Math.max(6, 0.15 * Math.max(bw, bh));
    let near = [bx - pad, by - pad, bw + 2 * pad, bh + 2 * pad];
    const frame = pic && pic.frame;
    const small = frame && near[2] < 0.6 * frame[2] && near[3] < 0.6 * frame[3];
    const whole = route.q.view === "all" || !small;
    if (frame) {                                    // no taller than it is wide, no flatter than 5:3, inside the picture
      const w = Math.min(frame[2], Math.max(near[2], near[3])), h = Math.min(frame[3], Math.max(near[3], 0.6 * w));
      const cx = near[0] + near[2] / 2, cy = near[1] + near[3] / 2;
      near = [Math.min(Math.max(cx - w / 2, frame[0]), frame[0] + frame[2] - w), Math.min(Math.max(cy - h / 2, frame[1]), frame[1] + frame[3] - h), w, h];
    }
    const view = frame && whole ? frame : near;
    const art = pic ? new Image() : null;
    const draw = () => {
      const W = 1200, H = Math.max(1, Math.round((W * view[3]) / view[2]));
      canvas.width = W;
      canvas.height = H;
      const c = canvas.getContext("2d"), css = getComputedStyle(document.documentElement);
      if (art && art.complete && art.naturalWidth) {
        const iw = art.naturalWidth, ih = art.naturalHeight, filters = "filter" in c;
        if (filters) c.filter = "grayscale(0.9) brightness(0.5) contrast(1.1)";
        c.drawImage(art, ((view[0] - frame[0]) / frame[2]) * iw, (1 - (view[1] + view[3] - frame[1]) / frame[3]) * ih,
          (view[2] / frame[2]) * iw, (view[3] / frame[3]) * ih, 0, 0, W, H);
        if (filters) c.filter = "none";
        else { c.fillStyle = "rgba(6, 13, 22, 0.55)"; c.fillRect(0, 0, W, H); }      // (a browser without them: a dark wash)
      }
      const at = (list, i) => [((list[i] - view[0]) / view[2]) * W, (1 - (list[i + 1] - view[1]) / view[3]) * H];
      const layers = [["deaths", spots.d, css.getPropertyValue("--death").trim() || "#6cb8ff"],
        ["kills", spots.k, css.getPropertyValue("--kill").trim() || "#f2b84b"]].filter((x) => show === "both" || show === x[0]);
      c.globalCompositeOperation = "lighter";
      for (const [, list, color] of layers) {
        for (let i = 0; i < list.length; i += 2) {
          const [x, y] = at(list, i), glow = c.createRadialGradient(x, y, 0, x, y, 44);
          glow.addColorStop(0, color + "70");
          glow.addColorStop(1, color + "00");
          c.fillStyle = glow;
          c.fillRect(x - 44, y - 44, 88, 88);
        }
      }
      c.globalCompositeOperation = "source-over";
      c.lineWidth = 3.5;
      c.lineCap = "round";
      for (const [kind, list, color] of layers) {
        c.fillStyle = c.strokeStyle = color;
        for (let i = 0; i < list.length; i += 2) {
          const [x, y] = at(list, i);
          c.beginPath();
          if (kind === "kills") c.arc(x, y, 7, 0, 2 * Math.PI);
          else { c.moveTo(x - 7, y - 7); c.lineTo(x + 7, y + 7); c.moveTo(x + 7, y - 7); c.lineTo(x - 7, y + 7); }
          if (kind === "kills") c.fill(); else c.stroke();
        }
      }
    };
    draw();
    if (art) { art.onload = draw; art.src = pic.img; }
    const figure = el("div", { class: "heat" }, canvas);
    const viewLink = small && el("p", null, el("a", { class: "more", href: link({ view: whole ? null : "all" }) },
      whole ? "Zoom in on where the fights were" : "Show the whole map"));
    return [banner(p), mapTabs,
      panel(mapName(id), el("div", { class: "body" }, figure, viewLink,
        el("ul", { class: "key" },
          el("li", null, el("span", { class: "sw kill" }), int(nk) + (nk === 1 ? " kill" : " kills") + ": a dot where " + p.name + " stood"),
          el("li", null, el("span", { class: "sw death" }), int(nd) + (nd === 1 ? " death" : " deaths") + ": a cross where it died")),
        el("p", { class: "note" }, killNote(g, bucket(p)) + (pic ? "" : " This PC has no top-down picture of this map, so the spots are plotted on their own."))),
        showTabs)];
  }

  function profile(p) {
    const s = (p.g[D.default_game] && p.g[D.default_game].cats.all) || ZERO;
    const w = D.credits;
    const earn = [["Games", s.games, w.game], ["Wins", s.wins, w.win], ["Kills", s.kills, w.kill], ["Assists", s.assists, w.assist], ["Medals", s.medals, w.medal]];
    const looks = p.looks;
    return [banner(p), el("div", { class: "grid" },
      panel("Profile", el("dl", { class: "stats" },
        el("dt", null, "Name"), el("dd", null, p.name),
        el("dt", null, "Clan tag"), el("dd", null, p.clan || "-"),
        el("dt", null, "Listed as"), el("dd", null, p.person ? "Player" : p.roster ? "Roster" : "Matchmaking pool"),
        el("dt", null, "Home state"), el("dd", null, STATES[p.state]
          ? el("a", { href: href(["states"], { area: p.state }) }, stateName(p.state) + " (" + areaName(regionOf(p)) + ")") : "-"),
        p.person ? null : [el("dt", null, "Difficulty"), el("dd", null, p.difficulty ? title(p.difficulty) : "Not saved")],
        el("dt", null, "Species (Reach)"), el("dd", null, looks ? looks.species : "-"))),
      panel("Armor (Reach)", looks && looks.pieces.length
        ? el("dl", { class: "stats" }, looks.pieces.map(([k, v]) => [el("dt", null, k), el("dd", null, v)]))
        : empty("No Reach look on file", "No line in the mod's looks file yet."))),
      panel("How the rank is earned", el("div", null,
        table("Credits (cR) come from counted " + gameName.get(D.default_game) + " matches" + (D.commendations && D.commendations.credits ? " and the commendation tiers they earn" : " only") + ", so the rank can always be rebuilt from the record.",
          [["Earned for", "l"], ["Count"], ["cR each"], ["cR"]],
          earn.map(([k, n, each]) => el("tr", null, td(k, "l"), td(int(n)), td(int(each)), td(int(n * each))))
            .concat(D.commendations && D.commendations.credits ? el("tr", null, td(el("a", { href: href(["p", p.name, "commendations"]) }, "Commendation tiers"), "l"),
              td(int((D.commendations.list || []).reduce((a, c) => a + commState(p, c).tier, 0))), td("varies"), td(int(p.comm_cr || 0))) : [])
            .concat(el("tr", null, el("th", { scope: "row", class: "l" }, "Total"), td(""), td(""), td(int(p.cr)))), { fit: true })))];
  }

  // where this bot places on every board it is on: in its state, its region and nationwide
  function placements(p) {
    const areas = [[p.state, stateName(p.state)], [regionOf(p), areaName(regionOf(p))], ["", "Nationwide"]];
    const g = side(p);
    const place = (b, a) => {
      const rows = standings(b, a), mine = rows.find((r) => r.p === p);
      return mine ? { place: mine.place, of: rows.length } : null;
    };
    const cell = (b, a, cls) => {
      const x = place(b, a);
      return td(x ? el("a", { href: boardHref(b, a), class: x.place === 1 ? "first" : null }, "#" + x.place, el("small", null, " of " + x.of)) : "-", cls);
    };
    const section = (heading, boards, none) => {
      const on = boards.filter((b) => b.value(p) != null);
      return panel(heading, on.length
        ? table(null, [[heading === "Modes" ? "Mode" : heading === "Weapons" ? "Weapon" : heading === "Vehicles" ? "Vehicle" : "Board", "l"], [on[0].unit],
          [areas[0][1]], [areas[1][1], "hide-s"], ["Nationwide"]],
          on.map((b) => el("tr", null, td(el("a", { href: boardHref(b, "") }, b.label), "l"), td(int(b.value(p))),
            cell(b, areas[0][0]), cell(b, areas[1][0], "hide-s"), cell(b, ""))))
        : empty("Not on these boards yet", none));
    };
    const overall = board("overall", "all");
    const hero = el("ul", { class: "hero" }, areas.map(([a, name]) => {
      const x = place(overall, a);
      return el("li", null, el("span", { class: "v" }, x ? "#" + x.place : "-"),
        el("span", { class: "k" }, (!a ? "" : REGIONS.has(a) ? "In the " : "In ") + name + (x ? " (of " + x.of + ")" : "")));
    }).concat(el("li", null, el("span", { class: "v" }, int(overall.value(p) || 0)), el("span", { class: "k" }, "cR in " + gameName.get(game())))));
    const kills = recorded(g) ? weaponList(g).filter(([k, n]) => n[0]) : [];
    const guns = kills.filter(([k]) => !VEHICLES.has(k)).map(([k]) => board("weapon", k));
    const rides = kills.filter(([k]) => VEHICLES.has(k)).map(([k]) => board("vehicle", k));
    const noRows = recorded(g) ? null : NO_KILLS;
    return [banner(p), el("p", { class: "note" }, p.name + "'s home state is " + stateName(p.state) + ", in the " + areaName(regionOf(p)) +
      " region: picked from its name, so it never moves. Each place counts only the names of that area with a number on the board; equal numbers share a place. ",
      el("a", { href: href(["states"], { area: p.state }) }, "Open the " + stateName(p.state) + " leaderboard"), "."),
      hero,
      section("Overall", [overall], "No counted match in " + gameName.get(game()) + " yet."),
      section("Modes", D.cats.map(([k]) => board("mode", k)), "No counted match in " + gameName.get(game()) + " yet."),
      section("Weapons", guns, noRows || "No kill with a weapon recorded in " + gameName.get(game()) + " yet."),
      section("Vehicles", rides.length ? [board("vehicle", "all")].concat(rides) : [], noRows || "No kill with a vehicle recorded in " + gameName.get(game()) + " yet.")];
  }

  const missing = {
    achievements: ["Achievements", "Not recorded", "Achievements belong to MCC accounts; none are recorded here."],
  };

  function playerPage(p, page, arg) {
    switch (page) {
      case "overview": return overview(p);
      case "placements": return placements(p);
      case "history": return history(p);
      case "match": return match(p, arg);
      case "summary": return summary(p);
      case "commendations": return commendations(p);
      case "types": return breakdown(p, "By game type", "types", (k) => k, "Game type");
      case "maps": return breakdown(p, "By map", "maps", mapName, "Map");
      case "medals": return medals(p);
      case "weapons": return weapons(p);
      case "enemies": return enemies(p);
      case "heatmaps": return heatmaps(p);
      case "profile": return profile(p);
      default: {
        const m = missing[page];
        return m ? [banner(p), panel(m[0], empty(m[1], m[2]))] : null;
      }
    }
  }

  // ---------------------------------------------------------------- draw
  function drawNav(p, page) {
    if (!p) { nav.replaceChildren(); card.replaceChildren(); card.hidden = true; shell.classList.add("wide"); return; }
    shell.classList.remove("wide");
    card.hidden = false;
    card.replaceChildren(...recordCard(p));
    const on = page === "match" ? "history" : page;
    nav.replaceChildren(el("a", { class: "back", href: href([]) }, icon("back", 16), "Leaderboard"),
      ...PAGES.map(([group, items]) => el("section", null, el("h2", null, group),
        el("ul", null, items.map(([k, label]) => el("li", null,
          el("a", { href: href(["p", p.name, k]), "aria-current": k === on ? "page" : null }, neon(k, 22), el("span", null, label))))))));
    const cur = nav.querySelector("[aria-current]");            // (the phone layout's strip: keep the open page in view)
    if (cur && nav.scrollWidth > nav.clientWidth) nav.scrollLeft = cur.offsetLeft - (nav.clientWidth - cur.offsetWidth) / 2;
  }
  let first = true;
  function render() {
    route = parse();
    gamePick.value = game();
    const [kind, name, page, arg] = route.parts;
    let nodes = null, label = "Bot Tracker", p = null;
    if (!kind) nodes = leaderboard();
    else if (kind === "states" && !name) { nodes = statesPage(); label = "State leaderboards"; }
    else if (kind === "ranks" && !name) { nodes = ranksPage(); label = "Ranks"; }
    else if (kind === "clans" && !name) { nodes = clansPage(); label = "Clans"; }
    else if (kind === "clans" && clanList().some((c) => c.key === name)) { nodes = clanPage(name); label = "Clan " + clanList().find((c) => c.key === name).title; }
    else if (kind === "p" && players.has(name)) {
      p = players.get(name);
      nodes = playerPage(p, page || "overview", arg);
      const found = PAGES.flatMap((x) => x[1]).find((x) => x[0] === (page || "overview"));
      label = (found ? found[1] : page === "match" ? "Carnage Report" : "Page") + " - " + p.name;
    }
    if (!nodes) {
      p = null;
      label = "Page not found";
      nodes = [el("h1", null, "Page not found"), el("p", { class: "note" }, "There is no page at this address. ",
        el("a", { href: href([]) }, "Go to the leaderboard"), ".")];
    }
    drawNav(p, page || "overview");
    document.body.classList.toggle("landing", !p && !!bgVideo);
    document.body.classList.toggle("record-page", !!p);         // (its own backdrop, when the owner's player.jpg is here)
    main.replaceChildren(...nodes.flat(Infinity).filter(Boolean));
    document.title = label + " | " + D.site;
    if (!first) { main.focus({ preventScroll: true }); window.scrollTo(0, 0); }
    const pick = route.q.badge && document.getElementById("badge-" + route.q.badge);   // (a badge on the player card: its card)
    if (pick) {
      setTimeout(() => pick.scrollIntoView({ block: "center", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }));
      pick.classList.add("flash");
    }
    first = false;
  }

  // The landing pages' background (the leaderboards and Ranks): MCC's Noble main-menu movie, muted and looping, its
  // still while it loads. It plays even when the system asks for less motion (the owner asked for the movie, and this
  // PC has Windows' animations off); a button in the corner pauses it, and the page remembers. render shows it on
  // those pages only.
  let videoPaused = false;
  try { videoPaused = localStorage.getItem("sr-video") === "paused"; } catch (e) { /* (storage off: it plays) */ }
  const bgVideo = (() => {
    const v = D.video || {};
    if (!v["noble.mp4"] && !v["noble.png"]) return null;
    const box = el("div", { class: "bgvideo", "aria-hidden": "true" },
      v["noble.mp4"]
        ? el("video", { src: v["noble.mp4"], poster: v["noble.png"] || null, autoplay: !videoPaused, muted: true, loop: true, playsinline: true, preload: "auto" })
        : el("img", { src: v["noble.png"], alt: "" }));
    document.body.prepend(box);
    const vid = box.querySelector("video");
    if (!vid) return box;
    vid.muted = true;
    const btn = el("button", { type: "button", class: "video-btn" });
    const show = () => { btn.textContent = videoPaused ? "▶ Play background" : "❚❚ Pause background"; btn.setAttribute("aria-pressed", String(videoPaused)); };
    btn.addEventListener("click", () => {
      videoPaused = !videoPaused;
      try { localStorage.setItem("sr-video", videoPaused ? "paused" : "playing"); } catch (e) { /* (not kept) */ }
      if (videoPaused) vid.pause(); else vid.play().catch(() => {});
      show();
    });
    show();
    document.body.append(btn);
    if (!videoPaused) vid.play().catch(() => {});
    return box;
  })();

  // the owner's header and sidebar pictures, when this PC has them (style.css falls back to backdrop.svg)
  for (const [file, prop] of [["header.jpg", "--header-art"], ["sidebar.jpg", "--side-art"], ["player.jpg", "--player-art"]]) {
    const src = D.backdrops && D.backdrops[file];
    if (src) document.documentElement.style.setProperty(prop, 'url("' + src + '")');
  }
  gamePick.replaceChildren(...D.games.map(([k, label]) => el("option", { value: k }, label)));
  gamePick.addEventListener("change", () => {
    const q = Object.assign({}, route.q, { game: gamePick.value === D.default_game ? null : gamePick.value });
    delete q.cat;
    route.q.game = null;
    location.hash = href(route.parts, q);
  });
  document.getElementById("built").textContent = "Built " + D.built + ". Rebuilds when a recorded match ends and when one starts.";
  window.addEventListener("hashchange", render);
  render();

  // hover notes on chart marks (the legends and tables carry the same numbers)
  const tip = document.getElementById("tip");
  document.addEventListener("mousemove", (e) => {
    const t = e.target.closest && e.target.closest("[data-tip]");
    if (!t) { tip.hidden = true; return; }
    tip.textContent = t.getAttribute("data-tip");
    tip.hidden = false;
    tip.style.left = Math.min(e.clientX + 12, window.innerWidth - tip.offsetWidth - 8) + "px";
    tip.style.top = Math.max(8, e.clientY - tip.offsetHeight - 10) + "px";
  });

  // a new build (stamp.js says so): show it. Works from the folder, where a page may not fetch files.
  window.SR_STAMP = (stamp) => { if (stamp !== D.stamp) location.reload(); };
  setInterval(() => {
    if (document.hidden) return;
    const s = document.createElement("script");
    s.src = "stamp.js?" + Date.now();
    s.onload = s.onerror = () => s.remove();
    document.head.append(s);
  }, 30000);
})();
