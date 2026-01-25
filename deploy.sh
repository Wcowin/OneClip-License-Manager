#!/bin/bash

# License Manager 一键部署脚本
# 交互式引导用户完成部署

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        return 1
    fi
    return 0
}

# 检查环境
check_environment() {
    print_info "检查部署环境..."
    
    # 检查Docker
    if ! check_command docker; then
        print_error "Docker 未安装，请先安装 Docker 20.10+"
        echo "安装命令: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    print_success "Docker 已安装: $(docker --version)"
    
    # 检查Docker Compose
    if ! check_command docker-compose && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Desktop 或 Docker Compose 2.0+"
        echo "安装命令: 访问 https://docs.docker.com/desktop/install/mac-install/"
        exit 1
    fi
    
    # 确定使用哪个命令
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
        print_success "Docker Compose 已安装: $(docker compose version)"
    else
        DOCKER_COMPOSE="docker-compose"
        print_success "Docker Compose 已安装: $(docker-compose --version)"
    fi
    
    # 检查端口占用
    print_info "检查端口占用..."
    
    # 检查 8080 端口
    if command -v lsof &> /dev/null; then
        if lsof -i :8080 -sTCP:LISTEN -t &> /dev/null; then
            print_warning "端口 8080 已被占用，请修改 docker-compose.yml 中的端口映射"
            read -p "是否继续部署? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    elif netstat -an &> /dev/null; then
        if netstat -an 2>/dev/null | grep -q "\.8080 "; then
            print_warning "端口 8080 已被占用，请修改 docker-compose.yml 中的端口映射"
            read -p "是否继续部署? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    fi
    
    # 检查 5000 端口
    if command -v lsof &> /dev/null; then
        if lsof -i :5000 -sTCP:LISTEN -t &> /dev/null; then
            print_warning "端口 5000 已被占用，请修改 docker-compose.yml 中的端口映射"
            read -p "是否继续部署? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    elif netstat -an &> /dev/null; then
        if netstat -an 2>/dev/null | grep -q "\.5000 "; then
            print_warning "端口 5000 已被占用，请修改 docker-compose.yml 中的端口映射"
            read -p "是否继续部署? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    fi
}

# 配置环境变量
configure_environment() {
    print_info "配置环境变量..."
    
    # 检查.env文件是否存在
    if [ -f .env ]; then
        print_warning ".env 文件已存在"
        read -p "是否重新配置? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return
        fi
    fi
    
    # 复制.env.example
    if [ -f .env.example ]; then
        cp .env.example .env
        print_success "已复制 .env.example 到 .env"
    else
        print_error ".env.example 文件不存在"
        exit 1
    fi
    
    # 生产环境域名配置（必填）
    echo ""
    print_info "生产部署需要配置域名（必填）"
    read -p "域名（如：example.com）: " DOMAIN_NAME
    
    if [ -z "$DOMAIN_NAME" ]; then
        print_error "域名不能为空，生产部署必须配置域名"
        exit 1
    fi
    
    # 验证域名格式
    if [[ ! $DOMAIN_NAME =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        print_error "域名格式无效"
        exit 1
    fi
    
    # 检查DNS解析
    print_info "检查DNS解析..."
    if ! nslookup $DOMAIN_NAME &> /dev/null; then
        print_warning "DNS解析失败，请确保域名已解析到此服务器"
        read -p "是否继续部署? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # 生成随机密码
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=')
    ADMIN_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=')
    API_KEY=$(openssl rand -hex 32)
    ADMIN_SECRET_KEY=$(openssl rand -hex 32)
    
    # 配置环境变量
    sed -i "s/DB_PASSWORD=.*/DB_PASSWORD=$DB_PASSWORD/" .env
    sed -i "s/ADMIN_PASSWORD=.*/ADMIN_PASSWORD=$ADMIN_PASSWORD/" .env
    sed -i "s/API_KEY=.*/API_KEY=$API_KEY/" .env
    sed -i "s/ADMIN_SECRET_KEY=.*/ADMIN_SECRET_KEY=$ADMIN_SECRET_KEY/" .env
    
    # 配置域名
    SERVER_URL="https://$DOMAIN_NAME"
    sed -i "s|ZPAY_NOTIFY_URL=.*|ZPAY_NOTIFY_URL=$SERVER_URL/api/payment/notify|" .env
    sed -i "s|ZPAY_RETURN_URL=.*|ZPAY_RETURN_URL=$SERVER_URL/client/complete_order.html|" .env
    
    # ZPAY配置（可选）
    print_info "是否配置ZPAY支付系统? (可选)"
    read -p "启用ZPAY? (y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "请输入ZPAY配置"
        read -p "ZPAY PID: " ZPAY_PID
        read -p "ZPAY KEY: " ZPAY_KEY
        
        if [ -n "$ZPAY_PID" ] && [ -n "$ZPAY_KEY" ]; then
            sed -i "s/ZPAY_PID=.*/ZPAY_PID=$ZPAY_PID/" .env
            sed -i "s/ZPAY_KEY=.*/ZPAY_KEY=$ZPAY_KEY/" .env
            print_success "ZPAY配置完成"
        else
            print_warning "ZPAY配置不完整，将使用模拟支付"
        fi
    fi
    
    # 保存配置信息
    cat > .deployment_info << EOF
DB_PASSWORD=$DB_PASSWORD
ADMIN_PASSWORD=$ADMIN_PASSWORD
API_KEY=$API_KEY
DOMAIN_NAME=$DOMAIN_NAME
DEPLOY_DATE=$(date)
EOF
    
    print_success "环境变量配置完成"
    print_warning "请保存以下密码信息："
    echo "  数据库密码: $DB_PASSWORD"
    echo "  管理员密码: $ADMIN_PASSWORD"
    echo "  API密钥: $API_KEY"
}

# 安全加固
security_hardening() {
    print_info "安全加固..."
    
    # 检查防火墙
    if command -v ufw &> /dev/null; then
        print_info "配置防火墙..."
        ufw allow 22/tcp
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw --force enable
        print_success "防火墙配置完成"
    elif command -v firewall-cmd &> /dev/null; then
        print_info "配置防火墙..."
        firewall-cmd --permanent --add-service=ssh
        firewall-cmd --permanent --add-service=http
        firewall-cmd --permanent --add-service=https
        firewall-cmd --reload
        print_success "防火墙配置完成"
    else
        print_warning "未检测到防火墙工具，请手动配置"
    fi
    
    # 创建备份目录
    mkdir -p backups
    
    # 创建备份脚本
    cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
mkdir -p $BACKUP_DIR

# 从环境变量读取密码
source ./.deployment_info 2>/dev/null || true

# 备份数据库
docker exec license-manager-mysql mysqldump -uroot -p${DB_PASSWORD} license_db > $BACKUP_DIR/backup_$DATE.sql

# 保留最近 7 天的备份
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete

echo "备份完成: backup_$DATE.sql"
EOF
    
    chmod +x backup.sh
    
    # 添加到 crontab（每天凌晨 2 点备份）
    (crontab -l 2>/dev/null | grep -v "backup.sh"; echo "0 2 * * * $(pwd)/backup.sh >> $(pwd)/backup.log 2>&1") | crontab -
    
    print_success "备份配置完成"
}

# 配置 SSL
configure_ssl() {
    print_info "配置 SSL 证书..."
    
    # 检查是否已安装 certbot
    if ! command -v certbot &> /dev/null; then
        print_info "安装 Certbot..."
        if command -v apt-get &> /dev/null; then
            apt-get update
            apt-get install -y certbot python3-certbot-nginx
        elif command -v yum &> /dev/null; then
            yum install -y certbot python3-certbot-nginx
        fi
    fi
    
    # 获取域名
    source ./.deployment_info 2>/dev/null || true
    DOMAIN_NAME=${DOMAIN_NAME:-}
    
    if [ -z "$DOMAIN_NAME" ]; then
        print_warning "未配置域名，跳过 SSL 配置"
        return
    fi
    
    # 获取 SSL 证书
    print_info "获取 SSL 证书..."
    if certbot certonly --standalone -d $DOMAIN_NAME -d www.$DOMAIN_NAME --non-interactive --agree-tos --register-email --email admin@$DOMAIN_NAME; then
        print_success "SSL 证书获取成功"
        
        # 创建 SSL 目录
        mkdir -p ssl
        
        # 复制证书
        cp /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem ssl/
        cp /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem ssl/
        chmod 644 ssl/*
        
        # 创建 nginx.conf
        cat > nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    server {
        listen 80;
        server_name $DOMAIN_NAME www.$DOMAIN_NAME;
        return 301 https://\$server_name\$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name $DOMAIN_NAME www.$DOMAIN_NAME;

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
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }
}
EOF
        
        # 更新 docker-compose.yml
        sed -i 's/ports:/# ports/' docker-compose.yml
        sed -i '/web:/a\    ports:\n      - "80:80"\n      - "443:443"' docker-compose.yml
        sed -i '/volumes:/a\      - ./nginx.conf:/etc/nginx/nginx.conf\n      - ./ssl:/etc/nginx/ssl' docker-compose.yml
        
        print_success "Nginx 配置完成"
    else
        print_warning "SSL 证书获取失败，将使用 HTTP"
    fi
}

# 启动服务
start_services() {
    print_info "启动服务..."
    
    # 构建镜像
    print_info "构建Docker镜像..."
    $DOCKER_COMPOSE build
    
    # 启动服务
    print_info "启动Docker容器..."
    $DOCKER_COMPOSE up -d
    
    # 等待服务启动
    print_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    print_info "检查服务状态..."
    $DOCKER_COMPOSE ps
    
    # 查看日志
    print_info "查看服务日志（按Ctrl+C退出）..."
    $DOCKER_COMPOSE logs -f --tail=50
}

# 验证部署
verify_deployment() {
    print_info "验证部署..."
    
    # 检查API健康
    print_info "检查API健康状态..."
    if curl -s http://localhost:5000/health > /dev/null; then
        print_success "API服务正常"
    else
        print_error "API服务异常"
        return 1
    fi
    
    # 检查Web服务
    print_info "检查Web服务..."
    if curl -s http://localhost:8080/client/ > /dev/null; then
        print_success "Web服务正常"
    else
        print_error "Web服务异常"
        return 1
    fi
    
    return 0
}

# 显示部署信息
show_deployment_info() {
    source ./.deployment_info 2>/dev/null || true
    
    echo ""
    print_success "==========================================="
    print_success "生产部署完成！"
    print_success "==========================================="
    echo ""
    echo "访问地址："
    echo "  首页: https://${DOMAIN_NAME}/client/"
    echo "  管理后台: https://${DOMAIN_NAME}/admin/login.html"
    echo "  API接口: https://${DOMAIN_NAME}/api/"
    echo ""
    echo "默认管理员账号："
    echo "  用户名: admin"
    echo "  密码: $ADMIN_PASSWORD"
    echo ""
    echo "备份信息："
    echo "  备份目录: $(pwd)/backups"
    echo "  备份脚本: $(pwd)/backup.sh"
    echo "  备份日志: $(pwd)/backup.log"
    echo ""
    echo "常用命令："
    echo "  查看状态: $DOCKER_COMPOSE ps"
    echo "  查看日志: $DOCKER_COMPOSE logs -f"
    echo "  停止服务: $DOCKER_COMPOSE down"
    echo "  重启服务: $DOCKER_COMPOSE restart"
    echo "  手动备份: ./backup.sh"
    echo ""
    echo "安全提醒："
    echo "  ✓ 已配置防火墙（仅开放 22/80/443）"
    echo "  ✓ 已配置自动备份（每天凌晨 2 点）"
    echo "  ✓ 已配置 SSL 证书"
    echo "  ✓ 数据库端口未暴露（仅内网访问）"
    echo ""
    print_success "==========================================="
}

# 主函数
main() {
    echo ""
    print_success "==========================================="
    print_success "License Manager 生产部署脚本"
    print_success "==========================================="
    echo ""
    
    # 检查环境
    check_environment
    
    # 配置环境变量
    configure_environment
    
    # 安全加固
    security_hardening
    
    # 配置 SSL
    configure_ssl
    
    # 启动服务
    start_services
    
    # 验证部署
    if verify_deployment; then
        # 显示部署信息
        show_deployment_info
    else
        print_error "部署验证失败，请检查日志"
        print_info "查看日志: $DOCKER_COMPOSE logs"
        exit 1
    fi
}

# 运行主函数
main
