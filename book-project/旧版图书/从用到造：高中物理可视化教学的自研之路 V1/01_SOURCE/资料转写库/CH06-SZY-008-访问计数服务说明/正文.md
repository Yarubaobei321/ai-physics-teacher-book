# 访问人次统计（自建计数服务）

## 总览

- **口径**：访问人次。同一浏览器的一次会话（`sessionStorage` 生命周期，含站内多页跳转）只计 1 次；关闭标签页后再访问算新的人次。
- **展示**：所有页面页脚右侧的「累计访问 N 人次」胶囊（`src/components/Footer.astro`）。
- **持久化**：计数存在服务器 `/var/lib/visit-counter/count.json`，与 `/var/www/shuzhiyucai.cn/releases/` 完全隔离，**站点发版、回滚都不会重置计数**。

## 架构

```
浏览器页脚脚本 ──fetch──▶ Nginx /api/visits ──proxy──▶ 127.0.0.1:8787
                                                      visit_counter.py (systemd)
                                                      └─ /var/lib/visit-counter/count.json
```

- 首次会话：`POST /api/visits/hit`（计数 +1 并返回最新值），随后在 `sessionStorage` 标记。
- 同会话再访问：`POST /api/visits`（只读）。
- 服务不可用时页脚显示占位符 `—`，不影响页面其他功能。
- **页面端读写一律走 POST**：站点 Cloudflare 开了边缘缓存（默认 `max-age=14400`），GET 响应会被缓存 4 小时导致读数滞后，而 POST 永远不会被 Cloudflare 缓存。`GET /api/visits` 仅保留给运维 curl 直连 origin 时用。

## 仓库内文件

| 文件 | 作用 |
|---|---|
| `server/visit-counter/visit_counter.py` | 计数服务（Python 标准库，零依赖），部署到服务器 `/opt/visit-counter/` |
| `server/visit-counter/visit-counter.service` | systemd 单元，部署到 `/etc/systemd/system/` |
| `server/visit-counter/nginx-visits.conf` | Nginx `location /api/visits` 反代片段，部署为 `/etc/nginx/snippets/shuzhiyucai-visits.conf` |
| `src/components/Footer.astro` | 页脚展示 + 会话判定脚本 |

## 服务器安装（一次性）

```bash
# 本地上传
scp -i ~/.ssh/id_ed25519_aliyun server/visit-counter/visit_counter.py \
    server/visit-counter/visit-counter.service \
    server/visit-counter/nginx-visits.conf \
    admin@47.89.213.28:/tmp/

# 服务器上
ssh -i ~/.ssh/id_ed25519_aliyun admin@47.89.213.28
sudo mkdir -p /opt/visit-counter
sudo cp /tmp/visit_counter.py /opt/visit-counter/
sudo cp /tmp/visit-counter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now visit-counter
curl -s http://127.0.0.1:8787/api/visits        # 应返回 {"total": 0}

# Nginx：放入 snippets 并在 443 server 块内 include
sudo cp /tmp/nginx-visits.conf /etc/nginx/snippets/shuzhiyucai-visits.conf
# 编辑 /etc/nginx/sites-available/shuzhiyucai.cn，在 443 server 块中加入：
#     include snippets/shuzhiyucai-visits.conf;
sudo nginx -t && sudo systemctl reload nginx
```

## 日常运维

```bash
systemctl status visit-counter                 # 服务状态
cat /var/lib/visit-counter/count.json          # 当前计数
curl -s https://shuzhiyucai.cn/api/visits      # 线上读数
sudo journalctl -u visit-counter -n 50         # 服务日志
```

- 修正计数：停服务 → 改 `count.json` 的 `total` → 启服务（`sudo systemctl stop/start visit-counter`）。
- 服务自动随系统启动（`enable`），崩溃自动拉起（`Restart=always`）。
- 备份：`count.json` 单文件，可随服务器例行备份；丢失则从 0 重计。
