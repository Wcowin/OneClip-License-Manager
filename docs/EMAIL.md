# 邮件配置指南

## 概述

License Manager 支持在支付成功后自动发送激活码邮件到用户邮箱。邮件功能是可选的，配置后即可使用。

## 支持的邮件服务商

### QQ邮箱（推荐）
- SMTP服务器：`smtp.qq.com`
- 端口：`587`（TLS）
- 特点：稳定、免费、适合国内用户

### 163邮箱
- SMTP服务器：`smtp.163.com`
- 端口：`465`（SSL）
- 特点：稳定、免费

### 企业邮箱
- SMTP服务器：`smtp.exmail.qq.com`
- 端口：`465`（SSL）
- 特点：专业、适合企业

## 配置步骤

### 1. 获取SMTP授权码

#### QQ邮箱
1. 登录QQ邮箱网页版
2. 点击"设置" → "账户"
3. 找到"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"
4. 开启"POP3/SMTP服务"
5. 按照提示获取授权码（16位字符）
6. **重要**：授权码不是QQ密码！

#### 163邮箱
1. 登录163邮箱网页版
2. 点击"设置" → "POP3/SMTP/IMAP"
3. 开启"POP3/SMTP服务"
4. 获取授权码

#### 企业邮箱
1. 登录企业邮箱管理后台
2. 开启SMTP服务
3. 获取授权码或密码

### 2. 配置环境变量

编辑 `.env` 文件，添加以下配置：

```bash
# 邮件配置（可选）
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your_email@qq.com
SMTP_PASSWORD=your_smtp_authorization_code
SMTP_FROM_EMAIL=your_email@qq.com
SMTP_FROM_NAME=License Manager
```

**参数说明：**

| 参数 | 说明 | 示例 |
|------|------|------|
| SMTP_SERVER | SMTP服务器地址 | smtp.qq.com |
| SMTP_PORT | SMTP端口 | 587（QQ）或 465（163/企业） |
| SMTP_USER | 邮箱账号 | your_email@qq.com |
| SMTP_PASSWORD | SMTP授权码 | 不是邮箱密码！ |
| SMTP_FROM_EMAIL | 发件人邮箱 | your_email@qq.com |
| SMTP_FROM_NAME | 发件人名称 | License Manager |

### 3. 测试邮件发送

启动服务后，支付成功会自动发送邮件。也可以通过API手动发送：

```bash
curl -X POST http://localhost:5000/api/admin/send-email \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your_session_cookie" \
  -d '{
    "email": "user@example.com",
    "activation_code": "ABCDE-FGHIJ-KLMN",
    "plan": "monthly",
    "device_cap": 5,
    "valid_until": "2025-02-25T00:00:00Z"
  }'
```

### 4. 查看邮件日志

```bash
# 查看服务日志
docker-compose logs -f api | grep "邮件"

# 查看完整日志
docker-compose logs api
```

## 邮件模板

邮件包含以下信息：

- 激活码（大号显示）
- 许可证信息（套餐类型、设备数量、有效期）
- 激活步骤
- 客服支持

## 常见问题

### 1. 邮件发送失败

**可能原因：**
- SMTP配置错误
- 授权码错误
- 网络问题
- 防火墙阻止

**解决方案：**
```bash
# 检查SMTP配置
cat .env | grep SMTP

# 测试SMTP连接
telnet smtp.qq.com 587

# 查看详细错误日志
docker-compose logs api | grep "邮件"
```

### 2. 邮件进入垃圾箱

**解决方案：**
- 检查邮件内容是否包含敏感词
- 添加发件人到白名单
- 调整邮件内容

### 3. QQ邮箱授权码获取失败

**解决方案：**
- 确保QQ邮箱已开启SMTP服务
- 使用手机QQ扫码验证
- 重新生成授权码

### 4. 邮件发送慢

**可能原因：**
- 网络延迟
- SMTP服务器响应慢
- 邮件队列

**解决方案：**
- 检查网络连接
- 尝试其他SMTP服务商
- 查看邮件队列状态

## 安全建议

1. **不要在代码中硬编码密码** - 使用环境变量
2. **定期更换授权码** - 每3-6个月更换
3. **限制发送频率** - 防止被标记为垃圾邮件
4. **监控发送日志** - 及时发现异常
5. **使用企业邮箱** - 更稳定、更专业

## 邮件发送时机

### 自动发送
- 支付成功后自动发送
- 管理员生成许可证后自动发送

### 手动发送
- 管理后台手动发送
- API接口手动发送

## 禁用邮件功能

如果不需要邮件功能，可以不配置SMTP环境变量。系统会自动跳过邮件发送。

## 邮件服务商对比

| 服务商 | 稳定性 | 速度 | 费用 | 推荐度 |
|--------|--------|------|------|--------|
| QQ邮箱 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 免费 | ⭐⭐⭐⭐⭐ |
| 163邮箱 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 免费 | ⭐⭐⭐⭐ |
| 企业邮箱 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 收费 | ⭐⭐⭐⭐ |
| Gmail | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 免费 | ⭐⭐⭐ |
| Outlook | ⭐⭐⭐⭐ | ⭐⭐⭐ | 免费 | ⭐⭐⭐ |

## 高级配置

### 自定义邮件模板

编辑 `backend/email_sender.py` 中的 `_build_email_template` 方法，自定义邮件内容。

### 添加附件

```python
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# 添加附件
with open('document.pdf', 'rb') as f:
    part = MIMEApplication(f.read(), Name='document.pdf')
    part['Content-Disposition'] = 'attachment; filename="document.pdf"'
    msg.attach(part)
```

### 邮件队列

对于大量邮件发送，建议使用邮件队列服务（如Redis、Celery）。

## 监控和日志

### 日志级别
- `INFO` - 邮件发送成功
- `WARNING` - 邮件发送失败但不影响主流程
- `ERROR` - 邮件发送错误

### 监控指标
- 发送成功率
- 发送延迟
- 失败原因统计

## 支持

如有问题，请查看：
- 邮件服务商文档
- 项目GitHub Issues
- 技术支持邮箱
