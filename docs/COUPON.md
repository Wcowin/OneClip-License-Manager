# 优惠码系统指南

## 概述

License Manager 支持优惠码功能，管理员可以创建各种类型的优惠码，用户在购买时可以使用优惠码享受折扣。

## 优惠码类型

### 固定金额折扣
- 减免固定金额
- 适用于小额优惠
- 示例：减免5元

### 百分比折扣
- 按百分比减免
- 适用于大额优惠
- 示例：减免20%

## 创建优惠码

### 通过管理后台

1. 登录管理后台
2. 点击"创建优惠码"
3. 填写优惠码信息：
   - **优惠码**：如 `WELCOME2024`
   - **名称**：优惠码名称
   - **折扣类型**：固定金额/百分比
   - **折扣值**：优惠金额或百分比
   - **最低消费金额**：0表示无限制
   - **适用套餐**：可多选
   - **使用次数限制**：0表示无限制
   - **每用户使用次数限制**：0表示无限制

### 通过API

```bash
curl -X POST http://localhost:5000/api/admin/coupons \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your_session_cookie" \
  -d '{
    "code": "WELCOME2024",
    "name": "新用户优惠",
    "type": "fixed",
    "value": 5.00,
    "min_amount": 0.00,
    "plans": ["monthly", "yearly", "lifetime"],
    "usage_limit": 100,
    "user_limit": 1
  }'
```

## 使用优惠码

### 用户购买流程

1. 选择套餐
2. 输入邮箱地址
3. 输入优惠码（可选）
4. 系统自动验证优惠码
5. 显示优惠金额
6. 完成支付

### 优惠码验证规则

优惠码必须满足以下条件才能使用：

1. **优惠码存在**：优惠码已创建
2. **优惠码激活**：优惠码状态为激活
3. **有效期有效**：在有效期内
4. **使用次数未超限**：未达到使用次数限制
5. **用户使用次数未超限**：用户未超过使用次数限制
6. **最低消费金额**：订单金额达到最低消费金额
7. **适用套餐**：优惠码适用于当前套餐

## 优惠码管理

### 查看优惠码列表

```bash
curl -X GET http://localhost:5000/api/admin/coupons \
  -H "Cookie: session=your_session_cookie"
```

### 启用/停用优惠码

```bash
curl -X POST http://localhost:5000/api/admin/coupons/1/toggle \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your_session_cookie" \
  -d '{"is_active": true}'
```

### 删除优惠码

```bash
curl -X DELETE http://localhost:5000/api/admin/coupons/1 \
  -H "Cookie: session=your_session_cookie"
```

## 优惠码使用记录

系统会自动记录每次优惠码的使用情况，包括：

- 使用时间
- 用户邮箱
- 订单ID
- 原始金额
- 优惠金额
- 最终金额

管理员可以通过数据库查询使用记录：

```sql
SELECT * FROM coupon_usage_logs ORDER BY used_at DESC;
```

## 常见问题

### Q: 优惠码如何生成？

A: 系统不自动生成优惠码，需要管理员手动创建。建议使用有意义的代码，如 `WELCOME2024`、`SAVE20` 等。

### Q: 优惠码可以设置有效期吗？

A: 可以。在创建优惠码时设置 `start_date` 和 `end_date`。

### Q: 如何限制优惠码的使用次数？

A: 设置 `usage_limit` 参数控制总使用次数，设置 `user_limit` 参数控制每个用户的使用次数。

### Q: 优惠码可以重复使用吗？

A: 取决于设置。如果 `usage_limit` 为 0，则无限制；如果 `user_limit` 为 0，则每个用户可以使用多次。

### Q: 如何查看优惠码使用情况？

A: 查看管理后台的优惠码列表，或直接查询 `coupon_usage_logs` 表。

### Q: 优惠码可以修改吗？

A: 不支持修改，只能删除后重新创建。

## 最佳实践

1. **命名规范**：使用有意义的优惠码名称，便于识别
2. **合理限制**：设置合理的使用次数限制，防止滥用
3. **有效期控制**：设置合理的有效期，避免长期有效
4. **适用套餐**：明确优惠码适用的套餐范围
5. **监控使用**：定期查看优惠码使用记录，及时调整策略

## 示例场景

### 新用户欢迎优惠

```json
{
  "code": "WELCOME2024",
  "name": "新用户欢迎优惠",
  "type": "fixed",
  "value": 5.00,
  "min_amount": 0.00,
  "plans": ["monthly"],
  "usage_limit": 1000,
  "user_limit": 1,
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

### 年度版折扣

```json
{
  "code": "YEARLY20",
  "name": "年度版8折",
  "type": "percentage",
  "value": 20.00,
  "min_amount": 200.00,
  "plans": ["yearly", "lifetime"],
  "usage_limit": 0,
  "user_limit": 0
}
```

### 限时抢购

```json
{
  "code": "FLASHSALE",
  "name": "限时抢购",
  "type": "fixed",
  "value": 10.00,
  "min_amount": 50.00,
  "plans": ["yearly"],
  "usage_limit": 100,
  "user_limit": 1,
  "start_date": "2024-01-01",
  "end_date": "2024-01-07"
}
```

## 技术实现

### 数据库表结构

```sql
-- 优惠码表
CREATE TABLE coupons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    type ENUM('fixed', 'percentage') NOT NULL,
    value DECIMAL(10,2) NOT NULL,
    min_amount DECIMAL(10,2) DEFAULT 0.00,
    plans JSON,
    usage_limit INT DEFAULT 0,
    user_limit INT DEFAULT 0,
    start_date TIMESTAMP NULL,
    end_date TIMESTAMP NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 优惠码使用记录表
CREATE TABLE coupon_usage_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    coupon_id INT NOT NULL,
    coupon_code VARCHAR(50) NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    order_id VARCHAR(100) NOT NULL,
    original_amount DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) NOT NULL,
    final_amount DECIMAL(10,2) NOT NULL,
    used_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (coupon_id) REFERENCES coupons(id) ON DELETE CASCADE
);
```

### API接口

- `GET /api/admin/coupons` - 获取优惠码列表
- `POST /api/admin/coupons` - 创建优惠码
- `DELETE /api/admin/coupons/<id>` - 删除优惠码
- `POST /api/admin/coupons/<id>/toggle` - 启用/停用优惠码
- `POST /api/payment/verify-coupon` - 验证优惠码

## 相关文档

- [API文档](API.md) - 完整的API接口文档
- [支付集成](PAYMENT.md) - 支付系统配置
- [部署指南](DEPLOY.md) - 部署教程
