#!/usr/bin/env python3
"""
License Manager API 服务器
提供RESTful API接口用于许可证管理
"""

from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import sys
from datetime import datetime, timezone
import logging
import time
from functools import wraps

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from license_manager import LicenseManager
from email_sender import send_activation_email

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Session密钥配置
SECRET_KEY = os.getenv('ADMIN_SECRET_KEY', 'your-secret-key-change-this-in-production')
app.secret_key = SECRET_KEY

# 管理员配置
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

# 登录失败记录
login_attempts = {}
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_TIME = 3600  # 1小时
SESSION_TIMEOUT = 3600  # 1小时

# 数据库配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'license_user'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME', 'license_db'),
    'charset': 'utf8mb4'
}

# 安全检查
if not DB_CONFIG['password']:
    raise ValueError("❌ DB_PASSWORD 环境变量未设置！请先设置: export DB_PASSWORD='your_password'")

# API密钥配置（可选，用于客户端验证）
API_KEY = os.getenv('API_KEY')

# 邮件配置
EMAIL_CONFIG = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.qq.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', 587)),
    'smtp_user': os.getenv('SMTP_USER'),
    'smtp_password': os.getenv('SMTP_PASSWORD'),
    'from_email': os.getenv('SMTP_FROM_EMAIL'),
    'from_name': os.getenv('SMTP_FROM_NAME', 'License Manager'),
    'use_ssl': os.getenv('SMTP_USE_SSL', 'false').lower() == 'true'
}

# 检查邮件配置
email_enabled = all([
    EMAIL_CONFIG['smtp_server'],
    EMAIL_CONFIG['smtp_user'],
    EMAIL_CONFIG['smtp_password'],
    EMAIL_CONFIG['from_email']
])

# ZPAY支付配置
ZPAY_CONFIG = {
    'pid': os.getenv('ZPAY_PID', ''),
    'key': os.getenv('ZPAY_KEY', ''),
    'api_url': os.getenv('ZPAY_API_URL', 'https://zpayz.cn/'),
    'notify_url': os.getenv('ZPAY_NOTIFY_URL', ''),
    'return_url': os.getenv('ZPAY_RETURN_URL', '')
}

# 导入ZPAY适配器
try:
    from zpay_adapter import ZPayAdapter
    # 初始化ZPAY适配器
    if ZPAY_CONFIG['pid'] and ZPAY_CONFIG['key']:
        zpay_adapter = ZPayAdapter(ZPAY_CONFIG)
        logger.info("✅ ZPAY支付系统已启用")
    else:
        zpay_adapter = None
        logger.info("⚠️ ZPAY配置不完整，支付功能将使用模拟模式")
except ImportError:
    zpay_adapter = None
    logger.info("⚠️ ZPAY适配器未找到，支付功能将使用模拟模式")

# 初始化许可证管理器
license_manager = LicenseManager(DB_CONFIG)


def check_login_attempts(ip):
    """检查登录尝试次数"""
    now = time.time()
    if ip not in login_attempts:
        login_attempts[ip] = []
    
    # 清理1小时前的记录
    login_attempts[ip] = [t for t in login_attempts[ip] if now - t < LOGIN_LOCKOUT_TIME]
    
    # 检查是否超过5次失败
    if len(login_attempts[ip]) >= MAX_LOGIN_ATTEMPTS:
        return False
    
    return True


def record_login_attempt(ip, success):
    """记录登录尝试"""
    if not success:
        login_attempts[ip] = login_attempts.get(ip, []) + [time.time()]


def is_admin_logged_in() -> bool:
    """检查管理员是否已登录且会话未超时"""
    if not session.get('admin_logged_in'):
        return False
    
    # 检查会话超时
    login_time = session.get('login_time', 0)
    if time.time() - login_time > SESSION_TIMEOUT:
        session.clear()
        return False
    
    return True


def require_admin(f):
    """要求管理员登录装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin_logged_in():
            return jsonify({
                'success': False,
                'message': '未登录或会话已超时',
                'code': 'UNAUTHORIZED'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def require_api_key(f):
    """API密钥验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != API_KEY:
            logger.warning(f"❌ API密钥验证失败: {request.remote_addr}")
            return jsonify({
                'success': False,
                'message': 'API密钥无效',
                'code': 'INVALID_API_KEY'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """管理员登录"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        ip = request.remote_addr
        
        # 检查登录尝试次数
        if not check_login_attempts(ip):
            return jsonify({
                'success': False,
                'message': '登录失败次数过多，请1小时后再试'
            }), 429
        
        # 验证用户名密码
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            # 登录成功
            session['admin_logged_in'] = True
            session['login_time'] = time.time()
            session['username'] = username
            record_login_attempt(ip, True)
            logger.info(f"✅ 管理员登录成功: {username} from {ip}")
            return jsonify({
                'success': True,
                'message': '登录成功'
            })
        else:
            # 登录失败
            record_login_attempt(ip, False)
            logger.warning(f"❌ 管理员登录失败: {username} from {ip}")
            return jsonify({
                'success': False,
                'message': '用户名或密码错误'
            }), 401
    except Exception as e:
        logger.error(f"❌ 登录处理失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '登录失败'
        }), 500


@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    """管理员登出"""
    session.clear()
    return jsonify({
        'success': True,
        'message': '登出成功'
    })


@app.route('/api/admin/check', methods=['GET'])
def admin_check():
    """检查登录状态"""
    return jsonify({
        'success': True,
        'logged_in': is_admin_logged_in(),
        'username': session.get('username') if is_admin_logged_in() else None
    })


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@app.route('/api/verify', methods=['POST'])
def verify_license():
    """验证许可证API端点"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据为空',
                'code': 'INVALID_REQUEST'
            }), 400
        
        # 提取参数
        activation_code = data.get('activation_code', '').strip()
        email = data.get('email', '').strip()
        device_id = data.get('device_id', '').strip()
        device_name = data.get('device_name', '')
        ip_address = data.get('ip_address') or request.remote_addr
        
        logger.info(f"🔍 收到验证请求: 邮箱={email}, 激活码={activation_code[:8]}..., 设备ID={device_id}")
        
        # 验证必要参数
        if not activation_code:
            return jsonify({
                'success': False,
                'message': '激活码不能为空',
                'code': 'MISSING_LICENSE'
            }), 400
        
        if not email:
            return jsonify({
                'success': False,
                'message': '邮箱不能为空',
                'code': 'MISSING_EMAIL'
            }), 400
        
        # 验证许可证
        result = license_manager.verify_license(
            activation_code, 
            email, 
            device_id=device_id,
            device_name=device_name,
            ip_address=ip_address
        )
        
        if result['valid']:
            logger.info(f"✅ 许可证验证成功: 许可证ID={result['license_id']}, 设备ID={device_id}")
            return jsonify({
                'success': True,
                'message': '许可证验证成功',
                'code': 'SUCCESS',
                'license': {
                    'key': result['license_id'],
                    'type': result['plan'],
                    'expiresAt': result['valid_until']
                },
                'isValid': True,
                'licenseType': result['plan'],
                'expiresAt': result['valid_until'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        else:
            logger.warning(f"❌ 许可证验证失败: 激活码={activation_code[:8]}..., 邮箱={email}, 错误={result.get('error', '未知错误')}")
            return jsonify({
                'success': False,
                'message': result.get('error', '许可证验证失败'),
                'code': 'INVALID_LICENSE',
                'isValid': False,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }), 400
            
    except Exception as e:
        logger.error(f"❌ 验证过程中发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'服务器内部错误: {str(e)}',
            'code': 'INTERNAL_ERROR',
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/admin/generate', methods=['POST'])
@require_admin
def admin_generate_license():
    """管理员生成许可证"""
    try:
        data = request.get_json(force=True)
        plan = data.get('plan')
        email = data.get('email')
        device_cap = int(data.get('device_cap', 5))
        days = data.get('days')
        user_hint = data.get('user_hint')
        
        if days is not None:
            try:
                days = int(days)
            except Exception:
                days = None
        
        result = license_manager.generate_license(plan, email, device_cap, days, user_hint)
        if 'error' in result:
            return jsonify({'success': False, 'message': result['error']}), 400
        
        return jsonify({'success': True, 'license': result})
    except Exception as e:
        logger.error(f"❌ 生成许可证失败: {str(e)}")
        return jsonify({'success': False, 'message': '生成失败'}), 500


@app.route('/api/admin/send-email', methods=['POST'])
@require_admin
def admin_send_email():
    """管理员发送激活码邮件"""
    try:
        data = request.get_json(force=True)
        email = data.get('email')
        activation_code = data.get('activation_code')
        plan = data.get('plan')
        device_cap = data.get('device_cap', 5)
        valid_until = data.get('valid_until')
        
        if not email or not activation_code:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
        if not email_enabled:
            return jsonify({'success': False, 'message': '邮件功能未配置'}), 400
        
        license_info = {
            'activation_code': activation_code,
            'plan': plan,
            'device_cap': device_cap,
            'valid_until': valid_until
        }
        
        if send_activation_email(email, license_info, EMAIL_CONFIG):
            return jsonify({'success': True, 'message': '邮件发送成功'})
        else:
            return jsonify({'success': False, 'message': '邮件发送失败'}), 500
            
    except Exception as e:
        logger.error(f"❌ 发送邮件失败: {str(e)}")
        return jsonify({'success': False, 'message': '发送失败'}), 500


# ==================== 优惠码管理 ====================

@app.route('/api/admin/coupons', methods=['GET'])
@require_admin
def admin_get_coupons():
    """获取优惠码列表"""
    try:
        conn = license_manager.get_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500
        
        cur = conn.cursor()
        cur.execute('''
            SELECT id, code, name, type, value, min_amount, plans, usage_limit, user_limit,
                   start_date, end_date, is_active, usage_count, created_at
            FROM coupons
            ORDER BY created_at DESC
        ''')
        rows = cur.fetchall()
        cur.close()
        
        coupons = []
        for row in rows:
            coupons.append({
                'id': row[0],
                'code': row[1],
                'name': row[2],
                'type': row[3],
                'value': row[4],
                'min_amount': row[5],
                'plans': json.loads(row[6]) if row[6] else [],
                'usage_limit': row[7],
                'user_limit': row[8],
                'start_date': row[9].isoformat() if row[9] else None,
                'end_date': row[10].isoformat() if row[10] else None,
                'is_active': bool(row[11]),
                'usage_count': row[12],
                'created_at': row[13].isoformat() if row[13] else None
            })
        
        return jsonify({'success': True, 'coupons': coupons})
    except Exception as e:
        logger.error(f"❌ 获取优惠码列表失败: {str(e)}")
        return jsonify({'success': False, 'message': '获取优惠码列表失败'}), 500


@app.route('/api/admin/coupons', methods=['POST'])
@require_admin
def admin_create_coupon():
    """创建优惠码"""
    try:
        data = request.get_json(force=True)
        code = data.get('code', '').strip()
        name = data.get('name', '')
        coupon_type = data.get('type', 'fixed')
        value = data.get('value', 0)
        min_amount = data.get('min_amount', 0)
        plans = data.get('plans', [])
        usage_limit = data.get('usage_limit', 0)
        user_limit = data.get('user_limit', 0)
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not code or not name:
            return jsonify({'success': False, 'message': '优惠码和名称不能为空'}), 400
        
        conn = license_manager.get_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500
        cur = conn.cursor()
        
        # 检查优惠码是否已存在
        cur.execute('SELECT id FROM coupons WHERE code = %s', (code,))
        if cur.fetchone():
            cur.close()
            return jsonify({'success': False, 'message': '优惠码已存在'}), 400
        
        # 插入新优惠码
        cur.execute('''
            INSERT INTO coupons (code, name, type, value, min_amount, plans, usage_limit, user_limit, start_date, end_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (code, name, coupon_type, value, min_amount, json.dumps(plans), usage_limit, user_limit, start_date, end_date))
        
        conn.commit()
        cur.close()
        
        logger.info(f"✅ 创建优惠码成功: {code}")
        return jsonify({'success': True, 'message': '优惠码创建成功'})
    except Exception as e:
        logger.error(f"❌ 创建优惠码失败: {str(e)}")
        return jsonify({'success': False, 'message': '创建优惠码失败'}), 500


@app.route('/api/admin/coupons/<int:coupon_id>', methods=['DELETE'])
@require_admin
def admin_delete_coupon(coupon_id):
    """删除优惠码"""
    try:
        conn = license_manager.get_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500
        cur = conn.cursor()
        cur.execute('DELETE FROM coupons WHERE id = %s', (coupon_id,))
        if cur.rowcount == 0:
            cur.close()
            return jsonify({'success': False, 'message': '优惠码不存在'}), 404
        
        conn.commit()
        cur.close()
        
        logger.info(f"✅ 删除优惠码成功: ID={coupon_id}")
        return jsonify({'success': True, 'message': '优惠码删除成功'})
    except Exception as e:
        logger.error(f"❌ 删除优惠码失败: {str(e)}")
        return jsonify({'success': False, 'message': '删除优惠码失败'}), 500


@app.route('/api/admin/coupons/<int:coupon_id>/toggle', methods=['POST'])
@require_admin
def admin_toggle_coupon(coupon_id):
    """启用/停用优惠码"""
    try:
        data = request.get_json(force=True)
        is_active = data.get('is_active', True)
        
        conn = license_manager.get_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500
        cur = conn.cursor()
        cur.execute('UPDATE coupons SET is_active = %s WHERE id = %s', (is_active, coupon_id))
        if cur.rowcount == 0:
            cur.close()
            return jsonify({'success': False, 'message': '优惠码不存在'}), 404
        
        conn.commit()
        cur.close()
        
        logger.info(f"✅ 优惠码状态更新成功: ID={coupon_id}, is_active={is_active}")
        return jsonify({'success': True, 'message': '优惠码状态更新成功'})
    except Exception as e:
        logger.error(f"❌ 更新优惠码状态失败: {str(e)}")
        return jsonify({'success': False, 'message': '更新优惠码状态失败'}), 500


@app.route('/api/payment/create', methods=['POST'])
def create_payment():
    """创建支付订单"""
    try:
        data = request.get_json(force=True)
        plan = data.get('plan')
        email = data.get('email')
        coupon_code = data.get('coupon_code')
        
        # 计算价格
        prices = {
            'monthly': 29.99,
            'yearly': 299.99,
            'lifetime': 399.99
        }
        
        base_price = prices.get(plan, 0)
        final_price = base_price
        discount_amount = 0
        coupon_id = None
        
        # 验证优惠码
        if coupon_code:
            verify_result = verify_coupon_internal({
                'code': coupon_code,
                'plan': plan,
                'base_price': base_price,
                'email': email
            })
            if verify_result.get('valid'):
                final_price = verify_result.get('final_price', base_price)
                discount_amount = verify_result.get('discount', 0)
                coupon_id = verify_result.get('coupon_id')
        
        # 生成订单ID
        order_id = f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        
        # 保存订单到数据库
        conn = license_manager.get_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO payment_orders (order_id, email, plan, amount, final_amount, coupon_code, coupon_id, discount_amount, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (order_id, email, plan, base_price, final_price, coupon_code, coupon_id, discount_amount, 'pending'))
            conn.commit()
            cur.close()
        
        # 调用 ZPAY 创建订单
        if zpay_adapter:
            result = zpay_adapter.create_order(
                out_trade_no=order_id,
                total_amount=int(final_price * 100),  # 转换为分
                subject=f'{plan}套餐',
                body=f'{plan}套餐 - {email}',
                payment_type='alipay',
                client_ip=request.remote_addr,
                device='pc',
                param=f'plan:{plan}|email:{email}'
            )
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'order_id': order_id,
                    'payment_url': result['payment_url'],
                    'amount': final_price,
                    'discount': discount_amount
                })
            else:
                return jsonify({'success': False, 'message': result.get('message', '创建支付订单失败')}), 500
        else:
            # 模拟支付
            return jsonify({
                'success': True,
                'order_id': order_id,
                'payment_url': f'/client/complete_order.html?order_id={order_id}',
                'amount': final_price,
                'discount': discount_amount,
                'simulated': True
            })
            
    except Exception as e:
        logger.error(f"❌ 创建支付订单失败: {str(e)}")
        return jsonify({'success': False, 'message': '创建支付订单失败'}), 500


def verify_coupon_internal(data):
    """内部优惠码验证函数"""
    code = data.get('code', '').strip()
    plan = data.get('plan')
    base_price = data.get('base_price', 0)
    email = data.get('email', '')
    
    if not code or not plan or not base_price:
        return {'valid': False, 'message': '缺少必要参数'}
    
    conn = license_manager.get_connection()
    if not conn:
        return {'valid': False, 'message': '数据库连接失败'}
    cur = conn.cursor(dictionary=True)
    cur.execute('''
        SELECT id, type, value, min_amount, plans, usage_limit, user_limit,
               start_date, end_date, is_active, usage_count
        FROM coupons
        WHERE code = %s
    ''', (code,))
    coupon = cur.fetchone()
    cur.close()
    
    if not coupon:
        return {'valid': False, 'message': '优惠码不存在'}
    
    # 检查优惠码是否激活
    if not coupon['is_active']:
        return {'valid': False, 'message': '优惠码已失效'}
    
    # 检查有效期
    now = datetime.now(timezone.utc)
    if coupon['start_date'] and now < coupon['start_date']:
        return {'valid': False, 'message': '优惠码尚未生效'}
    if coupon['end_date'] and now > coupon['end_date']:
        return {'valid': False, 'message': '优惠码已过期'}
    
    # 检查使用次数限制
    if coupon['usage_limit'] > 0 and coupon['usage_count'] >= coupon['usage_limit']:
        return {'valid': False, 'message': '优惠码已达到使用次数限制'}
    
    # 检查最低消费金额
    if base_price < coupon['min_amount']:
        return {'valid': False, 'message': f'最低消费金额 ¥{coupon["min_amount"]}'}
    
    # 检查适用套餐
    if coupon['plans']:
        plans_list = coupon['plans'] if isinstance(coupon['plans'], list) else json.loads(coupon['plans'])
        if plan not in plans_list:
            return {'valid': False, 'message': '此优惠码不适用于当前套餐'}
    
    # 检查用户使用次数限制
    if coupon['user_limit'] > 1:
        cur = conn.cursor()
        cur.execute('''
            SELECT COUNT(*) FROM coupon_usage_logs
            WHERE coupon_id = %s AND user_email = %s
        ''', (coupon['id'], email))
        result = cur.fetchone()
        user_usage_count = result[0] if result else 0
        cur.close()
        
        if user_usage_count >= coupon['user_limit']:
            return {'valid': False, 'message': '您已达到此优惠码的使用次数限制'}
    
    # 计算折扣
    if coupon['type'] == 'fixed':
        discount = coupon['value']
    else:  # percentage
        discount = base_price * (coupon['value'] / 100)
    
    final_price = max(0, base_price - discount)
    
    return {
        'valid': True,
        'message': f'优惠码有效，减免 ¥{discount:.2f}',
        'discount': discount,
        'final_price': final_price,
        'coupon_id': coupon['id']
    }


@app.route('/api/payment/verify-coupon', methods=['POST'])
def verify_coupon():
    """验证优惠码"""
    try:
        data = request.get_json(force=True)
        code = data.get('code', '').strip()
        plan = data.get('plan')
        device_cap = int(data.get('device_cap', 5))
        base_price = float(data.get('base_price', 0))
        days = data.get('days')
        email = data.get('email', '')
        
        if not code or not plan or not base_price:
            return jsonify({'valid': False, 'message': '缺少必要参数'}), 400
        
        conn = license_manager.get_connection()
        if not conn:
            return jsonify({'valid': False, 'message': '数据库连接失败'}), 500
        cur = conn.cursor(dictionary=True)
        cur.execute('''
            SELECT id, type, value, min_amount, plans, usage_limit, user_limit,
                   start_date, end_date, is_active, usage_count
            FROM coupons
            WHERE code = %s
        ''', (code,))
        coupon = cur.fetchone()
        cur.close()
        
        if not coupon:
            return jsonify({'valid': False, 'message': '优惠码不存在'}), 404
        
        # 检查优惠码是否激活
        if not coupon['is_active']:
            return jsonify({'valid': False, 'message': '优惠码已失效'})
        
        # 检查有效期
        now = datetime.now(timezone.utc)
        if coupon['start_date'] and now < coupon['start_date']:
            return jsonify({'valid': False, 'message': '优惠码尚未生效'})
        if coupon['end_date'] and now > coupon['end_date']:
            return jsonify({'valid': False, 'message': '优惠码已过期'})
        
        # 检查使用次数限制
        if coupon['usage_limit'] > 0 and coupon['usage_count'] >= coupon['usage_limit']:
            return jsonify({'valid': False, 'message': '优惠码已达到使用次数限制'})
        
        # 检查最低消费金额
        if base_price < coupon['min_amount']:
            return jsonify({'valid': False, 'message': f'最低消费金额 ¥{coupon["min_amount"]}'})
        
        # 检查适用套餐
        if coupon['plans']:
            plans_list = coupon['plans'] if isinstance(coupon['plans'], list) else json.loads(coupon['plans'])
            if plan not in plans_list:
                return jsonify({'valid': False, 'message': '此优惠码不适用于当前套餐'})
        
        # 检查用户使用次数限制
        if coupon['user_limit'] > 1:
            cur = conn.cursor()
            cur.execute('''
                SELECT COUNT(*) FROM coupon_usage_logs
                WHERE coupon_id = %s AND user_email = %s
            ''', (coupon['id'], email))
            result = cur.fetchone()
            user_usage_count = result[0] if result else 0
            cur.close()
            
            if user_usage_count >= coupon['user_limit']:
                return jsonify({'valid': False, 'message': '您已达到此优惠码的使用次数限制'})
        
        # 计算折扣
        if coupon['type'] == 'fixed':
            discount = coupon['value']
        else:  # percentage
            discount = base_price * (coupon['value'] / 100)
        
        final_price = max(0, base_price - discount)
        
        return jsonify({
            'valid': True,
            'message': f'优惠码有效，减免 ¥{discount:.2f}',
            'discount': discount,
            'final_price': final_price,
            'coupon_id': coupon['id']
        })
        
    except Exception as e:
        logger.error(f"❌ 验证优惠码失败: {str(e)}")
        return jsonify({'valid': False, 'message': '验证优惠码失败'}), 500


@app.route('/api/admin/revoke', methods=['POST'])
@require_admin
def admin_revoke_license():
    """管理员撤销许可证"""
    try:
        data = request.get_json(force=True)
        license_id = data.get('license_id')
        reason = data.get('reason', 'no reason provided')
        
        if not license_id:
            return jsonify({'success': False, 'message': '缺少 license_id'}), 400
        
        ok = license_manager.revoke_license(license_id, reason)
        if not ok:
            return jsonify({'success': False, 'message': '撤销失败或许可证不存在'}), 400
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"❌ 撤销许可证失败: {str(e)}")
        return jsonify({'success': False, 'message': '撤销失败'}), 500


@app.route('/api/admin/orders', methods=['GET'])
@require_admin
def admin_get_orders():
    """获取支付订单列表"""
    try:
        conn = license_manager.get_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500
        
        cur = conn.cursor()
        cur.execute('''
            SELECT order_id, email, plan, amount, final_amount, status, created_at, paid_at
            FROM payment_orders
            ORDER BY created_at DESC
            LIMIT 100
        ''')
        rows = cur.fetchall()
        cur.close()
        
        orders = []
        for row in rows:
            orders.append({
                'order_id': row[0],
                'email': row[1],
                'plan': row[2],
                'amount': row[3],
                'final_amount': row[4],
                'status': row[5],
                'created_at': row[6].isoformat() if row[6] else None,
                'paid_at': row[7].isoformat() if row[7] else None
            })
        
        return jsonify({'success': True, 'orders': orders})
    except Exception as e:
        logger.error(f"❌ 获取订单列表失败: {str(e)}")
        return jsonify({'success': False, 'message': '获取订单列表失败'}), 500


@app.route('/api/admin/deactivate-device', methods=['POST'])
@require_admin
def admin_deactivate_device():
    """管理员停用设备"""
    try:
        data = request.get_json(force=True)
        license_id = data.get('license_id')
        device_id = data.get('device_id')
        
        if not license_id or not device_id:
            return jsonify({'success': False, 'message': '缺少 license_id 或 device_id'}), 400
        
        ok = license_manager.deactivate_device(license_id, device_id)
        if not ok:
            return jsonify({'success': False, 'message': '停用失败'}), 400
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"❌ 停用设备失败: {str(e)}")
        return jsonify({'success': False, 'message': '停用失败'}), 500


@app.route('/api/admin/activate-device', methods=['POST'])
@require_admin
def admin_activate_device():
    """管理员恢复设备"""
    try:
        data = request.get_json(force=True)
        license_id = data.get('license_id')
        device_id = data.get('device_id')
        
        if not license_id or not device_id:
            return jsonify({'success': False, 'message': '缺少 license_id 或 device_id'}), 400
        
        ok = license_manager.activate_device(license_id, device_id)
        if not ok:
            return jsonify({'success': False, 'message': '恢复失败'}), 400
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"❌ 恢复设备失败: {str(e)}")
        return jsonify({'success': False, 'message': '恢复失败'}), 500


@app.route('/api/admin/licenses', methods=['GET'])
@require_admin
def admin_list_licenses():
    """管理员查询许可证列表"""
    try:
        status = request.args.get('status', None)
        limit = min(max(int(request.args.get('limit', 100)), 1), 1000)
        
        licenses = license_manager.list_licenses(status, limit)
        
        return jsonify({'success': True, 'licenses': licenses})
    except Exception as e:
        logger.error(f"❌ 查询许可证失败: {str(e)}")
        return jsonify({'success': False, 'message': '查询失败'}), 500


@app.route('/api/admin/stats', methods=['GET'])
@require_admin
def admin_get_stats():
    """管理员获取统计信息"""
    try:
        stats = license_manager.get_license_statistics()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        logger.error(f"❌ 获取统计失败: {str(e)}")
        return jsonify({'success': False, 'message': '获取统计失败'}), 500


# ==================== ZPAY支付API ====================

@app.route('/api/payment/create', methods=['POST'])
def create_payment():
    """创建支付订单"""
    try:
        data = request.get_json()
        plan = data.get('plan')
        email = data.get('email')
        
        # 计算价格
        prices = {
            'monthly': 29,
            'yearly': 299,
            'lifetime': 999
        }
        
        if plan not in prices:
            return jsonify({'success': False, 'message': '无效的套餐类型'}), 400
        
        # 生成订单ID
        import time
        order_id = f"ORD{int(time.time())}"
        
        # 判断使用真实支付还是模拟支付
        if zpay_adapter:
            # 使用ZPAY真实支付
            result = zpay_adapter.create_order({
                'order_id': order_id,
                'amount': prices[plan],
                'product_name': f'License Manager - {plan}',
                'payment_type': 'alipay',
                'client_ip': request.remote_addr,
                'device': 'pc',
                'param': f'plan:{plan}|email:{email}'
            })
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'order_id': order_id,
                    'pay_url': result.get('pay_url', ''),
                    'qr_code': result.get('qr_code', ''),
                    'img': result.get('img', ''),
                    'payment_mode': 'zpay'
                })
            else:
                return jsonify({'success': False, 'message': result.get('message', '创建支付订单失败')}), 500
        else:
            # 模拟支付
            logger.info(f"使用模拟支付模式: {order_id}")
            return jsonify({
                'success': True,
                'order_id': order_id,
                'pay_url': '',
                'qr_code': '',
                'img': '',
                'payment_mode': 'mock'
            })
            
    except Exception as e:
        logger.error(f"❌ 创建支付订单失败: {str(e)}")
        return jsonify({'success': False, 'message': '创建支付订单失败'}), 500


@app.route('/api/payment/notify', methods=['POST', 'GET'])
def payment_notify():
    """ZPAY支付异步通知"""
    try:
        # 获取通知参数 - 支持POST和GET
        if request.method == 'POST':
            notify_data = request.form.to_dict()
        else:
            notify_data = request.args.to_dict()
        
        logger.info(f"收到ZPAY支付通知 ({request.method}): {notify_data}")
        
        # 如果没有配置ZPAY，直接返回成功
        if not zpay_adapter:
            logger.warning("ZPAY未配置，跳过支付通知处理")
            return 'success'
        
        # 验证通知
        result = zpay_adapter.handle_notify(notify_data)
        
        if not result['success']:
            logger.error(f"支付通知验证失败: {result.get('message')}")
            return 'fail'
        
        order_id = result['order_id']
        trade_no = result['trade_no']
        
        logger.info(f"ZPAY支付回调验证成功: 订单={order_id}")
        
        # 解析订单参数
        param = notify_data.get('param', '')
        param_parts = param.split('|')
        plan = None
        email = None
        
        for part in param_parts:
            if ':' in part:
                key, value = part.split(':', 1)
                if key == 'plan':
                    plan = value
                elif key == 'email':
                    email = value
        
        if not plan or not email:
            logger.error(f"无法解析订单参数: {param}")
            return 'fail'
        
        # 生成激活码
        days = 30 if plan == 'monthly' else 365 if plan == 'yearly' else None
        license_result = license_manager.generate_license(
            plan=plan,
            email=email,
            device_cap=5,
            days=days,
            user_hint=f"购买订单: {order_id}"
        )
        
        if 'error' in license_result:
            logger.error(f"许可证生成失败: {license_result['error']}")
            return 'fail'
        
        logger.info(f"ZPAY支付成功，许可证生成成功: {order_id}")
        
        # 更新订单状态
        conn = license_manager.get_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                UPDATE payment_orders
                SET status = 'paid', paid_at = %s, activation_code = %s, license_id = %s
                WHERE order_id = %s
            ''', (datetime.now(timezone.utc), license_result.get('activation_code'), license_result.get('license_id'), order_id))
            conn.commit()
            
            # 记录优惠码使用
            cur.execute('''
                SELECT coupon_id, coupon_code, amount, final_amount
                FROM payment_orders
                WHERE order_id = %s
            ''', (order_id,))
            order_data = cur.fetchone()
            if order_data and order_data[0]:  # coupon_id
                coupon_id, coupon_code, amount, final_amount = order_data
                cur.execute('''
                    INSERT INTO coupon_usage_logs (coupon_id, coupon_code, user_email, order_id, original_amount, discount_amount, final_amount)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (coupon_id, coupon_code, email, order_id, amount, amount - final_amount, final_amount))
                
                # 更新优惠码使用次数
                cur.execute('UPDATE coupons SET usage_count = usage_count + 1 WHERE id = %s', (coupon_id,))
                conn.commit()
            
            cur.close()
        
        # 发送激活码邮件
        if email_enabled and email:
            try:
                license_info = {
                    'activation_code': license_result.get('activation_code'),
                    'plan': plan,
                    'device_cap': 5,
                    'valid_until': license_result.get('valid_until')
                }
                if send_activation_email(email, license_info, EMAIL_CONFIG):
                    # 更新邮件发送状态
                    conn = license_manager.get_connection()
                    if conn:
                        cur = conn.cursor()
                        cur.execute('UPDATE payment_orders SET email_sent = 1 WHERE order_id = %s', (order_id,))
                        conn.commit()
                        cur.close()
                    logger.info(f"✅ 激活码邮件发送成功: {email}")
                else:
                    logger.warning(f"⚠️ 激活码邮件发送失败: {email}")
            except Exception as e:
                logger.error(f"❌ 发送邮件异常: {str(e)}")
        
        return 'success'
        
    except Exception as e:
        logger.error(f"处理支付通知失败: {str(e)}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return 'fail'


@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'API端点不存在', 'code': 'NOT_FOUND'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': '服务器内部错误', 'code': 'INTERNAL_ERROR'}), 500


if __name__ == '__main__':
    print("🚀 License Manager API 服务器启动中...")
    print(f"📊 数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    if API_KEY:
        print(f"🔑 API密钥: {API_KEY[:8]}...")
    else:
        print("⚠️ API密钥未设置")
    if zpay_adapter:
        print(f"💳 ZPAY支付系统: 已启用")
    else:
        print(f"💳 ZPAY支付系统: 未启用（使用模拟支付）")
    print("✅ 服务器已启动，监听端口 5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
