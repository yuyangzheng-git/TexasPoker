# 服务器部署

## 当前服务器（原生部署）

当前服务器 `101.35.6.63` 已有 Nginx 与其他站点，采用预先构建前端 + 独立 Python 环境 + systemd 的方式发布：

- 公开入口：`http://101.35.6.63:3001`
- 当前发布：`/opt/texaspoker/current` → `/opt/texaspoker/releases/20261018-01`
- 后端服务：`texaspoker-api.service`，仅监听 `127.0.0.1:18001`
- 旧账号库：`/opt/texaspoker/shared/data/poker.db`（已停用，仅作存档）
- 持久对局日志：`/opt/texaspoker/shared/logs`
- 私密环境配置：`/opt/texaspoker/shared/server.env`，不要提交或公开
- 旧版配置与数据库备份：`/opt/texaspoker/backups/pre-20261018`

旧项目目录 `/var/www/poker-game` 保留。旧的 `poker-backend.service` 已停用，原占用 8000 的扑克进程已退出。其他项目的服务与端口继续使用原配置。当前版本为纯游客模式：不再提供注册、登录、个人页或后台管理，旧账号库不再读取，`JWT_SECRET_KEY` 等账号相关配置可以删除。

维护与验收（在服务器执行）：

```sh
sudo systemctl status texaspoker-api
sudo journalctl -u texaspoker-api -n 50 --no-pager
sudo systemctl restart texaspoker-api
sudo nginx -t && sudo nginx -s reload
/opt/texaspoker/shared/venv/bin/python /opt/texaspoker/current/deploy/smoke_test.py http://127.0.0.1:3001
```

原有 Nginx 当前由已有主进程运行，配置更新使用 `nginx -s reload`；不要再启动第二个实例。新后端与 Nginx 均已设置为开机启动。应用重启会终止内存中的进行中牌局。

本仓库的 `texaspoker-api.service` 和 `nginx.native.conf` 对应上述部署。后续更新先在独立 release 目录解压，保留 `logs` 指向共享日志目录的链接，核对依赖并备份 SQLite，再切换 `current` 链接与重启后端。首次回退至旧版时，应先停止新后端，恢复备份的 Nginx 配置，并使用旧目录自己的 `backend/venv/bin/python3` 启动旧后端；原旧 systemd 启动命令所用的全局环境存在问题，不能直接启用。

## 新服务器（Docker Compose）

需要 Linux 服务器、Docker Engine 和 Compose v2。发布当前工作目录，包含未提交的 UI 与规则修复；仅拉取 GitHub 的 main 不包含这些改动。

## 首次启动

在服务器的独立目录中放入项目文件，不要上传本地 `.env`、数据库、日志、`node_modules` 或虚拟环境。

```sh
python3 deploy/init_env.py
# 编辑服务器上新建的 .env，把 FRONTEND_URL 改成实际访问地址。
# 例如 FRONTEND_URL=http://服务器IP:8080
docker compose up -d --build --wait
docker compose ps
curl --fail http://127.0.0.1:8080/api/health
docker compose exec -T api python /app/deploy/smoke_test.py http://web:8080
```

默认入口为 `http://服务器IP:8080`。服务器防火墙/云安全组需要允许所选入口端口。后端 8000 不发布到主机。`HTTP_PORT` 可改为其他空闲端口。对局日志放在独立持久卷，容器重建后保留。

默认 `POKER_AGENT_MODE=strategy`，使用各角色的本地策略，不需要 API 密钥。要启用付费模型，在服务器 `.env` 中设置 `POKER_AGENT_MODE=llm` 和 `ANTHROPIC_API_KEY`，确认 `ANTHROPIC_BASE_URL` 是所选兼容服务的地址，再重新启动。密钥不进入前端构建与镜像。

## 域名与 HTTPS

若服务器已有 HTTPS 反向代理，将域名转发到本机 `127.0.0.1:8080`，并在 `.env` 设置 `BIND_ADDRESS=127.0.0.1`、`FRONTEND_URL=https://实际域名`。外层代理必须转发 WebSocket Upgrade/Connection，并设置长连接超时。当前内层 Nginx 仅提供 HTTP；HTTPS 证书由外层代理管理。

外层 Nginx 的 location 示例（放入已有证书的 server 块）：

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;
}
```

应用前端根据当前访问协议自动使用 WS 或 WSS。公开入口验收：在安装后端依赖的环境中运行 `python deploy/smoke_test.py https://实际域名`，会检查建桌、WebSocket 验证、完整一手行动与结算。

## 更新、备份与恢复

每次更新前保留旧发布目录和镜像，先备份日志，再执行 `docker compose up -d --build --wait`。不要执行 `docker compose down -v`，它会删除持久数据。

```sh
mkdir -p backups
docker compose cp api:/app/logs backups/logs
```

另行保存服务器 `.env`。切回旧版本时使用旧发布目录/镜像并保留同一组卷。

仅运行一个后端工作进程：当前牌桌存在内存中，重启会终止正在进行的对局；落盘日志保留。Nginx 为建桌提供基础频率限制。
