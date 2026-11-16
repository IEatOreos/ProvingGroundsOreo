/* Proving Grounds Service Record: the pages (tools/service_record.py copies this into the built site).
   Everything shown comes from window.SR_DATA (data.js); every number in it was summed by the build, this file only
   lays it out. Text always goes in as text, never as HTML. */
(function () {
  "use strict";
  const D = window.SR_DATA;
  const main = document.getElementById("main");
  const nav = document.getElementById("nav");
  const shell = document.querySelector(".shell");
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
    ["Service Record", [["overview", "Overview"], ["history", "Game History"], ["commendations", "Commendations"],
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
    "Nothing has been recorded here for " + gameName.get(game()) + ". This fills in after the bot's next match: " +
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
  function rankBlock(p) {
    const cur = D.ranks[p.rank], next = D.ranks[p.rank + 1];
    return el("div", { class: "rank" }, insignia(p.rank),
      el("div", { class: "name" }, cur[0]),
      next
        ? el("progress", { max: next[1] - cur[1], value: p.cr - cur[1], "aria-label": "Progress to " + next[0] })
        : el("progress", { max: 1, value: 1, "aria-label": "Highest rank reached" }),
      el("div", { class: "next" }, next
        ? "Next: " + next[0] + " (" + int(p.cr) + " of " + int(next[1]) + " cR)"
        : "Highest rank reached (" + int(p.cr) + " cR)"));
  }
  function banner(p) {
    const chips = [p.roster ? "Roster bot" : "Matchmaking pool bot",
      p.difficulty && "Difficulty: " + title(p.difficulty), p.style && "Play style: " + title(p.style)].filter(Boolean);
    return el("div", { class: "banner" }, emblem(p),
      el("div", { class: "who" }, el("h1", null, p.name), p.clan && el("div", { class: "tag" }, "Clan tag: " + p.clan),
        el("ul", { class: "chips" }, chips.map((c) => el("li", null, c)))),
      rankBlock(p));
  }

  function table(caption, heads, rows, opts) {
    const o = opts || {};
    return el("div", { class: "scroll" }, el("table", null, caption && el("caption", null, caption),
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
  // one thin bar per run of wins, oldest on the left; the longest is labelled
  function streakBars(runs) {
    const step = 16, w = 8, H = 120, base = 100, top = 16;
    const max = Math.max(...runs), width = Math.max(runs.length * step + 8, 160);
    let labelled = false;
    const marks = runs.map((n, i) => {
      const x = 8 + i * step, hgt = Math.max(4, ((base - top) * n) / max), y = base - hgt, r = Math.min(4, hgt);
      const bar = svg("path", { class: "b", d: `M${x} ${base}V${y + r}a${r} ${r} 0 0 1 ${r} ${-r}h${w - 2 * r}a${r} ${r} 0 0 1 ${r} ${r}V${base}z`,
        fill: "var(--bar)", "data-tip": n + (n === 1 ? " win" : " wins") + " in a row" });
      const lab = n === max && !labelled ? svg("text", { x: x + w / 2, y: y - 4, "text-anchor": "middle" }, n) : null;
      labelled = labelled || n === max;
      return [bar, lab];
    });
    return svg("svg", { class: "vbars", viewBox: `0 0 ${width} ${H}`, preserveAspectRatio: "xMinYMid meet", role: "img",
      "aria-label": "Runs of wins, oldest first: " + runs.join(", ") },
      svg("line", { x1: 0, x2: width, y1: base + 0.5, y2: base + 0.5 }), marks,
      svg("text", { x: 8, y: H - 4 }, "Oldest"), svg("text", { x: width - 4, y: H - 4, "text-anchor": "end" }, "Newest"));
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
        return el("tr", null, td(i + 1),
          td(el("span", { class: "cell" }, emblem(p, true), el("a", { href: href(["p", p.name, "overview"]) }, p.name),
            p.clan && el("span", { class: "tag hide-s" }, p.clan)), "l"),
          td(el("span", { class: "cell" }, insignia(p.rank, true), D.ranks[p.rank][0]), "l hide-s"),
          td(int(s.games)), td(int(s.wins), "hide-s"), td(int(s.kills)), td(int(s.deaths)), td(int(s.assists), "hide-s"), td(dec(s.r.kd)));
      }) : [el("tr", null, el("td", { class: "l", colspan: 9 }, "No bot matches “" + find + "”."))]));
      count.textContent = rows.length + " of " + D.players.length + " bots";
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
      el("h1", null, "Leaderboard"),
      el("p", { class: "note" }, played
        ? int(played) + " of " + int(D.players.length) + " bots have a counted match in " + gameName.get(game()) + ". Choose a bot to open its Service Record."
        : "No bot has a counted match in " + gameName.get(game()) + " yet. Every bot starts at 0; the numbers fill in after the next match."),
      panel("Bots", el("div", { class: "scroll" }, el("table", null,
        el("thead", null, el("tr", null, el("th", { scope: "col" }, "#"), head("name", "Bot", "l"), head("rank", "Rank", "l hide-s"),
          head("games", "Games"), head("wins", "Wins", "hide-s"), head("kills", "Kills"), head("deaths", "Deaths"),
          head("assists", "Assists", "hide-s"), head("kd", "K/D"))), body)),
        el("div", { class: "toolbar" }, count,
          el("label", null, "Find a bot", el("input", { type: "search", value: find, autocomplete: "off",
            oninput: (e) => { find = e.target.value; draw(); } })))),
    ];
  }

  // ---------------------------------------------------------------- a bot's pages
  function overview(p) {
    const g = side(p), s = bucket(p);
    const looks = p.looks;
    const armor = panel("Armor", looks && looks.pieces.length
      ? el("dl", { class: "stats" }, el("dt", null, "Species"), el("dd", null, looks.species),
        looks.pieces.map(([k, v]) => [el("dt", null, k), el("dd", null, v)]))
      : empty("No Reach look on file", "This bot has no line in the mod's looks file yet (it is written when the bot is rolled)."));
    const facts = panel("Service Record", el("dl", { class: "stats" },
      el("dt", null, "Last played"), el("dd", null, g ? day(g.last) : "-"),
      el("dt", null, "Games played"), el("dd", null, int(s.games)),
      el("dt", null, "Wins"), el("dd", null, int(s.wins), s.r.win != null && el("small", null, dec(s.r.win) + "%")),
      el("dt", null, "Kills"), el("dd", null, int(s.kills), el("small", null, "K/D " + dec(s.r.kd))),
      el("dt", null, "Deaths"), el("dd", null, int(s.deaths)),
      el("dt", null, "Assists"), el("dd", null, int(s.assists)),
      el("dt", null, "Medals"), el("dd", null, int(s.medals)),
      el("dt", null, "Betrayals"), el("dd", null, int(s.betrayals)),
      el("dt", null, "Most kills in a row"), el("dd", null, int(s.spree)),
      el("dt", null, "Playing since"), el("dd", null, g ? day(g.first) : "-")),
      el("a", { class: "more", href: href(["p", p.name, "summary"]) }, "Career stats"));
    const runs = g ? g.streak.runs : [];
    return [banner(p), el("div", { class: "grid" }, armor, facts),
      el("div", { class: "grid" },
        panel("Games played", el("div", { class: "body" }, ring(g ? g.cats : {}))),
        panel("Kills by type", s.detailed ? el("div", { class: "body" }, hbars(killTypes(s)), reportNote(s))
          : empty("Nothing recorded yet", "Weapon, grenade and melee kills come from MCC's post-game report.")),
        panel("Victory streaks", runs.length
          ? el("div", { class: "body" }, streakBars(runs), el("p", { class: "note" }, "Best: " + g.streak.best + " in a row. Current: " + g.streak.current + "."))
          : empty("No wins yet", "Each run of wins in a row shows here as a bar.")))];
  }

  function history(p) {
    const g = side(p);
    const list = g ? g.matches.map((i) => D.matches[i]) : [];
    const rows = list.map((m) => {
      const me = m.rows.find((r) => r.n === p.name) || {};
      return el("tr", null,
        td(el("a", { href: href(["p", p.name, "match", m.id]) }, m.when), "l"),
        td(mapName(m.map), "l"), td(m.type || "Unknown", "l"),
        td(me.won ? el("span", { class: "won" }, "Won") : "-", "l hide-s"),
        td(ordinal((me.st || 0) + 1)), td(int(me.k)), td(int(me.d)), td(int(me.a)));
    });
    return [banner(p), panel("Game history",
      table(list.length ? int(list.length) + (list.length === 1 ? " match" : " matches") + ", newest first. Open a date for the full scoreboard." : null,
        [["Date", "l"], ["Map", "l"], ["Game type", "l"], ["Result", "l hide-s"], ["Place"], ["Kills"], ["Deaths"], ["Assists"]], rows,
        { none: "No counted matches yet for " + gameName.get(game()) + "." }))];
  }

  function match(p, id) {
    const m = D.matches.find((x) => x.id === id);
    if (!m) return [banner(p), panel("Match", empty("Match not found", "This match is not in the record (it may be from before the bots' stats were reset)."))];
    const full = m.report;
    const heads = [["Place"], ["Player", "l"]].concat(full ? [["Score"]] : [], [["Kills"], ["Deaths"], ["Assists"]],
      full ? [["Betrayals", "hide-s"], ["Medals", "hide-s"]] : [], [["Time", "hide-s"]]);
    const line = (r) => el("tr", null, td(ordinal(r.st + 1)),
      td(el("span", { class: "cell" }, r.listed && players.has(r.n) ? el("a", { href: href(["p", r.n, "overview"]) }, r.n) : r.n,
        r.n === p.name && el("span", { class: "tag" }, "this bot"), !r.bot && el("span", { class: "tag" }, "player")), "l"),
      full ? td(int(r.score)) : null, td(int(r.k)), td(int(r.d)), td(int(r.a)),
      full ? [td(int(r.bt), "hide-s"), td(int(r.md), "hide-s")] : null,
      td(Math.floor(r.sec / 60) + ":" + String(r.sec % 60).padStart(2, "0"), "hide-s"));
    let rows;
    if (m.teams) {
      const teams = [...new Set(m.rows.map((r) => r.team))];
      rows = teams.map((t) => {
        const mine = m.rows.filter((r) => r.team === t);
        const sum = (k) => mine.reduce((n, r) => n + (r[k] || 0), 0);
        return [el("tr", { class: "team" }, el("th", { scope: "colgroup", colspan: heads.length },
          "Team " + (t + 1) + (mine[0].won ? " (won)" : "") + ": " + int(sum("k")) + " kills, " + int(sum("d")) + " deaths")), mine.map(line)];
      });
    } else rows = m.rows.map(line);
    return [banner(p), el("p", null, el("a", { class: "more", href: href(["p", p.name, "history"]) }, "Back to game history")),
      panel(mapName(m.map) + ": " + (m.type || "Unknown game type"),
        el("div", null, table(m.when + ", " + (gameName.get(m.game) || m.game) + (full ? "" : ". MCC's full report for this match was not kept, so only kills, deaths and assists remain."),
          heads, rows.flat(Infinity))))];
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
      panel("Top weapons", el("div", { class: "body" },
        el("p", { class: "note" }, "Kills and deaths per weapon are not recorded yet: MCC's report only splits a bot's kills by type."),
        bucket(p).detailed ? hbars(killTypes(bucket(p))) : null),
        el("a", { class: "more", href: href(["p", p.name, "weapons"]) }, "View weapons"))];
  }

  function breakdown(p, heading, group, label, first) {
    const g = side(p);
    const rows = Object.entries((g && g[group]) || {}).sort((a, b) => b[1].games - a[1].games || label(a[0]).localeCompare(label(b[0])))
      .map(([k, s]) => el("tr", null, td(label(k), "l wrap"), td(int(s.games)), td(int(s.wins)), td(int(s.kills)), td(int(s.deaths)),
        td(int(s.assists), "hide-s"), td(dec(s.r.kd)), td(dec(s.r.kpg), "hide-s"), td(s.r.playtime, "hide-s")));
    return [banner(p), panel(heading, table(null,
      [[first, "l"], ["Games"], ["Wins"], ["Kills"], ["Deaths"], ["Assists", "hide-s"], ["K/D"], ["Kills/Game", "hide-s"], ["Playtime", "hide-s"]],
      rows, { none: "No counted matches yet for " + gameName.get(game()) + "." }))];
  }

  function medals(p) {
    const list = medalList(side(p));
    return [banner(p), panel("Medals", list.length
      ? el("div", { class: "body" }, el("ul", { class: "medals" }, list.map(([id, n]) => medalTile(id, n))))
      : empty("No medals yet", "Medals come from MCC's post-game report of each counted match."),
      list.length ? el("span", { class: "note" }, int(bucket(p).medals) + " in all") : null),
      !D.medal_art && list.length ? el("p", { class: "note" },
        "Medals show by MCC's number because their names and icons have not been read from this PC's MCC yet: " +
        "python\\python.exe -I tools\\service_record_art.py medals") : null];
  }

  function weapons(p) {
    const s = bucket(p);
    const rows = s.detailed ? killTypes(s).map(([label, n]) => el("tr", null, td(label, "l"), td(int(n)),
      td(s.kills ? Math.round((100 * n) / s.kills) + "%" : "-"))) : [];
    return [banner(p),
      panel("Weapons", empty("Not recorded yet", "Kills and deaths per weapon need a record of every kill (killer, victim, weapon), " +
        "which the mod does not write yet. MCC's own report only splits kills by type, below.")),
      panel("Kills by type", el("div", null, table(null, [["Type", "l"], ["Kills"], ["Share of kills"]], rows,
        { none: "No report recorded yet for " + gameName.get(game()) + "." }), reportNote(s) && el("div", { class: "body" }, reportNote(s))))];
  }

  function enemies(p) {
    const g = side(p);
    const list = (obj, what) => table(null, [["Opponent", "l"], ["Matches as " + what], ["Kills in those matches"]],
      Object.entries(obj || {}).sort((a, b) => b[1][1] - a[1][1] || a[0].localeCompare(b[0])).map(([n, v]) =>
        el("tr", null, td(players.has(n) ? el("a", { href: href(["p", n, "overview"]) }, n) : n, "l wrap"), td(int(v[0])), td(int(v[1])))),
      { none: "No report recorded yet for " + gameName.get(game()) + "." });
    return [banner(p),
      panel("Enemies", empty("Full versus table not recorded yet", "MCC's report names only two rivals per match: who this bot killed most " +
        "and who killed it most. A table of every opponent needs a record of every kill, which the mod does not write yet.")),
      el("div", { class: "grid" }, panel("Killed most", list(g && g.killed, "top victim")),
        panel("Killed most by", list(g && g.killed_by, "top killer")))];
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
        el("dt", null, "Listed as"), el("dd", null, p.roster ? "Roster bot" : "Matchmaking pool bot"),
        el("dt", null, "Difficulty"), el("dd", null, p.difficulty ? title(p.difficulty) : "Not saved"),
        el("dt", null, "Play style"), el("dd", null, p.style ? title(p.style) : "Not saved"),
        el("dt", null, "Species (Reach)"), el("dd", null, looks ? looks.species : "-"))),
      panel("Armor (Reach)", looks && looks.pieces.length
        ? el("dl", { class: "stats" }, looks.pieces.map(([k, v]) => [el("dt", null, k), el("dd", null, v)]))
        : empty("No Reach look on file", "This bot has no line in the mod's looks file yet."))),
      panel("How the rank is earned", el("div", null,
        table("Credits (cR) come from this bot's counted " + gameName.get(D.default_game) + " matches only, so the rank can always be rebuilt from the record.",
          [["Earned for", "l"], ["Count"], ["cR each"], ["cR"]],
          earn.map(([k, n, each]) => el("tr", null, td(k, "l"), td(int(n)), td(int(each)), td(int(n * each))))
            .concat(el("tr", null, el("th", { scope: "row", class: "l" }, "Total"), td(""), td(""), td(int(p.cr)))))))];
  }

  const missing = {
    commendations: ["Commendations", "Not recorded", "MCC's post-game report does not include commendations, so there is nothing to total here. Medals are recorded: see Career Stats, Medals."],
    heatmaps: ["Heatmaps", "Not recorded yet", "A heatmap needs the position of every kill and death. The mod does not write a record of each kill to the match trace yet."],
    achievements: ["Achievements", "Not recorded", "Achievements belong to MCC accounts, and the bots have none. Nothing is recorded for them."],
  };

  function playerPage(p, page, arg) {
    switch (page) {
      case "overview": return overview(p);
      case "history": return history(p);
      case "match": return match(p, arg);
      case "summary": return summary(p);
      case "types": return breakdown(p, "By game type", "types", (k) => k, "Game type");
      case "maps": return breakdown(p, "By map", "maps", mapName, "Map");
      case "medals": return medals(p);
      case "weapons": return weapons(p);
      case "enemies": return enemies(p);
      case "profile": return profile(p);
      default: {
        const m = missing[page];
        return m ? [banner(p), panel(m[0], empty(m[1], m[2]))] : null;
      }
    }
  }

  // ---------------------------------------------------------------- draw
  function drawNav(p, page) {
    if (!p) { nav.replaceChildren(); shell.classList.add("wide"); return; }
    shell.classList.remove("wide");
    const on = page === "match" ? "history" : page;
    nav.replaceChildren(el("a", { class: "back", href: href([]) }, "All bots"),
      ...PAGES.map(([group, items]) => el("section", null, el("h2", null, group),
        el("ul", null, items.map(([k, label]) => el("li", null,
          el("a", { href: href(["p", p.name, k]), "aria-current": k === on ? "page" : null }, label)))))));
    const cur = nav.querySelector("[aria-current]");            // (the phone layout's strip: keep the open page in view)
    if (cur && nav.scrollWidth > nav.clientWidth) nav.scrollLeft = cur.offsetLeft - (nav.clientWidth - cur.offsetWidth) / 2;
  }
  let first = true;
  function render() {
    route = parse();
    gamePick.value = game();
    const [kind, name, page, arg] = route.parts;
    let nodes = null, label = "Leaderboard", p = null;
    if (!kind) nodes = leaderboard();
    else if (kind === "p" && players.has(name)) {
      p = players.get(name);
      nodes = playerPage(p, page || "overview", arg);
      const found = PAGES.flatMap((x) => x[1]).find((x) => x[0] === (page || "overview"));
      label = (found ? found[1] : page === "match" ? "Match" : "Page") + " - " + p.name;
    }
    if (!nodes) {
      p = null;
      label = "Page not found";
      nodes = [el("h1", null, "Page not found"), el("p", { class: "note" }, "There is no page at this address. ",
        el("a", { href: href([]) }, "Go to the leaderboard"), ".")];
    }
    drawNav(p, page || "overview");
    main.replaceChildren(...nodes.flat(Infinity).filter(Boolean));
    document.title = label + " | " + D.site;
    if (!first) { main.focus({ preventScroll: true }); window.scrollTo(0, 0); }
    first = false;
  }

  gamePick.replaceChildren(...D.games.map(([k, label]) => el("option", { value: k }, label)));
  gamePick.addEventListener("change", () => {
    const q = Object.assign({}, route.q, { game: gamePick.value === D.default_game ? null : gamePick.value });
    delete q.cat;
    route.q.game = null;
    location.hash = href(route.parts, q);
  });
  document.getElementById("built").textContent = "Built " + D.built + ". Rebuilds when a match starts.";
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
