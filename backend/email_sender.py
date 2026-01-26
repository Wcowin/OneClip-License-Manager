#!/usr/bin/env python3
"""
邮件发送模块
支持多个邮件服务商：QQ邮箱、163邮箱、企业邮箱等
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# 邮件服务商配置
EMAIL_PROVIDERS = {
    'qq': {
        'name': 'QQ邮箱',
        'smtp_server': 'smtp.qq.com',
        'smtp_port': 587,
        'use_ssl': False,
        'from_email': None,  # 从环境变量读取
        'from_name': 'License Manager'
    },
    '163': {
        'name': '163邮箱',
        'smtp_server': 'smtp.163.com',
        'smtp_port': 465,
        'use_ssl': True,
        'from_email': None,
        'from_name': 'License Manager'
    },
    'exmail': {
        'name': '企业邮箱',
        'smtp_server': 'smtp.exmail.qq.com',
        'smtp_port': 465,
        'use_ssl': True,
        'from_email': None,
        'from_name': 'License Manager'
    }
}


class EmailSender:
    """邮件发送器"""
    
    def __init__(self, config: Dict[str, str]):
        """
        初始化邮件发送器
        
        Args:
            config: 邮件配置，包含 smtp_server, smtp_port, smtp_user, smtp_password, from_email, from_name
        """
        self.config = config
        self.smtp_server = config.get('smtp_server', 'smtp.qq.com')
        self.smtp_port = int(config.get('smtp_port', 587))
        self.smtp_user = config.get('smtp_user')
        self.smtp_password = config.get('smtp_password')
        self.from_email = config.get('from_email')
        self.from_name = config.get('from_name', 'License Manager')
        self.use_ssl = config.get('use_ssl', False)
    
    def send_activation_email(self, email: str, license_info: Dict[str, Any]) -> bool:
        """
        发送激活码邮件
        
        Args:
            email: 收件人邮箱
            license_info: 许可证信息，包含 activation_code, plan, device_cap, valid_until 等
        
        Returns:
            是否发送成功
        """
        try:
            # 构建邮件内容
            subject = f"🎉 您的 License Manager 激活码已生成"
            html_content = self._build_email_template(license_info)
            
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = email
            msg['Subject'] = subject
            
            # 添加HTML内容
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 发送邮件
            if self.use_ssl:
                # 使用SSL连接
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            else:
                # 使用TLS连接
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            
            logger.info(f"✅ 激活码邮件发送成功: {email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 发送激活码邮件失败: {str(e)}")
            return False
    
    def _build_email_template(self, license_info: Dict[str, Any]) -> str:
        """
        构建邮件模板
        
        Args:
            license_info: 许可证信息
        
        Returns:
            HTML邮件内容
        """
        activation_code = license_info.get('activation_code', '')
        plan = license_info.get('plan', '')
        device_cap = license_info.get('device_cap', 5)
        valid_until = license_info.get('valid_until', '永久')
        
        # 套餐名称映射
        plan_names = {
            'monthly': '月度版',
            'yearly': '年度版',
            'lifetime': '终身版'
        }
        plan_name = plan_names.get(plan, plan)
        
        html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>激活码邮件</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <!-- 头部 -->
                <div style="text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #e5e7eb;">
                    <h1 style="color: #1f2937; margin: 0; font-size: 24px;">🎉 激活码已生成</h1>
                    <p style="color: #6b7280; margin: 10px 0 0; font-size: 14px;">感谢您购买 License Manager</p>
                </div>
                
                <!-- 激活码 -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 8px; margin-bottom: 30px; text-align: center;">
                    <p style="color: #ffffff; margin: 0 0 15px; font-size: 14px; opacity: 0.9;">您的激活码</p>
                    <div style="background: rgba(255,255,255,0.2); padding: 20px; border-radius: 6px; backdrop-filter: blur(10px);">
                        <code style="color: #ffffff; font-size: 28px; font-weight: bold; letter-spacing: 2px; background: none;">{activation_code}</code>
                    </div>
                </div>
                
                <!-- 许可证信息 -->
                <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 30px;">
                    <h3 style="color: #1f2937; margin: 0 0 15px; font-size: 16px;">📋 许可证信息</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">套餐类型</td>
                            <td style="padding: 8px 0; color: #1f2937; font-size: 14px; font-weight: 500;">{plan_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">设备数量</td>
                            <td style="padding: 8px 0; color: #1f2937; font-size: 14px; font-weight: 500;">{device_cap} 台设备</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">有效期</td>
                            <td style="padding: 8px 0; color: #1f2937; font-size: 14px; font-weight: 500;">{valid_until}</td>
                        </tr>
                    </table>
                </div>
                
                <!-- 激活步骤 -->
                <div style="margin-bottom: 30px;">
                    <h3 style="color: #1f2937; margin: 0 0 15px; font-size: 16px;">💻 激活步骤</h3>
                    <ol style="color: #4b5563; margin: 0; padding-left: 20px; font-size: 14px; line-height: 1.8;">
                        <li>下载并安装应用</li>
                        <li>打开设置 → 高级功能</li>
                        <li>输入邮箱和激活码，点击激活</li>
                    </ol>
                </div>
                
                <!-- 提示 -->
                <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin-bottom: 30px; border-radius: 4px;">
                    <p style="color: #92400e; margin: 0; font-size: 13px;">💡 请妥善保管此邮件，建议标记为重要或收藏</p>
                </div>
                
                <!-- 客服支持 -->
                <div style="text-align: center; margin-bottom: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                    <p style="color: #6b7280; margin: 0; font-size: 14px;">📞 需要帮助？</p>
                    <a href="mailto:support@license-manager.com" style="color: #3b82f6; text-decoration: none; font-size: 14px;">support@license-manager.com</a>
                </div>
                
                <!-- 页脚 -->
                <div style="text-align: center; color: #9ca3af; font-size: 12px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                    <p style="margin: 0 0 5px;">此邮件由系统自动发送，请勿直接回复</p>
                    <p style="margin: 0;">© 2025 License Manager</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html


def send_activation_email(email: str, license_info: Dict[str, Any], config: Dict[str, str]) -> bool:
    """
    发送激活码邮件（便捷函数）
    
    Args:
        email: 收件人邮箱
        license_info: 许可证信息
        config: 邮件配置
    
    Returns:
        是否发送成功
    """
    sender = EmailSender(config)
    return sender.send_activation_email(email, license_info)
