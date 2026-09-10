# 育才一中物理创新实验室门户 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个可本地运行、可部署的 Astro 门户网站，包含首页、在线编程和网页版 DIS 三个页面。

**Architecture:** Astro 负责页面和布局，Tailwind CSS 负责视觉样式，原生 TypeScript 负责在线编程和 DIS 演示交互。硬件连接第一版只做权限检测和模拟流程，真实 Web Serial / Web Bluetooth 数据流留到后续版本。

**Tech Stack:** Astro, Tailwind CSS, TypeScript, Canvas, Web Serial API detection, Web Bluetooth API detection.

---

### Task 1: 项目骨架

**Files:**
- Create: `package.json`
- Create: `astro.config.mjs`
- Create: `tailwind.config.mjs`
- Create: `tsconfig.json`
- Create: `.gitignore`

- [x] **Step 1: 创建 Astro + Tailwind 配置**
- [x] **Step 2: 配置构建、检查和预览脚本**

### Task 2: 基础页面和视觉系统

**Files:**
- Create: `src/styles/global.css`
- Create: `src/components/BaseLayout.astro`
- Create: `src/components/Header.astro`
- Create: `src/components/Footer.astro`
- Create: `src/components/Hero.astro`
- Create: `src/data/site.ts`
- Create: `src/pages/index.astro`

- [x] **Step 1: 建立育才蓝色彩、全局排版和页面容器**
- [x] **Step 2: 使用 LOGO 和校园照片完成首页首屏**
- [x] **Step 3: 建立首页方向介绍和两个工具入口**

### Task 3: 在线编程原型

**Files:**
- Create: `src/data/programmingTemplates.ts`
- Create: `src/components/ProgrammingPanel.astro`
- Create: `src/pages/programming.astro`

- [x] **Step 1: 添加四个 MicroPython 模板**
- [x] **Step 2: 添加模板选择、代码编辑、连接状态和模拟串口输出**
- [x] **Step 3: 检测 Web Serial 支持情况**

### Task 4: 网页版 DIS 原型

**Files:**
- Create: `src/components/DisPanel.astro`
- Create: `src/pages/dis.astro`

- [x] **Step 1: 用 Canvas 绘制实时模拟曲线**
- [x] **Step 2: 添加暂停、清空、导出 CSV**
- [x] **Step 3: 检测 Web Bluetooth 支持情况**

### Task 5: 验证和提交

**Files:**
- Modify: generated lockfile after dependency install

- [x] **Step 1: 安装依赖**
- [x] **Step 2: 运行 `npm run build`**
- [x] **Step 3: 检查 Git 状态**
- [x] **Step 4: 创建初始提交**
