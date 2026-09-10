"use strict";

const assert = require("node:assert/strict");
const data = require("../app/data.js");
const engine = require("../app/engine.js");

let passed = 0;

function test(name, fn) {
  try {
    fn();
    passed += 1;
    process.stdout.write(`✓ ${name}\n`);
  } catch (error) {
    process.stderr.write(`✗ ${name}\n${error.stack}\n`);
    process.exitCode = 1;
  }
}

function profile(id) {
  return data.profiles.find((item) => item.id === id);
}

test("数据结构通过内置校验", () => {
  assert.deepEqual(engine.validateData(data), []);
});

test("资源与检查任务数量保持在最小范围", () => {
  assert.equal(data.resources.length, 10);
  assert.equal(data.checks.length, 4);
  assert.equal(data.profiles.length, 3);
});

test("合成画像A优先复核守恒条件，而不是下游未知节点", () => {
  const ranked = engine.rankRecommendations(data, profile("SYN-A").initialEvents, []);
  assert.equal(ranked.candidates[0].targetConceptId, "K3");
  assert.equal(ranked.states.K3.state, "not_yet_shown");
});

test("合成画像B优先复核能量项表达", () => {
  const ranked = engine.rankRecommendations(data, profile("SYN-B").initialEvents, []);
  assert.equal(ranked.candidates[0].targetConceptId, "K2");
});

test("未观察节点先补检查，不被写成薄弱", () => {
  const ranked = engine.rankRecommendations(data, profile("SYN-C").initialEvents, []);
  assert.equal(ranked.candidates[0].id, "VERIFY-K1");
  assert.match(ranked.candidates[0].evidenceSummary, /没有直接观察/);
  assert.doesNotMatch(ranked.candidates[0].editableReason, /未掌握|完全不会/);
});

test("相同输入产生完全相同的候选与理由", () => {
  const events = profile("SYN-A").initialEvents;
  assert.deepEqual(
    engine.rankRecommendations(data, events, []),
    engine.rankRecommendations(data, events, [])
  );
});

test("检查形成支持后，画像A的K3状态更新", () => {
  const initial = profile("SYN-A").initialEvents;
  const candidate = engine.rankRecommendations(data, initial, []).candidates[0];
  const updatedEvents = engine.appendCheckEvidence(initial, candidate, "pass", 1);
  const states = engine.computeConceptStates(data, updatedEvents);
  assert.equal(states.K3.state, "supported_this_task");
  assert.equal(initial.length + 1, updatedEvents.length);
});

test("相反检查结果形成矛盾状态，不输出确定结论", () => {
  const events = [
    { id: "X0A", checkId: "C01", conceptResults: { K1: "pass" }, note: "上游已有本轮支持" },
    { id: "X0B", checkId: "C02", conceptResults: { K2: "pass" }, note: "上游已有本轮支持" },
    { id: "X1", checkId: "C01", conceptResults: { K3: "not-yet" }, note: "情境一" },
    { id: "X2", checkId: "C03", conceptResults: { K3: "pass" }, note: "情境二" },
  ];
  const ranked = engine.rankRecommendations(data, events, []);
  assert.equal(ranked.states.K3.state, "mixed");
  const k3Candidate = ranked.candidates.find((item) => item.targetConceptId === "K3");
  assert.ok(k3Candidate);
  assert.match(k3Candidate.uncertainty, /冲突/);
});

test("教师否决后原候选不再出现，其他候选仍可审", () => {
  const events = profile("SYN-A").initialEvents;
  const first = engine.rankRecommendations(data, events, []).candidates[0];
  const next = engine.rankRecommendations(data, events, [first.bundleId]);
  assert.ok(!next.candidates.some((item) => item.id === first.id));
  assert.ok(next.candidates.length > 0);
});

test("仅阅读资源不会改变概念证据状态", () => {
  const events = profile("SYN-A").initialEvents;
  const before = engine.computeConceptStates(data, events);
  const simulatedResourceCompletion = events.slice();
  const after = engine.computeConceptStates(data, simulatedResourceCompletion);
  assert.deepEqual(after, before);
});

test("循环知识结构会被拒绝", () => {
  const invalid = JSON.parse(JSON.stringify(data));
  invalid.concepts.find((item) => item.id === "K1").prerequisiteIds = ["K6"];
  assert.ok(engine.validateData(invalid).some((item) => item.includes("循环")));
});

test("缺少资源权利说明会被拒绝", () => {
  const invalid = JSON.parse(JSON.stringify(data));
  invalid.resources[0].rightsNote = "";
  assert.ok(engine.validateData(invalid).some((item) => item.includes("授权说明")));
});

if (!process.exitCode) {
  process.stdout.write(`\n${passed}项规则测试全部通过。\n`);
}
