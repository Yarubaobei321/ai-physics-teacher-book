#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const registerDir = path.resolve(scriptDir, "..");
const sourcePath = path.join(registerDir, "04_综合项目组合与优先路线.md");
const dataDir = path.join(registerDir, "data");
const jsonlPath = path.join(dataDir, "projects.jsonl");
const csvPath = path.join(dataDir, "projects.csv");

const sourceHeading = "## 四、前12项目总表";
const expectedHeaders = [
  "排名",
  "组合ID",
  "层",
  "去重后的项目",
  "主要来源ID映射",
  "当前成熟度",
  "优先级",
  "直接依赖",
];
const expectedIds = [
  "U01",
  "U02",
  "U03",
  "U04",
  "U05",
  "V01",
  "V02",
  "V03",
  "V04",
  "V05",
  "R01",
  "R02",
];
const outputFields = [
  "rank",
  "id",
  "layer",
  "name",
  "source_mappings",
  "maturity_label",
  "primary_maturity",
  "priority_label",
  "primary_priority",
  "dependencies",
  "source_file",
  "source_line",
  "source_sha256",
];

function fail(message) {
  throw new Error(message);
}

function sha256(content) {
  return crypto.createHash("sha256").update(content).digest("hex");
}

function splitMarkdownRow(line) {
  const trimmed = line.trim();
  if (!trimmed.startsWith("|") || !trimmed.endsWith("|")) return null;

  const cells = [];
  let current = "";
  let inCode = false;
  let escaped = false;

  for (const character of trimmed.slice(1, -1)) {
    if (escaped) {
      current += character;
      escaped = false;
      continue;
    }
    if (character === "\\") {
      escaped = true;
      current += character;
      continue;
    }
    if (character === "`") {
      inCode = !inCode;
      current += character;
      continue;
    }
    if (character === "|" && !inCode) {
      cells.push(current.trim());
      current = "";
      continue;
    }
    current += character;
  }
  cells.push(current.trim());
  return cells;
}

function cleanCell(value) {
  return value
    .trim()
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\s+/g, " ");
}

function isSeparatorRow(cells) {
  return (
    cells?.length === expectedHeaders.length &&
    cells.every((cell) => /^:?-{3,}:?$/.test(cell.trim()))
  );
}

function extractMappings(cell) {
  const mappings = [];
  const seen = new Set();
  const tokenPattern = /`([^`]+)`|(^|[^A-Za-z0-9_-])(B2-16|S[1-4])(?=$|[^A-Za-z0-9_-])/g;
  let match;

  while ((match = tokenPattern.exec(cell)) !== null) {
    const rawToken = match[1] ?? match[3];
    const candidates = rawToken
      .split(/[、，,\s]+/)
      .map((value) => value.trim())
      .filter(Boolean);
    for (const candidate of candidates) {
      if (!seen.has(candidate)) {
        seen.add(candidate);
        mappings.push(candidate);
      }
    }
  }

  if (mappings.length === 0) {
    fail(`来源映射无法解析：${cell}`);
  }
  return mappings;
}

function extractPrimary(label, pattern, allowed, fieldName, id) {
  const match = label.match(pattern);
  if (!match || !allowed.has(match[1])) {
    fail(`${id} 的${fieldName}无法从“${label}”解析`);
  }
  return match[1];
}

function parseSource(sourceText) {
  const sourceHash = sha256(sourceText);
  const lines = sourceText.replace(/\r\n/g, "\n").split("\n");
  const headingIndex = lines.findIndex((line) => line.trim() === sourceHeading);
  if (headingIndex < 0) fail(`找不到权威表标题：${sourceHeading}`);

  let headerIndex = -1;
  for (let index = headingIndex + 1; index < lines.length; index += 1) {
    const cells = splitMarkdownRow(lines[index]);
    if (cells) {
      headerIndex = index;
      if (JSON.stringify(cells) !== JSON.stringify(expectedHeaders)) {
        fail(`前12项目总表表头变化：${cells.join(" | ")}`);
      }
      break;
    }
  }
  if (headerIndex < 0) fail("找不到前12项目总表表头");

  const separatorCells = splitMarkdownRow(lines[headerIndex + 1] ?? "");
  if (!isSeparatorRow(separatorCells)) fail("前12项目总表缺少合法分隔行");

  const records = [];
  for (let index = headerIndex + 2; index < lines.length; index += 1) {
    const cells = splitMarkdownRow(lines[index]);
    if (!cells) break;
    if (cells.length !== expectedHeaders.length) {
      fail(`源文件第${index + 1}行列数应为8，实际为${cells.length}`);
    }

    const [rankCell, idCell, layerCell, nameCell, mappingsCell, maturityCell, priorityCell, dependencyCell] = cells;
    if (!/^\d+$/.test(rankCell)) break;

    const id = cleanCell(idCell);
    const maturityLabel = cleanCell(maturityCell);
    const priorityLabel = cleanCell(priorityCell);
    const record = {
      rank: Number.parseInt(rankCell, 10),
      id,
      layer: cleanCell(layerCell),
      name: cleanCell(nameCell),
      source_mappings: extractMappings(mappingsCell),
      maturity_label: maturityLabel,
      primary_maturity: extractPrimary(
        maturityLabel,
        /\b(R[01])\b/,
        new Set(["R0", "R1"]),
        "主成熟度",
        id,
      ),
      priority_label: priorityLabel,
      primary_priority: extractPrimary(
        priorityLabel,
        /\b(P[01])\b/,
        new Set(["P0", "P1"]),
        "主优先级",
        id,
      ),
      dependencies: cleanCell(dependencyCell),
      source_file: path.relative(registerDir, sourcePath).split(path.sep).join("/"),
      source_line: index + 1,
      source_sha256: sourceHash,
    };
    records.push(record);
  }

  return records;
}

function validateRecords(records) {
  if (records.length !== 12) fail(`项目数应为12，实际为${records.length}`);

  const ids = records.map((record) => record.id);
  if (new Set(ids).size !== ids.length) fail("组合ID存在重复");
  if (JSON.stringify(ids) !== JSON.stringify(expectedIds)) {
    fail(`组合ID或顺序变化：${ids.join(", ")}`);
  }

  for (let index = 0; index < records.length; index += 1) {
    const record = records[index];
    if (record.rank !== index + 1) {
      fail(`${record.id} 的排名应为${index + 1}，实际为${record.rank}`);
    }
    for (const field of outputFields) {
      const value = record[field];
      if (Array.isArray(value)) {
        if (value.length === 0 || value.some((item) => String(item).trim() === "")) {
          fail(`${record.id}.${field} 不能为空`);
        }
      } else if (value === null || value === undefined || String(value).trim() === "") {
        fail(`${record.id}.${field} 不能为空`);
      }
    }
    if (!new Set(["R0", "R1"]).has(record.primary_maturity)) {
      fail(`${record.id} 的主成熟度非法：${record.primary_maturity}`);
    }
    if (!new Set(["P0", "P1"]).has(record.primary_priority)) {
      fail(`${record.id} 的主优先级非法：${record.primary_priority}`);
    }
    if (!/^[a-f0-9]{64}$/.test(record.source_sha256)) {
      fail(`${record.id} 的源SHA-256非法`);
    }
  }
}

function csvEscape(value) {
  const stringValue = Array.isArray(value) ? value.join(";") : String(value);
  return `"${stringValue.replaceAll('"', '""')}"`;
}

function renderJsonl(records) {
  return `${records.map((record) => JSON.stringify(record)).join("\n")}\n`;
}

function renderCsv(records) {
  const lines = [outputFields.map(csvEscape).join(",")];
  for (const record of records) {
    lines.push(outputFields.map((field) => csvEscape(record[field])).join(","));
  }
  return `${lines.join("\n")}\n`;
}

function writeIfChanged(filePath, content) {
  if (fs.existsSync(filePath) && fs.readFileSync(filePath, "utf8") === content) {
    return "unchanged";
  }
  fs.writeFileSync(filePath, content, "utf8");
  return "written";
}

function compareOutput(filePath, expected) {
  if (!fs.existsSync(filePath)) fail(`缺少输出：${path.relative(registerDir, filePath)}`);
  const actual = fs.readFileSync(filePath, "utf8");
  if (actual !== expected) {
    fail(`输出已过期或被修改：${path.relative(registerDir, filePath)}`);
  }
}

function printSummary(mode, records, jsonl, csv, statuses = {}) {
  const sourceHash = records[0].source_sha256;
  process.stdout.write(
    [
      `${mode}: ${records.length} projects`,
      `ids=${records.map((record) => record.id).join(",")}`,
      `source_sha256=${sourceHash}`,
      `projects_jsonl_sha256=${sha256(jsonl)}`,
      `projects_csv_sha256=${sha256(csv)}`,
      ...Object.entries(statuses).map(([key, value]) => `${key}=${value}`),
    ].join("\n") + "\n",
  );
}

function main() {
  const args = process.argv.slice(2);
  if (args.length > 1 || (args[0] && !["--write", "--check"].includes(args[0]))) {
    fail("用法：node tools/build_project_register.mjs [--write|--check]");
  }
  const mode = args[0] === "--check" ? "check" : "write";
  const sourceText = fs.readFileSync(sourcePath, "utf8");
  const records = parseSource(sourceText);
  validateRecords(records);

  const jsonl = renderJsonl(records);
  const csv = renderCsv(records);
  if (jsonl !== renderJsonl(records) || csv !== renderCsv(records)) {
    fail("同一输入在同一进程中产生了非确定性输出");
  }

  if (mode === "check") {
    compareOutput(jsonlPath, jsonl);
    compareOutput(csvPath, csv);
    printSummary("check ok", records, jsonl, csv);
    return;
  }

  fs.mkdirSync(dataDir, { recursive: true });
  const statuses = {
    projects_jsonl: writeIfChanged(jsonlPath, jsonl),
    projects_csv: writeIfChanged(csvPath, csv),
  };
  compareOutput(jsonlPath, jsonl);
  compareOutput(csvPath, csv);
  printSummary("write ok", records, jsonl, csv, statuses);
}

try {
  main();
} catch (error) {
  process.stderr.write(`ERROR: ${error.message}\n`);
  process.exitCode = 1;
}
