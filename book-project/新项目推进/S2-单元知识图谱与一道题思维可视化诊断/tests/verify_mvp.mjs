import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(testDir, "..");
const context = { window: {} };
vm.createContext(context);

function read(relativePath) {
  return fs.readFileSync(path.join(projectRoot, relativePath), "utf8");
}

function loadScript(relativePath) {
  vm.runInContext(read(relativePath), context, { filename: relativePath });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function firstMatch(patterns, text) {
  for (const pattern of patterns) {
    pattern.lastIndex = 0;
    if (pattern.test(text)) return true;
  }
  return false;
}

function checkpointMap(diagnostic, text) {
  return new Map(diagnostic.checkpoints.map((checkpoint) => {
    const hitCount = checkpoint.groups.filter((group) => firstMatch(group.patterns, text)).length;
    return [checkpoint.id, hitCount >= checkpoint.minimumGroups];
  }));
}

const requiredFiles = [
  "README.md", "AGENTS.md", "app/index.html", "app/styles.css", "app/app.js",
  "data/knowledge-graph.js", "data/diagnostic-rules.js",
  "docs/01_材料回查与对象选择.md", "docs/02_自编题与标准推理树.md",
  "docs/04_文字映射与隐私边界.md", "docs/06_失败记录.md",
  "release/s2-release-gate.yaml", "review/S2最小系统-2026-08-29/review.md",
  "review/S2最小系统-2026-08-29/index.html", "HANDOFF.md"
];
requiredFiles.forEach((file) => assert(fs.existsSync(path.join(projectRoot, file)), `缺少文件：${file}`));

loadScript("data/knowledge-graph.js");
loadScript("data/diagnostic-rules.js");
const graph = context.window.S2_GRAPH;
const diagnostic = context.window.S2_DIAGNOSTIC;

assert(graph && diagnostic, "图谱或诊断数据未成功加载");
assert(graph.nodes.length >= 30 && graph.nodes.length <= 50, `节点数应为30—50，实际${graph.nodes.length}`);
assert(graph.edges.length >= 30, "关系数过少");
assert(new Set(graph.nodes.map((node) => node.id)).size === graph.nodes.length, "存在重复节点ID");
assert(new Set(graph.edges.map((edge) => edge.id)).size === graph.edges.length, "存在重复关系ID");

const nodeIds = new Set(graph.nodes.map((node) => node.id));
const sourceIds = new Set(graph.sources.map((source) => source.id));
graph.edges.forEach((edge) => {
  assert(nodeIds.has(edge.from), `关系${edge.id}起点不存在：${edge.from}`);
  assert(nodeIds.has(edge.to), `关系${edge.id}终点不存在：${edge.to}`);
});
graph.nodes.forEach((node) => {
  assert(node.sourceIds.length > 0, `节点${node.id}没有来源`);
  node.sourceIds.forEach((sourceId) => assert(sourceIds.has(sourceId), `节点${node.id}来源不存在：${sourceId}`));
});

assert(sourceIds.has("SRC-TRAIN-PPT"), "未登记V4-2培训材料");
assert(diagnostic.question.rights === "self_created", "题目必须标记为自编");
assert(diagnostic.checkpoints.length === 8, "当前MVP应有8个检查点");
diagnostic.checkpoints.forEach((checkpoint) => {
  checkpoint.nodeIds.forEach((nodeId) => assert(nodeIds.has(nodeId), `检查点${checkpoint.id}引用不存在节点${nodeId}`));
});
diagnostic.contradictions.forEach((item) => {
  item.nodeIds.forEach((nodeId) => assert(nodeIds.has(nodeId), `冲突${item.id}引用不存在节点${nodeId}`));
});

const samples = new Map(diagnostic.samples.map((sample) => [sample.id, sample.text]));
const complete = checkpointMap(diagnostic, samples.get("SAMPLE-COMPLETE"));
assert([...complete.values()].every(Boolean), `完整样例未覆盖所有检查点：${[...complete].filter(([, value]) => !value).map(([id]) => id).join(",")}`);

const resultOnly = checkpointMap(diagnostic, samples.get("SAMPLE-RESULT"));
assert(resultOnly.get("CH05") && resultOnly.get("CH06") && resultOnly.get("CH07"), "结果样例应命中三个计算检查点");
assert(!resultOnly.get("CH02") && !resultOnly.get("CH04") && !resultOnly.get("CH08"), "结果样例不应被误判为系统／条件／边界完整");

const conflictText = samples.get("SAMPLE-CONFLICT");
assert(diagnostic.contradictions.some((item) => firstMatch(item.patterns, conflictText)), "典型混淆样例未触发冲突");

const html = read("app/index.html");
const appJs = read("app/app.js");
assert(html.includes("教学提示，不是自动诊断结论"), "页面缺少核心边界声明");
assert(html.includes("不要输入姓名、学号"), "页面缺少隐私输入提醒");
assert(!/https?:\/\//i.test(html), "页面不应加载网络资源");
assert(!/\bfetch\s*\(|XMLHttpRequest|localStorage|sessionStorage|indexedDB/i.test(appJs), "应用不应联网或持久化输入");

const localReferences = [...html.matchAll(/(?:href|src)="([^"]+)"/g)]
  .map((match) => match[1])
  .filter((reference) => !reference.startsWith("#") && !reference.startsWith("data:"));
localReferences.forEach((reference) => {
  const resolved = path.resolve(projectRoot, "app", reference);
  assert(fs.existsSync(resolved), `页面本地链接不存在：${reference}`);
});

const reviewHtml = read("review/S2最小系统-2026-08-29/index.html");
const reviewReferences = [...reviewHtml.matchAll(/(?:href|src)="([^"]+)"/g)]
  .map((match) => match[1])
  .filter((reference) => !reference.startsWith("#") && !reference.startsWith("data:"));
reviewReferences.forEach((reference) => {
  const resolved = path.resolve(projectRoot, "review/S2最小系统-2026-08-29", reference);
  assert(fs.existsSync(resolved), `审阅页本地链接不存在：${reference}`);
});
assert(!/https?:\/\//i.test(reviewHtml), "审阅页不应加载网络资源");

console.log(`PASS nodes=${graph.nodes.length} edges=${graph.edges.length} checks=${diagnostic.checkpoints.length} samples=${diagnostic.samples.length}`);
