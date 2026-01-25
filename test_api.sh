#!/bin/bash

# License Manager API 测试脚本
# 用于快速验证 API 是否正常工作

API_URL="http://localhost:5000"
API_KEY="test_api_key"

# 检查 jq 是否安装
if ! command -v jq &> /dev/null; then
    echo "⚠️  警告: jq 未安装，JSON 格式化将被跳过"
    JQ_AVAILABLE=false
else
    JQ_AVAILABLE=true
fi

format_json() {
    if [ "$JQ_AVAILABLE" = true ]; then
        jq .
    else
        cat
    fi
}

echo "==================================="
echo "License Manager API 测试"
echo "==================================="
echo ""

# 1. 健康检查
echo "1. 健康检查..."
curl -s "$API_URL/health" | format_json
echo ""

# 2. 生成激活码
echo "2. 生成激活码..."
GENERATE_RESPONSE=$(curl -s -X POST "$API_URL/api/admin/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "plan": "monthly",
    "email": "test@example.com",
    "device_cap": 5,
    "days": 30
  }')

echo "$GENERATE_RESPONSE" | format_json

# 提取激活码
if [ "$JQ_AVAILABLE" = true ]; then
    ACTIVATION_CODE=$(echo "$GENERATE_RESPONSE" | jq -r '.license.activation_code')
    EMAIL=$(echo "$GENERATE_RESPONSE" | jq -r '.license.email')
else
    echo ""
    echo "⚠️  无法解析激活码（需要 jq），跳过后续测试"
    echo "==================================="
    echo "测试完成！"
    echo "==================================="
    exit 0
fi

echo ""
echo "生成的激活码: $ACTIVATION_CODE"
echo ""

# 3. 验证激活码
echo "3. 验证激活码..."
curl -s -X POST "$API_URL/api/verify" \
  -H "Content-Type: application/json" \
  -d "{
    \"activation_code\": \"$ACTIVATION_CODE\",
    \"email\": \"$EMAIL\",
    \"device_id\": \"test-device-001\",
    \"device_name\": \"Test Device\",
    \"ip_address\": \"127.0.0.1\"
  }" | format_json
echo ""

# 4. 查询许可证列表
echo "4. 查询许可证列表..."
curl -s -X GET "$API_URL/api/admin/licenses?limit=5" \
  -H "X-API-Key: $API_KEY" | format_json
echo ""

# 5. 获取统计信息
echo "5. 获取统计信息..."
curl -s -X GET "$API_URL/api/admin/stats" \
  -H "X-API-Key: $API_KEY" | format_json
echo ""

echo "==================================="
echo "测试完成！"
echo "==================================="
