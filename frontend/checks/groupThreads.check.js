import { groupThreads } from "../src/groupThreads.js";

const now = new Date(2026, 10, 28, 16, 0);
const at = (...parts) => new Date(...parts).toISOString();
const ids = (group) => group.threads.map((t) => t.thread_id);

const mixed = groupThreads(
  [
    { thread_id: "old", updated_at: at(2026, 10, 20, 10, 0) },
    { thread_id: "today-early", updated_at: at(2026, 10, 28, 9, 0) },
    { thread_id: "yesterday", updated_at: at(2026, 10, 27, 23, 30) },
    { thread_id: "today-late", updated_at: at(2026, 10, 28, 15, 0) },
    { thread_id: "missing" },
    { thread_id: "garbage", updated_at: "not a date" },
  ],
  now
);

const onlyToday = groupThreads([{ thread_id: "a", updated_at: at(2026, 10, 28, 0, 0) }], now);

const cases = [
  ["Groups come out as Today, Yesterday, Earlier", mixed.map((g) => g.label).join() === "Today,Yesterday,Earlier"],
  ["Newest first inside a group", ids(mixed[0]).join() === "today-late,today-early"],
  ["Yesterday holds only yesterday", ids(mixed[1]).join() === "yesterday"],
  ["Old, missing and invalid dates land in Earlier", ids(mixed[2]).join() === "old,missing,garbage"],
  ["No threads gives no groups", groupThreads([], now).length === 0],
  ["Empty groups are left out, midnight counts as today", onlyToday.length === 1 && onlyToday[0].label === "Today"],
];

let passed = 0;
for (const [name, ok] of cases) {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}`);
  if (ok) passed += 1;
}
console.log(`\nPassed ${passed}/${cases.length}`);
process.exitCode = passed === cases.length ? 0 : 1;