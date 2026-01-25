# License Manager 客户端使用文档

## 完整流程

本系统提供完整的许可证管理流程，包括：

1. **购买流程** - 用户选择套餐并购买
2. **激活流程** - 用户使用激活码激活设备
3. **验证流程** - 系统验证许可证有效性
4. **管理流程** - 管理员生成和管理许可证

## 访问地址

- **管理后台**: http://localhost:8080/admin/login.html
- **购买页面**: http://localhost:8080/client/purchase.html
- **激活页面**: http://localhost:8080/client/index.html

## 完整使用流程

### 步骤1：管理员生成许可证

1. 访问管理后台：http://localhost:8080/admin/login.html
2. 使用管理员账号登录（默认：admin / admin123）
3. 点击"生成许可证"按钮
4. 填写信息：
   - 套餐类型：月度版/年度版/终身版
   - 邮箱：用户购买时使用的邮箱
   - 设备数量限制：例如5台
   - 有效期：月度版30天，年度版365天，终身版留空
5. 点击"生成"按钮，获取激活码（格式：XXXXX-XXXXX-XXXXX）

### 步骤2：用户购买许可证

1. 访问购买页面：http://localhost:8080/client/purchase.html
2. 选择合适的套餐（月度版/年度版/终身版）
3. 填写邮箱地址
4. 点击"购买"按钮
5. 系统生成激活码（实际应用中应该集成支付系统）

### 步骤3：用户激活设备

1. 访问激活页面：http://localhost:8080/client/index.html
2. 输入激活码和邮箱
3. 点击"验证激活码"
4. 系统显示设备信息
5. 点击"激活此设备"
6. 激活成功，显示许可证信息

### 步骤4：应用验证许可证

应用在启动时调用验证API：

```javascript
// 示例代码
async function verifyLicense(activationCode, email) {
    const response = await fetch('http://localhost:5000/api/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            activation_code: activationCode,
            email: email,
            device_id: 'device-unique-id',
            device_name: 'User Device',
            ip_address: '127.0.0.1'
        })
    });
    
    const result = await response.json();
    
    if (result.valid) {
        console.log('许可证有效');
        console.log('许可证ID:', result.license_id);
        console.log('套餐类型:', result.plan);
        console.log('设备限制:', result.device_cap);
        console.log('已激活设备:', result.active_devices);
        return true;
    } else {
        console.log('许可证无效:', result.error);
        return false;
    }
}
```

## API 接口说明

### 1. 验证许可证

**端点**: `POST /api/verify`

**请求参数**:
```json
{
    "activation_code": "ABCDE-FGHIJ-KLMN",
    "email": "user@example.com",
    "device_id": "device-unique-id",
    "device_name": "User Device",
    "ip_address": "127.0.0.1"
}
```

**响应示例**:
```json
{
    "valid": true,
    "license_id": "LIC-ABC12345",
    "plan": "monthly",
    "device_cap": 5,
    "active_devices": 1,
    "issued_at": "2025-01-25T00:00:00Z",
    "valid_until": "2025-02-25T00:00:00Z",
    "user_hint": "用户备注"
}
```

### 2. 健康检查

**端点**: `GET /health`

**响应示例**:
```json
{
    "status": "ok",
    "timestamp": "2025-01-25T00:00:00Z"
}
```

## 集成到应用中

### 1. Swift (macOS/iOS)

```swift
import Foundation

class LicenseManager {
    private let apiURL = "http://localhost:5000"
    
    func verifyLicense(activationCode: String, email: String) async -> Bool {
        guard let url = URL(string: "\(apiURL)/api/verify") else {
            return false
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let deviceId = getDeviceId()
        let deviceName = getDeviceName()
        
        let body: [String: Any] = [
            "activation_code": activationCode,
            "email": email,
            "device_id": deviceId,
            "device_name": deviceName,
            "ip_address": ""
        ]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
            let (data, _, error) = URLSession.shared.data(for: request)
            
            guard let data = data, error == nil else {
                return false
            }
            
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let valid = json["valid"] as? Bool {
                return valid
            }
        } catch {
            print("验证失败: \(error)")
        }
        
        return false
    }
    
    private func getDeviceId() -> String {
        return UIDevice.current.identifierForVendor ?? "unknown-device"
    }
    
    private func getDeviceName() -> String {
        var systemInfo = utsname()
        uname(&systemInfo)
        return withUnsafePointer(to: &systemInfo.machine) {
            $0.withMemoryRebound(to: CChar.self, capacity: 1) {
                String(validatingUTF8: $0)
            }
        } ?? "Unknown Device"
    }
}
```

### 2. Python

```python
import requests
import platform
import uuid

class LicenseManager:
    def __init__(self, api_url="http://localhost:5000"):
        self.api_url = api_url
    
    def verify_license(self, activation_code, email):
        device_id = self.get_device_id()
        device_name = platform.node()
        
        data = {
            "activation_code": activation_code,
            "email": email,
            "device_id": device_id,
            "device_name": device_name,
            "ip_address": ""
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/api/verify",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            result = response.json()
            return result.get("valid", False)
        except Exception as e:
            print(f"验证失败: {e}")
            return False
    
    def get_device_id(self):
        return f"device-{uuid.uuid4().hex[:16]}"
```

### 3. JavaScript (Web)

```javascript
class LicenseManager {
    constructor(apiUrl = 'http://localhost:5000') {
        this.apiUrl = apiUrl;
    }
    
    async verifyLicense(activationCode, email) {
        const deviceId = this.getDeviceId();
        const deviceName = this.getDeviceName();
        
        const response = await fetch(`${this.apiUrl}/api/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                activation_code: activationCode,
                email: email,
                device_id: deviceId,
                device_name: deviceName,
                ip_address: ''
            })
        });
        
        const result = await response.json();
        return result.valid || false;
    }
    
    getDeviceId() {
        let deviceId = localStorage.getItem('device_id');
        if (!deviceId) {
            deviceId = 'device-' + Math.random().toString(36).substring(2, 15);
            localStorage.setItem('device_id', deviceId);
        }
        return deviceId;
    }
    
    getDeviceName() {
        return navigator.userAgent.split(' ')[0] || 'Unknown Device';
    }
}
```

## 安全建议

1. **HTTPS**: 生产环境使用HTTPS加密传输
2. **API Key**: 可选配置API Key防止滥用
3. **设备绑定**: 每个设备绑定唯一ID，防止共享
4. **设备限制**: 限制同时激活的设备数量
5. **会话超时**: 设置合理的会话超时时间
6. **IP限制**: 可选添加IP白名单

## 测试流程

1. 启动服务：`docker-compose up -d`
2. 访问管理后台：http://localhost:8080/admin/login.html
3. 生成测试许可证
4. 访问购买页面：http://localhost:8080/client/purchase.html
5. 访问激活页面：http://localhost:8080/client/index.html
6. 测试激活流程
7. 测试设备限制
8. 测试许可证过期

## 故障排查

### 问题1：无法连接到API
- 检查API服务是否启动：`docker-compose ps`
- 检查端口是否正确：`curl http://localhost:5000/health`
- 检查防火墙设置

### 问题2：激活失败
- 检查激活码格式是否正确（XXXXX-XXXXX-XXXXX）
- 检查邮箱是否匹配
- 检查设备数量是否超限
- 检查许可证是否已过期

### 问题3：管理后台无法访问
- 检查是否正确登录
- 检查会话是否超时（1小时）
- 检查浏览器是否支持Cookie

## 扩展功能

可以根据需要扩展以下功能：

1. **支付集成** - 集成微信支付、支付宝等
2. **邮件通知** - 发送激活码到用户邮箱
3. **自动续费** - 到期自动续费
4. **使用统计** - 统计用户使用情况
5. **设备管理** - 远程停用设备
6. **许可证转让** - 允许用户转让许可证
