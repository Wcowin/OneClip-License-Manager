# License Manager Demo

一个简单易用的许可证管理系统，支持激活码生成、验证和设备管理。

## 功能特性

- 激活码生成（支持月度/年度/终身套餐）
- 激活码验证（邮箱+激活码双重验证）
- 设备管理（激活/停用/恢复设备）
- 设备数量限制
- 完整的激活历史记录
- RESTful API接口
- Web管理界面（用户名+密码登录）
- 客户端示例（购买+激活全流程）
- Docker快速部署
- 支付系统集成（模拟支付，支持扩展）

## 快速开始

### 方式1：一键部署脚本（推荐）

```bash
# 克隆项目
git clone https://github.com/Wcowin/OneClip-License-Manager.git
cd OneClip-License-Manager

# 运行一键部署脚本
chmod +x deploy.sh
./deploy.sh
```

脚本会自动：
- 检查Docker和Docker Compose环境
- 交互式配置环境变量
- 构建并启动服务
- 验证部署状态

### 方式2：Docker部署

```bash
# 克隆项目
git clone https://github.com/Wcowin/OneClip-License-Manager.git
cd OneClip-License-Manager

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置数据库密码等

# 启动服务
docker-compose up -d

# 访问服务
# 首页: http://localhost:8080/client/
# 管理后台: http://localhost:8080/admin/login.html
# API接口: http://localhost:5000
# 默认管理员账号: admin / admin123
```

### 方式2：手动部署

```bash
# 安装依赖
cd backend
pip install -r requirements.txt

# 配置环境变量
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=license_user
export DB_PASSWORD=your_password
export DB_NAME=license_db
export API_KEY=your_api_key

# 启动服务
cd ..
python backend/app.py
```

## 完整流程

### 1. 用户访问首页

访问首页：http://localhost:8080/client/

- 查看产品介绍和功能特性
- 选择合适的套餐（月度版/年度版/终身版）
- 点击"立即购买"进入购买页面

### 2. 用户购买许可证

访问购买页面：http://localhost:8080/client/purchase.html?plan=monthly

- 填写邮箱地址
- 确认套餐类型
- 点击"购买并获取激活码"
- 系统生成激活码并跳转到订单完成页面

### 3. 查看订单完成页面

访问订单完成页面：http://localhost:8080/client/complete_order.html

- 查看激活码（可复制）
- 查看购买信息
- 查看激活步骤
- 下载应用

### 4. 管理员管理许可证

访问管理后台：http://localhost:8080/admin/login.html

- 使用管理员账号登录（默认：admin / admin123）
- 生成许可证
- 查看统计信息
- 撤销许可证

## 支付功能

本demo使用模拟支付，展示完整的购买流程。

如需集成真实支付，请参考 [支付集成指南](docs/PAYMENT.md)

### 支持的支付平台

**OneClip推荐**：
- **zpay** - [OneClip](https://oneclip.cloud/)正在使用的支付系统，支持微信支付、支付宝  
![下载.png](https://i.imgant.com/v2/W5l9vVj.png)

**其他平台**：
- 微信支付 - 适合国内移动端用户
- 支付宝 - 适合国内PC端和移动端用户
- Stripe - 适合国际信用卡支付
- PayPal - 适合国际用户

### 集成步骤

1. 注册支付平台账号
2. 获取API密钥
3. 修改后端代码，添加支付API
4. 修改前端代码，调用支付接口
5. 处理支付回调

详细步骤请参考 [docs/PAYMENT.md](docs/PAYMENT.md)

## 使用示例

### 1. 生成激活码

```bash
curl -X POST http://localhost:5000/api/admin/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "plan": "monthly",
    "email": "user@example.com",
    "device_cap": 5,
    "days": 30
  }'
```

响应：
```json
{
  "success": true,
  "license": {
    "license_id": "LIC-ABC12345",
    "activation_code": "ABCDE-FGHIJ-KLMN",
    "email": "user@example.com",
    "plan": "monthly",
    "device_cap": 5,
    "valid_until": "2025-02-25T00:00:00Z"
  }
}
```

### 2. 验证激活码

```bash
curl -X POST http://localhost:5000/api/verify \
  -H "Content-Type: application/json" \
  -d '{
    "activation_code": "ABCDE-FGHIJ-KLMN",
    "email": "user@example.com",
    "device_id": "device-uuid-123",
    "device_name": "MacBook Pro",
    "ip_address": "192.168.1.100"
  }'
```

响应：
```json
{
  "success": true,
  "valid": true,
  "license_id": "LIC-ABC12345",
  "plan": "monthly",
  "device_cap": 5,
  "valid_until": "2025-02-25T00:00:00Z"
}
```

### 3. 查询许可证列表

```bash
curl -X GET http://localhost:5000/api/admin/licenses \
  -H "X-API-Key: your_api_key"
```

## 项目结构

```
license-manager-demo/
├── backend/
│   ├── app.py              # Flask API服务器
│   ├── license_manager.py  # 许可证管理核心逻辑
│   ├── database.py         # 数据库配置
│   └── requirements.txt    # Python依赖
├── database/
│   └── schema.sql          # 数据库结构
├── docs/
│   ├── API.md             # API文档
│   └── DEPLOY.md          # 部署指南
├── .env.example           # 环境变量示例
├── docker-compose.yml     # Docker配置
└── README.md              # 项目说明
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| DB_HOST | 数据库主机 | localhost | 是 |
| DB_PORT | 数据库端口 | 3306 | 是 |
| DB_USER | 数据库用户名 | - | 是 |
| DB_PASSWORD | 数据库密码 | - | 是 |
| DB_NAME | 数据库名称 | - | 是 |
| ADMIN_USERNAME | 管理员用户名 | admin | 是 |
| ADMIN_PASSWORD | 管理员密码 | - | 是 |
| API_KEY | API密钥 | - | 是 |

### 套餐类型

- `monthly`：月度版（默认30天）
- `yearly`：年度版（默认365天）
- `lifetime`：终身版（永久有效）

## API文档

详细的API文档请参考 [docs/API.md](docs/API.md)

## 安全建议

⚠️ **重要提醒**：

1. 不要在生产环境使用默认密码
2. 使用HTTPS保护API通信
3. 定期备份数据库
4. 限制API访问频率
5. 监控异常登录和激活行为
6. 定期更新依赖包

## 部署指南

详细的部署指南请参考 [docs/DEPLOY.md](docs/DEPLOY.md)

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

- 项目地址：https://github.com/yourname/license-manager-demo
- 问题反馈：https://github.com/yourname/license-manager-demo/issues

## 技术栈

- 后端：Python Flask
- 数据库：MySQL
- 容器化：Docker & Docker Compose

## 常见问题

### Q: 如何修改激活码格式？

A: 修改 `backend/license_manager.py` 中的 `CHARSET` 常量和 `generate_activation_code()` 方法。

### Q: 如何增加新的套餐类型？

A: 在 `backend/license_manager.py` 的 `generate_license_with_email()` 方法中添加新的套餐类型。

### Q: 如何自定义设备数量限制？

A: 在生成激活码时通过 `device_cap` 参数指定，或在数据库中直接修改 `device_limit` 字段。

## 更新日志

### v1.0.0 (2025-01-25)

- 初始版本发布
- 支持激活码生成和验证
- 支持设备管理
- 提供完整的API接口
- 支持Docker部署
