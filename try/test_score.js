// Parity test: browser scoring must match the Python app exactly.
//   python try/build_data.py && node try/test_score.js
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ctx = { window: {} };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, "data.js"), "utf8"), ctx);
const D = ctx.window.ATO_DATA;
const S = require("./score.js");

let failures = 0;
function check(name, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  console.log((ok ? "ok   " : "FAIL ") + name);
  if (!ok) { failures++; console.log("  got ", JSON.stringify(got)); console.log("  want", JSON.stringify(want)); }
}

const scored = S.score(D.customers, D.rules, D.labels, D.weights);
check("alert order (" + scored.length + " customers)", scored.map(c => c.customer_id), D.check.order);
for (const t of Object.keys(D.check.perf)) {
  check("rule performance @ threshold " + t, S.performance(scored, D.rules, D.labels, Number(t), D.totalAto), D.check.perf[t]);
}
process.exit(failures ? 1 : 0);
