# 服务器部署指南

本指南介绍如何将 License Manager 部署到生产服务器。

## 前置要求

- 服务器：Ubuntu 20.04+ / CentOS 7+ / Debian 10+
- 域名：已解析到服务器 IP
- Docker：20.10+
- Docker Compose：2.0+
- 内存：至少 2GB
- 磁盘：至少 20GB

## 快速部署

### 1. 准备服务器

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo apt install docker-compose -y

# 验证安装
docker --version
docker-compose --version
```

### 2. 克隆项目

```bash
git clone https://github.com/Wcowin/OneClip-License-Manager.git
cd OneClip-License-Manager
```

### 3. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置
nano .env
```

**必须配置的变量：**

```bash
# 数据库配置
DB_PASSWORD=your_secure_password_here
DB_ROOT_PASSWORD=your_root_password_here

# 管理员配置
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_admin_password_here

# API 密钥
API_KEY=your_random_api_key_here

# 会话密钥
ADMIN_SECRET_KEY=your_secret_key_here_change_this_in_production

# 域名配置（重要）
ZPAY_NOTIFY_URL=https://yourdomain.com/api/payment/notify
ZPAY_RETURN_URL=https://yourdomain.com/client/complete_order.html

# ZPAY 支付配置（可选）
ZPAY_PID=your_zpay_pid
ZPAY_KEY=your_zpay_key
ZPAY_API_URL=https://zpayz.cn/
```

### 4. 配置域名

**DNS 配置：**

```
A 记录: yourdomain.com → 服务器IP
A 记录: www.yourdomain.com → 服务器IP
```

**修改 docker-compose.yml：**

```yaml
web:
  image: nginx:alpine
  container_name: license-manager-web
  restart: always
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./admin:/usr/share/nginx/html/admin
    - ./client:/usr/share/nginx/html/client
    - ./nginx.conf:/etc/nginx/nginx.conf
    - ./ssl:/etc/nginx/ssl
  networks:
    - license-network
```

### 5. 配置 SSL 证书

**使用 Let's Encrypt：**

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取证书
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# 复制证书
sudo mkdir -p ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/
sudo chmod 644 ssl/*
```

**创建 nginx.conf：**

```nginx
events {
    worker_connections 1024;
}

http {
    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        client_max_body_size 10M;

        location /admin/ {
            alias /usr/share/nginx/html/admin/;
            index login.html;
        }

        location /client/ {
            alias /usr/share/nginx/html/client/;
            index index.html;
        }

        location /api/ {
            proxy_pass http://license-manager-api:5000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### 6. 启动服务

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 7. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 检查 API
curl https://yourdomain.com/api/health

# 检查 Web
curl https://yourdomain.com/client/

# 检查数据库
docker exec -it license-manager-mysql mysql -uroot -p
```

## 安全配置

### 1. 防火墙配置

```bash
# Ubuntu/Debian
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 2. 数据库安全

```bash
# 限制数据库端口访问
# 修改 docker-compose.yml，删除 mysql 的 ports 映射
# 只允许 api 容器访问数据库
```

### 3. API 安全

```bash
# 在 .env 中设置强密码
API_KEY=$(openssl rand -hex 32)
ADMIN_SECRET_KEY=$(openssl rand -hex 32)

# 限制 API 访问频率（可选，需要修改代码）
```

### 4. 定期备份

```bash
# 创建备份脚本
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
mkdir -p $BACKUP_DIR

# 备份数据库
docker exec license-manager-mysql mysqldump -uroot -p$DB_ROOT_PASSWORD license_db > $BACKUP_DIR/backup_$DATE.sql

# 保留最近 7 天的备份
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
EOF

chmod +x backup.sh

# 添加到 crontab
(crontab -l 2>/dev/null; echo "0 2 * * * /path/to/backup.sh") | crontab -
```

## 监控

### 1. 日志监控

```bash
# 查看实时日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f api
docker-compose logs -f web
docker-compose logs -f mysql
```

### 2. 性能监控

```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
df -h
du -sh /var/lib/docker
```

### 3. 健康检查

```bash
# 创建健康检查脚本
cat > healthcheck.sh << 'EOF'
#!/bin/bash
API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" https://yourdomain.com/api/health)
WEB_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" https://yourdomain.com/client/)

if [ "$API_HEALTH" != "200" ] || [ "$WEB_HEALTH" != "200" ]; then
    echo "Health check failed: API=$API_HEALTH, WEB=$WEB_HEALTH"
    # 发送告警通知
    exit 1
fi

echo "Health check passed"
exit 0
EOF

chmod +x healthcheck.sh

# 添加到 crontab（每 5 分钟检查一次）
(crontab -l 2>/dev/null; echo "*/5 * * * * /path/to/healthcheck.sh") | crontab -
```

## 故障排查

### 1. 服务无法启动

```bash
# 查看日志
docker-compose logs

# 查看容器状态
docker-compose ps

# 重启服务
docker-compose restart

# 重新构建
docker-compose down
docker-compose build
docker-compose up -d
```

### 2. 数据库连接失败

```bash
# 检查数据库容器
docker exec -it license-manager-mysql mysql -uroot -p

# 检查网络连接
docker exec license-manager-api ping license-manager-mysql

# 查看数据库日志
docker-compose logs mysql
```

### 3. 支付回调失败

```bash
# 检查 ZPAY 配置
cat .env | grep ZPAY

# 检查回调 URL
curl -X POST https://yourdomain.com/api/payment/notify

# 查看支付日志
docker-compose logs api | grep ZPAY
```

## 更新部署

```bash
# 拉取最新代码
git pull

# 重新构建
docker-compose build

# 重启服务（无数据丢失）
docker-compose up -d

# 数据迁移（如果有）
# docker exec license-manager-mysql mysql -uroot -p < migration.sql
```

## 性能优化

### 1. 数据库优化

```sql
-- 在 MySQL 容器中执行
-- 创建索引
CREATE INDEX idx_activation_code ON licenses(activation_code);
CREATE INDEX idx_email ON licenses(email);
CREATE INDEX idx_status ON licenses(status);
CREATE INDEX idx_created_at ON licenses(created_at);
```

### 2. Nginx 缓存

```nginx
# 添加到 nginx.conf
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=1g inactive=60m;

location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    proxy_cache my_cache;
    proxy_cache_valid 200 7d;
    expires 7d;
}
```

### 3. 连接池配置

```python
# 在 backend/app.py 中添加
# MySQL 连接池配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'license_user'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME', 'license_db'),
    'charset': 'utf8mb4',
    'pool_size': 10,
    'pool_reset_session': True
}
```

## 常见问题

### Q: 如何修改端口？

修改 `docker-compose.yml` 中的端口映射：
```yaml
web:
  ports:
    - "8080:80"  # 改为 8080:80
```

### Q: 如何增加服务器资源？

修改 `docker-compose.yml` 中的资源限制：
```yaml
api:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
```

### Q: 如何备份数据？

参考"定期备份"部分，使用 mysqldump 备份数据库。

### Q: 如何恢复数据？

```bash
# 恢复数据库
docker exec -i license-manager-mysql mysql -uroot -p$DB_ROOT_PASSWORD license_db < backup.sql
```

## 支持

- 文档：[docs/](./docs/)
- 问题反馈：[GitHub Issues](https://github.com/Wcowin/OneClip-License-Manager/issues)
- 邮件支持：support@license-manager.com
