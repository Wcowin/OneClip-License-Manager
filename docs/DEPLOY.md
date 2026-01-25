# License Manager 部署指南

## 部署方式

本系统支持多种部署方式：

1. **Docker Compose**（推荐）- 最简单快速
2. **手动部署** - 适合自定义环境
3. **云服务部署** - 适合生产环境

---

## 方式1：Docker Compose 部署（推荐）

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+

### 快速部署

```bash
# 1. 克隆项目
git clone https://github.com/yourname/license-manager-demo.git
cd license-manager-demo

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置数据库密码和API密钥

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f

# 5. 测试服务
curl http://localhost:5000/health
```

### 环境变量配置

编辑 `.env` 文件：

```bash
# 数据库配置
DB_ROOT_PASSWORD=root_secure_password  # MySQL root密码
DB_USER=license_user                  # 应用数据库用户
DB_PASSWORD=license_secure_password   # 应用数据库密码
DB_NAME=license_db                    # 数据库名称

# API配置
API_KEY=your_secure_api_key_here      # API密钥（必须设置）
```

### 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f api
docker-compose logs -f mysql

# 进入容器
docker-compose exec api bash
docker-compose exec mysql bash

# 备份数据库
docker-compose exec mysql mysqldump -u root -p${DB_ROOT_PASSWORD} license_db > backup.sql

# 恢复数据库
docker-compose exec -T mysql mysql -u root -p${DB_ROOT_PASSWORD} license_db < backup.sql
```

---

## 方式2：手动部署

### 前置要求

- Python 3.8+
- MySQL 8.0+
- pip

### 部署步骤

#### 1. 安装 MySQL

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install mysql-server
sudo mysql_secure_installation
```

**macOS:**
```bash
brew install mysql
brew services start mysql
```

**Windows:**
下载并安装 [MySQL Community Server](https://dev.mysql.com/downloads/mysql/)

#### 2. 创建数据库

```bash
mysql -u root -p
```

```sql
CREATE DATABASE license_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'license_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON license_db.* TO 'license_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### 3. 导入数据库结构

```bash
mysql -u license_user -p license_db < database/schema.sql
```

#### 4. 安装 Python 依赖

```bash
cd backend
pip install -r requirements.txt
```

#### 5. 配置环境变量

```bash
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=license_user
export DB_PASSWORD=your_password
export DB_NAME=license_db
export API_KEY=your_api_key
```

或者创建 `.env` 文件：

```bash
DB_HOST=localhost
DB_PORT=3306
DB_USER=license_user
DB_PASSWORD=your_password
DB_NAME=license_db
API_KEY=your_api_key
```

#### 6. 启动服务

```bash
python app.py
```

服务将在 `http://localhost:5000` 启动。

#### 7. 使用 systemd 管理服务（Linux）

创建服务文件 `/etc/systemd/system/license-manager.service`：

```ini
[Unit]
Description=License Manager API
After=network.target mysql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/license-manager-demo/backend
Environment="DB_HOST=localhost"
Environment="DB_PORT=3306"
Environment="DB_USER=license_user"
Environment="DB_PASSWORD=your_password"
Environment="DB_NAME=license_db"
Environment="API_KEY=your_api_key"
ExecStart=/usr/bin/python3 /path/to/license-manager-demo/backend/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable license-manager
sudo systemctl start license-manager
sudo systemctl status license-manager
```

---

## 方式3：云服务部署

### 阿里云 ECS 部署

#### 1. 购买 ECS 实例

- 选择 Ubuntu 20.04 或 CentOS 8
- 配置：2核4G 起步
- 安全组：开放 5000 端口

#### 2. 安装 Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

#### 3. 部署应用

```bash
git clone https://github.com/yourname/license-manager-demo.git
cd license-manager-demo
docker-compose up -d
```

#### 4. 配置域名和 SSL

使用 Nginx 反向代理：

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name api.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 腾讯云 CVM 部署

步骤与阿里云类似，参考上述文档。

---

## 生产环境配置

### 1. 安全配置

**防火墙设置：**
```bash
# 只开放必要端口
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

**数据库安全：**
- 修改默认端口
- 禁用远程 root 登录
- 定期备份数据库
- 使用强密码

**API 安全：**
- 使用 HTTPS
- 限制 API 访问频率
- 定期更换 API Key
- 添加 IP 白名单

### 2. 性能优化

**数据库优化：**
```sql
-- 添加索引
CREATE INDEX idx_email ON licenses(email);
CREATE INDEX idx_activation_code ON licenses(activation_code);

-- 优化查询
EXPLAIN SELECT * FROM licenses WHERE activation_code = 'XXX';
```

**应用优化：**
```python
# 使用连接池
from mysql.connector import pooling

connection_pool = pooling.MySQLConnectionPool(
    pool_name="license_pool",
    pool_size=5,
    **DB_CONFIG
)
```

### 3. 日志管理

**配置日志轮转：**
```bash
# /etc/logrotate.d/license-manager
/path/to/license-manager-demo/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
}
```

### 4. 监控告警

**使用 Prometheus + Grafana：**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'license-manager'
    static_configs:
      - targets: ['localhost:5000']
```

**使用 Uptime Robot：**
- 监控 API 健康状态
- 设置告警通知

---

## 备份与恢复

### 数据库备份

**自动备份脚本：**
```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/path/to/backups"
DB_NAME="license_db"
DB_USER="license_user"
DB_PASSWORD="your_password"

mkdir -p $BACKUP_DIR

# 备份数据库
mysqldump -u $DB_USER -p$DB_PASSWORD $DB_NAME > $BACKUP_DIR/backup_$DATE.sql

# 压缩备份
gzip $BACKUP_DIR/backup_$DATE.sql

# 删除7天前的备份
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: backup_$DATE.sql.gz"
```

**设置定时任务：**
```bash
# 每天凌晨2点备份
crontab -e
0 2 * * * /path/to/backup.sh
```

### 数据恢复

```bash
# 解压备份
gunzip backup_20250125_020000.sql.gz

# 恢复数据库
mysql -u license_user -p license_db < backup_20250125_020000.sql
```

---

## 故障排查

### 常见问题

**1. 数据库连接失败**

```bash
# 检查数据库服务状态
sudo systemctl status mysql

# 检查数据库端口
netstat -tlnp | grep 3306

# 测试连接
mysql -u license_user -p -h localhost
```

**2. API 无法访问**

```bash
# 检查服务状态
sudo systemctl status license-manager

# 检查端口占用
netstat -tlnp | grep 5000

# 查看日志
tail -f /var/log/license-manager/error.log
```

**3. Docker 容器启动失败**

```bash
# 查看容器日志
docker-compose logs api

# 重新构建镜像
docker-compose build --no-cache

# 重启容器
docker-compose restart
```

---

## 更新升级

### 更新代码

```bash
# 拉取最新代码
git pull origin main

# 重新构建
docker-compose build

# 重启服务
docker-compose up -d
```

### 数据库迁移

```bash
# 备份当前数据库
mysqldump -u license_user -p license_db > backup_before_migration.sql

# 应用迁移脚本
mysql -u license_user -p license_db < database/migrations/v1.1.0.sql
```

---

## 性能测试

### 使用 Apache Bench

```bash
# 测试健康检查接口
ab -n 1000 -c 10 http://localhost:5000/health

# 测试验证接口
ab -n 1000 -c 10 -p verify.json -T application/json http://localhost:5000/api/verify
```

### 使用 Locust

```python
# locustfile.py
from locust import HttpUser, task, between

class LicenseUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def verify_license(self):
        self.client.post("/api/verify", json={
            "activation_code": "ABCDE-FGHIJ-KLMN",
            "email": "test@example.com",
            "device_id": "test-device"
        })
```

运行测试：

```bash
locust -f locustfile.py --host=http://localhost:5000
```

---

## 支持与帮助

- **文档**: https://github.com/yourname/license-manager-demo
- **问题反馈**: https://github.com/yourname/license-manager-demo/issues
- **邮件**: support@example.com
