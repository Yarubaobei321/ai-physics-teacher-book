import { readFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const pilotDir = resolve(here, "..");
const projectDir = resolve(pilotDir, "../../..");
const csvPath = join(pilotDir, "教师判断事件库.csv");
const lines = readFileSync(csvPath, "utf8").trim().split(/\r?\n/);
const header = lines.shift().split(",");
const expectedColumns = 12;
const allowedTypes = new Set(["定义问题", "定义测量", "审查证据", "决定干预", "决定停止"]);
const allowedLevels = new Set(["A", "B"]);
const errors = [];

if (header.length !== expectedColumns) {
  errors.push(`表头应有 ${expectedColumns} 列，实际为 ${header.length} 列`);
}

if (lines.length < 15 || lines.length > 20) {
  errors.push(`事件数量应为 15—20，实际为 ${lines.length}`);
}

const seen = new Set();
for (const [index, line] of lines.entries()) {
  const row = line.split(",");
  const lineNumber = index + 2;
  if (row.length !== expectedColumns) {
    errors.push(`第 ${lineNumber} 行应有 ${expectedColumns} 列，实际为 ${row.length} 列`);
    continue;
  }
  const [id, type, level, ...rest] = row;
  if (!/^J\d{2}$/.test(id)) errors.push(`第 ${lineNumber} 行事件编号无效：${id}`);
  if (seen.has(id)) errors.push(`事件编号重复：${id}`);
  seen.add(id);
  if (!allowedTypes.has(type)) errors.push(`第 ${lineNumber} 行判断类型无效：${type}`);
  if (!allowedLevels.has(level)) errors.push(`第 ${lineNumber} 行证据等级无效：${level}`);
  if (rest.some((value) => value.trim() === "")) errors.push(`第 ${lineNumber} 行存在空字段`);
  const sourcePath = row[10];
  if (!existsSync(join(projectDir, sourcePath))) {
    errors.push(`第 ${lineNumber} 行源文件不存在：${sourcePath}`);
  }
}

if (errors.length > 0) {
  console.error(errors.join("\n"));
  process.exit(1);
}

const typeCounts = Object.fromEntries([...allowedTypes].map((type) => [type, 0]));
const levelCounts = { A: 0, B: 0 };
for (const line of lines) {
  const [, type, level] = line.split(",");
  typeCounts[type] += 1;
  levelCounts[level] += 1;
}

console.log(JSON.stringify({ events: lines.length, typeCounts, levelCounts, sourceFiles: "all_found" }, null, 2));
