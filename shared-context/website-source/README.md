# 育才物理创新实验室门户

线上：<https://shuzhiyucai.cn> · <https://www.shuzhiyucai.cn>

Astro 静态站点，承担四类工具的统一入口：在线编程（Web Serial · ESP32）、网页版 DIS（Web Bluetooth · ESP32）、在线实验室（机械能守恒方案一 / 二 / 三）、模拟实验室。

## 技术栈

- Astro 静态站点 + Tailwind CSS + TypeScript（火星车地面站页为 React island）
- 服务器：阿里云硅谷节点 Ubuntu 24.04 + Nginx，前置 Cloudflare CDN
- 部署：本地 `npm run build` → tarball → SCP 上传 → 在 `/var/www/shuzhiyucai.cn/releases/<时间戳>` 解压并切软链 → `nginx -t && systemctl reload nginx` → Cloudflare URL purge

## 本地开发

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # astro check + astro build
npm test
```

## 内页功能与实验草稿本地审阅

2026-09-05 根据用户反馈恢复原版首页。跨栏目资源搜索、用途筛选与收藏移到独立的 `/resources/` 页面，由导航栏搜索图标进入。三套机械能实验支持自动保存/恢复原始表格，并提供数据、图像、实验回顾和习题的快捷导航。草稿仅在当前浏览器保存，不保存设备连接或未填入表格的采集日志。

审阅运行 `npm run build` 后执行 `npm run review:site`，访问 <http://127.0.0.1:4367/>。此入口使用生产构建，支持 `public/` 下静态模型的目录地址；不要把开发服务器对这类目录的 404 当作构建产物失效。审阅材料见 [本轮审阅记录](review/site-inner-pages-followup/review.md)。候选版未发布。

## 《智启格物》高考真题模拟快照

本地工作树已包含 20 个高考真题交互模型：2026 薄膜冲击独立页保留 10 项自检，其余 19 个模型共用统一运行底座并登记 77 项物理回归测试。20 个页面均支持 `?view=book` 图书模式；测试、参数有效性与模型警告共同控制共享页面的截图门禁。

截至 2026-08-02，本轮快照已通过本地生成核对、`npm test`、生产构建和 20 条模型路由预览。该快照尚未部署到线上，也尚未经过作者审核。书稿截图和模型边界应在作者逐项确认后再标记为定稿。详见 [docs/gaokao-simulations.md](docs/gaokao-simulations.md)。

## 目录约定

```
src/
  components/      # 可复用 Astro 组件
  pages/           # 路由（每个 .astro 即一个页面）
  data/
    exercises/     # 在线实验室结构化习题数据
    lab-reviews/   # 在线实验室「实验回顾」结构化数据
    site.ts        # 站点元数据 / 导航
  styles/global.css

docs/              # 项目文档（设计、运维、教学）
public/            # 静态资源（含 .webp 与原图回退）
scripts/           # 一次性脚本
.local-deploy-notes/  # 本地保存的部署敏感信息（不进 git）
.agents/skills/    # Cursor 工作流 SKILL（已 .gitignore）
```

## 文档索引

| 文档 | 内容 |
|---|---|
| [docs/architecture.md](docs/architecture.md) | 站点结构、关键组件、数据约定 |
| [docs/performance-china-access.md](docs/performance-china-access.md) | 中国大陆访问优化（Cloudflare + Nginx + 资源 + 兼容降级），本轮所有调整与上线状态 |
| [docs/online-lab.md](docs/online-lab.md) | 在线实验室方案、习题数据结构、实验回顾组件 |
| [docs/gaokao-simulations.md](docs/gaokao-simulations.md) | 《智启格物》20 个高考真题模拟、统一底座、截图门禁与审核边界 |
| [docs/student-ai-literacy-evaluation.md](docs/student-ai-literacy-evaluation.md) | 学生 AI 素养评价的现场规则、v4 双轨量规、证据顺序与隐私边界 |
| [docs/exercises/](docs/exercises/) | 三套机械能守恒习题（教师可直接打印分发） |
| [docs/dis-ble-devices.md](docs/dis-ble-devices.md) | DIS 工具 BLE 设备协议 |
| [docs/visit-counter.md](docs/visit-counter.md) | 访问人次统计（自建计数服务 + 页脚展示）架构与运维 |
| [docs/2026-06-11-mars-rover-merge.md](docs/2026-06-11-mars-rover-merge.md) | 尘光一号火星车地面站合并记录（React 集成、CSS 作用域隔离、验证） |
| [docs/website-optimization-plan.md](docs/website-optimization-plan.md) | 网站优化计划（模拟实验显示与教学效果，P0–P3） |
| `.local-deploy-notes/aliyun-shuzhiyucai.md` | 服务器与部署敏感信息（仅本地） |
| `.agents/skills/shuzhiyucai-aliyun-update/SKILL.md` | 部署 / 回滚 SKILL（Cursor 工作流） |

## 学生 AI 素养评价本地审阅

本地工作树包含 77 份八学科代号案例的学生 AI 素养评价页面。页面展示脱敏对话、DeepSeek 第一版、学生提交最终版、AI 研究性评分 v4、评审重构的最优提示词和 DeepSeek 优化对照；不提供数据文件下载，不建立排行榜。

本地审阅服务使用 `npm run review:student-ai-lab`，只监听 `127.0.0.1`。该专题尚未部署到线上；修改发布集后必须先运行 `npm run validate:student-ai-lab && npm run build && npm test`。

## 部署速查

完整流程见 [docs/performance-china-access.md](docs/performance-china-access.md) 与 SKILL；常用命令：

```bash
# 本地
npm run build && npm test
TAG=$(date +%Y%m%d-%H%M%S)
tar -czf /tmp/shuzhiyucai-$TAG.tar.gz -C dist .
scp -i ~/.ssh/id_ed25519_aliyun /tmp/shuzhiyucai-$TAG.tar.gz admin@47.89.213.28:/tmp/

# 服务器
sudo mkdir -p /var/www/shuzhiyucai.cn/releases/$TAG
sudo tar -xzf /tmp/shuzhiyucai-$TAG.tar.gz -C /var/www/shuzhiyucai.cn/releases/$TAG
sudo chown -R www-data:www-data /var/www/shuzhiyucai.cn/releases/$TAG
sudo ln -sfn /var/www/shuzhiyucai.cn/releases/$TAG /var/www/shuzhiyucai.cn/html
sudo nginx -t && sudo systemctl reload nginx
```

Cloudflare 缓存清理必须放在服务器软链切换、`nginx reload` 成功之后执行。不要把 token 写进仓库或 `.env`；本机部署时优先把配置放到已忽略的本地文件：

```bash
.local-deploy-notes/cloudflare.env
```

内容格式：

```bash
export CF_API_TOKEN=xxx
export CF_ZONE_ID=xxx
export SITE_URL=https://shuzhiyucai.cn
```

也可以不写 `export`，直接写成 `CF_API_TOKEN=xxx`。CI 或服务器 shell 中仍可直接配置同名环境变量；真实环境变量会优先于本地文件。然后运行：

```bash
npm run purge:cloudflare-cache
```

默认使用精确 URL purge，会清理首页、`index.html`、构建出的路由入口、Astro 的 `/_astro/` 资源、`/images/` 资源、根目录 logo/campus 图片和 ESP32 库 manifest。Cloudflare API Token 至少需要当前 Zone 的 `Cache Purge` 权限。

如果临时无法判断变更影响的具体 URL，可以使用全站清缓存：

```bash
CF_PURGE_EVERYTHING=1 npm run purge:cloudflare-cache
```

这会调用 Cloudflare 的 `purge_everything`，等同于清空整个 Zone 的边缘缓存，访问量较大时会让后续请求回源更多。

回滚：把 `html` 软链指回上一个 `releases/<旧时间戳>`，再 `nginx -t && systemctl reload nginx`。
回滚后如果 Cloudflare 已缓存新版本，也要重新执行 `npm run purge:cloudflare-cache`，否则浏览器可能仍看到边缘节点里的旧内容。
