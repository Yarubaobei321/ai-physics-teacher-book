import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const context = { window: {}, console };
context.globalThis = context;
vm.createContext(context);
vm.runInContext(fs.readFileSync("topics.bundle.js", "utf8"), context);
vm.runInContext(fs.readFileSync("model.js", "utf8"), context);

const topics = context.window.TEXTBOOK_TOPICS;
const { filterTopics, summarize } = context.TopicRadar;
const allowedCarriers = new Set(["K", "S", "D", "H", "V", "P"]);

assert.equal(topics.length, 111);
assert.equal(new Set(topics.map((topic) => topic.id)).size, 111);
topics.forEach((topic) => {
  assert.equal(topic.schema_version, "1.1");
  assert.ok(allowedCarriers.has(topic.primary_carrier));
  assert.ok(Array.isArray(topic.supporting_carriers));
  assert.ok(topic.supporting_carriers.every((carrier) => allowedCarriers.has(carrier)));
  assert.deepEqual(
    JSON.parse(JSON.stringify(topic.carriers)),
    [topic.primary_carrier, ...topic.supporting_carriers],
  );
});

const summary = summarize(topics);
assert.deepEqual(
  JSON.parse(JSON.stringify(summary.domains)),
  { MEC: 42, EM: 40, THM: 29 },
);
assert.equal(Object.values(summary.priorities).reduce((sum, value) => sum + value, 0), 111);
assert.equal(Object.values(summary.primaryCarriers).reduce((sum, value) => sum + value, 0), 111);

const p0 = filterTopics(topics, { priorities: ["P0"] });
assert.ok(p0.length > 0 && p0.every((topic) => topic.priority === "P0"));

const dis = filterTopics(topics, { carriers: ["D"] });
assert.ok(dis.length > 0 && dis.every((topic) => topic.carriers.includes("D")));

const primaryDis = filterTopics(topics, { primaryCarriers: ["D"] });
assert.ok(
  primaryDis.length > 0 && primaryDis.every((topic) => topic.primary_carrier === "D"),
);

const supportingDisTopic = topics.find(
  (topic) => topic.primary_carrier !== "D" && topic.supporting_carriers.includes("D"),
);
assert.ok(supportingDisTopic, "应存在首选非D、支持载体含D的主题");
assert.ok(dis.some((topic) => topic.id === supportingDisTopic.id));
assert.ok(!primaryDis.some((topic) => topic.id === supportingDisTopic.id));

const primaryKContainingD = filterTopics(topics, {
  primaryCarriers: ["K"],
  carriers: ["D"],
});
assert.ok(
  primaryKContainingD.length > 0 &&
    primaryKContainingD.every(
      (topic) => topic.primary_carrier === "K" && topic.carriers.includes("D"),
    ),
);

const electromagnetic = filterTopics(topics, { domains: ["EM"], priorities: ["P0"] });
assert.ok(
  electromagnetic.length > 0 &&
    electromagnetic.every(
      (topic) => topic.domain === "EM" && topic.priority === "P0",
    ),
);

const search = filterTopics(topics, { search: "动量" });
assert.ok(search.length > 0 && search.some((topic) => topic.topic.includes("动量")));

const none = filterTopics(topics, { search: "不存在的教材主题-20260831" });
assert.equal(none.length, 0);

const html = fs.readFileSync("index.html", "utf8");
assert.match(html, /id="primary-carrier-filters"/u);
assert.match(html, /id="carrier-filters"/u);

console.log(`PASS catalog ${topics.length} topics, IDs unique`);
console.log(`PASS domains MEC=${summary.domains.MEC} EM=${summary.domains.EM} THM=${summary.domains.THM}`);
console.log(`PASS schema 1.1 carrier order and roles for ${topics.length} topics`);
console.log(`PASS filters P0=${p0.length} primary-D=${primaryDis.length} contains-D=${dis.length} K+contains-D=${primaryKContainingD.length} EM+P0=${electromagnetic.length}`);
console.log(`PASS search 动量=${search.length} empty=${none.length}`);
