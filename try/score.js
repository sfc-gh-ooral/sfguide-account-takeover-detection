// Scoring for the hosted example. Mirrors score() and rule_performance() in app/detection.py.
(function (root) {
  "use strict";

  function score(customers, rules, labels, w) {
    var keys = Object.keys(rules);
    var out = customers.map(function (c) {
      var s = 0, n = 0;
      keys.forEach(function (k) { if (c.flags[k]) { s += w[k]; n += 1; } });
      var o = Object.assign({}, c);
      o.alert_score = s; o.rules_fired = n;
      o.rules = keys.filter(function (k) { return c.flags[k]; }).map(function (k) { return labels[k]; }).join(", ");
      return o;
    });
    out.sort(function (a, b) {
      return (b.alert_score - a.alert_score) || (b.rules_fired - a.rules_fired) ||
        (a.customer_id < b.customer_id ? -1 : a.customer_id > b.customer_id ? 1 : 0);
    });
    out.forEach(function (c, i) { c.alert_rank = i + 1; });
    return out;
  }

  // Python round(x, 2): values here are never exact halves at 3 decimals, so standard rounding matches.
  function r2(x) { return Math.round(x * 100) / 100; }

  function row(name, hit, totalAto) {
    var tp = hit.filter(function (c) { return c.confirmed_ato; }).length;
    return { "Rule": name, "Customers flagged": hit.length, "Confirmed takeovers": tp, "False positives": hit.length - tp,
             "Precision": hit.length ? r2(tp / hit.length) : null, "Recall": totalAto ? r2(tp / totalAto) : null };
  }

  function performance(scored, rules, labels, threshold, totalAto) {
    var rows = Object.keys(rules).map(function (k) {
      return row(labels[k], scored.filter(function (c) { return c.flags[k]; }), totalAto);
    });
    rows.push(row("Alerts (score >= " + threshold + ")", scored.filter(function (c) { return c.alert_score >= threshold; }), totalAto));
    return rows;
  }

  var api = { score: score, performance: performance };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.AtoScore = api;
})(this);
