// Hosted no-install example. Data from data.js (synthetic); scoring from score.js.
(function () {
  "use strict";
  var D = window.ATO_DATA, S = window.AtoScore, KEYS = Object.keys(D.rules);
  var defaults = Object.assign({}, D.weights), weights = Object.assign({}, D.weights);
  var threshold = D.threshold, scored = [], selected = null, ruleFilter = {}, onlyAlerts = true;

  function el(tag, attrs, text) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }
  function svgEl(tag, attrs) {
    var n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    return n;
  }
  function pct(x) { return x === null ? "n/a" : Math.round(x * 100) + "%"; }

  function kpiRow(target, items) {
    target.textContent = "";
    items.forEach(function (p) {
      var c = el("div", { class: "kpi" }); c.appendChild(el("span", {}, p[0])); c.appendChild(el("strong", {}, p[1]));
      target.appendChild(c);
    });
  }

  function table(t, rows, cols) {
    t.textContent = "";
    var tr = el("tr");
    cols.forEach(function (c) { tr.appendChild(el("th", c.num ? { class: "num", scope: "col" } : { scope: "col" }, c.label)); });
    var thead = el("thead"); thead.appendChild(tr); t.appendChild(thead);
    var tb = el("tbody");
    rows.forEach(function (r) {
      var row = el("tr");
      cols.forEach(function (c) {
        var td = el("td", c.num ? { class: "num" } : {});
        if (c.render) c.render(td, r[c.key], r); else td.textContent = r[c.key] === null ? "" : r[c.key];
        row.appendChild(td);
      });
      tb.appendChild(row);
    });
    t.appendChild(tb);
    return tb;
  }

  function hbars(target, rows, desc) {
    target.textContent = "";
    var W = 560, rowH = 26, P = { l: 170, r: 40 }, H = rows.length * rowH + 10;
    var max = Math.max.apply(null, rows.map(function (r) { return r.value; }).concat([1]));
    var s = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": desc });
    rows.forEach(function (r, i) {
      var y = 5 + i * rowH, w = (W - P.l - P.r) * r.value / max;
      var lb = svgEl("text", { x: P.l - 8, y: y + 16, "text-anchor": "end" }); lb.textContent = r.label; s.appendChild(lb);
      s.appendChild(svgEl("rect", { x: P.l, y: y + 4, width: Math.max(w, 1), height: rowH - 10, fill: "var(--c1)", rx: 2 }));
      var v = svgEl("text", { x: P.l + w + 6, y: y + 16 }); v.textContent = r.value; s.appendChild(v);
    });
    target.appendChild(s);
  }

  // Two-line chart: x = threshold, y in [0, 1].
  function lines(target, xs, series, desc) {
    target.textContent = "";
    var W = 560, H = 220, P = { l: 40, r: 90, t: 10, b: 30 };
    var s = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": desc });
    var x = function (v) { return P.l + (W - P.l - P.r) * (v - xs[0]) / (xs[xs.length - 1] - xs[0]); };
    var y = function (v) { return P.t + (H - P.t - P.b) * (1 - v); };
    [0, 0.5, 1].forEach(function (g) {
      s.appendChild(svgEl("line", { x1: P.l, x2: W - P.r, y1: y(g), y2: y(g), stroke: "var(--border)" }));
      var t = svgEl("text", { x: P.l - 6, y: y(g) + 4, "text-anchor": "end" }); t.textContent = pct(g); s.appendChild(t);
    });
    [xs[0], 50, 100, xs[xs.length - 1]].forEach(function (v) {
      var t = svgEl("text", { x: x(v), y: H - 8, "text-anchor": "middle" }); t.textContent = v; s.appendChild(t);
    });
    series.forEach(function (sr, i) {
      var d = "", started = false;
      sr.values.forEach(function (v, j) {
        if (v === null) { started = false; return; }
        d += (started ? "L" : "M") + x(xs[j]).toFixed(1) + "," + y(v).toFixed(1); started = true;
      });
      s.appendChild(svgEl("path", { d: d, fill: "none", stroke: i ? "var(--c2)" : "var(--c1)", "stroke-width": 2 }));
      var lab = svgEl("text", { x: W - P.r + 6, y: P.t + 14 + 18 * i, fill: i ? "var(--c2)" : "var(--c1)" });
      lab.textContent = sr.name; s.appendChild(lab);
    });
    target.appendChild(s);
  }

  // ---------- alert queue ----------
  var wBox = document.getElementById("weights");
  KEYS.forEach(function (k) {
    var lab = el("label", { title: D.rules[k] }, D.labels[k]);
    var inp = el("input", { type: "number", min: "0", max: "100", step: "5", value: String(weights[k]), "data-key": k });
    inp.addEventListener("input", function () { weights[k] = Math.max(0, Math.min(100, parseInt(inp.value, 10) || 0)); rescore(); });
    lab.appendChild(inp); wBox.appendChild(lab);
  });
  var thr = document.getElementById("threshold");
  thr.value = threshold;
  thr.addEventListener("input", function () { threshold = Number(thr.value); renderAlerts(); });
  document.getElementById("reset").addEventListener("click", function () {
    weights = Object.assign({}, defaults); threshold = D.threshold; thr.value = threshold;
    wBox.querySelectorAll("input").forEach(function (i) { i.value = weights[i.getAttribute("data-key")]; });
    rescore();
  });
  var rf = document.getElementById("rule-filters");
  KEYS.forEach(function (k) {
    var b = el("button", { class: "chip", type: "button", "aria-pressed": "false" }, D.labels[k]);
    b.addEventListener("click", function () { ruleFilter[k] = !ruleFilter[k]; b.setAttribute("aria-pressed", String(!!ruleFilter[k])); renderAlerts(); });
    rf.appendChild(b);
  });
  document.getElementById("only-alerts").addEventListener("change", function (e) { onlyAlerts = e.target.checked; renderAlerts(); });

  function renderAlerts() {
    document.getElementById("thr-label").textContent = threshold;
    var custom = threshold !== D.threshold || KEYS.some(function (k) { return defaults[k] !== weights[k]; });
    document.getElementById("custom-badge").hidden = !custom;
    var alerts = scored.filter(function (c) { return c.alert_score >= threshold; });
    var tp = alerts.filter(function (c) { return c.confirmed_ato; }).length;
    kpiRow(document.getElementById("kpis"), [
      ["Customers with a rule hit", String(scored.length)], ["Alerts (score " + threshold + "+)", String(alerts.length)],
      ["Alerts that are confirmed takeovers", String(tp)], ["Takeovers caught", tp + " of " + D.totalAto]]);
    var active = KEYS.filter(function (k) { return ruleFilter[k]; });
    var view = (onlyAlerts ? alerts : scored).filter(function (c) {
      return !active.length || active.some(function (k) { return c.flags[k]; });
    });
    var maxScore = KEYS.reduce(function (a, k) { return a + weights[k]; }, 0) || 1;
    var tb = table(document.getElementById("alert-table"), view, [
      { key: "alert_rank", label: "Rank", num: true }, { key: "customer_id", label: "Customer" },
      { key: "customer_name", label: "Name" }, { key: "segment", label: "Segment" }, { key: "home_city", label: "Home city" },
      { key: "rules_fired", label: "Rules", num: true }, { key: "rules", label: "Rules triggered" },
      { key: "alert_score", label: "Score", render: function (td, v) {
        var b = el("span", { class: "bar" }); b.style.width = Math.round(60 * v / maxScore) + "px";
        td.appendChild(b); td.appendChild(document.createTextNode(v)); } }]);
    Array.prototype.forEach.call(tb.rows, function (tr, i) {
      tr.tabIndex = 0; tr.className = "clickable"; tr.title = "Open case timeline";
      var open = function () { selected = view[i].customer_id; show("case"); };
      tr.addEventListener("click", open);
      tr.addEventListener("keydown", function (e) { if (e.key === "Enter") open(); });
    });
    document.getElementById("alert-note").textContent = view.length + " customers. Select a row to open the case timeline.";
    hbars(document.getElementById("chart-hits"), KEYS.map(function (k) {
      return { label: D.labels[k], value: scored.filter(function (c) { return c.flags[k]; }).length };
    }).sort(function (a, b) { return b.value - a.value; }), "Number of customers that triggered each rule");
  }

  // ---------- case ----------
  var pick = document.getElementById("case-pick");
  pick.addEventListener("change", function () { selected = pick.value; renderCase(); });

  function renderCase() {
    pick.textContent = "";
    scored.forEach(function (c) { pick.appendChild(el("option", { value: c.customer_id }, "#" + c.alert_rank + " · " + c.customer_id + " · " + c.customer_name)); });
    var c = scored.find(function (x) { return x.customer_id === selected; }) || scored[0];
    pick.value = c.customer_id; selected = c.customer_id;
    kpiRow(document.getElementById("case-kpis"), [
      ["Rank", "#" + c.alert_rank + " of " + scored.length], ["Alert score", String(c.alert_score)],
      ["Rules triggered", String(c.rules_fired)], ["Home", c.home_city + " · " + c.segment]]);
    var why = document.getElementById("case-why"); why.textContent = "";
    KEYS.forEach(function (k) {
      if (!c.flags[k]) return;
      var box = el("div", { class: "why" });
      box.appendChild(el("strong", {}, D.labels[k] + " · " + weights[k] + " points"));
      box.appendChild(el("p", { class: "sub" }, c.why[k]));
      why.appendChild(box);
    });
    document.getElementById("case-summary").textContent = c.summary;
    table(document.getElementById("case-timeline"), c.timeline.slice().reverse().map(function (t) { return { ts: t[0], type: t[1], detail: t[2], session: t[3] }; }),
      [{ key: "ts", label: "Time" }, { key: "type", label: "Event" }, { key: "detail", label: "Detail" }, { key: "session", label: "Session" }]);
  }

  // ---------- rules ----------
  function renderRules() {
    var perf = S.performance(scored, D.rules, D.labels, threshold, D.totalAto), last = perf[perf.length - 1];
    kpiRow(document.getElementById("perf-kpis"), [
      ["Confirmed takeovers in the data", String(D.totalAto)], ["Caught by alerts (score " + threshold + "+)", String(last["Confirmed takeovers"])],
      ["Alert precision", pct(last.Precision)], ["False alerts", String(last["False positives"])]]);
    table(document.getElementById("perf-table"), perf, [
      { key: "Rule", label: "Rule" }, { key: "Customers flagged", label: "Customers flagged", num: true },
      { key: "Confirmed takeovers", label: "Confirmed takeovers", num: true }, { key: "False positives", label: "False positives", num: true },
      { key: "Precision", label: "Precision", num: true, render: function (td, v) { td.textContent = pct(v); } },
      { key: "Recall", label: "Recall", num: true, render: function (td, v) { td.textContent = pct(v); } }]);
    var xs = [], p = [], r = [];
    for (var t = 10; t <= 150; t += 5) {
      var a = scored.filter(function (c) { return c.alert_score >= t; });
      var tp = a.filter(function (c) { return c.confirmed_ato; }).length;
      xs.push(t); p.push(a.length ? tp / a.length : null); r.push(tp / D.totalAto);
    }
    lines(document.getElementById("chart-pr"), xs, [{ name: "Precision", values: p }, { name: "Recall", values: r }],
      "Alert precision and recall at each threshold");
  }

  function rescore() { scored = S.score(D.customers, D.rules, D.labels, weights); renderAlerts(); }

  // ---------- navigation ----------
  function show(id) {
    document.querySelectorAll(".page").forEach(function (p) { p.hidden = p.id !== id; });
    document.querySelectorAll(".nav").forEach(function (b) {
      var on = b.getAttribute("data-page") === id;
      b.classList.toggle("active", on);
      if (on) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
    });
    if (id === "case") renderCase();
    if (id === "rules") renderRules();
    if (id === "alerts") renderAlerts();
    if (location.hash !== "#" + id) history.replaceState(null, "", "#" + id);
    window.scrollTo(0, 0);
  }
  document.querySelectorAll(".nav").forEach(function (b) { b.addEventListener("click", function () { show(b.getAttribute("data-page")); }); });
  document.querySelectorAll("[data-window]").forEach(function (n) { n.textContent = D.window; });

  scored = S.score(D.customers, D.rules, D.labels, weights);
  var start = location.hash.slice(1);
  show(["alerts", "case", "rules"].indexOf(start) >= 0 ? start : "alerts");
})();
