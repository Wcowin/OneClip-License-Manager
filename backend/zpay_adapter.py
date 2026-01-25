#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZPAY支付适配器
处理与ZPAY支付系统的集成
"""

import requests
import json
import hashlib
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class ZPayAdapter:
    """ZPAY支付适配器"""
    
    def __init__(self, config):
        self.pid = config['pid']
        self.key = config['key']
        self.api_url = config['api_url']
        self.notify_url = config.get('notify_url', '')
        self.return_url = config.get('return_url', '')
    
    def _generate_sign(self, params):
        """生成签名 - 按照ZPAY官方文档的签名算法"""
        # 移除空值、sign和sign_type参数
        filtered_params = {k: v for k, v in params.items() if v and k not in ['sign', 'sign_type']}
        
        # 按照参数名ASCII码从小到大排序（a-z）
        sorted_params = sorted(filtered_params.items())
        
        # 拼接成URL键值对格式，参数值不进行url编码
        sign_parts = []
        for k, v in sorted_params:
            sign_parts.append(f'{k}={v}')
        
        sign_str = '&'.join(sign_parts)
        sign_str += self.key  # 直接拼接KEY，不加&符号
        
        # MD5加密，结果为小写
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().lower()
        return sign
    
    def create_order(self, order_data):
        """创建支付订单"""
        try:
            # 构建请求参数
            params = {
                'pid': self.pid,
                'type': order_data.get('payment_type', 'alipay'),
                'out_trade_no': order_data['order_id'],
                'notify_url': self.notify_url,
                'return_url': self.return_url,
                'name': order_data.get('product_name', 'License Manager'),
                'money': str(order_data['amount']),
                'clientip': order_data.get('client_ip', '127.0.0.1'),
                'device': order_data.get('device', 'pc'),
                'param': order_data.get('param', ''),
                'sign_type': 'MD5'
            }
            
            # 生成签名
            params['sign'] = self._generate_sign(params)
            
            logger.info(f"创建ZPAY订单: {order_data['order_id']}, 金额: ¥{order_data['amount']}")
            
            # 发送请求 - 使用mapi.php接口
            response = requests.post(
                f"{self.api_url}mapi.php",
                data=params,
                timeout=30
            )
            
            logger.info(f"ZPAY响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"ZPAY JSON解析成功: {json.dumps(result, indent=2, ensure_ascii=False)}")
                except json.JSONDecodeError as e:
                    logger.error(f"ZPAY响应JSON解析失败: {str(e)}")
                    logger.error(f"原始响应内容: {response.text}")
                    
                    # 检查响应内容类型
                    if response.text.strip().startswith('<!DOCTYPE html>') or response.text.strip().startswith('<html>'):
                        # 如果返回的是HTML页面，说明订单创建成功，跳转到支付页面
                        logger.info("ZPAY返回支付页面HTML，订单创建成功")
                        return {
                            'success': True,
                            'pay_url': response.url,
                            'qr_code': '',
                            'img': '',
                            'trade_no': order_data['order_id'],
                            'message': '订单创建成功，跳转到支付页面'
                        }
                    else:
                        return {
                            'success': False,
                            'message': f'ZPAY响应格式错误: {str(e)}'
                        }
                
                if result.get('code') == 1:
                    logger.info(f"ZPAY订单创建成功: {order_data['order_id']}")
                    
                    return {
                        'success': True,
                        'pay_url': result.get('payurl', ''),
                        'qr_code': result.get('qrcode', ''),
                        'img': result.get('img', ''),
                        'trade_no': result.get('trade_no', ''),
                        'message': '订单创建成功'
                    }
                else:
                    logger.error(f"ZPAY订单创建失败: {result.get('msg', '未知错误')}")
                    return {
                        'success': False,
                        'message': result.get('msg', '订单创建失败')
                    }
            else:
                logger.error(f"ZPAY请求失败: HTTP {response.status_code}")
                return {
                    'success': False,
                    'message': f'请求失败: HTTP {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"ZPAY订单创建异常: {str(e)}")
            return {
                'success': False,
                'message': f'订单创建异常: {str(e)}'
            }
    
    def query_order(self, order_id):
        """查询订单状态"""
        try:
            # 按照文档：https://zpayz.cn/api.php?act=order&pid={商户ID}&key={商户密钥}&out_trade_no={商户订单号}
            params = {
                'act': 'order',
                'pid': self.pid,
                'key': self.key,
                'out_trade_no': order_id
            }
            
            response = requests.get(
                f"{self.api_url}api.php",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('code') == 1:
                    return {
                        'success': True,
                        'status': result.get('status', 'unknown'),
                        'trade_no': result.get('trade_no', ''),
                        'money': result.get('money', 0),
                        'message': '查询成功'
                    }
                else:
                    return {
                        'success': False,
                        'message': result.get('msg', '查询失败')
                    }
            else:
                return {
                    'success': False,
                    'message': f'查询请求失败: HTTP {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"ZPAY订单查询异常: {str(e)}")
            return {
                'success': False,
                'message': f'查询异常: {str(e)}'
            }
    
    def handle_notify(self, notify_data):
        """处理ZPAY支付回调通知"""
        try:
            logger.info(f"处理ZPAY支付回调: {notify_data}")
            
            # 验证必要参数
            required_fields = ['pid', 'out_trade_no', 'trade_no', 'trade_status', 'sign']
            for field in required_fields:
                if field not in notify_data:
                    logger.error(f"缺少必要参数: {field}")
                    return {
                        'success': False,
                        'message': f'缺少必要参数: {field}'
                    }
            
            # 验证商户ID
            if notify_data.get('pid') != self.pid:
                logger.error(f"商户ID不匹配: {notify_data.get('pid')} != {self.pid}")
                return {
                    'success': False,
                    'message': '商户ID不匹配'
                }
            
            # 验证支付状态
            if notify_data.get('trade_status') != 'TRADE_SUCCESS':
                logger.warning(f"支付状态不是成功: {notify_data.get('trade_status')}")
                return {
                    'success': False,
                    'message': f'支付状态不是成功: {notify_data.get("trade_status")}'
                }
            
            # 验证签名
            received_sign = notify_data.get('sign', '')
            calculated_sign = self._generate_sign(notify_data)
            
            if received_sign != calculated_sign:
                logger.error(f"签名验证失败: 接收={received_sign}, 计算={calculated_sign}")
                return {
                    'success': False,
                    'message': '签名验证失败'
                }
            
            logger.info(f"ZPAY支付回调验证成功: 订单={notify_data.get('out_trade_no')}")
            
            return {
                'success': True,
                'order_id': notify_data.get('out_trade_no'),
                'trade_no': notify_data.get('trade_no'),
                'money': notify_data.get('money'),
                'name': notify_data.get('name'),
                'type': notify_data.get('type'),
                'param': notify_data.get('param', ''),
                'message': '支付回调验证成功'
            }
            
        except Exception as e:
            logger.error(f"处理ZPAY支付回调异常: {str(e)}")
            return {
                'success': False,
                'message': f'处理回调异常: {str(e)}'
            }
