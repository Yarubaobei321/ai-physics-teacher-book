# 2026-06-11 尘光一号火星车地面站合并记录

> 本文记录本次合并的问题背景、关键决策、已完成的修改与验证结果。配套产出的网站优化计划见 [website-optimization-plan.md](website-optimization-plan.md)。

## 问题背景

「尘光一号火星车」项目自带一个独立的网页地面站（源项目：`零一工坊课件代码/P2-ESP32物联网图形化编程-代码/mycar/尘光一号火星车/ground-station`，Astro 5 + React 19 应用），需要合并进数智育才网站。合并前存在三个问题：

1. **功能差距**：网站里已有一个早期手写的简化版面板（`MarsRoverControlPanel.astro`，725 行原生 JS），只有单页遥测视图；而源项目是完整三视图地面站——任务驾驶舱（弧形仪表/姿态仪/趋势线）、操控台（虚拟摇杆/模式切换/急停）、部件原理（8 个数据驱动 SVG 原理动画，教学价值最高），并自带演示模式与 CSV 导出。
2. **协议过时**：简化版面板使用 PM2.5 字段，而火星车固件协议已升级到 v0.2（去掉 PM2.5，新增 lux/dist/line/speed/dust），数据对不上。
3. **技术栈冲突**：网站是纯 Astro + Tailwind（无 React），源项目依赖 React 19；源项目的 2195 行深空 HUD 主题 CSS 直接挂在 `:root`/`body` 上，直接引入会污染全站浅色主题。

## 关键决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| 合并方式 | 完整移植 React 版（网站新增 @astrojs/react 集成） | 部件原理动画等教学功能用原生 JS 重写代价过大；Astro islands 架构下 React 只在火星车一页加载，其余页面零 JS 增量 |
| 视觉风格 | 火星车页保留深空 HUD 主题，仅套用站点统一 Header/Footer | 学生项目展示页差异化风格更有沉浸感；改浅色需重写 2195 行 CSS 且 HUD 仪表表现力下降 |
| CSS 隔离 | `.rover-stage` 容器作用域方案 | 源 CSS 全局选择器集中在前 120 行，其余全是类选择器；把 `:root`/`body`/`::selection` 样式收敛到容器内即可，变量名碰撞（`--ink`）由就近覆盖天然解决 |
| 旧简化版 | 删除 | 协议过时且功能为完整版子集 |

## 已完成的修改

- **React 集成**：`package.json`（+@astrojs/react、react 19、react-dom、@types/react、@types/react-dom、@types/web-bluetooth）、`astro.config.mjs`（+react()）、`tsconfig.json`（jsx: react-jsx、types 加 web-bluetooth）。
- **组件落位**：源项目 5 个组件 → `src/components/mars-rover/`（RoverControlCenter / MissionView / ControlView / AnatomyView / widgets），3 个库文件 → `src/lib/mars-rover/`（roverProtocol 协议解析 / useRover BLE hook / demoTelemetry 演示数据），仅修改 10 处 import 路径，组件逻辑零改动。
- **样式**：`src/styles/mars-rover.css`（由源 global.css 改写）——删除与 Tailwind preflight 重复的归一化段；`:root`→`.rover-stage`；`body`/`button,input`/`:focus-visible`/`::selection`/reduced-motion 全部加 `.rover-stage` 作用域。注意：`.rover-stage` 上不可设 position/z-index/transform/filter/isolation（`.hud-bg` 的 fixed 星空背景依赖根层叠上下文）。
- **页面**：重写 `src/pages/projects/mars-rover/index.astro`（BaseLayout + `.rover-stage` 包裹 + `client:load`）；不引 BrowserSupportNotice（组件自带深色风格蓝牙检测提示，且无蓝牙时演示模式完整可用）。
- **清理**：删除 `src/components/MarsRoverControlPanel.astro`；首页入口卡片文案 "PM2.5" → "光照与积尘"。

## 验证结果

- `astro check`：0 错误 / 0 警告；`npm run build`：10 页构建成功。
- 构建产物核查：rover 主题 CSS 仅由 `/projects/mars-rover/` 页引用，站点共享 CSS 中无任何 rover 样式。
- Playwright 实测（preview 服务器）：三视图渲染正常，演示模式下仪表走数、姿态仪工作、链路徽章点亮、操控台滑块可用、部件原理动画随数据驱动；页面呈现"白色站点导航 + 深空 HUD 正文"。
- 回归：首页 body 背景 `#f5f8fb`、文字 `#102033`，浅色主题无污染。

## 后续

各模拟实验页面的显示效果与教学效果优化（Canvas DPR、KaTeX 本地化、慢放单步、动量/能量可视化分层等）按 [website-optimization-plan.md](website-optimization-plan.md) 的 P0→P3 顺序分批实施。
