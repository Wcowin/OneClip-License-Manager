# 支付系统集成指南

## 概述

本demo使用模拟支付，展示完整的购买流程。在生产环境中，需要集成真实的支付系统。

**ZPAY集成**：本demo已集成ZPAY支付系统，开箱即用。只需配置环境变量即可启用真实支付。

## 推荐支付平台

### OneClip推荐：zpay
- **zpay** - [OneClip](https://oneclip.cloud/)正在使用的支付系统
- 作为微信支付服务商和支付宝ISV服务商
- 专业为开发者/个体户/小微企业提供正规、安全、稳定的创收支持
- 解决个人收款痛点，是个人站长收款的最佳解决方案
- 正规商户渠道，100%支付成功率，安全合法
- 支持微信支付、支付宝
- 简单易用，适合国内用户
- 链接：https://z-pay.cn/?uid=19636

![下载.png](https://i.imgant.com/v2/W5l9vVj.png)

### 其他支付平台

**国内用户**：
- 微信支付 - 适合移动端用户
- 支付宝 - 适合PC端和移动端用户

**国际用户**：
- Stripe - 适合信用卡支付
- PayPal - 适合国际用户

## 集成步骤

### 1. 注册支付平台账号

**微信支付**：
1. 注册微信商户账号
2. 获取商户号、API密钥
3. 配置支付回调地址

**支付宝**：
1. 注册支付宝开放平台账号
2. 创建应用并获取AppID、私钥
3. 配置支付回调地址

**Stripe**：
1. 注册Stripe账号
2. 获取API密钥（测试环境和生产环境）
3. 配置Webhook

### 2. 修改后端代码

#### 添加支付配置

在 `backend/app.py` 中添加：

```python
# 支付配置
WECHAT_PAY_APP_ID = os.getenv('WECHAT_PAY_APP_ID')
WECHAT_PAY_MCH_ID = os.getenv('WECHAT_PAY_MCH_ID')
WECHAT_PAY_API_KEY = os.getenv('WECHAT_PAY_API_KEY')

ALIPAY_APP_ID = os.getenv('ALIPAY_APP_ID')
ALIPAY_PRIVATE_KEY = os.getenv('ALIPAY_PRIVATE_KEY')
ALIPAY_PUBLIC_KEY = os.getenv('ALIPAY_PUBLIC_KEY')

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
```

#### 添加支付API

```python
@app.route('/api/payment/create', methods=['POST'])
@require_admin
def create_payment():
    """创建支付订单"""
    data = request.get_json()
    plan = data.get('plan')
    email = data.get('email')
    
    # 计算价格
    prices = {
        'monthly': 29,
        'yearly': 299,
        'lifetime': 999
    }
    
    # 创建支付订单
    order_id = generate_order_id()
    
    # 调用支付平台API
    # 这里以支付宝为例
    try:
        import alipay
        alipay_client = alipay.AliPay(
            appid=ALIPAY_APP_ID,
            app_notify_url='https://yourdomain.com/api/payment/callback',
            app_private_key_string=ALIPAY_PRIVATE_KEY,
            alipay_public_key_string=ALIPAY_PUBLIC_KEY
        )
        
        # 创建订单
        order_string = alipay_client.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(prices[plan]),
            subject=f'License Manager - {plan}',
            return_url='https://yourdomain.com/client/complete_order.html'
        )
        
        return jsonify({
            'success': True,
            'payment_url': order_string,
            'order_id': order_id
        })
    except Exception as e:
        logger.error(f"创建支付订单失败: {e}")
        return jsonify({
            'success': False,
            'message': '创建支付订单失败'
        }), 500

@app.route('/api/payment/callback', methods=['POST'])
def payment_callback():
    """处理支付回调"""
    # 验证支付结果
    # 生成激活码
    # 返回给前端
    
    try:
        # 获取支付结果
        # 验证签名
        # 检查订单状态
        
        # 生成激活码
        activation_code = generate_activation_code()
        license_id = generate_license_id()
        
        # 保存到数据库
        license_manager.create_license(
            activation_code=activation_code,
            email=email,
            plan=plan,
            device_cap=5,
            days=30 if plan == 'monthly' else 365 if plan == 'yearly' else None
        )
        
        return jsonify({
            'success': True,
            'activation_code': activation_code,
            'license_id': license_id
        })
    except Exception as e:
        logger.error(f"支付回调处理失败: {e}")
        return jsonify({
            'success': False,
            'message': '支付回调处理失败'
        }), 500
```

### 3. 修改前端代码

#### 修改 `client/purchase.html`

```javascript
document.getElementById('purchase-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const plan = document.getElementById('plan-type').value;
    const email = document.getElementById('purchase-email').value.trim();
    
    if (!email) {
        alert('请输入邮箱地址');
        return;
    }
    
    // 调用支付API
    try {
        const response = await fetch(`${API_URL}/api/payment/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                plan: plan,
                email: email
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 跳转到支付页面
            window.location.href = result.payment_url;
        } else {
            alert('创建支付订单失败');
        }
    } catch (error) {
        console.error('创建支付订单失败:', error);
        alert('创建支付订单失败');
    }
});
```

#### 修改 `client/complete_order.html`

```javascript
// 页面加载时从URL参数获取激活码
window.addEventListener('load', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const activationCode = urlParams.get('activation_code');
    const email = urlParams.get('email');
    const plan = urlParams.get('plan');
    
    if (activationCode) {
        // 显示激活码
        document.getElementById('activationCode').textContent = activationCode;
        document.getElementById('userEmail').textContent = email;
        document.getElementById('purchaseType').textContent = plan === 'monthly' ? '月度版' : plan === 'yearly' ? '年度版' : '终身版';
    }
});
```

### 4. 环境变量配置

在 `.env.example` 中添加：

```bash
# 支付配置
# 微信支付
WECHAT_PAY_APP_ID=your_wechat_app_id
WECHAT_PAY_MCH_ID=your_wechat_mch_id
WECHAT_PAY_API_KEY=your_wechat_api_key

# 支付宝
ALIPAY_APP_ID=your_alipay_app_id
ALIPAY_PRIVATE_KEY=your_alipay_private_key
ALIPAY_PUBLIC_KEY=your_alipay_public_key

# Stripe
STRIPE_SECRET_KEY=your_stripe_secret_key
```

### 5. 安装支付SDK

在 `backend/requirements.txt` 中添加：

```text
# 支付SDK
alipay-sdk-python==3.7.0
wechatpy==1.8.18
stripe==7.12.0
```

## 测试支付

### 微信支付测试

1. 使用微信支付沙箱环境
2. 测试金额：0.01元
3. 验证支付流程

### 支付宝测试

1. 使用支付宝沙箱环境
2. 测试金额：0.01元
3. 验证支付流程

### Stripe测试

1. 使用Stripe测试环境
2. 使用测试卡号
3. 验证支付流程

## 安全建议

1. **验证签名** - 所有支付回调必须验证签名
2. **防重复通知** - 使用订单号去重
3. **金额验证** - 验证支付金额是否正确
4. **异步处理** - 支付回调异步处理，避免超时
5. **日志记录** - 记录所有支付操作
6. **异常监控** - 监控支付异常情况

## 常见问题

### Q1: 支付回调未收到？

**A**: 检查回调地址配置，确保服务器可访问

### Q2: 支付验证失败？

**A**: 检查API密钥配置，验证签名算法

### Q3: 如何测试支付？

**A**: 使用各支付平台的沙箱环境进行测试

## 参考资料

- [微信支付开发文档](https://pay.weixin.qq.com/wiki/doc/api/index.html)
- [支付宝开放平台](https://open.alipay.com/)
- [Stripe文档](https://stripe.com/docs)
