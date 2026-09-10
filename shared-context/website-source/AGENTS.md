# AGENTS.md

数智育才网站 / 育才物理创新实验室门户的项目协作说明。

## PROJECT_SUMMARY

- 目标与入口：Astro 静态教学门户；先读 `README.md`，按模块查 `docs/architecture.md`。本机项目根是 `/Users/yaril/个人文档/数智育才网站`。
- 目录：`src/pages/` 是路由，`src/components/` 是交互与展示，`src/data/` 是数据，`public/` 是静态实验，`scripts/` 是生成和验证入口，构建输出为 `dist/`。
- 维护入口：`.agents/skills/shuzhiyucai-aliyun-update/SKILL.md`；构建使用现有锁文件和依赖，不因更新说明升级依赖。
- 本地检查：`npm run generate:gaokao-pages -- --all --check`、`npm run validate:student-ai-lab`、`npm run build`、`npm test`。2026-09-05 在当前源码隔离副本中全部通过；这只代表本地软件检查。
- 2026-09-05 改版前完整工作树已备份到 Git `7642a67`；本轮改版分支为 `codex/site-usability-redesign`。初版改版提交为 `a9f2285`；按用户反馈，首页主体与文案已恢复到改版前版本。38 项资源查找与收藏移到 `/resources/`；三套机械能实验草稿、快捷导航和手机菜单保留。
- 审阅入口：`npm run review:site` → `http://127.0.0.1:4367/`；当前记录 `review/site-inner-pages-followup/review.md`；`review/site-usability-redesign/` 是被用户否决首页设计的历史候选。浏览器回归入口 `scripts/browser-site-usability-checks.js`（Playwright MCP），本次 52 项检查通过，构建完成 102 个路由。
- 边界：学生页面只用代号；`.local-deploy-notes/` 的凭据不复制到审阅或日志。本地通过、线上发布、物理与课堂/作者验收分别记录；本轮未部署、未操作设备、未作课堂验证。

## What this is

Astro 5 静态站点，作为四类教学工具的统一入口：在线编程（Web Serial · ESP32）、网页版 DIS（Web Bluetooth · ESP32）、在线实验室（机械能守恒方案一/二/三）、模拟实验室。线上：<https://shuzhiyucai.cn>。**先读 [README.md](README.md) 与 [docs/architecture.md](docs/architecture.md)**，再改敏感区域。

## Commands

```bash
npm install
npm run dev      # http://localhost:4321，--host 0.0.0.0
npm run build    # astro check && astro build —— 提交前必跑，check 不过即构建失败
npm test         # node scripts/verify-site.mjs，构建产物验证
npm run check    # 仅 astro check（类型/诊断）
npm run purge:cloudflare-cache        # 部署后清 CDN 缓存，需 .local-deploy-notes/cloudflare.env
npm run validate:student-ai-lab       # 校验 src/data/student-ai-lab.json（77 代号）与静态资源；可选 STUDENT_AI_LAB_NAME_LIST 真名门禁
```

`build` 含 `astro check`（strict tsconfig），改完任何 `.astro`/`.ts`/React 后必须本地 `npm run build` 通过。

## 目录与边界

```
src/pages/        # 路由：每个 .astro 一个页面（index / dis / programming / online-lab / simulations / projects / project-learning / maker）
src/components/   # 复用 Astro 组件；mars-rover/、smart-car/ 为 React island
src/data/         # 结构化数据（site.ts 导航元数据、exercises/、lab-reviews/、student-ai-lab.json）
src/lib/, src/styles/global.css
docs/             # 项目文档——改对应模块前先读相关文档
public/           # 静态资源（图片优先 .webp，保留原图回退）
scripts/          # 一次性脚本（部署、校验、导入）
.local-deploy-notes/  # 服务器/Cloudflare 敏感信息，已 .gitignore，勿进仓库
.agents/skills/       # 已 .gitignore
```

层级规则：数据放 `src/data/`，组件保持展示层；新增页面在 `src/pages/` 下加 `.astro`，导航元数据在 `src/data/site.ts` 维护。

## 技术栈与约定

- Astro 静态 + Tailwind CSS（`applyBaseStyles: false`，全局样式在 `src/styles/global.css`）+ TypeScript（`astro/tsconfigs/strict`）。
- React island 仅限需交互的页面（火星车地面站等）；`jsxImportSource: react`，`@types/web-bluetooth` 已装。
- 中文字体兜底、webp 首屏、robots/sitemap（`@astrojs/sitemap`，site=`https://shuzhiyucai.cn`）、自定义 404 均已就位，改动时勿破坏。
- `site` 字段在 `astro.config.mjs` 固定为 `https://shuzhiyucai.cn`，sitemap/Canonical 依赖它。

## 部署（生产环境敏感，谨慎）

阿里云硅谷 Ubuntu 24.04 + Nginx，前置 Cloudflare。**完整流程见 [docs/performance-china-access.md](docs/performance-china-access.md) 与 `.agents/skills/shuzhiyucai-aliyun-update/SKILL.md`**。要点：

1. 本地 `npm run build && npm test` 通过；
2. tarball → SCP → 服务器解压到 `/var/www/shuzhiyucai.cn/releases/<时间戳>` → `chown www-data` → 切 `html` 软链 → `nginx -t && systemctl reload nginx`；
3. **Cloudflare purge 必须放在软链切换与 nginx reload 成功之后**；
4. 回滚 = 软链指回旧 release + reload + 重新 purge；
5. 不要把 CF token / SSH key 写进仓库或 `.env`；放 `.local-deploy-notes/cloudflare.env`（已忽略）。

未经用户确认，不要执行任何对外部署/缓存清理/服务器改动。

## 写作与内容约定

- 公开页面中**不得出现学生真实姓名**。对照样例库只使用学科代号（P/B/M/C/H/G/L/E）；改 `src/data/student-ai-lab.json` 或 `public/simulations/student-ai-lab/` 后跑 `npm run validate:student-ai-lab`。旧复核数据已归档至 `docs/archive/student-ai-audits.json`，勿再挂公开页。
- 中文文案面向教师和学生，说明学习任务、操作与必要条件；开发进度、构建/回归测试、路由和内部验收说明放项目文档。保留影响实际使用的模型假设和数据保存范围。
- 用户已明确保留原版首页的大幅校园照片与整体布局；后续优化聚焦内页。改动首页/导航文案时同步 `src/data/site.ts`。
- 文档快照放 `docs/site-content/`；全站审查报告见 `docs/adversarial-site-review-*.md` 与 `docs/student-ai-work-adversarial-review.md`，改动相关板块前参考。
