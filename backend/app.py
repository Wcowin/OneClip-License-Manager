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
    'password': os.getenv('DB_PASSWORD', 'license_password'),
    'database': os.getenv('DB_NAME', 'license_db'),
    'charset': 'utf8mb4'
}

# 安全检查
if not DB_CONFIG['password']:
    raise ValueError("❌ DB_PASSWORD 环境变量未设置！请先设置: export DB_PASSWORD='your_password'")

# API密钥配置（可选，用于客户端验证）
API_KEY = os.getenv('API_KEY')

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
        license_result = license_manager.create_license(
            activation_code=None,  # 自动生成
            email=email,
            plan=plan,
            device_cap=5,
            days=days,
            user_hint=f"购买订单: {order_id}"
        )
        
        if 'error' in license_result:
            logger.error(f"许可证生成失败: {license_result['error']}")
            return 'fail'
        
        logger.info(f"ZPAY支付成功，许可证生成成功: {order_id}")
        return 'success'
        
    except Exception as e:
        logger.error(f"处理支付通知失败: {str(e)}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return 'fail'


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()})


@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'API端点不存在', 'code': 'NOT_FOUND'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': '服务器内部错误', 'code': 'INTERNAL_ERROR'}), 500


if __name__ == '__main__':
    print("🚀 License Manager API 服务器启动中...")
    print(f"📊 数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print(f"🔑 API密钥: {API_KEY[:8]}...")
    if zpay_adapter:
        print(f"💳 ZPAY支付系统: 已启用")
    else:
        print(f"💳 ZPAY支付系统: 未启用（使用模拟支付）")
    print("✅ 服务器已启动，监听端口 5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
