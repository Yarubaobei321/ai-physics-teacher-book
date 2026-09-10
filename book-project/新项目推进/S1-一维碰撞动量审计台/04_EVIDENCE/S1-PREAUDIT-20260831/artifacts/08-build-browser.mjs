import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const toolDirectory = path.dirname(fileURLToPath(import.meta.url));
const prototypeDirectory = path.resolve(toolDirectory, "..");
const modelPath = path.join(prototypeDirectory, "src", "model.js");
const appPath = path.join(prototypeDirectory, "src", "app.js");
const outputDirectory = path.join(prototypeDirectory, "dist");
const outputPath = path.join(outputDirectory, "app.bundle.js");

const modelSource = fs
  .readFileSync(modelPath, "utf8")
  .replace(/^export\s+/gm, "");
const appSource = fs
  .readFileSync(appPath, "utf8")
  .replace(
    /import\s*\{[\s\S]*?\}\s*from\s*["']\.\/model\.js["'];\s*/,
    "",
  );

if (/^export\s+/m.test(modelSource) || /^import\s+/m.test(appSource)) {
  throw new Error("浏览器包生成失败：仍存在未处理的ES模块语句");
}

const bundle = `/* 自动生成，请修改 src/model.js 或 src/app.js 后运行 npm run build。 */
(() => {
  "use strict";

${modelSource}

${appSource}
})();
`;

fs.mkdirSync(outputDirectory, { recursive: true });
fs.writeFileSync(outputPath, bundle, "utf8");
console.log(`BUILD ${path.relative(prototypeDirectory, outputPath)}`);
