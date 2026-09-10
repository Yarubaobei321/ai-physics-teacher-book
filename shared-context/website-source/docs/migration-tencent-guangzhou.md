# 迁移到腾讯云广州 + 个人 ICP 备案 操作清单

> 目标：把站点从「阿里云硅谷 + Cloudflare」迁到「腾讯云广州」，并完成个人 ICP 备案。
> 核心策略：**备案期间老站继续运行，全程零停机**。腾讯云服务器只要"存在"即可备案，不必先搬站。等备案号下来再搬站、切 DNS、下线旧设施。

当前架构：Astro 静态站 + Python 访问计数微服务（systemd + Nginx 反代 `/api/visits`），源站在阿里云硅谷（`47.89.213.28`），前置 Cloudflare。域名 `shuzhiyucai.cn` 注册在阿里云（万网）。迁移后**彻底去掉 Cloudflare**。

---

## 交接背景（给接手的 agent / 维护者）

读这一节，你就能在不翻聊天记录的情况下接手本次迁移。

### 项目性质与技术栈
- 一名高中物理老师的个人物理实验门户站，**非经营性**。Astro 5 静态站（Tailwind + TS，火星车地面站为 React island），`npm run build` 产出 `dist/`。
- 唯一后端：`server/visit-counter/visit_counter.py`（Python 标准库零依赖，systemd 跑在 `127.0.0.1:8787`，Nginx 反代 `/api/visits`）。
- 部署机制（阿里云现状）：本地 build → tarball → scp → 服务器 `releases/<时间戳>` 解压并切软链 → `nginx -t && systemctl reload nginx`。详见 [README.md](../README.md) 与 [docs/performance-china-access.md](performance-china-access.md)。

### 为什么迁 + 已定的决策
- 迁移动因：阿里云硅谷跨太平洋对国内访问不友好，且**要在国内做 ICP 备案**，故迁到腾讯云广州。
- 已定决策：① **个人备案**（非单位）；② 域名注册商保持阿里云（万网，工信部批准，无需转移）；③ **迁移后彻底去掉 Cloudflare**，DNS 直达腾讯云源站。
- 备案归属：按**主办者本人所在省**（预计广东管局），与服务器在广州无强绑定。

### ⚠️ 本次会话已完成的「去机构化」准备（备案前置，已改代码，未部署）
为提高个人备案过审率，已系统性移除站内的"学校官网"信号。接手者需知道这些是**有意为之**，不要回退：
1. **改名**：全站 `育才一中物理创新实验室` → `育才物理创新实验室`（去掉具体校名"一中"，119 处）。
2. **学生作品页下线**：`git rm` 删除 `public/simulations/student-works/`（含班级+学生真实姓名的 205+ 个评审/作品 HTML）；删除路由 `src/pages/simulations/students.astro`、组件 `src/components/StudentWorks.astro`、数据 `src/data/student-works.ts`；`src/pages/simulations/index.astro` 改为只剩「教师作品」单入口。**教师作品（动量模型，`public/simulations/momentum/`）保留**。备案后若要恢复展示，可 `git revert` 对应提交。
3. **去掉「公众号」**：删除 `Footer.astro` 的公众号行、`site.ts` 的 `account` 字段、6 个 momentum HTML 里的公众号行。
4. **定位改写为「教师个人兴趣站」**：`site.ts` 简介/方向、`Footer` 标语、首页与科创天地的"选修课/同学们/学生科创作品"、`project-learning.ts` 的"选修课名额/校内报名"奖励，全部改成中性/个人口吻。
5. **去掉交互工具的身份字段**：`ProjectAnalysisWorkbench.astro` 与 `project-learning/ultrasonic-lab.astro` 删除「学生姓名 / 班级·分组」输入框及导出 CSV/PNG 的姓名班级水印；`project-learning.ts` 报告封面去掉"姓名、班级"，提交说明删除收作业邮箱 `964631805@qq.com`（改为"成果整理"）。工具的数据分析/拟合/导出功能**全部保留**。
6. **测试同步**：`scripts/verify-site.mjs` 删掉了校验已下线内容的断言；当前 `npm run build`（21 页）+ `npm test`（7/7 PASS）均通过。

### 关键文件 / 路径（迁移时要复刻或迁移）
| 项 | 阿里云现状路径 | 说明 |
|---|---|---|
| 站点发布目录 | `/var/www/shuzhiyucai.cn/`（`releases/*` + `html` 软链） | 静态产物 |
| Nginx 配置 | `/etc/nginx/sites-available/shuzhiyucai.cn` | HTTP/2、缓存、安全头、`/api/visits` 反代 |
| 计数服务 | `/opt/visit-counter/visit_counter.py` | systemd `visit-counter.service` |
| **计数数据** | `/var/lib/visit-counter/count.json` | **迁移时必须 scp 过去，否则访问人次归零** |
| 站点常量 | `astro.config.mjs` `site: 'https://shuzhiyucai.cn'` | canonical / og 依赖，不改 |

### 待办（**等切到腾讯云稳定后再做**，本次按用户要求未动）
- ~~在 `Footer.astro` 加 ICP 备案号占位~~ ✅ **已搭好（配置驱动）**：`src/data/site.ts` 新增 `icp`、`police` 字段，`Footer.astro` 条件渲染。当前两字段为空 → 页脚不显示任何号。**备案号下来后，只需把 `site.ts` 的 `icp` 填成 `'粤ICP备XXXXXXXX号'`，重新 build 部署即可显示**（带 `beian.miit.gov.cn` 链接）。
- 上线 30 日内做**公安联网备案**，拿到号后把 `site.ts` 的 `police` 填上即可（机制同上，带 `beian.mps.gov.cn` 链接）。
- **清理仓库 Cloudflare / 阿里云残留**：`scripts/purge-cloudflare-cache.mjs`、`package.json` 的 `purge:cloudflare-cache`、`README.md` 与 `docs/performance-china-access.md` 的 Cloudflare/阿里云硅谷表述、`.local-deploy-notes/` 旧密钥。
- （可选）接腾讯云 EdgeOne/CDN 替代原 Cloudflare 边缘加速。

---

## 阶段 0 · 前置确认（动手前先核对，否则备案会卡）

- [ ] **域名实名 = 你本人**。登录阿里云域名控制台，确认 `shuzhiyucai.cn` 的实名认证主体是你个人身份证（不是学校、不是别人）。个人备案要求域名实名信息与备案主体一致，否则「域名核验」过不了。
- [ ] **域名在有效期内**，且 `.cn` 已实名（阿里云/万网是工信部批准注册商，✓）。
- [ ] **想好备案省份**。个人备案归属地按**你本人证件/居住地所在省**走，不是按服务器位置。你人在广东 → 走广东管局；服务器在广州只是接入商节点，两者不必同省。
- [ ] **⚠️ 网站名称要重新斟酌**。个人备案对网站名称审得严，「育才物理创新实验室」带"实验室"机构感，广东管局有被驳回风险。备案表里填的网站名称**可以和站内标题不同**，挑一个更个人化的报上去即可，站内显示名不受影响。
  - 规避词：实验室 / 中心 / 平台 / 学院 / 网 / 系统 / 团队 / 官方 / 教育（机构感或需前置审批）。
  - **推荐候选**（按个人备案过审稳妥度排序）：
    1. `<姓氏>老师的物理实验笔记` —— 带个人称谓，过审率最高（如「李老师的物理实验笔记」）。
    2. `物理实验笔记` / `物理实验手记` —— 简洁、个人化、零机构感。
    3. `物理实验探究小站` —— "小站"是个人备案友好词。
    4. `数智物理实验笔记` —— 呼应域名 `数智育才`，又不带机构词。
  - 备案「网站名称」最终选定后回填此处：**数智物理实验笔记**（已定）
- [ ] **服务内容类目避开敏感项**。备案时「服务内容」选「个人博客 / 作品展示 / 技术分享」一类；**不要选「教育」**（部分管局教育类需前置审批）。本站是非经营性工具站，按非经营备案即可，别出现"培训/招生/收费"字样（这些已在上一轮清理掉）。

---

## 阶段 1 · 买服务器 + 提交备案（老站不动，可正常访问）

### 1.1 购买腾讯云服务器（广州）
- [ ] 买**轻量应用服务器**（够用、便宜）或 CVM，地域选**广州**，镜像 **Ubuntu 24.04 LTS**，配置 ≥ 2核2G，带独立公网 IP。
- [ ] 备案对服务器有要求：**包年包月**、剩余有效期通常需 **≥ 3 个月**。买 1 年最省心。
- [ ] 在轻量服务器「防火墙」/CVM「安全组」放行端口：**22（SSH）、80（HTTP）、443（HTTPS）**。

### 1.2 生成备案授权码
- [ ] 腾讯云控制台 → 「备案」→ 用刚买的服务器**生成备案授权码（备案服务码）**。一个授权码能备的域名个数有配额，本次只备 1 个域名，足够。

### 1.3 提交备案（腾讯云备案小程序 / 控制台）
- [ ] 填**主体信息（个人）**：姓名、身份证、手机、邮箱、真实居住地址。
- [ ] 填**网站信息**：域名 `shuzhiyucai.cn`、网站名称（用阶段 0 斟酌后的个人化名称）、服务内容（非经营、个人类目）。
- [ ] 上传证件 + **人脸核验**（用腾讯云 App / 小程序扫脸）。
- [ ] **腾讯云初审**（约 1–2 工作日）。
- [ ] **工信部短信核验**：初审过后工信部下发短信/「一证通查」核验，按提示在规定时间内完成，否则退回。
- [ ] **管局审核**：广东管局，**1–20 工作日**（实际常见 3–10 天）。其间老站照常在 Cloudflare→阿里云上跑，不受影响。
- [ ] **拿到备案号**（形如 `粤ICP备XXXXXXXX号`）。

> 备案期间不要把 `shuzhiyucai.cn` 解析到腾讯云广州 IP——未备案域名指向腾讯大陆 IP 时，80/443 会被拦截。保持解析在 Cloudflare 即可。

---

## 阶段 2 · 备案号下来后：搭新站（仍不切流量，先在新机器上跑通）

### 2.1 服务器初始化（腾讯云广州机器）
- [ ] SSH 登录，建普通用户 + 上传 SSH 公钥，禁用密码登录（可选但推荐）。
- [ ] 安装：`nginx`、`python3`、`certbot`（`python3-certbot-nginx`）。
- [ ] 开 `ufw`：放行 22/80/443。

### 2.2 部署静态站（复刻阿里云那套）
- [ ] 本地：`npm run build && npm test`，打包 `dist/` 成 tarball，`scp` 到腾讯云。
- [ ] 服务器：解压到 `/var/www/shuzhiyucai.cn/releases/<时间戳>/`，软链到 `html`，`chown www-data`。
- [ ] 复刻 Nginx 配置 `/etc/nginx/sites-available/shuzhiyucai.cn`（HTTP/2、Gzip、静态长缓存、HTML 短缓存、安全头），可直接照搬 [docs/performance-china-access.md](performance-china-access.md) 第 2 节。

### 2.3 ⚠️ TLS 证书自己签（关键变化：没有 Cloudflare 兜底了）
- [ ] 以前 HTTPS 是 Cloudflare 边缘提供的；去掉 Cloudflare 后，**源站必须自己装有效证书**。
- [ ] 用 **certbot + Let's Encrypt** 签 `shuzhiyucai.cn` 和 `www.shuzhiyucai.cn`，自动续期：
      `sudo certbot --nginx -d shuzhiyucai.cn -d www.shuzhiyucai.cn`
      （也可用腾讯云免费 DV 证书，但要手动每年换；certbot 自动续期更省事。）
  > 注意：certbot 签发需要域名已能解析到本机并通过 80 端口验证——这一步要等阶段 3 切了 DNS 之后，或先用 DNS-01 验证。实操上：可在阶段 3 切 DNS 后立即 `certbot --nginx` 一次签好。

### 2.4 部署访问计数服务（别丢了历史访问数）
- [ ] 跑 `scripts/deploy-visit-counter.sh` 那套：`visit_counter.py` 放 `/opt/visit-counter/`，装 `visit-counter.service`（systemd），Nginx 加 `/api/visits` 反代到 `127.0.0.1:8787`（见 `server/visit-counter/nginx-visits.conf`）。
- [ ] **迁移计数文件**：从阿里云 `scp` 下 `/var/lib/visit-counter/count.json`，放到腾讯云同路径，否则累计访问人次会清零。
- [ ] `systemctl enable --now visit-counter`，`curl 127.0.0.1:8787` 自测。

### 2.5 加上备案号公示（法律要求，管局会复查）
- [ ] 备案号下来后**必须**在网站底部展示 `粤ICP备XXXXXXXX号`，并链接到 `https://beian.miit.gov.cn`。
- [ ] **占位已搭好（配置驱动）**：只需把 `src/data/site.ts` 的 `icp` 字段填成 `'粤ICP备XXXXXXXX号'`，`npm run build` 后部署，页脚自动出现带链接的备案号。无需改组件。
- [ ] 留空时页脚不显示任何号——**切勿在备案通过前填入未生效的号**。

---

## 阶段 3 · 切流量到腾讯云 + 去掉 Cloudflare

> 选低峰时段操作。切之前先用 `--resolve` 直连腾讯云 IP 验证新站完全正常。

- [ ] **本机直连验证**：`curl -I --resolve shuzhiyucai.cn:443:<腾讯云IP> https://shuzhiyucai.cn/` 等关键页面，确认 200 + 内容正确。
- [ ] **改 DNS / 去 Cloudflare**：当前域名很可能用的是 Cloudflare 的 nameserver。去掉 Cloudflare 的做法二选一：
  - 方案 A（推荐）：在阿里云域名处把 **nameserver 改成腾讯云 DNSPod**，在 DNSPod 加 A 记录 `@` 和 `www` → 腾讯云广州 IP。DNS 跟服务器同厂商，管理方便。
  - 方案 B：nameserver 改回**阿里云 DNS**，在阿里云解析里加 A 记录指向腾讯云 IP。
  - 两种都意味着**不再经过 Cloudflare 代理**，解析直达腾讯云源站。
- [ ] DNS 生效后（几分钟到 48 小时，通常很快），**签 TLS 证书**：`sudo certbot --nginx -d shuzhiyucai.cn -d www.shuzhiyucai.cn`。
- [ ] 全面验证：浏览器访问 `https://shuzhiyucai.cn/`、`/simulations/`、`/programming/`、`/dis/`、访问计数是否正常、HTTPS 锁是否有效、`www` 跳转是否正常。
- [ ] 观察 1–2 天确认稳定。

---

## 阶段 4 · 收尾

- [ ] **公安联网备案**：网站上线后 **30 日内**到 `https://beian.mps.gov.cn` 做公安备案，拿到公安备案号后也在底部公示（同样是 Footer 一处改动）。
- [ ] **下线阿里云**：确认腾讯云稳定后，停掉/退订阿里云硅谷实例。
- [ ] **删 Cloudflare 配置**：Cloudflare 账号里删掉该 Zone（或保留但不再使用）。
- [ ] **清理仓库里 Cloudflare 残留**（去掉已无用的部署步骤，避免误导后续部署）：
  - `scripts/purge-cloudflare-cache.mjs`、`package.json` 的 `purge:cloudflare-cache`
  - `README.md` / `docs/performance-china-access.md` 里 Cloudflare 相关段落与「阿里云硅谷」表述
  - `.local-deploy-notes/` 里阿里云/Cloudflare 的密钥与备注
  > 这些是代码改动，等切换稳定后再做；需要时我帮你一次性清干净。
- [ ] （可选加速）备案完成后可接 **腾讯云 EdgeOne / CDN**（需已备案）替代原 Cloudflare 的边缘缓存能力，国内访问更快。

---

## 关键提醒汇总

1. **顺序就是省心的关键**：先备案（老站不动）→ 再搭新站 → 再切 DNS。别一上来就把域名指向腾讯云，否则未备案被拦、老站也断。
2. **域名实名必须是你本人**，否则个人备案第一步就卡。
3. **网站名称要个人化**，「实验室」有被广东管局驳回的风险，先想好备选。
4. **TLS 要自己签**（certbot），这是去掉 Cloudflare 后最容易忘的一步。
5. **count.json 要迁过去**，否则访问人次归零。
6. **备案号 + 公安备案号必须在底部公示**（两处 Footer 代码改动，可让我帮你加）。
</content>
