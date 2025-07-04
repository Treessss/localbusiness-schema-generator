"""Google商家Schema生成器应用程序

这是一个基于FastAPI的Web应用程序，用于从Google Maps商家页面
提取商家信息并生成符合Schema.org标准的结构化数据。

主要功能：
- 爬取Google Maps商家信息
- 生成Schema.org LocalBusiness结构化数据
- 提供JSON-LD格式的脚本标签
- 智能缓存机制提高性能
- 实时统计和监控功能
- WebSocket支持实时数据推送

模块组织：
- main.py: FastAPI应用程序主入口
- crawler.py: Google商家信息爬虫
- schema_generator.py: Schema.org数据生成器
- models.py: Pydantic数据模型
- utils.py: 工具函数
- cache.py: 缓存系统实现
- stats.py: 统计数据收集
- middleware.py: 中间件组件

Author: Local Business Schema Generator Team
Version: 1.0.0
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Local Business Schema Generator"