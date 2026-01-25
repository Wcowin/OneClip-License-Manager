#!/usr/bin/env python3
"""
许可证管理器 - 核心逻辑
支持激活码生成、验证和设备管理
"""

import hashlib
import uuid
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
import mysql.connector
from mysql.connector import Error

# 字符集：去掉容易混淆的字符 (0,O,1,I,L)
CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CHARSET_LENGTH = len(CHARSET)


class LicenseManager:
    """许可证管理器"""
    
    def __init__(self, db_config: Dict[str, Any]):
        """初始化许可证管理器
        
        Args:
            db_config: 数据库配置字典
                - host: 数据库主机
                - port: 数据库端口
                - user: 数据库用户名
                - password: 数据库密码
                - database: 数据库名称
        """
        self.db_config = db_config
        self.test_connection()
    
    def test_connection(self):
        """测试数据库连接"""
        try:
            conn = self.get_connection()
            conn.close()
            print("✅ 数据库连接成功")
        except Error as e:
            print(f"❌ 数据库连接失败: {e}")
            raise e
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            return mysql.connector.connect(**self.db_config)
        except Error as e:
            print(f"❌ 数据库连接失败: {e}")
            raise e
    
    def generate_short_id(self) -> str:
        """生成短ID (11位)
        
        Returns:
            11位短ID字符串
        """
        timestamp = int(time.time() * 1000) % (36 ** 6)  # 6位时间戳
        random_part = uuid.uuid4().int % (36 ** 5)  # 5位随机数
        
        combined = timestamp * (36 ** 5) + random_part
        
        result = ""
        for _ in range(11):
            result = CHARSET[combined % CHARSET_LENGTH] + result
            combined //= CHARSET_LENGTH
        
        return result
    
    def calculate_checksum(self, short_id: str) -> str:
        """计算校验码
        
        Args:
            short_id: 11位短ID
            
        Returns:
            4位校验码
        """
        if len(short_id) != 11:
            return ""
        
        # 使用SHA256计算校验码
        hash_obj = hashlib.sha256(short_id.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        
        # 取前4位作为校验码
        checksum = ""
        for i in range(4):
            start_index = i * 2
            end_index = start_index + 2
            hex_byte = hash_hex[start_index:end_index]
            
            int_value = int(hex_byte, 16)
            char_index = int_value % CHARSET_LENGTH
            checksum += CHARSET[char_index]
        
        return checksum
    
    def generate_activation_code(self) -> str:
        """生成激活码
        
        Returns:
            格式为 XXXXX-XXXXX-XXXXX 的激活码
        """
        short_id = self.generate_short_id()
        checksum = self.calculate_checksum(short_id)
        
        # 格式化为 XXXXX-XXXXX-XXXXX
        activation_code = f"{short_id[:5]}-{short_id[5:10]}-{short_id[10:11]}{checksum}"
        return activation_code
    
    def generate_license(self, plan: str, email: str, device_cap: int = 5, 
                       days: Optional[int] = None, user_hint: Optional[str] = None) -> Dict[str, Any]:
        """生成许可证
        
        Args:
            plan: 套餐类型 (monthly/yearly/lifetime)
            email: 绑定邮箱
            device_cap: 设备数量限制
            days: 有效期天数（终身版不需要）
            user_hint: 用户备注
            
        Returns:
            包含许可证信息的字典
        """
        try:
            # 验证邮箱格式
            if not self.is_valid_email(email):
                return {"error": "邮箱格式无效"}
            
            # 规范化套餐类型
            normalized_plan = (plan or '').strip().lower()
            if normalized_plan not in ('monthly', 'yearly', 'lifetime'):
                return {"error": "未知的套餐类型"}
            
            # 按套餐给默认时长
            if days is not None:
                try:
                    days = int(days)
                except Exception:
                    days = None
            
            if normalized_plan == 'monthly' and not days:
                days = 30
            if normalized_plan == 'yearly' and not days:
                days = 365
            
            # 生成激活码
            activation_code = self.generate_activation_code()
            license_id = f"LIC-{uuid.uuid4().hex[:8].upper()}"
            
            # 计算过期时间
            valid_until = None
            if days and normalized_plan != 'lifetime':
                valid_until = datetime.now(timezone.utc) + timedelta(days=days)
            
            # 保存到数据库
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO licenses (license_id, activation_code, email, plan, device_limit, 
                                    issued_at, valid_until, user_hint, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (license_id, activation_code, email, normalized_plan, device_cap, 
                  datetime.now(timezone.utc), valid_until, user_hint, 'active'))
            
            conn.commit()
            cursor.close()
            
            return {
                "license_id": license_id,
                "activation_code": activation_code,
                "email": email,
                "plan": normalized_plan,
                "device_cap": device_cap,
                "valid_until": valid_until.isoformat() if valid_until else None
            }
            
        except Error as e:
            return {"error": f"数据库操作失败: {str(e)}"}
        except Exception as e:
            return {"error": f"生成失败: {str(e)}"}
    
    def verify_license(self, activation_code: str, email: str, device_id: Optional[str] = None, 
                     device_name: Optional[str] = None, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """验证许可证
        
        Args:
            activation_code: 激活码
            email: 邮箱
            device_id: 设备ID
            device_name: 设备名称
            ip_address: IP地址
            
        Returns:
            验证结果字典
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 查询许可证信息
            cursor.execute('''
                SELECT license_id, plan, device_limit, issued_at, valid_until, 
                       user_hint, status, email
                FROM licenses
                WHERE activation_code = %s AND status = 'active'
            ''', (activation_code,))
            
            result = cursor.fetchone()
            if not result:
                return {"valid": False, "error": "激活码不存在或已停用"}
            
            # 验证邮箱匹配
            if result['email'].lower() != email.lower():
                return {"valid": False, "error": "邮箱与激活码不匹配"}
            
            # 检查有效期
            if result['valid_until']:
                now_utc = datetime.now(timezone.utc)
                valid_until = result['valid_until']
                
                if valid_until.tzinfo is None:
                    valid_until = valid_until.replace(tzinfo=timezone.utc)
                
                if now_utc > valid_until:
                    return {"valid": False, "error": "激活码已过期"}
            
            # 处理设备激活
            if device_id:
                # 检查设备是否已存在
                cursor.execute('''
                    SELECT is_active FROM device_activations 
                    WHERE license_id = %s AND device_id = %s
                ''', (result['license_id'], device_id))
                
                existing_device = cursor.fetchone()
                
                if existing_device:
                    if existing_device['is_active'] == 1:
                        # 设备已激活，更新最后活跃时间
                        cursor.execute('''
                            UPDATE device_activations 
                            SET last_seen_at = %s, device_name = %s, ip_address = %s
                            WHERE license_id = %s AND device_id = %s
                        ''', (datetime.now(timezone.utc), device_name, ip_address, 
                              result['license_id'], device_id))
                        
                        conn.commit()
                        cursor.close()
                        
                        return {
                            "valid": True,
                            "license_id": result['license_id'],
                            "plan": result['plan'],
                            "device_cap": result['device_limit'],
                            "issued_at": result['issued_at'].isoformat() if result['issued_at'] else None,
                            "valid_until": result['valid_until'].isoformat() if result['valid_until'] else None,
                            "user_hint": result['user_hint'],
                            "message": "设备已激活"
                        }
                    else:
                        return {"valid": False, "error": "设备已被停用"}
                else:
                    # 新设备，检查槽位是否可用
                    cursor.execute('''
                        SELECT COUNT(*) as count FROM device_activations 
                        WHERE license_id = %s AND is_active = 1
                    ''', (result['license_id'],))
                    current_devices = cursor.fetchone()['count']
                    
                    if current_devices >= result['device_limit']:
                        return {"valid": False, "error": f"设备数量已达上限({result['device_limit']}台)"}
                    
                    # 激活新设备
                    cursor.execute('''
                        INSERT INTO device_activations 
                        (license_id, device_id, device_name, ip_address, last_seen_at, is_active) 
                        VALUES (%s, %s, %s, %s, %s, 1)
                    ''', (result['license_id'], device_id, device_name, ip_address, datetime.now(timezone.utc)))
                    
                    conn.commit()
                    cursor.close()
            
            cursor.close()
            
            return {
                "valid": True,
                "license_id": result['license_id'],
                "plan": result['plan'],
                "device_cap": result['device_limit'],
                "issued_at": result['issued_at'].isoformat() if result['issued_at'] else None,
                "valid_until": result['valid_until'].isoformat() if result['valid_until'] else None,
                "user_hint": result['user_hint']
            }
            
        except Error as e:
            return {"valid": False, "error": f"数据库操作失败: {str(e)}"}
        except Exception as e:
            return {"valid": False, "error": f"验证失败: {str(e)}"}
    
    def revoke_license(self, license_id: str, reason: str) -> bool:
        """撤销许可证
        
        Args:
            license_id: 许可证ID
            reason: 撤销原因
            
        Returns:
            是否成功
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT 1 FROM licenses WHERE license_id = %s', (license_id,))
            if not cursor.fetchone():
                return False
            
            cursor.execute('UPDATE licenses SET status = "revoked" WHERE license_id = %s', (license_id,))
            
            conn.commit()
            cursor.close()
            
            return True
            
        except Error as e:
            print(f"❌ 撤销许可证失败: {e}")
            return False
    
    def deactivate_device(self, license_id: str, device_id: str) -> bool:
        """停用设备
        
        Args:
            license_id: 许可证ID
            device_id: 设备ID
            
        Returns:
            是否成功
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE device_activations 
                SET is_active = 0 
                WHERE license_id = %s AND device_id = %s
            ''', (license_id, device_id))
            
            conn.commit()
            cursor.close()
            
            return True
            
        except Error as e:
            print(f"❌ 停用设备失败: {e}")
            return False
    
    def activate_device(self, license_id: str, device_id: str) -> bool:
        """恢复设备
        
        Args:
            license_id: 许可证ID
            device_id: 设备ID
            
        Returns:
            是否成功
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE device_activations 
                SET is_active = 1 
                WHERE license_id = %s AND device_id = %s
            ''', (license_id, device_id))
            
            conn.commit()
            cursor.close()
            
            return True
            
        except Error as e:
            print(f"❌ 恢复设备失败: {e}")
            return False
    
    def list_licenses(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """列出许可证
        
        Args:
            status: 状态筛选 (active/revoked)
            limit: 返回数量限制
            
        Returns:
            许可证列表
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = '''
                SELECT l.*, 
                       COUNT(da.device_id) as active_devices
                FROM licenses l
                LEFT JOIN device_activations da ON l.license_id = da.license_id AND da.is_active = 1
            '''
            
            params = []
            if status:
                query += ' WHERE l.status = %s'
                params.append(status)
            
            query += ' GROUP BY l.license_id ORDER BY l.issued_at DESC LIMIT %s'
            params.append(limit)
            
            cursor.execute(query, params)
            licenses = cursor.fetchall()
            cursor.close()
            
            return licenses
            
        except Error as e:
            return [{"error": f"查询失败: {str(e)}"}]
    
    def get_license_statistics(self) -> Dict[str, Any]:
        """获取许可证统计信息
        
        Returns:
            统计信息字典
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 总许可证数
            cursor.execute('SELECT COUNT(*) as count FROM licenses')
            total_licenses = cursor.fetchone()['count']
            
            # 活跃许可证数
            cursor.execute('SELECT COUNT(*) as count FROM licenses WHERE status = "active"')
            active_licenses = cursor.fetchone()['count']
            
            # 按类型统计
            cursor.execute('''
                SELECT plan, COUNT(*) as count FROM licenses 
                WHERE status = "active" GROUP BY plan
            ''')
            plan_stats = {row['plan']: row['count'] for row in cursor.fetchall()}
            
            # 设备激活统计
            cursor.execute('SELECT COUNT(*) as count FROM device_activations WHERE is_active = 1')
            active_devices = cursor.fetchone()['count']
            
            return {
                "total_licenses": total_licenses,
                "active_licenses": active_licenses,
                "plan_statistics": plan_stats,
                "active_devices": active_devices
            }
            
        except Error as e:
            return {"error": f"获取统计失败: {str(e)}"}
    
    def is_valid_email(self, email: str) -> bool:
        """验证邮箱格式
        
        Args:
            email: 邮箱地址
            
        Returns:
            是否有效
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
