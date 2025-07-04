"""测试配置文件"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """创建测试客户端"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_crawler():
    """Mock 爬虫实例"""
    with patch('app.main.crawler') as mock:
        mock.extract_business_info = AsyncMock()
        mock._is_started = True
        mock.browser = AsyncMock()
        yield mock


@pytest.fixture
def mock_cache():
    """Mock 缓存实例"""
    with patch('app.main.cache') as mock:
        mock.get.return_value = None
        mock.set.return_value = None
        yield mock


@pytest.fixture
def mock_schema_generator():
    """Mock schema 生成器"""
    with patch('app.main.schema_generator') as mock:
        def generate_script(business_data, original_url, custom_description=None):
            # 根据传入的 business_data 动态生成 JSON-LD script
            name = business_data.get('name', '测试餐厅')
            return f'<script type="application/ld+json">\n{{"@context": "https://schema.org", "@type": "LocalBusiness", "name": "{name}", "address": {{"@type": "PostalAddress"}}}}\n</script>'
        
        mock.generate_json_ld_script.side_effect = generate_script
        yield mock


@pytest.fixture
def sample_business_data():
    """示例商家数据"""
    return {
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
            'Tuesday': '09:00-22:00',
            'Wednesday': '09:00-22:00',
            'Thursday': '09:00-22:00',
            'Friday': '09:00-23:00',
            'Saturday': '10:00-23:00',
            'Sunday': '10:00-22:00'
        },
        'images': [
            'https://example.com/image1.jpg',
            'https://example.com/image2.jpg'
        ]
    }


@pytest.fixture
def valid_google_business_url():
    """有效的 Google 商家 URL"""
    return "https://maps.google.com/maps?cid=123456789"


@pytest.fixture
def invalid_url():
    """无效的 URL"""
    return "https://invalid-website.com"