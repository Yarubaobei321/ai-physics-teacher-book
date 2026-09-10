# 中国大陆访问优化记录

> 起因：本站托管在美国硅谷阿里云节点，跨太平洋链路对中国大陆移动端不友好（首字节延迟、丢包、握手开销）。本文记录已落地的全部优化项与状态，供后续维护参考。

## 总体策略

按"无需 ICP 备案"的边界做到尽可能好，主要分四层：

1. **CDN 边缘**：Cloudflare 免费档（HTML 缓存 + Brotli + HTTP/3 + Tiered Cache 等）
2. **Origin Nginx**：HTTP/2 + HSTS + Gzip + 长缓存策略
3. **资源体积**：图片 WebP + 懒加载 + favicon 瘦身
4. **页面体验**：浏览器兼容降级提示、移动端 Header 压缩 + 横滚 fade、SEO/分享元数据

国内 CDN 与 ICP 备案的方案保留为长期选项，目前不启用。

## 1. Cloudflare 边缘配置（已开启，由用户在 Dashboard 完成）

| 项 | 状态 | 备注 |
|---|---|---|
| Caching → Cache Rules | HTML 缓存命中 | 默认 HTML 是 `DYNAMIC`（不缓存），通过 Cache Rule 让 `*.html` 也命中边缘 |
| Brotli | ON | 文本资源传输体积更小 |
| Early Hints | ON | 提前下发 `103` 节省首屏时间 |
| HTTP/3 (QUIC) | ON | 移动网络更快 |
| 0-RTT Connection Resumption | ON | 重复访问减少握手 |
| Tiered Cache | ON | 中央缓存层降低 origin 流量 |
| Always Online™ | ON | origin 故障时回源 Wayback |
| Always Use HTTPS | ON | 强制 HTTPS |
| Automatic HTTPS Rewrites | ON | 修正混合内容 |
| Min TLS Version | 1.2 | 兼容旧设备的同时拒绝弱 TLS |
| Rocket Loader | OFF | 避免 JS 执行时序问题，本站不需要 |

**强更新切换**：上线重要内容后，服务器软链切换并 `nginx reload` 成功后运行 `npm run purge:cloudflare-cache`，按 URL 清理首页、路由入口和关键静态资源。若无法判断具体 URL，可临时运行 `CF_PURGE_EVERYTHING=1 npm run purge:cloudflare-cache` 全站清缓存；这会让后续请求更多回源。

## 2. Origin Nginx 配置（已写入 `/etc/nginx/sites-available/shuzhiyucai.cn`）

关键 directive：

- `listen 443 ssl http2;` — 启用 HTTP/2
- `add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;`
- `add_header X-Content-Type-Options "nosniff" always;`
- `add_header Referrer-Policy "strict-origin-when-cross-origin" always;`
- 静态资源（`css|js|mjs|png|jpg|jpeg|gif|svg|webp|ico|woff2?|ttf|otf|wasm`）：`expires 1y; add_header Cache-Control "public, immutable";`
- HTML：`expires 5m; add_header Cache-Control "public, must-revalidate";`
- Gzip：`gzip on; gzip_comp_level 6; gzip_min_length 1024; gzip_proxied any; gzip_vary on;` 加上常见文本类型

> Nginx `add_header` 不会被子 location 继承。HSTS / 安全头需要在每个 `location` 块里重复声明。

## 3. 资源体积优化

### 图片 → WebP

用 `cwebp` 把 6 张关键图转为 WebP，整体 4.79 MB → 644 KB（节省 87%）：

| 路径 | 原大小 | WebP |
|---|---|---|
| `/campus.jpeg` | 156 KB | 118 KB |
| `/logo-web.png` | 329 KB | 37 KB |
| `/images/mechanical-energy-falling-body.png` | … | … |
| `/images/mechanical-energy-curved-ramp.png` | … | … |
| `/images/mechanical-energy-air-track.png` | … | … |
| `/images/photogate-motion-lab.png` | … | … |

模板：

```astro
<picture>
  <source srcset="/path/foo.webp" type="image/webp" />
  <img src="/path/foo.png" width="..." height="..." loading="lazy" decoding="async" />
</picture>
```

首屏 hero 图加 `fetchpriority="high"` 而不是 `loading="lazy"`。

### Favicon 瘦身

`<link rel="icon">` 由 `/logo.png`（1.5 MB）切到 `/logo-web.png`（337 KB），并复用为 `apple-touch-icon`。

## 4. SEO / 分享 / 移动端体验

### `<head>` 元数据（`src/components/BaseLayout.astro`）

- `theme-color`（亮 / 暗两份，配合系统主题）
- `color-scheme: light`
- `format-detection: telephone=no`（避免 iOS 把数字识别为电话）
- `apple-mobile-web-app-*`（含 status bar style）
- `viewport`：含 `viewport-fit=cover`，适配 iPhone 刘海屏
- `link rel="canonical"` — 自动用 `Astro.site` + 当前路径
- `link rel="apple-touch-icon"` → `/logo-web.png`
- Open Graph：`og:type` / `og:site_name` / `og:title` / `og:description` / `og:url` / `og:image` / `og:locale`
- Twitter Card：`summary_large_image`

每个页面通过 `BaseLayout` 的 props 覆盖：

```astro
<BaseLayout
  title="网页版 DIS | 育才一中物理创新实验室"
  description="网页版 DIS 实验工具：通过浏览器连接 ESP32 BLE 接收力、距离、光电门数据，实时绘图并导出 CSV。"
>
```

`astro.config.mjs` 配 `site: 'https://shuzhiyucai.cn'`，是 canonical 与 og:image 拼绝对 URL 的前提。

### 浏览器兼容降级提示

- `src/components/BrowserSupportNotice.astro` 客户端检测：
  - `window.isSecureContext`（非 HTTPS 直接换文案）
  - `'bluetooth' in navigator`
  - `'serial' in navigator`
- 不支持时才显示琥珀色横幅，文案区分两个 API：
  - `/dis/` → `feature="bluetooth"`，推荐桌面 Chrome / Edge / Opera 或 Android Chrome；提示 iOS 系统限制
  - `/programming/` → `feature="serial"`，推荐桌面 Chrome / Edge / Opera；不支持移动端与 Safari
- 都附 MDN 文档外链。

### 移动端 sticky Header（`src/components/Header.astro`）

- 滚动 > 8px 时给 header 加 `data-scrolled='true'`：
  - logo 行高 4rem → 3rem
  - logo 图 40 → 28 px
  - 标题字号收紧
  - 导航行 padding 收紧
- 桌面端不变。

### 移动端导航横滚 fade mask

- 移动 nav 包一层 `.mobile-nav-wrapper`，左右各 28px 渐变伪元素
- 监听 `scrollLeft` 设置 `data-can-scroll-left/right`，到边时蒙层自动隐藏
- 初始化时把激活的 nav 项滚到视口中央

### 习题区跳转锚点

- 每个 `*EnergyLab.astro` 顶部加「跳到配套习题 ↓」按钮，`href="#exercises-<slug>"`
- `ExerciseSection.astro` 的 `<section>` 含 `id="exercises-<slug>"` + `scroll-mt-24` + `data-exercise-section="<slug>"`
- `src/styles/global.css` 全局 `html { scroll-behavior: smooth }`

### 习题徽章去重

`ExerciseSection.astro` 删掉了右上角独立的 `kindLabel`（"单选题/多选题/..."），把灰字 `category` 升级为靠右的圆角徽章，避免和题型重复。

## 5. 验证清单

每次部署后建议至少 curl 这几项：

```bash
# 在线状态 + HTTP/2
for url in https://shuzhiyucai.cn/ https://www.shuzhiyucai.cn/ https://shuzhiyucai.cn/dis/ \
           https://shuzhiyucai.cn/programming/ https://shuzhiyucai.cn/online-lab/falling-body/; do
  curl -sI "$url" | head -1
done

# head meta
curl -s https://shuzhiyucai.cn/ | grep -E 'apple-touch-icon|og:image|theme-color|canonical'

# 兼容降级提示就位（DOM 默认 hidden，由 JS 在不支持时显示）
curl -s https://shuzhiyucai.cn/dis/ | grep -c 'data-feature="bluetooth"'
curl -s https://shuzhiyucai.cn/programming/ | grep -c 'data-feature="serial"'

# 实验回顾 + 习题区
for slug in falling-body curved-ramp air-track; do
  curl -s "https://shuzhiyucai.cn/online-lab/$slug/?cb=$(date +%s)" \
    | grep -cE "lab-review-$slug|exercises-$slug"
done

# 静态资源缓存策略（origin 直访）
curl -sI --resolve shuzhiyucai.cn:443:47.89.213.28 https://shuzhiyucai.cn/logo-web.webp | grep -i cache-control
```

## 6. 长期路线（暂不做）

| 方向 | 触发条件 |
|---|---|
| ICP 备案 + 国内 CDN（阿里 / 腾讯 / 七牛） | 业务规模 / 学校行政流程允许时 |
| 国内 origin 镜像（杭州 / 北京） | 中国大陆访问量稳定上升时 |
| 字体子集化 | 当引入更多中文字体时 |
| HTTP 3 origin（Nginx 1.25 quic） | Cloudflare → origin 仍需 H3 时 |
