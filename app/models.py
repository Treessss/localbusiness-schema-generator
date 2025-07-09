"""应用程序数据模型

本模块定义了应用程序中使用的所有数据模型，包括：
- API请求和响应模型
- Schema.org标准的结构化数据模型
- 缓存和健康检查相关模型

所有模型都基于Pydantic，提供数据验证和序列化功能。
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Union
from datetime import datetime


class ExtractRequest(BaseModel):
    """商家信息提取请求模型
    
    用于接收客户端的商家信息提取请求，包含目标URL、
    缓存控制选项和可选的自定义描述。
    
    Attributes:
        url: Google Business分享链接
        force_refresh: 是否强制刷新缓存，默认False
        description: 自定义商家描述，最多500个字符
    """
    url: str = Field(..., description="Google Business分享链接")
    force_refresh: bool = Field(False, description="是否强制刷新缓存")
    description: Optional[str] = Field(None, max_length=500,
                                       description="自定义商家描述，最多500个字符")

    @validator('description')
    def validate_description(cls, v):
        if v is not None and len(v) > 500:
            raise ValueError('描述不能超过500个字符')
        return v


class OpeningHoursSpecification(BaseModel):
    """遵循Schema.org标准的营业时间规范模型
    
    定义商家的营业时间信息，支持单日或多日的时间规范。
    符合Schema.org OpeningHoursSpecification标准。
    
    Attributes:
        type: 固定值"OpeningHoursSpecification"
        dayOfWeek: 星期几或日期列表（如Monday, Tuesday等）
        opens: 开门时间，HH:MM格式
        closes: 关门时间，HH:MM格式
    """
    type: str = Field(default="OpeningHoursSpecification", alias="@type")
    dayOfWeek: Union[str, List[str]] = Field(..., description="星期几（Monday, Tuesday等）或日期列表")
    opens: Optional[str] = Field(None, description="开门时间，HH:MM格式")
    closes: Optional[str] = Field(None, description="关门时间，HH:MM格式")

    class Config:
        populate_by_name = True


class PostalAddress(BaseModel):
    """遵循Schema.org标准的邮政地址模型
    
    定义商家的完整地址信息，包含街道、城市、州省、
    邮政编码和国家等详细信息。
    
    Attributes:
        type: 固定值"PostalAddress"
        street_address: 街道地址
        address_locality: 城市或地区
        address_region: 州或省
        postal_code: 邮政编码
        address_country: 国家代码
        extended_address: 扩展地址信息
    """
    type: str = Field(default="PostalAddress", alias="@type")
    street_address: Optional[str] = Field(None, alias="streetAddress", description="街道地址")
    address_locality: Optional[str] = Field(None, alias="addressLocality", description="城市或地区")
    address_region: Optional[str] = Field(None, alias="addressRegion", description="州或省")
    postal_code: Optional[str] = Field(None, alias="postalCode", description="邮政编码")
    address_country: Optional[str] = Field(None, alias="addressCountry", description="国家代码")
    extended_address: Optional[str] = Field(None, alias="extendedAddress",
                                            description="扩展地址信息")

    class Config:
        populate_by_name = True


class GeoCoordinates(BaseModel):
    """遵循Schema.org标准的地理坐标模型
    
    定义商家的精确地理位置坐标，用于地图定位和导航。
    
    Attributes:
        type: 固定值"GeoCoordinates"
        latitude: 纬度坐标（-90到90之间的浮点数）
        longitude: 经度坐标（-180到180之间的浮点数）
    """
    type: str = Field(default="GeoCoordinates", alias="@type")
    latitude: Optional[float] = Field(None, description="纬度坐标")
    longitude: Optional[float] = Field(None, description="经度坐标")

    class Config:
        populate_by_name = True


class AggregateRating(BaseModel):
    """遵循Schema.org标准的聚合评分模型
    
    定义商家的聚合评分信息，包含平均评分、评分数量等统计数据。
    
    Attributes:
        type: 固定值"AggregateRating"
        rating_value: 评分值（通常为1-5分）
        rating_count: 评分数量
        best_rating: 最佳可能评分，默认5.0
    """
    type: str = Field(default="AggregateRating", alias="@type")
    rating_value: Optional[float] = Field(None, alias="ratingValue", description="评分值")
    rating_count: Optional[int] = Field(None, alias="ratingCount", description="评分数量")
    best_rating: Optional[float] = Field(5.0, alias="bestRating",
                                         description="最佳可能评分")

    class Config:
        populate_by_name = True


class MakesOffer(BaseModel):
    """遵循Schema.org标准的优惠模型
    
    定义商家提供的优惠或服务信息。
    
    Attributes:
        type: 固定值"Offer"
        name: 优惠名称或服务描述
    """
    type: str = Field(default="Offer", alias="@type")
    name: Optional[str] = Field(None, description="优惠名称")


class LocalBusinessSchema(BaseModel):
    """遵循Schema.org标准的本地商家结构化数据模型
    
    符合Google官方LocalBusiness结构化数据格式，用于生成搜索引擎
    可理解的商家信息。包含商家的基本信息、地址、联系方式、
    营业时间、评分等完整信息。
    """
    context: str = Field(default="https://schema.org", alias="@context")
    type: str = Field(default="LocalBusiness", alias="@type")

    # 必需属性
    name: str = Field(..., description="商家名称")
    address: PostalAddress = Field(..., description="商家地址")

    # 推荐属性
    description: Optional[str] = Field(None, description="商家描述")
    telephone: Optional[str] = Field(None, description="商家电话号码")
    url: Optional[str] = Field(None, description="商家网站URL")
    geo: Optional[GeoCoordinates] = Field(None, description="地理坐标")
    opening_hours_specification: Optional[List[OpeningHoursSpecification]] = Field(
        None, alias="openingHoursSpecification", description="营业时间"
    )
    makesOffer: Optional[List[MakesOffer]] = Field(None, description="提供的优惠")

    image: Optional[List[str]] = Field(None, description="商家图片")
    aggregate_rating: Optional[AggregateRating] = Field(
        None, alias="aggregateRating", description="聚合评分"
    )
    price_range: Optional[str] = Field(
        None, alias="priceRange", description="价格范围（例如：$$）"
    )
    same_as: Optional[List[str]] = Field(
        None, alias="sameAs", description="社交媒体和其他URL"
    )

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CacheInfo(BaseModel):
    """缓存信息模型
    
    用于存储和管理缓存条目的元数据信息，包含缓存的URL、
    创建时间、过期时间和访问统计。
    
    Attributes:
        url: 缓存的原始URL
        cached_at: 缓存创建时间
        expires_at: 缓存过期时间
        hit_count: 缓存命中次数，默认0
    """
    url: str
    cached_at: datetime
    expires_at: datetime
    hit_count: int = 0


class HealthResponse(BaseModel):
    """健康检查响应模型
    
    用于API健康检查端点的响应数据结构，提供服务状态、
    时间戳、版本信息和缓存大小等系统信息。
    
    Attributes:
        status: 服务状态，默认"healthy"
        timestamp: 响应时间戳
        version: API版本号，默认"1.0.0"
        cache_size: 当前缓存大小，默认0
    """
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    cache_size: int = 0
