"""专门测试 /api/extract 接口响应格式的测试模块"""

import pytest
import json
from datetime import datetime
from typing import Dict, Any
from jsonschema import validate, ValidationError


class TestResponseFormat:
    """测试响应格式的类"""
    
    # 定义成功响应的 JSON Schema
    SUCCESS_RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "success": {
                "type": "boolean",
                "const": True
            },
            "script": {
                "type": "string",
                "minLength": 1
            },
            "cached": {
                "type": "boolean"
            },
            "extracted_at": {
                "type": "string",
                "format": "date-time"
            }
        },
        "required": ["success", "script", "cached", "extracted_at"],
        "additionalProperties": False
    }
    
    # 定义错误响应的 JSON Schema
    ERROR_RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "success": {
                "type": "boolean",
                "const": False
            },
            "error": {
                "type": "string",
                "minLength": 1
            },
            "extracted_at": {
                "type": "string",
                "format": "date-time"
            }
        },
        "required": ["success", "error", "extracted_at"],
        "additionalProperties": False
    }
    
    # 定义 JSON-LD 内容的 Schema
    JSON_LD_SCHEMA = {
        "type": "object",
        "properties": {
            "@context": {
                "type": "string",
                "const": "https://schema.org"
            },
            "@type": {
                "type": "string",
                "const": "LocalBusiness"
            },
            "name": {
                "type": "string",
                "minLength": 1
            },
            "address": {
                "type": "object",
                "properties": {
                    "@type": {
                        "type": "string",
                        "const": "PostalAddress"
                    }
                },
                "required": ["@type"]
            }
        },
        "required": ["@context", "@type", "name"],
        "additionalProperties": True
    }
    
    def validate_success_response(self, response_data: Dict[str, Any]) -> None:
        """验证成功响应格式"""
        try:
            validate(instance=response_data, schema=self.SUCCESS_RESPONSE_SCHEMA)
        except ValidationError as e:
            pytest.fail(f"成功响应格式验证失败: {e.message}")
    
    def validate_error_response(self, response_data: Dict[str, Any]) -> None:
        """验证错误响应格式"""
        try:
            validate(instance=response_data, schema=self.ERROR_RESPONSE_SCHEMA)
        except ValidationError as e:
            pytest.fail(f"错误响应格式验证失败: {e.message}")
    
    def validate_json_ld_content(self, script_content: str) -> None:
        """验证 JSON-LD script 内容格式"""
        # 提取 script 标签中的 JSON 内容
        if not script_content.startswith('<script type="application/ld+json">'):
            pytest.fail("Script 标签格式错误：缺少正确的开始标签")
        
        if not script_content.endswith('</script>'):
            pytest.fail("Script 标签格式错误：缺少正确的结束标签")
        
        # 提取 JSON 内容
        json_start = script_content.find('>\n') + 2
        json_end = script_content.rfind('\n<')
        
        if json_start >= json_end:
            pytest.fail("无法从 script 标签中提取 JSON 内容")
        
        json_content = script_content[json_start:json_end]
        
        # 验证 JSON 格式
        try:
            parsed_json = json.loads(json_content)
        except json.JSONDecodeError as e:
            pytest.fail(f"JSON-LD 内容格式无效: {e}")
        
        # 验证 JSON-LD 结构
        try:
            validate(instance=parsed_json, schema=self.JSON_LD_SCHEMA)
        except ValidationError as e:
            pytest.fail(f"JSON-LD 结构验证失败: {e.message}")
    
    def validate_timestamp_format(self, timestamp: str) -> None:
        """验证时间戳格式"""
        try:
            # 尝试解析 ISO 格式时间戳
            parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # 验证时间戳是否合理（不能是未来时间，不能太久以前）
            now = datetime.now()
            time_diff = abs((now - parsed_time.replace(tzinfo=None)).total_seconds())
            
            if time_diff > 3600:  # 不能超过1小时前
                pytest.fail(f"时间戳不合理：{timestamp}，与当前时间相差 {time_diff} 秒")
                
        except ValueError as e:
            pytest.fail(f"时间戳格式无效: {timestamp}, 错误: {e}")
    
    def test_success_response_structure(self, client, mock_crawler, mock_cache, 
                                      mock_schema_generator, sample_business_data,
                                      valid_google_business_url):
        """测试成功响应的结构"""
        # 设置 mock
        mock_crawler.extract_business_info.return_value = sample_business_data
        mock_cache.get.return_value = None
        
        response = client.post(
            "/api/extract",
            json={"url": valid_google_business_url}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 使用 JSON Schema 验证响应格式
        self.validate_success_response(data)
        
        # 验证时间戳格式
        self.validate_timestamp_format(data["extracted_at"])
        
        # 验证 JSON-LD script 内容
        self.validate_json_ld_content(data["script"])
    
    def test_cached_response_structure(self, client, mock_cache, sample_business_data,
                                     valid_google_business_url):
        """测试缓存响应的结构"""
        from app.models import LocalBusinessSchema, PostalAddress
        
        # 创建缓存的 schema
        cached_schema = LocalBusinessSchema(
            name=sample_business_data['name'],
            address=PostalAddress(street_address='测试地址')
        )
        
        mock_cache.get.return_value = cached_schema
        
        response = client.post(
            "/api/extract",
            json={"url": valid_google_business_url}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证缓存响应格式
        self.validate_success_response(data)
        assert data["cached"] is True
        
        # 验证时间戳和 JSON-LD 内容
        self.validate_timestamp_format(data["extracted_at"])
        self.validate_json_ld_content(data["script"])
    
    def test_error_response_structure(self, client, mock_crawler, mock_cache,
                                    valid_google_business_url):
        """测试错误响应的结构"""
        # 设置 mock 抛出异常
        mock_crawler.extract_business_info.side_effect = Exception("测试错误消息")
        mock_cache.get.return_value = None
        
        response = client.post(
            "/api/extract",
            json={"url": valid_google_business_url}
        )
        
        assert response.status_code == 200  # API 返回 200 但包含错误信息
        data = response.json()
        
        # 使用 JSON Schema 验证错误响应格式
        self.validate_error_response(data)
        
        # 验证错误消息
        assert data["error"] == "测试错误消息"
        
        # 验证时间戳格式
        self.validate_timestamp_format(data["extracted_at"])
    
    def test_validation_error_response(self, client, invalid_url):
        """测试输入验证错误的响应格式"""
        response = client.post(
            "/api/extract",
            json={"url": invalid_url}
        )
        
        assert response.status_code == 400
        data = response.json()
        
        # 验证 HTTP 错误响应格式
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0
    
    def test_missing_url_validation(self, client):
        """测试缺少 URL 参数的验证"""
        response = client.post(
            "/api/extract",
            json={}
        )
        
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        
        # 验证 Pydantic 验证错误格式
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert len(data["detail"]) > 0
        
        # 检查错误详情
        error = data["detail"][0]
        assert "field_required" in error["type"] or "missing" in error["type"]
        assert "url" in str(error["loc"])
    
    def test_description_length_validation(self, client, valid_google_business_url):
        """测试描述长度验证"""
        long_description = "a" * 501  # 超过 500 字符限制
        
        response = client.post(
            "/api/extract",
            json={
                "url": valid_google_business_url,
                "description": long_description
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # 验证验证错误格式
        assert "detail" in data
        assert isinstance(data["detail"], list)
        
        # 检查是否包含描述长度错误
        error_messages = [str(error) for error in data["detail"]]
        assert any("500" in msg for msg in error_messages)
    
    def test_response_content_types(self, client, mock_crawler, mock_cache,
                                  mock_schema_generator, sample_business_data,
                                  valid_google_business_url):
        """测试响应内容的数据类型"""
        mock_crawler.extract_business_info.return_value = sample_business_data
        mock_cache.get.return_value = None
        
        response = client.post(
            "/api/extract",
            json={"url": valid_google_business_url}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 详细检查每个字段的类型
        assert isinstance(data["success"], bool), "success 字段必须是布尔类型"
        assert isinstance(data["script"], str), "script 字段必须是字符串类型"
        assert isinstance(data["cached"], bool), "cached 字段必须是布尔类型"
        assert isinstance(data["extracted_at"], str), "extracted_at 字段必须是字符串类型"
        
        # 检查字符串字段不为空
        assert len(data["script"]) > 0, "script 字段不能为空"
        assert len(data["extracted_at"]) > 0, "extracted_at 字段不能为空"
    
    def test_json_ld_script_encoding(self, client, mock_crawler, mock_cache,
                                   mock_schema_generator, valid_google_business_url):
        """测试 JSON-LD script 的编码处理"""
        # 包含中文字符的商家数据
        chinese_business_data = {
            'name': '北京烤鸭店',
            'address': '北京市东城区王府井大街123号',
            'business_type': '中餐厅'
        }
        
        mock_crawler.extract_business_info.return_value = chinese_business_data
        mock_cache.get.return_value = None
        
        response = client.post(
            "/api/extract",
            json={"url": valid_google_business_url}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证中文字符在 JSON-LD 中正确编码
        script_content = data["script"]
        assert "北京烤鸭店" in script_content or "\\u" in script_content
        
        # 验证 JSON 可以正确解析
        self.validate_json_ld_content(script_content)