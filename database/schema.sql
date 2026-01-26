-- License Manager 数据库结构
-- 版本: 1.0.0
-- 创建日期: 2025-01-25
-- 注意：此脚本由 Docker 自动执行，数据库已预先创建，无需 CREATE DATABASE

-- 许可证表
CREATE TABLE IF NOT EXISTS licenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    license_id VARCHAR(32) NOT NULL UNIQUE COMMENT '许可证ID',
    activation_code VARCHAR(16) NOT NULL UNIQUE COMMENT '激活码',
    email VARCHAR(255) NOT NULL COMMENT '绑定邮箱',
    plan VARCHAR(20) NOT NULL COMMENT '套餐类型: monthly/yearly/lifetime',
    device_limit INT NOT NULL DEFAULT 5 COMMENT '设备数量限制',
    issued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '签发时间',
    valid_until TIMESTAMP NULL COMMENT '过期时间（终身版为NULL）',
    user_hint TEXT COMMENT '用户备注',
    status VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '状态: active/revoked',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_activation_code (activation_code),
    INDEX idx_email (email),
    INDEX idx_status (status),
    INDEX idx_plan (plan),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='许可证表';

-- 设备激活表
CREATE TABLE IF NOT EXISTS device_activations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    license_id VARCHAR(32) NOT NULL COMMENT '许可证ID',
    device_id VARCHAR(255) NOT NULL COMMENT '设备ID',
    device_name VARCHAR(255) COMMENT '设备名称',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    last_seen_at TIMESTAMP NULL COMMENT '最后活跃时间',
    is_active TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否激活: 1=激活, 0=停用',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_device (license_id, device_id),
    INDEX idx_license_id (license_id),
    INDEX idx_device_id (device_id),
    INDEX idx_is_active (is_active),
    FOREIGN KEY (license_id) REFERENCES licenses(license_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='设备激活表';

-- 激活历史表
CREATE TABLE IF NOT EXISTS activation_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    license_id VARCHAR(32) NOT NULL COMMENT '许可证ID',
    action VARCHAR(20) NOT NULL COMMENT '操作类型: activate/deactivate/heartbeat/revoke',
    device_id VARCHAR(255) COMMENT '设备ID',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    details TEXT COMMENT '详细信息（JSON格式）',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_license_id (license_id),
    INDEX idx_action (action),
    INDEX idx_device_id (device_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (license_id) REFERENCES licenses(license_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='激活历史表';

-- 管理员操作日志表
CREATE TABLE IF NOT EXISTS admin_operation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    operation VARCHAR(100) NOT NULL COMMENT '操作类型',
    details TEXT COMMENT '操作详情（JSON格式）',
    admin_ip VARCHAR(45) COMMENT '管理员IP',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_operation (operation),
    INDEX idx_admin_ip (admin_ip),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='管理员操作日志表';

-- 优惠码表
CREATE TABLE IF NOT EXISTS coupons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL COMMENT '优惠码',
    name VARCHAR(100) NOT NULL COMMENT '优惠码名称',
    type ENUM('fixed', 'percentage') NOT NULL DEFAULT 'fixed' COMMENT '折扣类型',
    value DECIMAL(10,2) NOT NULL COMMENT '折扣值',
    min_amount DECIMAL(10,2) DEFAULT 0.00 COMMENT '最低消费金额',
    plans JSON COMMENT '适用套餐',
    usage_limit INT DEFAULT 0 COMMENT '使用次数限制（0=无限制）',
    user_limit INT DEFAULT 0 COMMENT '每用户使用次数限制（0=无限制）',
    start_date TIMESTAMP NULL COMMENT '开始时间',
    end_date TIMESTAMP NULL COMMENT '结束时间',
    is_active TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否激活',
    usage_count INT DEFAULT 0 COMMENT '已使用次数',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_code (code),
    INDEX idx_is_active (is_active),
    INDEX idx_dates (start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='优惠码表';

-- 优惠码使用记录表
CREATE TABLE IF NOT EXISTS coupon_usage_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    coupon_id INT NOT NULL COMMENT '优惠码ID',
    coupon_code VARCHAR(50) NOT NULL COMMENT '优惠码',
    user_email VARCHAR(255) NOT NULL COMMENT '用户邮箱',
    order_id VARCHAR(100) NOT NULL COMMENT '订单ID',
    original_amount DECIMAL(10,2) NOT NULL COMMENT '原始金额',
    discount_amount DECIMAL(10,2) NOT NULL COMMENT '优惠金额',
    final_amount DECIMAL(10,2) NOT NULL COMMENT '最终金额',
    used_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '使用时间',
    FOREIGN KEY (coupon_id) REFERENCES coupons(id) ON DELETE CASCADE,
    INDEX idx_coupon_id (coupon_id),
    INDEX idx_user_email (user_email),
    INDEX idx_order_id (order_id),
    INDEX idx_used_at (used_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='优惠码使用记录表';

-- 支付订单表
CREATE TABLE IF NOT EXISTS payment_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE NOT NULL COMMENT '订单ID',
    email VARCHAR(255) NOT NULL COMMENT '邮箱',
    plan VARCHAR(50) NOT NULL COMMENT '套餐类型',
    device_cap INT DEFAULT 5 COMMENT '设备数量',
    days INT DEFAULT NULL COMMENT '有效期天数',
    amount DECIMAL(10,2) NOT NULL COMMENT '订单金额',
    final_amount DECIMAL(10,2) NOT NULL COMMENT '最终金额',
    coupon_code VARCHAR(100) DEFAULT NULL COMMENT '优惠码',
    coupon_id INT DEFAULT NULL COMMENT '优惠码ID',
    discount_amount DECIMAL(10,2) DEFAULT 0 COMMENT '优惠金额',
    status ENUM('pending', 'paid', 'failed', 'cancelled') DEFAULT 'pending' COMMENT '订单状态',
    trade_no VARCHAR(100) DEFAULT NULL COMMENT '交易号',
    activation_code VARCHAR(16) DEFAULT NULL COMMENT '激活码',
    license_id VARCHAR(32) DEFAULT NULL COMMENT '许可证ID',
    email_sent TINYINT(1) DEFAULT 0 COMMENT '邮件是否发送',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP NULL COMMENT '支付时间',
    INDEX idx_order_id (order_id),
    INDEX idx_email (email),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_license_id (license_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付订单表';

-- 插入测试数据（可选）
-- INSERT INTO licenses (license_id, activation_code, email, plan, device_limit, valid_until, user_hint)
-- VALUES ('LIC-TEST0001', 'ABCDE-FGHIJ-KLMN', 'test@example.com', 'monthly', 5, DATE_ADD(NOW(), INTERVAL 30 DAY), '测试许可证');
