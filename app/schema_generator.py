"""Schema.org本地商家结构化数据生成器

本模块负责将爬取的商家数据转换为符合Schema.org标准的LocalBusiness结构化数据，
支持生成JSON-LD格式的脚本标签，便于搜索引擎理解和索引商家信息。

主要功能：
- 生成LocalBusiness Schema.org结构化数据
- 解析和格式化营业时间
- 提取地理坐标信息
- 生成JSON-LD脚本标签
"""

import re
from typing import Dict, Any, List, Optional
from loguru import logger

from .models import (
    LocalBusinessSchema,
    PostalAddress,
    GeoCoordinates,
    AggregateRating,
    OpeningHoursSpecification,
    MakesOffer
)
from .utils import parse_address


class SchemaGenerator:
    """为本地商家生成Schema.org结构化数据
    
    负责将爬虫提取的原始商家数据转换为符合Schema.org标准的
    LocalBusiness结构化数据，支持多种数据格式和营业时间解析。
    
    功能特性：
    - 生成符合Schema.org标准的LocalBusiness对象
    - 解析和格式化营业时间信息
    - 提取地理坐标信息
    - 生成JSON-LD格式的脚本标签
    - 支持多语言日期映射
    
    Attributes:
        day_mapping: 中英文星期映射字典
    """

    def __init__(self):
        """初始化Schema生成器
        
        设置中英文星期映射字典，支持多种日期格式的解析。
        """
        self.day_mapping = {
            'monday': 'Monday',
            'tuesday': 'Tuesday',
            'wednesday': 'Wednesday',
            'thursday': 'Thursday',
            'friday': 'Friday',
            'saturday': 'Saturday',
            'sunday': 'Sunday',
            '星期一': 'Monday',
            '星期二': 'Tuesday',
            '星期三': 'Wednesday',
            '星期四': 'Thursday',
            '星期五': 'Friday',
            '星期六': 'Saturday',
            '星期日': 'Sunday',
            '周一': 'Monday',
            '周二': 'Tuesday',
            '周三': 'Wednesday',
            '周四': 'Thursday',
            '周五': 'Friday',
            '周六': 'Saturday',
            '周日': 'Sunday'
        }

    def generate_schema(self, business_data: Dict[str, Any],
                        original_url: str, custom_description: Optional[str] = None) -> LocalBusinessSchema:
        """从提取的商家数据生成LocalBusiness schema
        
        将爬虫提取的原始商家数据转换为符合Schema.org标准的LocalBusiness对象。
        自动处理地址解析、坐标提取、营业时间格式化等复杂逻辑。
        
        Args:
            business_data: 爬虫提取的商家数据字典，包含name、address、phone等字段
            original_url: 原始商家URL，用作备用网站地址
            custom_description: 自定义商家描述，优先级高于爬取的描述
            
        Returns:
            LocalBusinessSchema: 符合Schema.org标准的本地商家对象
            
        Note:
            - 商家名称为必需字段，缺失时使用默认值
            - 地址会自动解析为结构化格式
            - 支持多种营业时间格式的转换
        """
        logger.info(f"正在为商家生成schema: {business_data.get('name', '未知')}")

        # 确保必需字段有默认值
        business_name = business_data.get('name')
        if not business_name or not business_name.strip():
            business_name = "Business Name Not Available"
            logger.warning("商家名称缺失，使用默认值")

        # 使用新的parse_address函数提取或创建地址
        address_text = business_data.get('address', '')
        extended_address = business_data.get('extended_address')

        if address_text:
            # 将地址字符串解析为结构化格式
            parsed_address = parse_address(address_text)

            # 使用解析的数据创建PostalAddress对象
            address = PostalAddress(
                street_address=parsed_address.get('streetAddress'),
                address_locality=parsed_address.get('addressLocality'),
                address_region=parsed_address.get('addressRegion'),
                postal_code=parsed_address.get('postalCode'),
                address_country=parsed_address.get('addressCountry'),
                extended_address=extended_address
            )
        else:
            # 回退到空的PostalAddress
            address = PostalAddress(extended_address=extended_address)

        # 使用必需字段创建schema
        schema = LocalBusinessSchema(
            name=business_name,
            address=address
        )

        # 可选字段
        # 优先使用自定义描述，然后是爬取的描述
        schema.description = custom_description or business_data.get('description')
        schema.url = business_data.get('website') or original_url
        schema.telephone = business_data.get('phone')

        # 地理坐标（如果可用）
        schema.geo = self._extract_coordinates(business_data)

        # 营业时间规范现在在爬虫中处理

        # 评分信息
        if business_data.get('rating') or business_data.get('review_count'):
            schema.aggregate_rating = AggregateRating(
                rating_value=business_data.get('rating'),
                rating_count=business_data.get('review_count')
            )

        # 价格范围
        schema.price_range = business_data.get('price_range')

        # 商家类型/菜系
        if business_data.get('business_type'):
            make_offer = MakesOffer()
            make_offer.name = business_data.get('business_type')
            schema.makesOffer = [make_offer]

        # 图片
        if business_data.get('images'):
            schema.image = business_data['images']

        # 提取社交媒体和其他URL
        same_as = []
        if business_data.get('website'):
            same_as.append(business_data.get('website'))

        if same_as:
            schema.same_as = same_as

        # 添加营业时间 - 支持文本和结构化格式
        if business_data.get('opening_hours'):
            # 如果已经是OpeningHoursSpecification格式
            if isinstance(business_data['opening_hours'], list) and len(
                    business_data['opening_hours']) > 0:
                if isinstance(business_data['opening_hours'][0], dict) and '@type' in \
                        business_data['opening_hours'][0]:
                    # 将字典转换为OpeningHoursSpecification对象
                    opening_hours_list = []
                    for hours_dict in business_data['opening_hours']:
                        try:
                            # 从字典创建OpeningHoursSpecification对象
                            opening_hours_obj = OpeningHoursSpecification(
                                dayOfWeek=hours_dict.get('dayOfWeek'),
                                opens=hours_dict.get('opens'),
                                closes=hours_dict.get('closes')
                            )
                            opening_hours_list.append(opening_hours_obj)
                        except Exception as e:
                            logger.warning(f"从字典创建OpeningHoursSpecification失败: {e}")
                            continue

                    if opening_hours_list:
                        schema.opening_hours_specification = opening_hours_list

        logger.info(f"成功为商家生成schema: {schema.name}")
        return schema

    def generate_json_ld_script(self, business_data: Dict[str, Any], original_url: str, custom_description: Optional[str] = None) -> str:
        """生成包装在script标签中的Schema.org JSON-LD
        
        将商家数据转换为完整的JSON-LD脚本标签，可直接嵌入HTML页面。
        生成的脚本符合Schema.org标准，有助于搜索引擎理解和索引。
        
        Args:
            business_data: 爬虫提取的商家数据字典
            original_url: 原始商家URL
            custom_description: 自定义商家描述（可选）
            
        Returns:
            str: 包含JSON-LD数据的HTML script标签字符串
            
        Example:
            返回格式类似：
            <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "LocalBusiness",
              ...
            }
            </script>
        """
        schema = self.generate_schema(business_data, original_url, custom_description)

        # 将schema转换为字典然后转换为JSON
        schema_dict = schema.model_dump(by_alias=True, exclude_none=True)

        # 为Schema.org添加@context和@type
        schema_dict["@context"] = "https://schema.org"
        schema_dict["@type"] = "LocalBusiness"

        # 转换为格式化的JSON字符串
        import json
        json_content = json.dumps(schema_dict, indent=2, ensure_ascii=False)

        # 包装在script标签中
        script_content = f'<script type="application/ld+json">\n{json_content}\n</script>'

        logger.info("生成了格式正确的Schema.org JSON-LD脚本")
        return script_content

    def _extract_coordinates(self, business_data: Dict[str, Any]) -> Optional[GeoCoordinates]:
        """从URL或商家数据中提取地理坐标
        
        尝试从当前URL和原始URL中解析地理坐标信息。
        优先使用当前页面URL，失败时回退到原始URL。
        
        Args:
            business_data: 包含URL信息的商家数据字典，需包含current_url或original_url
            
        Returns:
            Optional[GeoCoordinates]: 地理坐标对象，未找到坐标时返回None
            
        Note:
            支持多种Google Maps URL格式的坐标提取
        """
        # 首先尝试从当前页面URL提取
        current_url = business_data.get('current_url', '')
        logger.info(f"获取到页面url为:{current_url}")
        if current_url:
            coords = self._extract_coords_from_url(current_url)
            if coords:
                return coords

        # 尝试从原始URL提取
        original_url = business_data.get('original_url', '')
        if original_url:
            coords = self._extract_coords_from_url(original_url)
            if coords:
                return coords

        return None

    def _extract_coords_from_url(self, url: str) -> Optional[GeoCoordinates]:
        """使用正则表达式从Google Maps URL中提取坐标
        
        支持多种Google Maps URL格式的坐标提取，包括@lat,lng和!3d!4d格式。
        
        Args:
            url: Google Maps URL字符串
            
        Returns:
            Optional[GeoCoordinates]: 地理坐标对象，解析失败时返回None
            
        Supported Formats:
            - @latitude,longitude,zoom (如: @-37.8770935,145.1652529,17z)
            - !3dlatitude!4dlongitude (如: !3d-37.8770935!4d145.1652529)
        """
        if not url:
            return None

        import re

        # Google Maps URL中@latitude,longitude的模式
        # 示例: @-37.8770935,145.1652529,17z
        coord_pattern = r'@(-?\d+\.\d+),(-?\d+\.\d+)'

        match = re.search(coord_pattern, url)
        if match:
            try:
                latitude = float(match.group(1))
                longitude = float(match.group(2))

                logger.info(f"从URL提取坐标: 纬度={latitude}, 经度={longitude}")

                return GeoCoordinates(
                    latitude=latitude,
                    longitude=longitude
                )
            except (ValueError, IndexError) as e:
                logger.warning(f"从URL解析坐标时出错: {e}")

        # 不同URL格式的替代模式
        # !3d和!4d格式的模式: !3dlatitude!4dlongitude
        alt_pattern = r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)'
        alt_match = re.search(alt_pattern, url)
        if alt_match:
            try:
                latitude = float(alt_match.group(1))
                longitude = float(alt_match.group(2))

                logger.info(f"从URL提取坐标（替代格式）: 纬度={latitude}, 经度={longitude}")

                return GeoCoordinates(
                    latitude=latitude,
                    longitude=longitude
                )
            except (ValueError, IndexError) as e:
                logger.warning(f"从URL解析坐标时出错（替代格式）: {e}")

        return None

    def _parse_opening_hours(self, hours_data: List[str]) -> Optional[
        List[OpeningHoursSpecification]]:
        """从各种格式解析营业时间
        
        将文本格式的营业时间转换为结构化的OpeningHoursSpecification对象。
        支持24/7营业、常规营业时间等多种格式。
        
        Args:
            hours_data: 营业时间文本列表
            
        Returns:
            Optional[List[OpeningHoursSpecification]]: 营业时间规范对象列表，解析失败时返回None
            
        Note:
            自动识别24小时营业、休息日等特殊情况
        """
        if not hours_data:
            return None

        business_hours = []

        for hours_text in hours_data:
            if isinstance(hours_text, str):
                parsed_hours = self._parse_hours_text(hours_text)
                business_hours.extend(parsed_hours)

        return business_hours if business_hours else None

    def _parse_hours_text(self, hours_text: str) -> List[OpeningHoursSpecification]:
        """将时间文本解析为OpeningHoursSpecification对象
        
        解析单个营业时间文本，支持24/7营业和常规营业时间格式。
        自动识别中英文星期表示和多种时间格式。
        
        Args:
            hours_text: 营业时间文本字符串
            
        Returns:
            List[OpeningHoursSpecification]: 营业时间规范对象列表
            
        Supported Formats:
            - "24小时营业" / "24/7" -> 全天营业
            - "周一 9:00-18:00" -> 常规营业时间
            - "Monday 9:00-18:00" -> 英文格式
            - "关闭" / "closed" -> 休息日
        """
        hours = []

        if not hours_text:
            return hours

        # 检查24/7营业
        if re.search(r'24.*7|24.*小时|全天', hours_text, re.IGNORECASE):
            # 为所有天添加24/7营业时间
            for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
                        'Sunday']:
                hours.append(OpeningHoursSpecification(
                    day_of_week=day,
                    opens='00:00',
                    closes='23:59'
                ))
            return hours

        # 尝试解析单独的日期时间
        # 这是一个简化的解析器 - 在生产环境中需要更复杂的解析
        lines = hours_text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 尝试匹配日期和时间模式
            day_match = None
            for day_key, day_value in self.day_mapping.items():
                if day_key.lower() in line.lower():
                    day_match = day_value
                    break

            if day_match:
                # 提取时间信息
                time_match = re.search(r'(\d{1,2}:?\d{0,2}).*?[–-].*?(\d{1,2}:?\d{0,2})', line)
                if time_match:
                    opens = self._normalize_time(time_match.group(1))
                    closes = self._normalize_time(time_match.group(2))

                    hours.append(OpeningHoursSpecification(
                        day_of_week=day_match,
                        opens=opens,
                        closes=closes
                    ))
                elif re.search(r'关闭|closed|休息', line, re.IGNORECASE):
                    hours.append(OpeningHoursSpecification(
                        day_of_week=day_match,
                        opens=None,
                        closes=None
                    ))

        return hours

    def _normalize_time(self, time_str: str) -> str:
        """将时间字符串规范化为HH:MM格式
        
        处理各种时间格式，统一转换为标准的24小时制HH:MM格式。
        自动补零和添加冒号分隔符。
        
        Args:
            time_str: 原始时间字符串（如"9:30"、"930"、"9"等）
            
        Returns:
            str: 规范化后的时间字符串（HH:MM格式，如"09:30"）
            
        Examples:
            - "9:30" -> "09:30"
            - "930" -> "09:30"
            - "9" -> "09:00"
        """
        if not time_str:
            return ''

        # 移除任何非数字和非冒号字符
        time_str = re.sub(r'[^\d:]', '', time_str)

        # 如果缺少冒号则添加
        if ':' not in time_str and len(time_str) >= 3:
            time_str = time_str[:-2] + ':' + time_str[-2:]

        # 确保两位数格式
        parts = time_str.split(':')
        if len(parts) == 2:
            hour = parts[0].zfill(2)
            minute = parts[1].zfill(2)
            return f"{hour}:{minute}"

        return time_str
