#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.dirname(SCRIPT_DIR);
const DATA_DIR = path.join(ROOT_DIR, 'data');

const SOURCES = [
  {
    file: '02A_力学振动波与光开发矩阵.md',
    domain: 'MEC',
    domainTitle: '力学、振动、波与光',
    expected: 42,
  },
  {
    file: '02B_电磁学与传感器开发矩阵.md',
    domain: 'EM',
    domainTitle: '电磁学与传感器',
    expected: 40,
  },
  {
    file: '02C_热学与近代物理开发矩阵.md',
    domain: 'THM',
    domainTitle: '热学与近代物理',
    expected: 29,
  },
];

const ALLOWED_CARRIERS = ['K', 'S', 'D', 'H', 'V', 'P'];
const ALLOWED_AI = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8'];
const ALLOWED_PRIORITIES = ['P0', 'P1', 'P2', 'P3'];
const SCHEMA_VERSION = '1.1';
const REQUIRED_FIELDS = [
  'schema_version',
  'id',
  'domain',
  'domain_title',
  'section',
  'section_title',
  'ordinal',
  'source_file',
  'source_line',
  'source_sha256',
  'topic',
  'textbook_anchor',
  'primary_carrier',
  'supporting_carriers',
  'carriers',
  'learning_object',
  'mvp_ai',
  'ai_capabilities',
  'reality_requirement',
  'priority',
];

function sha256(text) {
  return crypto.createHash('sha256').update(text).digest('hex');
}

function parseTableRow(line) {
  if (!line.startsWith('|') || !line.endsWith('|')) return null;
  return line
    .slice(1, -1)
    .split('|')
    .map((cell) => cell.trim());
}

function parseTopicAnchor(raw, sourceFile, sourceLine) {
  const matched = raw.match(/^(.*)（([^（）]+)）$/u);
  if (!matched) {
    throw new Error(`${sourceFile}:${sourceLine} 主题未以全角括号提供教材锚点：${raw}`);
  }
  const topic = matched[1].trim();
  const textbookAnchor = matched[2].trim();
  if (!topic || !textbookAnchor) {
    throw new Error(`${sourceFile}:${sourceLine} 主题或教材锚点为空：${raw}`);
  }
  return { topic, textbookAnchor };
}

function extractTextbookCodes(anchor) {
  const codes = [...anchor.matchAll(/\b(?:RJ|YJ)-(?:B|X)[1-3]\b/gu)].map(
    (match) => match[0],
  );
  return [...new Set(codes)];
}

function extractAiCapabilities(text) {
  const codes = [...text.matchAll(/\bA[1-8]\b/gu)].map((match) => match[0]);
  return [...new Set(codes)];
}

function makeStableId(domain, topicAnchorRaw) {
  const digest = sha256(`${domain}\n${topicAnchorRaw}`).slice(0, 10).toUpperCase();
  return `TB-${domain}-${digest}`;
}

function readSource(source) {
  const absolutePath = path.join(ROOT_DIR, source.file);
  const markdown = fs.readFileSync(absolutePath, 'utf8');
  const sourceHash = sha256(markdown);
  const lines = markdown.split(/\r?\n/u);
  const records = [];
  let sectionTitle = '';
  let sectionIndex = 0;

  lines.forEach((line, index) => {
    if (line.startsWith('## ')) {
      sectionTitle = line.slice(3).trim();
      sectionIndex += 1;
      return;
    }

    const cells = parseTableRow(line);
    if (!cells) return;
    if (cells[0] === '教材主题与锚点') {
      if (cells[1] !== '主载体') {
        throw new Error(`${source.file}:${index + 1} 第二列表头应为“主载体”，实际为“${cells[1]}”`);
      }
      return;
    }
    if (cells.every((cell) => /^:?-{3,}:?$/u.test(cell))) {
      return;
    }
    if (cells.length !== 6) {
      throw new Error(`${source.file}:${index + 1} 主题表应为6列，实际为${cells.length}列`);
    }
    if (!sectionTitle) {
      throw new Error(`${source.file}:${index + 1} 主题表之前缺少二级标题`);
    }

    const [topicAnchorRaw, carrierRaw, learningObject, mvpAi, realityRequirement, priority] = cells;
    const { topic, textbookAnchor } = parseTopicAnchor(topicAnchorRaw, source.file, index + 1);
    const carriers = carrierRaw.split('＋').map((item) => item.trim());
    if (carriers.length === 0 || carriers.some((carrier) => !carrier)) {
      throw new Error(`${source.file}:${index + 1} 主载体组合不完整：${carrierRaw}`);
    }
    const [primaryCarrier, ...supportingCarriers] = carriers;
    const aiCapabilities = extractAiCapabilities(mvpAi);
    const ordinal = records.length + 1;

    records.push({
      schema_version: SCHEMA_VERSION,
      id: makeStableId(source.domain, topicAnchorRaw),
      domain: source.domain,
      domain_title: source.domainTitle,
      section: `${source.domain}-${String(sectionIndex).padStart(2, '0')}`,
      section_title: sectionTitle,
      ordinal,
      source_file: source.file,
      source_line: index + 1,
      source_sha256: sourceHash,
      topic,
      textbook_anchor: textbookAnchor,
      textbook_codes: extractTextbookCodes(textbookAnchor),
      primary_carrier: primaryCarrier,
      supporting_carriers: supportingCarriers,
      carriers,
      learning_object: learningObject,
      mvp_ai: mvpAi,
      ai_capabilities: aiCapabilities,
      reality_requirement: realityRequirement,
      priority,
    });
  });

  if (records.length !== source.expected) {
    throw new Error(`${source.file} 主题数应为${source.expected}，实际为${records.length}`);
  }
  return records;
}

function isNonEmpty(value) {
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'number') return Number.isFinite(value) && value > 0;
  return typeof value === 'string' && value.trim().length > 0;
}

function hasRequiredValue(record, field) {
  if (!Object.hasOwn(record, field)) return false;
  if (field === 'supporting_carriers') return Array.isArray(record[field]);
  return isNonEmpty(record[field]);
}

function assertEnumValues(records, field, allowed) {
  const invalid = [];
  records.forEach((record) => {
    const values = Array.isArray(record[field]) ? record[field] : [record[field]];
    values.forEach((value) => {
      if (!allowed.includes(value)) invalid.push(`${record.id}:${value}`);
    });
  });
  if (invalid.length > 0) {
    throw new Error(`${field} 出现非法枚举：${invalid.join(', ')}`);
  }
}

function validate(records) {
  if (records.length !== 111) {
    throw new Error(`总主题数应为111，实际为${records.length}`);
  }

  const ids = records.map((record) => record.id);
  if (new Set(ids).size !== ids.length) {
    const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);
    throw new Error(`ID不唯一：${[...new Set(duplicates)].join(', ')}`);
  }

  const missing = [];
  records.forEach((record) => {
    REQUIRED_FIELDS.forEach((field) => {
      if (!hasRequiredValue(record, field)) missing.push(`${record.id}:${field}`);
    });
  });
  if (missing.length > 0) {
    throw new Error(`必填字段为空：${missing.join(', ')}`);
  }

  assertEnumValues(records, 'primary_carrier', ALLOWED_CARRIERS);
  assertEnumValues(records, 'supporting_carriers', ALLOWED_CARRIERS);
  assertEnumValues(records, 'carriers', ALLOWED_CARRIERS);
  assertEnumValues(records, 'ai_capabilities', ALLOWED_AI);
  assertEnumValues(records, 'priority', ALLOWED_PRIORITIES);

  const carrierRoleErrors = [];
  records.forEach((record) => {
    const expectedCarriers = [record.primary_carrier, ...record.supporting_carriers];
    if (JSON.stringify(record.carriers) !== JSON.stringify(expectedCarriers)) {
      carrierRoleErrors.push(record.id);
    }
  });
  if (carrierRoleErrors.length > 0) {
    throw new Error(`载体角色未按源顺序保存：${carrierRoleErrors.join(', ')}`);
  }

  return {
    primaryCarriers: new Set(records.map((record) => record.primary_carrier)),
    carriers: new Set(records.flatMap((record) => record.carriers)),
    ai: new Set(records.flatMap((record) => record.ai_capabilities)),
    priorities: new Set(records.map((record) => record.priority)),
  };
}

function csvEscape(value) {
  const stringValue = String(value ?? '');
  return `"${stringValue.replaceAll('"', '""')}"`;
}

function toCsv(records) {
  const columns = [
    'schema_version',
    'id',
    'domain',
    'domain_title',
    'section',
    'section_title',
    'ordinal',
    'source_file',
    'source_line',
    'source_sha256',
    'topic',
    'textbook_anchor',
    'textbook_codes',
    'primary_carrier',
    'supporting_carriers',
    'carriers',
    'learning_object',
    'mvp_ai',
    'ai_capabilities',
    'reality_requirement',
    'priority',
  ];
  const rows = records.map((record) =>
    columns.map((column) => {
      const value = Array.isArray(record[column]) ? record[column].join(';') : record[column];
      return csvEscape(value);
    }),
  );
  return [columns.map(csvEscape), ...rows].map((row) => row.join(',')).join('\n') + '\n';
}

function formatCoverage(allowed, observed) {
  return allowed.map((code) => `${code}:${observed.has(code) ? '✓' : '0'}`).join(' ');
}

function main() {
  const records = SOURCES.flatMap(readSource);
  const coverage = validate(records);

  const jsonl = records.map((record) => JSON.stringify(record)).join('\n') + '\n';
  const csv = toCsv(records);
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(path.join(DATA_DIR, 'topics.jsonl'), jsonl, 'utf8');
  fs.writeFileSync(path.join(DATA_DIR, 'topics.csv'), csv, 'utf8');

  console.log('教材主题目录验证通过');
  for (const source of SOURCES) {
    console.log(`- ${source.domain}: ${source.expected}`);
  }
  console.log(`- 总计: ${records.length}`);
  console.log(`- 唯一ID: ${new Set(records.map((record) => record.id)).size}`);
  console.log(`- 必填字段: ${records.length}/${records.length} 完整`);
  console.log(`- 首选载体: ${formatCoverage(ALLOWED_CARRIERS, coverage.primaryCarriers)}`);
  console.log(`- 全部载体: ${formatCoverage(ALLOWED_CARRIERS, coverage.carriers)}`);
  console.log(`- AI枚举: ${formatCoverage(ALLOWED_AI, coverage.ai)}`);
  console.log(`- 优先级枚举: ${formatCoverage(ALLOWED_PRIORITIES, coverage.priorities)}`);
  if (!coverage.ai.has('A7')) {
    console.log('- 说明: A7为合法枚举，但现有111项主题表未显式使用；生成器不从正文外推标签。');
  }
  console.log(`- 写入: ${path.relative(ROOT_DIR, path.join(DATA_DIR, 'topics.jsonl'))}`);
  console.log(`- 写入: ${path.relative(ROOT_DIR, path.join(DATA_DIR, 'topics.csv'))}`);
}

try {
  main();
} catch (error) {
  console.error(`生成失败: ${error.message}`);
  process.exitCode = 1;
}
