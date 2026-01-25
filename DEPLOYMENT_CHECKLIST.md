# License Manager Demo - 快速部署清单

## 部署前检查清单

### ✅ 环境准备

- [ ] 已安装Docker 20.10+
- [ ] 已安装Docker Compose 2.0+
- [ ] 已克隆项目到本地
- [ ] 已进入项目目录

### ✅ 配置文件

- [ ] 已复制 `.env.example` 为 `.env`
- [ ] 已设置数据库密码（DB_PASSWORD）
- [ ] 已设置管理员密码（ADMIN_PASSWORD）
- [ ] （可选）已配置ZPAY支付系统

### ✅ 启动服务

- [ ] 执行 `docker-compose up -d` 启动服务
- [ ] 等待所有服务启动完成（约30秒）
- [ ] 检查服务状态：`docker-compose ps`

### ✅ 验证服务

- [ ] 访问首页：http://localhost:8080/client/
- [ ] 访问管理后台：http://localhost:8080/admin/login.html
- [ ] 测试登录：admin / admin123
- [ ] 检查API健康：http://localhost:5000/health

## 快速部署步骤

### 1. 克隆项目

```bash
git clone https://github.com/yourname/license-manager-demo.git
cd license-manager-demo
```

### 2. 配置环境变量

```bash
# 复制环境变量配置
cp .env.example .env

# 编辑.env文件，设置必要的环境变量
nano .env
```

**必须配置**：
```bash
DB_PASSWORD=your_secure_password_here  # 数据库密码
ADMIN_PASSWORD=your_admin_password_here  # 管理员密码
```

**可选配置（启用ZPAY真实支付）**：
```bash
ZPAY_PID=your_zpay_pid_here
ZPAY_KEY=your_zpay_key_here
ZPAY_API_URL=https://zpayz.cn/
ZPAY_NOTIFY_URL=https://yourdomain.com/api/payment/notify
ZPAY_RETURN_URL=https://yourdomain.com/client/complete_order.html
```

### 3. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 4. 验证部署

```bash
# 检查API健康状态
curl http://localhost:5000/health

# 应该返回：
# {"status":"healthy","timestamp":"..."}
```

### 5. 访问服务

- **首页**: http://localhost:8080/client/
- **管理后台**: http://localhost:8080/admin/login.html
- **API接口**: http://localhost:5000

默认管理员账号：`admin` / `admin123`

## 常用命令

### 服务管理

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
```

### 数据库管理

```bash
# 进入MySQL容器
docker-compose exec mysql bash

# 备份数据库
docker-compose exec mysql mysqldump -u root -p${DB_ROOT_PASSWORD} license_db > backup.sql

# 恢复数据库
docker-compose exec -T mysql mysql -u root -p${DB_ROOT_PASSWORD} license_db < backup.sql
```

### 故障排查

```bash
# 查看容器日志
docker-compose logs api

# 重新构建镜像
docker-compose build --no-cache

# 重启容器
docker-compose restart api
```

## 生产环境部署

### 1. 修改配置

编辑 `docker-compose.yml`，修改端口映射：
```yaml
ports:
  - "80:80"        # Web服务
  - "443:443"      # HTTPS
  - "5000:5000"    # API服务
```

### 2. 配置域名

编辑 `nginx.conf`，配置域名和SSL证书：
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8080;
    }
}
```

### 3. 配置防火墙

```bash
# 只开放必要端口
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 4. 配置自动备份

创建定时任务：
```bash
# 编辑crontab
crontab -e

# 每天凌晨2点备份
0 2 * * * /path/to/backup.sh
```

## 优化建议

### 性能优化

1. **数据库优化**
   - 添加索引
   - 使用连接池
   - 定期清理历史数据

2. **应用优化**
   - 启用缓存
   - 优化查询
   - 使用CDN

### 安全优化

1. **修改默认密码**
   - 数据库密码
   - 管理员密码
   - Session密钥

2. **启用HTTPS**
   - 配置SSL证书
   - 强制HTTPS访问

3. **限制访问**
   - 配置防火墙
   - 使用IP白名单
   - 限制API访问频率

### 监控告警

1. **日志监控**
   - 配置日志轮转
   - 监控错误日志
   - 设置告警通知

2. **服务监控**
   - 监控服务状态
   - 监控资源使用
   - 设置自动重启

## 故障排查

### 服务无法启动

```bash
# 查看容器日志
docker-compose logs api

# 检查端口占用
netstat -tlnp | grep 8080

# 重新构建镜像
docker-compose build --no-cache
```

### 数据库连接失败

```bash
# 检查MySQL容器状态
docker-compose ps mysql

# 查看MySQL日志
docker-compose logs mysql

# 测试数据库连接
docker-compose exec mysql mysql -u license_user -p
```

### 支付功能异常

```bash
# 检查ZPAY配置
docker-compose exec api env | grep ZPAY

# 查看支付日志
docker-compose logs api | grep payment

# 测试支付API
curl -X POST http://localhost:5000/api/payment/create \
  -H "Content-Type: application/json" \
  -d '{"plan":"monthly","email":"test@example.com"}'
```

## 联系支持

如果遇到问题，请查看：
- [部署指南](docs/DEPLOY.md)
- [API文档](docs/API.md)
- [支付集成指南](docs/PAYMENT.md)

或联系技术支持：vip@oneclip.cloud

## 快速参考

### 端口说明
- 8080 - Web服务
- 5000 - API服务
- 3306 - MySQL数据库

### 默认账号
- 管理员：admin / admin123

### 配置文件
- `.env` - 环境变量
- `docker-compose.yml` - Docker配置
- `Dockerfile` - 镜像构建

### 日志位置
- 容器日志：`docker-compose logs`
- 应用日志：容器内 `/app/logs/`

### 数据备份
- 备份命令：`docker-compose exec mysql mysqldump ...`
- 恢复命令：`docker-compose exec -T mysql mysql ...`
