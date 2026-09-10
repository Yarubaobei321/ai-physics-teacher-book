import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const toolDirectory = path.dirname(fileURLToPath(import.meta.url));
const viewerDirectory = path.resolve(toolDirectory, "..");
const sourcePath = path.resolve(viewerDirectory, "..", "data", "topics.jsonl");
const outputPath = path.join(viewerDirectory, "topics.bundle.js");
const allowedCarriers = new Set(["K", "S", "D", "H", "V", "P"]);

const topics = fs
  .readFileSync(sourcePath, "utf8")
  .split(/\r?\n/u)
  .filter(Boolean)
  .map((line) => JSON.parse(line));

if (topics.length !== 111 || new Set(topics.map((topic) => topic.id)).size !== 111) {
  throw new Error("教材主题源数据必须恰好包含111个唯一主题");
}

topics.forEach((topic) => {
  if (topic.schema_version !== "1.1") {
    throw new Error(`${topic.id} schema_version应为1.1`);
  }
  if (!allowedCarriers.has(topic.primary_carrier)) {
    throw new Error(`${topic.id} primary_carrier非法`);
  }
  if (
    !Array.isArray(topic.supporting_carriers) ||
    topic.supporting_carriers.some((carrier) => !allowedCarriers.has(carrier))
  ) {
    throw new Error(`${topic.id} supporting_carriers非法`);
  }
  const expectedCarriers = [topic.primary_carrier, ...topic.supporting_carriers];
  if (JSON.stringify(topic.carriers) !== JSON.stringify(expectedCarriers)) {
    throw new Error(`${topic.id} carriers未按首选与支持顺序生成`);
  }
});

const bundle = `/* 由 tools/build-data.mjs 从 ../data/topics.jsonl 自动生成。 */\nwindow.TEXTBOOK_TOPICS = Object.freeze(${JSON.stringify(topics)});\n`;
fs.writeFileSync(outputPath, bundle, "utf8");
console.log(`BUILD topics.bundle.js topics=${topics.length}`);
