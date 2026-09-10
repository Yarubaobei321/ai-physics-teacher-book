"use strict";

const fs = require("node:fs");
const path = require("node:path");
const data = require("../app/data.js");
const engine = require("../app/engine.js");

const root = path.resolve(__dirname, "..");
const failures = [];

const requiredFiles = [
  "AGENTS.md",
  "README.md",
  "HANDOFF.md",
  "app/index.html",
  "app/styles.css",
  "app/data.js",
  "app/engine.js",
  "app/app.js",
  "docs/00_需求与边界.md",
  "docs/01_三路线比较与技术决策.md",
  "docs/02_知识结构、证据与推荐规则.md",
  "docs/03_微资源与检查任务台账.md",
  "docs/04_来源、失败与版本记录.md",
  "docs/05_教师审核门与试用脚本.md",
  "docs/06_证据边界与可入书价值.md",
  "review/S4-v0.1/review.md",
  "review/S4-v0.1/index.html",
  "validation-report.txt",
];

requiredFiles.forEach((relativePath) => {
  if (!fs.existsSync(path.join(root, relativePath))) failures.push(`缺少文件：${relativePath}`);
});

engine.validateData(data).forEach((error) => failures.push(`数据：${error}`));

const appFiles = ["app/index.html", "app/data.js", "app/engine.js", "app/app.js"]
  .filter((relativePath) => fs.existsSync(path.join(root, relativePath)))
  .map((relativePath) => fs.readFileSync(path.join(root, relativePath), "utf8"))
  .join("\n");

[
  ["fetch(", "发现网络fetch调用"],
  ["XMLHttpRequest", "发现XMLHttpRequest调用"],
  ["WebSocket", "发现WebSocket调用"],
  ["https://", "应用文件含外部HTTPS地址"],
  ["http://", "应用文件含外部HTTP地址"],
].forEach(([needle, message]) => {
  if (appFiles.includes(needle)) failures.push(message);
});

const indexPath = path.join(root, "app/index.html");
if (fs.existsSync(indexPath)) {
  const index = fs.readFileSync(indexPath, "utf8");
  const order = ["data.js", "engine.js", "app.js"].map((name) => index.indexOf(name));
  if (order.some((value) => value < 0) || !(order[0] < order[1] && order[1] < order[2])) {
    failures.push("脚本加载顺序不正确，应为data→engine→app。");
  }
  ["教师审核门", "证据边界", "合成画像"].forEach((term) => {
    if (!index.includes(term)) failures.push(`页面缺少关键边界词：${term}`);
  });
}

[
  "app/index.html",
  "review/S4-v0.1/index.html",
].forEach((relativePath) => {
  const absolutePath = path.join(root, relativePath);
  if (!fs.existsSync(absolutePath)) return;
  const html = fs.readFileSync(absolutePath, "utf8");
  const links = [...html.matchAll(/(?:href|src)="([^"#]+)"/g)].map((match) => match[1]);
  links
    .filter((link) => !/^(?:https?:|data:|mailto:)/.test(link))
    .forEach((link) => {
      const target = path.resolve(path.dirname(absolutePath), link);
      if (!fs.existsSync(target)) failures.push(`${relativePath}存在失效本地链接：${link}`);
    });
});

if (failures.length) {
  process.stderr.write(`${JSON.stringify({ status: "failed", failures }, null, 2)}\n`);
  process.exit(1);
}

process.stdout.write(`${JSON.stringify({
  status: "passed",
  version: data.meta.version,
  concepts: data.concepts.length,
  resources: data.resources.length,
  checks: data.checks.length,
  syntheticProfiles: data.profiles.length,
  networkCalls: 0,
  requiredFiles: requiredFiles.length,
}, null, 2)}\n`);
