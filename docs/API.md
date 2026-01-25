# License Manager API 文档

## 基础信息

- **Base URL**: `http://localhost:5000`
- **认证方式**: API Key（通过 `X-API-Key` 请求头）
- **响应格式**: JSON

## 认证

所有管理接口都需要在请求头中包含 API Key：

```
X-API-Key: your_api_key_here
```

## API 接口

### 1. 健康检查

检查服务是否正常运行。

**请求**
```
GET /health
```

**响应**
```json
{
  "status": "ok",
  "timestamp": "2025-01-25T00:00:00Z"
}
```

---

### 2. 验证许可证

验证激活码是否有效。

**请求**
```
POST /api/verify
Content-Type: application/json

{
  "activation_code": "ABCDE-FGHIJ-KLMN",
  "email": "user@example.com",
  "device_id": "device-uuid-123",
  "device_name": "MacBook Pro",
  "ip_address": "192.168.1.100"
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| activation_code | string | 是 | 激活码（格式：XXXXX-XXXXX-XXXXX） |
| email | string | 是 | 绑定的邮箱地址 |
| device_id | string | 否 | 设备唯一标识 |
| device_name | string | 否 | 设备名称 |
| ip_address | string | 否 | 设备IP地址 |

**成功响应**
```json
{
  "success": true,
  "message": "许可证验证成功",
  "code": "SUCCESS",
  "license": {
    "key": "LIC-ABC12345",
    "type": "monthly",
    "expiresAt": "2025-02-25T00:00:00Z"
  },
  "isValid": true,
  "licenseType": "monthly",
  "expiresAt": "2025-02-25T00:00:00Z",
  "timestamp": "2025-01-25T00:00:00Z"
}
```

**失败响应**
```json
{
  "success": false,
  "message": "激活码不存在或已停用",
  "code": "INVALID_LICENSE",
  "isValid": false,
  "timestamp": "2025-01-25T00:00:00Z"
}
```

---

### 3. 生成许可证（管理员）

生成新的激活码。

**请求**
```
POST /api/admin/generate
X-API-Key: your_api_key
Content-Type: application/json

{
  "plan": "monthly",
  "email": "user@example.com",
  "device_cap": 5,
  "days": 30,
  "user_hint": "测试用户"
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| plan | string | 是 | 套餐类型：monthly/yearly/lifetime |
| email | string | 是 | 绑定邮箱 |
| device_cap | integer | 否 | 设备数量限制（默认5） |
| days | integer | 否 | 有效期天数（终身版不需要） |
| user_hint | string | 否 | 用户备注 |

**成功响应**
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

**套餐类型说明**

| 类型 | 说明 | 默认有效期 |
|------|------|-----------|
| monthly | 月度版 | 30天 |
| yearly | 年度版 | 365天 |
| lifetime | 终身版 | 永久 |

---

### 4. 撤销许可证（管理员）

撤销一个许可证。

**请求**
```
POST /api/admin/revoke
X-API-Key: your_api_key
Content-Type: application/json

{
  "license_id": "LIC-ABC12345",
  "reason": "用户申请退款"
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| license_id | string | 是 | 许可证ID |
| reason | string | 否 | 撤销原因 |

**成功响应**
```json
{
  "success": true
}
```

---

### 5. 停用设备（管理员）

停用某个设备。

**请求**
```
POST /api/admin/deactivate-device
X-API-Key: your_api_key
Content-Type: application/json

{
  "license_id": "LIC-ABC12345",
  "device_id": "device-uuid-123"
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| license_id | string | 是 | 许可证ID |
| device_id | string | 是 | 设备ID |

**成功响应**
```json
{
  "success": true
}
```

---

### 6. 恢复设备（管理员）

恢复某个被停用的设备。

**请求**
```
POST /api/admin/activate-device
X-API-Key: your_api_key
Content-Type: application/json

{
  "license_id": "LIC-ABC12345",
  "device_id": "device-uuid-123"
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| license_id | string | 是 | 许可证ID |
| device_id | string | 是 | 设备ID |

**成功响应**
```json
{
  "success": true
}
```

---

### 7. 查询许可证列表（管理员）

获取许可证列表。

**请求**
```
GET /api/admin/licenses?status=active&limit=100
X-API-Key: your_api_key
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 状态筛选：active/revoked |
| limit | integer | 否 | 返回数量限制（默认100） |

**成功响应**
```json
{
  "success": true,
  "licenses": [
    {
      "id": 1,
      "license_id": "LIC-ABC12345",
      "activation_code": "ABCDE-FGHIJ-KLMN",
      "email": "user@example.com",
      "plan": "monthly",
      "device_limit": 5,
      "issued_at": "2025-01-25T00:00:00Z",
      "valid_until": "2025-02-25T00:00:00Z",
      "user_hint": "测试用户",
      "status": "active",
      "created_at": "2025-01-25T00:00:00Z",
      "updated_at": "2025-01-25T00:00:00Z",
      "active_devices": 2
    }
  ]
}
```

---

### 8. 获取统计信息（管理员）

获取许可证统计信息。

**请求**
```
GET /api/admin/stats
X-API-Key: your_api_key
```

**成功响应**
```json
{
  "success": true,
  "stats": {
    "total_licenses": 100,
    "active_licenses": 95,
    "plan_statistics": {
      "monthly": 50,
      "yearly": 30,
      "lifetime": 20
    },
    "active_devices": 150
  }
}
```

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| INVALID_API_KEY | API密钥无效 |
| INVALID_REQUEST | 请求参数无效 |
| MISSING_LICENSE | 激活码不能为空 |
| MISSING_EMAIL | 邮箱不能为空 |
| INVALID_LICENSE | 激活码无效或已停用 |
| INTERNAL_ERROR | 服务器内部错误 |
| NOT_FOUND | API端点不存在 |

---

## 使用示例

### cURL 示例

**生成激活码**
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

**验证激活码**
```bash
curl -X POST http://localhost:5000/api/verify \
  -H "Content-Type: application/json" \
  -d '{
    "activation_code": "ABCDE-FGHIJ-KLMN",
    "email": "user@example.com",
    "device_id": "device-uuid-123"
  }'
```

**查询许可证列表**
```bash
curl -X GET "http://localhost:5000/api/admin/licenses?status=active&limit=50" \
  -H "X-API-Key: your_api_key"
```

### Python 示例

```python
import requests

# 生成激活码
response = requests.post(
    'http://localhost:5000/api/admin/generate',
    headers={'X-API-Key': 'your_api_key'},
    json={
        'plan': 'monthly',
        'email': 'user@example.com',
        'device_cap': 5,
        'days': 30
    }
)
print(response.json())

# 验证激活码
response = requests.post(
    'http://localhost:5000/api/verify',
    json={
        'activation_code': 'ABCDE-FGHIJ-KLMN',
        'email': 'user@example.com',
        'device_id': 'device-uuid-123'
    }
)
print(response.json())
```

---

## 注意事项

1. **安全性**
   - 不要在客户端代码中暴露 API Key
   - 使用 HTTPS 保护 API 通信
   - 定期更换 API Key

2. **性能优化**
   - 使用连接池
   - 添加缓存机制
   - 限制查询返回数量

3. **错误处理**
   - 检查响应的 `success` 字段
   - 根据错误码进行相应处理
   - 记录错误日志

4. **设备管理**
   - 设备ID应该是唯一且持久的
   - 定期清理不活跃的设备
   - 监控异常激活行为
