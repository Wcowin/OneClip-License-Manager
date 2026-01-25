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
    if ! check_command docker-compose; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose 2.0+"
        echo "安装命令: sudo apt-get install docker-compose 或参考官方文档"
        exit 1
    fi
    print_success "Docker Compose 已安装: $(docker-compose --version)"
    
    # 检查端口占用
    print_info "检查端口占用..."
    if netstat -tlnp 2>/dev/null | grep -q ":8080 "; then
        print_warning "端口 8080 已被占用，请修改 docker-compose.yml 中的端口映射"
        read -p "是否继续部署? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    if netstat -tlnp 2>/dev/null | grep -q ":5000 "; then
        print_warning "端口 5000 已被占用，请修改 docker-compose.yml 中的端口映射"
        read -p "是否继续部署? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
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
    
    # 交互式配置
    echo ""
    print_info "请设置数据库密码（必填）"
    read -p "数据库密码: " DB_PASSWORD
    
    if [ -z "$DB_PASSWORD" ]; then
        print_error "数据库密码不能为空"
        exit 1
    fi
    
    print_info "请设置管理员密码（必填）"
    read -p "管理员密码: " ADMIN_PASSWORD
    
    if [ -z "$ADMIN_PASSWORD" ]; then
        print_error "管理员密码不能为空"
        exit 1
    fi
    
    print_info "是否配置ZPAY支付系统? (可选)"
    read -p "启用ZPAY? (y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "请输入ZPAY配置"
        read -p "ZPAY PID: " ZPAY_PID
        read -p "ZPAY KEY: " ZPAY_KEY
        
        if [ -n "$ZPAY_PID" ] && [ -n "$ZPAY_KEY" ]; then
            # 更新.env文件
            sed -i "s/ZPAY_PID=.*/ZPAY_PID=$ZPAY_PID/" .env
            sed -i "s/ZPAY_KEY=.*/ZPAY_KEY=$ZPAY_KEY/" .env
            
            print_info "请输入服务器地址（用于支付回调）"
            read -p "服务器地址（如：https://yourdomain.com）: " SERVER_URL
            
            if [ -n "$SERVER_URL" ]; then
                sed -i "s|ZPAY_NOTIFY_URL=.*|ZPAY_NOTIFY_URL=$SERVER_URL/api/payment/notify|" .env
                sed -i "s|ZPAY_RETURN_URL=.*|ZPAY_RETURN_URL=$SERVER_URL/client/complete_order.html|" .env
            fi
            
            print_success "ZPAY配置完成"
        else
            print_warning "ZPAY配置不完整，将使用模拟支付"
        fi
    fi
    
    # 更新数据库密码和管理员密码
    sed -i "s/DB_PASSWORD=.*/DB_PASSWORD=$DB_PASSWORD/" .env
    sed -i "s/ADMIN_PASSWORD=.*/ADMIN_PASSWORD=$ADMIN_PASSWORD/" .env
    
    print_success "环境变量配置完成"
}

# 启动服务
start_services() {
    print_info "启动服务..."
    
    # 构建镜像
    print_info "构建Docker镜像..."
    docker-compose build
    
    # 启动服务
    print_info "启动Docker容器..."
    docker-compose up -d
    
    # 等待服务启动
    print_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    print_info "检查服务状态..."
    docker-compose ps
    
    # 查看日志
    print_info "查看服务日志（按Ctrl+C退出）..."
    docker-compose logs -f --tail=50
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
    echo ""
    print_success "==========================================="
    print_success "部署完成！"
    print_success "==========================================="
    echo ""
    echo "访问地址："
    echo "  首页: http://localhost:8080/client/"
    echo "  管理后台: http://localhost:8080/admin/login.html"
    echo "  API接口: http://localhost:5000"
    echo ""
    echo "默认管理员账号："
    echo "  用户名: admin"
    echo "  密码: $ADMIN_PASSWORD"
    echo ""
    echo "常用命令："
    echo "  查看状态: docker-compose ps"
    echo "  查看日志: docker-compose logs -f"
    echo "  停止服务: docker-compose down"
    echo "  重启服务: docker-compose restart"
    echo ""
    print_success "==========================================="
}

# 主函数
main() {
    echo ""
    print_success "==========================================="
    print_success "License Manager 一键部署脚本"
    print_success "==========================================="
    echo ""
    
    # 检查环境
    check_environment
    
    # 配置环境变量
    configure_environment
    
    # 启动服务
    start_services
    
    # 验证部署
    if verify_deployment; then
        # 显示部署信息
        show_deployment_info
    else
        print_error "部署验证失败，请检查日志"
        print_info "查看日志: docker-compose logs"
        exit 1
    fi
}

# 运行主函数
main
