"""测试 /api/extract 接口的输出格式"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.models import LocalBusinessSchema, PostalAddress, AggregateRating


class TestExtractAPI:
    """测试 /api/extract 接口"""
    
    def setup_method(self):
        """设置测试客户端"""
        self.client = TestClient(app)
        
    def test_extract_success_response_format(self):
        """测试成功响应的格式"""
        # Mock 商家数据
        mock_business_data = {
            'name': '测试餐厅',
            'address': '北京市朝阳区测试街道123号',
            'phone': '+86-10-12345678',
            'rating': 4.5,
            'review_count': 100,
            'website': 'https://test-restaurant.com',
            'business_type': '餐厅',
            'price_range': '$$',
            'opening_hours': {
                'Monday': '09:00-22:00',
                'Tuesday': '09:00-22:00'
            },
            'images': ['https://example.com/image1.jpg']
        }
        
        # Mock schema
        mock_schema = LocalBusinessSchema(
            name='测试餐厅',
            address=PostalAddress(
                street_address='测试街道123号',
                address_locality='朝阳区',
                address_region='北京市',
                address_country='CN'
            ),
            telephone='+86-10-12345678',
            aggregate_rating=AggregateRating(
                rating_value=4.5,
                rating_count=100
            )
        )
        
        with patch('app.main.crawler.extract_business_info', new_callable=AsyncMock) as mock_extract, \
             patch('app.main.schema_generator.generate_json_ld_script') as mock_generate_script, \
             patch('app.main.schema_generator.generate_schema') as mock_generate_schema, \
             patch('app.main.cache.get') as mock_cache_get, \
             patch('app.main.cache.set') as mock_cache_set:
            
            # 设置 mock 返回值
            mock_extract.return_value = mock_business_data
            mock_generate_script.return_value = '<script type="application/ld+json">\n{"@context": "https://schema.org", "@type": "LocalBusiness"}\n</script>'
            mock_generate_schema.return_value = mock_schema
            mock_cache_get.return_value = None  # 无缓存
            
            # 发送请求
            response = self.client.post(
                "/api/extract",
                json={
                    "url": "https://maps.google.com/maps?cid=123456789",
                    "force_refresh": False
                }
            )
            
            # 验证响应状态码
            assert response.status_code == 200
            
            # 验证响应格式
            data = response.json()
            
            # 检查必需字段
            assert "success" in data
            assert "script" in data
            assert "cached" in data
            assert "extracted_at" in data
            
            # 检查字段类型
            assert isinstance(data["success"], bool)
            assert isinstance(data["script"], str)
            assert isinstance(data["cached"], bool)
            assert isinstance(data["extracted_at"], str)
            
            # 检查成功响应的值
            assert data["success"] is True
            assert data["cached"] is False
            assert data["script"].startswith('<script type="application/ld+json">')
            assert data["script"].endswith('</script>')
            
            # 验证时间戳格式
            try:
                datetime.fromisoformat(data["extracted_at"])
            except ValueError:
                pytest.fail("extracted_at 时间戳格式无效")
    
    def test_extract_cached_response_format(self):
        """测试缓存响应的格式"""
        # Mock 缓存的 schema
        mock_cached_schema = LocalBusinessSchema(
            name='缓存餐厅',
            address=PostalAddress(
                street_address='缓存街道456号',
                address_locality='海淀区',
                address_region='北京市',
                address_country='CN'
            )
        )
        
        with patch('app.main.cache.get') as mock_cache_get:
            mock_cache_get.return_value = mock_cached_schema
            
            response = self.client.post(
                "/api/extract",
                json={
                    "url": "https://maps.google.com/maps?cid=123456789",
                    "force_refresh": False
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 检查缓存响应的特定字段
            assert data["success"] is True
            assert data["cached"] is True
            assert "script" in data
            assert "extracted_at" in data
    
    def test_extract_error_response_format(self):
        """测试错误响应的格式"""
        with patch('app.main.crawler.extract_business_info', new_callable=AsyncMock) as mock_extract, \
             patch('app.main.cache.get') as mock_cache_get:
            
            mock_cache_get.return_value = None
            mock_extract.side_effect = Exception("测试错误")
            
            response = self.client.post(
                "/api/extract",
                json={
                    "url": "https://maps.google.com/maps?cid=123456789"
                }
            )
            
            assert response.status_code == 200  # API 不抛出 HTTP 错误，而是返回错误信息
            data = response.json()
            
            # 检查错误响应格式
            assert "success" in data
            assert "error" in data
            assert "extracted_at" in data
            
            assert data["success"] is False
            assert isinstance(data["error"], str)
            assert data["error"] == "测试错误"
    
    def test_extract_invalid_url_format(self):
        """测试无效 URL 的响应格式"""
        response = self.client.post(
            "/api/extract",
            json={
                "url": "https://invalid-url.com"
            }
        )
        
        # 应该返回 400 错误
        assert response.status_code == 400
        data = response.json()
        
        # 检查错误响应格式
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert "Invalid Google Business URL" in data["detail"]
    
    def test_extract_json_ld_script_format(self):
        """测试 JSON-LD script 标签的格式"""
        mock_business_data = {
            'name': '测试商家',
            'address': '测试地址'
        }
        
        mock_schema = LocalBusinessSchema(
            name='测试商家',
            address=PostalAddress(street_address='测试地址')
        )
        
        with patch('app.main.crawler.extract_business_info', new_callable=AsyncMock) as mock_extract, \
             patch('app.main.schema_generator.generate_json_ld_script') as mock_generate_script, \
             patch('app.main.schema_generator.generate_schema') as mock_generate_schema, \
             patch('app.main.cache.get') as mock_cache_get, \
             patch('app.main.cache.set') as mock_cache_set:
            
            # 生成真实的 JSON-LD script
            schema_dict = {
                "@context": "https://schema.org",
                "@type": "LocalBusiness",
                "name": "测试商家",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "测试地址"
                }
            }
            json_content = json.dumps(schema_dict, indent=2, ensure_ascii=False)
            expected_script = f'<script type="application/ld+json">\n{json_content}\n</script>'
            
            mock_extract.return_value = mock_business_data
            mock_generate_script.return_value = expected_script
            mock_generate_schema.return_value = mock_schema
            mock_cache_get.return_value = None
            
            response = self.client.post(
                "/api/extract",
                json={
                    "url": "https://maps.google.com/maps?cid=123456789"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            script = data["script"]
            
            # 验证 script 标签格式
            assert script.startswith('<script type="application/ld+json">')
            assert script.endswith('</script>')
            
            # 提取 JSON 内容并验证
            json_start = script.find('>\n') + 2
            json_end = script.rfind('\n<')
            json_content = script[json_start:json_end]
            
            # 验证 JSON 格式
            try:
                parsed_json = json.loads(json_content)
                assert parsed_json["@context"] == "https://schema.org"
                assert parsed_json["@type"] == "LocalBusiness"
                assert "name" in parsed_json
            except json.JSONDecodeError:
                pytest.fail("JSON-LD 内容格式无效")
    
    def test_extract_request_validation(self):
        """测试请求参数验证"""
        # 测试缺少 URL
        response = self.client.post(
            "/api/extract",
            json={}
        )
        assert response.status_code == 422  # Validation error
        
        # 测试描述过长
        long_description = "a" * 501  # 超过 500 字符限制
        response = self.client.post(
            "/api/extract",
            json={
                "url": "https://maps.google.com/maps?cid=123456789",
                "description": long_description
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_extract_with_custom_description(self):
        """测试带自定义描述的请求"""
        mock_business_data = {'name': '测试商家'}
        mock_schema = LocalBusinessSchema(
            name='测试商家',
            address=PostalAddress(street_address='测试地址')
        )
        
        with patch('app.main.crawler.extract_business_info', new_callable=AsyncMock) as mock_extract, \
             patch('app.main.schema_generator.generate_json_ld_script') as mock_generate_script, \
             patch('app.main.schema_generator.generate_schema') as mock_generate_schema, \
             patch('app.main.cache.get') as mock_cache_get, \
             patch('app.main.cache.set') as mock_cache_set:
            
            mock_extract.return_value = mock_business_data
            mock_generate_script.return_value = '<script></script>'
            mock_generate_schema.return_value = mock_schema
            mock_cache_get.return_value = None
            
            response = self.client.post(
                "/api/extract",
                json={
                    "url": "https://maps.google.com/maps?cid=123456789",
                    "description": "自定义商家描述"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            
            # 验证自定义描述被传递给 schema 生成器
            mock_generate_schema.assert_called_once()
            args = mock_generate_schema.call_args
            assert args[0][2] == "自定义商家描述"  # 第三个参数是描述