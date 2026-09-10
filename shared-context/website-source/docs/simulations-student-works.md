# 模拟实验室 · 学生 AI 对话作品

## 概述

模拟实验室栏目 `/simulations/` 下半部分展示学生使用 AI 协作完成的物理模拟网页。每份作品包含：

- 评审报告页（对话过程、阶段性作品、评分与理想提示词）
- 最终成品 HTML
- `阶段性作品/` 目录下的各版本演示页

## 目录结构

```
public/simulations/student-works/
  a2-c0e890/                    # 短 slug（由导入脚本生成）
    高一14班-涂迪森-...-评审报告.html
    高一14班-涂迪森-...html      # 最终成品
    阶段性作品/
      01_基础版.html
      ...
src/data/student-works.ts       # 门户卡片数据（自动生成）
scripts/import-student-works.mjs
```

## 更新流程

> **重要复核提示（2026-06-30）**：旧批量评审报告存在系统性提取错误，部分报告把 DeepSeek 的回复误标为“学生提示词”，导致评分偏高。重新导入或恢复学生作品前，必须先阅读并处理 [学生 AI 对话作品对抗性审查报告](/Users/yaril/个人文档/数智育才网站/docs/student-ai-work-adversarial-review.md)，不要直接复用旧的 `*-评审报告.html`。

1. 将新作品放入源目录（默认）：
   `/Users/yaril/个人文档/0 物理实验项目课题/模拟实验网页设计/学生作品/`
2. 每个作品文件夹需包含 `*-评审报告.html` 及关联 HTML。
3. 在项目根目录运行：

```bash
node scripts/import-student-works.mjs
npm run test
npm run build
```

导入脚本会自动扫描 `阶段性作品/` 目录，补全评审报告里缺失的版本卡片与对话跳转链接。

4. 确认 `/simulations/` 页面卡片与评审报告内链正常后，再部署到阿里云。

## 环境变量

可通过 `STUDENT_WORKS_SOURCE` 指定不同的源目录：

```bash
STUDENT_WORKS_SOURCE=/path/to/学生作品 node scripts/import-student-works.mjs
```

导入脚本会在复制文件前预检评审报告。如果检测到疑似把 DeepSeek 回复误标为“学生提示词”，或报告显示 `no_txt`、`txt_html_only`、`no_share_url` 等证据不足状态，脚本会默认中止，且不会清空现有 `public/simulations/student-works/`。只有做本地取证、明确不准备发布时，才可以临时跳过：

```bash
STUDENT_WORKS_SOURCE=/path/to/学生作品 STUDENT_WORKS_ALLOW_UNVERIFIED=1 node scripts/import-student-works.mjs
```

历史脚本中的默认路径曾指向旧目录；运行前建议显式设置 `STUDENT_WORKS_SOURCE`，避免误导入空目录或旧目录。

## 注意事项

- 导入脚本只复制 `.html` 文件，保留文件夹内相对链接。
- 评审报告页导航已指向门户根路径（`/`、`/simulations/` 等），部署后可直接使用。
- 部分阶段性作品依赖 CDN（Chart.js、MathJax、Three.js 等），需联网访问。
