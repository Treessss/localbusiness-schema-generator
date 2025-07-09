"""应用程序工具函数

本模块提供了应用程序中使用的各种工具函数，包括：
- URL验证和解析
- 文本清理和格式化
- 数据解析和转换
- 地址解析和标准化

这些函数为爬虫和数据处理提供基础支持。
"""

import re
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any
from loguru import logger


def is_google_business_url(url: str) -> bool:
    """验证URL是否为Google商家分享URL
    
    检查给定的URL是否为有效的Google商家或Google Maps链接。
    支持多种Google Maps URL格式，包括短链接和完整链接。
    
    Args:
        url: 待验证的URL字符串
        
    Returns:
        bool: 如果是有效的Google商家URL返回True，否则返回False
        
    Examples:
        >>> is_google_business_url('https://maps.app.goo.gl/abc123')
        True
        >>> is_google_business_url('https://maps.google.com/place/...')
        True
        >>> is_google_business_url('https://example.com')
        False
    """
    try:
        parsed = urlparse(str(url))
        
        # 检查Google Maps域名
        valid_domains = [
            'maps.app.goo.gl',
            'goo.gl',
            'maps.google.com',
            'www.google.com'
        ]
        
        if parsed.netloc in valid_domains:
            return True
        
        # 检查Google Maps URL模式
        if 'google' in parsed.netloc and 'maps' in parsed.netloc:
            return True
        
        # 检查特定的Google商家URL模式
        google_patterns = [
            r'maps\.app\.goo\.gl',
            r'goo\.gl',
            r'maps\.google\.',
            r'google\.com/maps'
        ]
        
        for pattern in google_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"验证URL {url} 时出错: {e}")
        return False


def extract_place_id_from_url(url: str) -> Optional[str]:
    """从Google Maps URL中提取地点ID
    
    尝试从URL中解析Google Places API的地点ID。
    支持从URL路径和查询参数中提取地点ID。
    
    Args:
        url: Google Maps URL字符串
        
    Returns:
        Optional[str]: 地点ID字符串，未找到时返回None
        
    Examples:
        >>> extract_place_id_from_url('https://maps.google.com/?place_id=ChIJ...')
        'ChIJ...'
    """
    try:
        # URL中地点ID的模式
        place_id_pattern = r'place_id:([a-zA-Z0-9_-]+)'
        match = re.search(place_id_pattern, url)
        
        if match:
            return match.group(1)
        
        # 尝试从查询参数中提取
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        if 'place_id' in query_params:
            return query_params['place_id'][0]
        
        return None
        
    except Exception as e:
        logger.error(f"从URL {url} 提取地点ID时出错: {e}")
        return None


def clean_text(text: str) -> str:
    """清理和规范化文本内容
    
    移除多余的空白字符、特殊字符和不需要的符号。
    确保文本适合JSON序列化和数据处理。
    
    Args:
        text: 待清理的文本字符串
        
    Returns:
        str: 清理后的文本字符串
        
    Examples:
        'Hello World'
        'Restaurant'
    """
    if not text:
        return ""
    
    # 移除多余的空白和换行符
    text = re.sub(r'\s+', ' ', text.strip())
    
    # 移除可能破坏JSON的特殊字符
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # 移除开头的常见不需要字符
    # 移除前导符号、箭头、项目符号等
    text = re.sub(r'^[^\w\d]+', '', text)
    
    # 移除尾部不需要的字符
    text = re.sub(r'[^\w\d\s,.\-()]+$', '', text)
    
    return text.strip()


def parse_rating(rating_text: str) -> Optional[float]:
    """从文本中解析评分
    
    从包含评分信息的文本中提取数值评分。
    自动验证评分范围的有效性。
    
    Args:
        rating_text: 包含评分的文本字符串
        
    Returns:
        Optional[float]: 评分数值（0-5范围），解析失败时返回None
        
    Examples:
        >>> parse_rating('4.5 stars')
        4.5
        >>> parse_rating('Rating: 3.2/5')
        3.2
    """
    if not rating_text:
        return None
    
    try:
        # 提取数字评分（例如从"4.5 stars"中提取"4.5"）
        rating_match = re.search(r'(\d+\.?\d*)', rating_text)
        if rating_match:
            rating = float(rating_match.group(1))
            # 确保评分在有效范围内（0-5）
            if 0 <= rating <= 5:
                return rating
        return None
    except (ValueError, AttributeError):
        return None


def parse_review_count(review_text: str) -> Optional[int]:
    """从文本中解析评论数量
    
    从包含评论数量信息的文本中提取数值。
    支持带逗号分隔符的大数字格式。
    
    Args:
        review_text: 包含评论数量的文本字符串
        
    Returns:
        Optional[int]: 评论数量整数，解析失败时返回None
        
    Examples:
        >>> parse_review_count('(1,234 reviews)')
        1234
        >>> parse_review_count('500条评论')
        500
    """
    if not review_text:
        return None
    
    try:
        # 从评论文本中提取数字
        # 处理如"(1,234)"、"1,234 reviews"等格式
        review_match = re.search(r'([\d,]+)', review_text)
        if review_match:
            count_str = review_match.group(1).replace(',', '')
            return int(count_str)
        return None
    except (ValueError, AttributeError):
        return None


def parse_price_range(price_text: str) -> Optional[str]:
    """从文本中解析价格范围
    
    从包含价格信息的文本中提取价格范围符号。
    支持多种价格表示格式，包括美元符号和中文描述。
    
    Args:
        price_text: 包含价格信息的文本字符串
        
    Returns:
        Optional[str]: 价格范围符号（如$、$$、$$$、$$$$），解析失败时返回None
        
    Examples:
        >>> parse_price_range('Price range: $$$')
        '$$$'
        >>> parse_price_range('Moderate pricing')
        '$$'
    """
    if not price_text:
        return None
    
    # 常见的价格范围模式
    price_patterns = {
        r'\$\$\$\$': '$$$$',
        r'\$\$\$': '$$$',
        r'\$\$': '$$',
        r'\$': '$',
        r'便宜': '$',
        r'中等': '$$',
        r'昂贵': '$$$',
        r'很贵': '$$$$'
    }
    
    for pattern, range_val in price_patterns.items():
        if re.search(pattern, price_text, re.IGNORECASE):
            return range_val
    
    return None


def parse_business_hours(hours_text: str) -> Dict[str, Any]:
    """从文本中解析营业时间
    
    将营业时间文本解析为结构化的时间数据。
    支持多种时间格式和语言，自动处理休息日。
    
    Args:
        hours_text: 包含营业时间的文本字符串
        
    Returns:
        Dict[str, Any]: 营业时间信息字典，包含is_open_24_7和hours字段
        
    Examples:
        >>> parse_business_hours('Monday: 9:00 AM - 5:00 PM')
        {'is_open_24_7': False, 'hours': [...]}
    """
    if not hours_text:
        return {}
    
    # 这是一个简化的解析器 - 实际上，您需要更复杂的解析
    # 来处理不同的语言和格式
    hours_info = {
        'is_open_24_7': False,
        'hours': []
    }
    
    # 检查是否24/7营业
    if re.search(r'24.*7|24.*小时|全天', hours_text, re.IGNORECASE):
        hours_info['is_open_24_7'] = True
    
    return hours_info


def format_phone_number(phone: str) -> Optional[str]:
    """格式化电话号码
    
    将电话号码格式化为标准格式。
    移除非数字字符并应用标准格式化规则。
    
    Args:
        phone: 原始电话号码字符串
        
    Returns:
        Optional[str]: 格式化后的电话号码字符串，无效时返回None
        
    Examples:
        >>> format_phone_number('(555) 123-4567')
        '+1-555-123-4567'
        >>> format_phone_number('555.123.4567')
        '+1-555-123-4567'
    """
    if not phone:
        return None
    
    # 移除除开头的+号外的所有非数字字符
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # 确保以+开头的国际格式
    if cleaned and not cleaned.startswith('+'):
        # 假设这是本地号码，您可能想在这里添加国家代码逻辑
        pass
    
    return cleaned if cleaned else None


def sanitize_filename(filename: str) -> str:
    """清理文件名以进行安全的文件操作
    
    移除或替换文件名中的非法字符。
    确保文件名在不同操作系统中都能安全使用。
    
    Args:
        filename: 原始文件名字符串
        
    Returns:
        str: 清理后的安全文件名字符串
        
    Examples:
        >>> sanitize_filename('file<name>.txt')
        'file_name_.txt'
        >>> sanitize_filename('my/file\\name')
        'my_file_name'
    """
    # 移除或替换无效的文件名字符
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    sanitized = sanitized.strip('. ')
    return sanitized[:255]  # 限制长度


def parse_address(address_string: str) -> Dict[str, Any]:
    """将地址字符串解析为PostalAddress schema.org格式
    
    将地址文本解析为结构化的地址数据。
    支持多种地址格式和国际地址标准。
    
    Args:
        address_string: 完整地址字符串，如'23 Smith St, Warragul VIC 3820, Australia'
        
    Returns:
        Dict[str, Any]: 包含地址组件的字典，符合Schema.org PostalAddress格式
        
    Examples:
        >>> parse_address('123 Main St, New York, NY 10001, USA')
        {'streetAddress': '123 Main St', 'addressLocality': 'New York', ...}
    """
    if not address_string:
        return {
            "@type": "PostalAddress"
        }
    
    # 清理地址字符串
    address = clean_text(address_string)
    
    # 使用schema.org类型初始化结果
    result = {
        "@type": "PostalAddress"
    }
    
    # 按逗号分割地址
    parts = [part.strip() for part in address.split(',')]
    
    if not parts:
        return result
    
    # 常见变体的国家映射
    country_mapping = {
        # 英语国家
        'australia': 'AU',
        'united states': 'US',
        'usa': 'US',
        'united states of america': 'US',
        'america': 'US',
        'united kingdom': 'GB',
        'uk': 'GB',
        'great britain': 'GB',
        'britain': 'GB',
        'england': 'GB',
        'scotland': 'GB',
        'wales': 'GB',
        'northern ireland': 'GB',
        'canada': 'CA',
        'new zealand': 'NZ',
        'ireland': 'IE',
        'south africa': 'ZA',
        
        # 欧洲国家
        'germany': 'DE',
        'deutschland': 'DE',
        'france': 'FR',
        'italy': 'IT',
        'spain': 'ES',
        'portugal': 'PT',
        'netherlands': 'NL',
        'holland': 'NL',
        'belgium': 'BE',
        'switzerland': 'CH',
        'austria': 'AT',
        'sweden': 'SE',
        'norway': 'NO',
        'denmark': 'DK',
        'finland': 'FI',
        'poland': 'PL',
        'czech republic': 'CZ',
        'hungary': 'HU',
        'romania': 'RO',
        'bulgaria': 'BG',
        'croatia': 'HR',
        'slovenia': 'SI',
        'slovakia': 'SK',
        'estonia': 'EE',
        'latvia': 'LV',
        'lithuania': 'LT',
        'greece': 'GR',
        'cyprus': 'CY',
        'malta': 'MT',
        'luxembourg': 'LU',
        'iceland': 'IS',
        'russia': 'RU',
        'ukraine': 'UA',
        'belarus': 'BY',
        'moldova': 'MD',
        'serbia': 'RS',
        'montenegro': 'ME',
        'bosnia and herzegovina': 'BA',
        'north macedonia': 'MK',
        'albania': 'AL',
        'kosovo': 'XK',
        
        # 亚洲国家
        'china': 'CN',
        'japan': 'JP',
        'south korea': 'KR',
        'korea': 'KR',
        'north korea': 'KP',
        'india': 'IN',
        'pakistan': 'PK',
        'bangladesh': 'BD',
        'sri lanka': 'LK',
        'nepal': 'NP',
        'bhutan': 'BT',
        'maldives': 'MV',
        'afghanistan': 'AF',
        'iran': 'IR',
        'iraq': 'IQ',
        'turkey': 'TR',
        'israel': 'IL',
        'palestine': 'PS',
        'jordan': 'JO',
        'lebanon': 'LB',
        'syria': 'SY',
        'saudi arabia': 'SA',
        'united arab emirates': 'AE',
        'uae': 'AE',
        'qatar': 'QA',
        'kuwait': 'KW',
        'bahrain': 'BH',
        'oman': 'OM',
        'yemen': 'YE',
        'thailand': 'TH',
        'vietnam': 'VN',
        'cambodia': 'KH',
        'laos': 'LA',
        'myanmar': 'MM',
        'burma': 'MM',
        'malaysia': 'MY',
        'singapore': 'SG',
        'indonesia': 'ID',
        'philippines': 'PH',
        'brunei': 'BN',
        'mongolia': 'MN',
        'kazakhstan': 'KZ',
        'uzbekistan': 'UZ',
        'turkmenistan': 'TM',
        'kyrgyzstan': 'KG',
        'tajikistan': 'TJ',
        
        # 非洲国家
        'egypt': 'EG',
        'libya': 'LY',
        'tunisia': 'TN',
        'algeria': 'DZ',
        'morocco': 'MA',
        'sudan': 'SD',
        'south sudan': 'SS',
        'ethiopia': 'ET',
        'kenya': 'KE',
        'uganda': 'UG',
        'tanzania': 'TZ',
        'rwanda': 'RW',
        'burundi': 'BI',
        'somalia': 'SO',
        'djibouti': 'DJ',
        'eritrea': 'ER',
        'chad': 'TD',
        'central african republic': 'CF',
        'cameroon': 'CM',
        'nigeria': 'NG',
        'niger': 'NE',
        'mali': 'ML',
        'burkina faso': 'BF',
        'senegal': 'SN',
        'gambia': 'GM',
        'guinea': 'GN',
        'guinea-bissau': 'GW',
        'sierra leone': 'SL',
        'liberia': 'LR',
        'ivory coast': 'CI',
        'ghana': 'GH',
        'togo': 'TG',
        'benin': 'BJ',
        'gabon': 'GA',
        'equatorial guinea': 'GQ',
        'sao tome and principe': 'ST',
        'democratic republic of congo': 'CD',
        'congo': 'CG',
        'angola': 'AO',
        'zambia': 'ZM',
        'malawi': 'MW',
        'mozambique': 'MZ',
        'zimbabwe': 'ZW',
        'botswana': 'BW',
        'namibia': 'NA',
        'lesotho': 'LS',
        'swaziland': 'SZ',
        'eswatini': 'SZ',
        'madagascar': 'MG',
        'mauritius': 'MU',
        'seychelles': 'SC',
        'comoros': 'KM',
        'cape verde': 'CV',
        
        # 北美洲国家
        'mexico': 'MX',
        'guatemala': 'GT',
        'belize': 'BZ',
        'el salvador': 'SV',
        'honduras': 'HN',
        'nicaragua': 'NI',
        'costa rica': 'CR',
        'panama': 'PA',
        
        # 南美洲国家
        'brazil': 'BR',
        'argentina': 'AR',
        'chile': 'CL',
        'peru': 'PE',
        'colombia': 'CO',
        'venezuela': 'VE',
        'ecuador': 'EC',
        'bolivia': 'BO',
        'paraguay': 'PY',
        'uruguay': 'UY',
        'guyana': 'GY',
        'suriname': 'SR',
        'french guiana': 'GF',
        
        # 加勒比海国家
        'cuba': 'CU',
        'jamaica': 'JM',
        'haiti': 'HT',
        'dominican republic': 'DO',
        'puerto rico': 'PR',
        'trinidad and tobago': 'TT',
        'barbados': 'BB',
        'bahamas': 'BS',
        'antigua and barbuda': 'AG',
        'saint lucia': 'LC',
        'grenada': 'GD',
        'saint vincent and the grenadines': 'VC',
        'dominica': 'DM',
        'saint kitts and nevis': 'KN',
        
        # 大洋洲国家
        'fiji': 'FJ',
        'papua new guinea': 'PG',
        'solomon islands': 'SB',
        'vanuatu': 'VU',
        'samoa': 'WS',
        'tonga': 'TO',
        'kiribati': 'KI',
        'tuvalu': 'TV',
        'nauru': 'NR',
        'palau': 'PW',
        'marshall islands': 'MH',
        'micronesia': 'FM',
        
        # 常见中文名称
        '中国': 'CN',
        '美国': 'US',
        '英国': 'GB',
        '法国': 'FR',
        '德国': 'DE',
        '日本': 'JP',
        '韩国': 'KR',
        '澳大利亚': 'AU',
        '加拿大': 'CA',
        '新西兰': 'NZ',
        '新加坡': 'SG',
        '马来西亚': 'MY',
        '泰国': 'TH',
        '印度': 'IN',
        '俄罗斯': 'RU',
        '意大利': 'IT',
        '西班牙': 'ES',
        '荷兰': 'NL',
        '瑞士': 'CH',
        '瑞典': 'SE',
        '挪威': 'NO',
        '丹麦': 'DK',
        '芬兰': 'FI',
        '巴西': 'BR',
        '阿根廷': 'AR',
        '墨西哥': 'MX'
    }
    
    # 提取国家（通常是最后一部分）
    if len(parts) >= 1:
        potential_country = parts[-1].lower().strip()
        if potential_country in country_mapping:
            result["addressCountry"] = country_mapping[potential_country]
            parts = parts[:-1]  # 从部分中移除国家
        elif len(potential_country) == 2 and potential_country.isalpha():
            # 假设它已经是国家代码
            result["addressCountry"] = potential_country.upper()
            parts = parts[:-1]
    
    # 从最后部分提取邮政编码和地区
    if len(parts) >= 2:
        # 美国格式："City", "STATE ZIP"
        state_zip_part = parts[-1].strip()
        city_part = parts[-2].strip()
        
        # 美国地址模式："STATE ZIP"
        us_pattern = r'^([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$'
        us_match = re.match(us_pattern, state_zip_part)
        
        if us_match:
            result["addressLocality"] = city_part
            result["addressRegion"] = us_match.group(1)
            result["postalCode"] = us_match.group(2)
            parts = parts[:-2]
        else:
            # Try single part format like "City STATE POSTCODE"
            last_part = parts[-1].strip()
            
            # 澳大利亚地址模式："City STATE POSTCODE"
            au_pattern = r'^(.+?)\s+([A-Z]{2,3})\s+(\d{4})$'
            au_match = re.match(au_pattern, last_part)
            
            if au_match:
                result["addressLocality"] = au_match.group(1).strip()
                result["addressRegion"] = au_match.group(2)
                result["postalCode"] = au_match.group(3)
                parts = parts[:-1]
            else:
                # 尝试从末尾提取邮政编码
                postal_pattern = r'(.+?)\s+(\d{3,6})$'
                postal_match = re.match(postal_pattern, last_part)
                
                if postal_match:
                    result["addressLocality"] = postal_match.group(1).strip()
                    result["postalCode"] = postal_match.group(2)
                    parts = parts[:-1]
                else:
                    # 如果没有找到邮政编码，则视为地区
                    result["addressLocality"] = last_part
                    parts = parts[:-1]
    elif len(parts) >= 1:
        # 剩余单个部分，尝试解析它
        last_part = parts[-1].strip()
        
        # 澳大利亚地址模式："City STATE POSTCODE"
        au_pattern = r'^(.+?)\s+([A-Z]{2,3})\s+(\d{4})$'
        au_match = re.match(au_pattern, last_part)
        
        if au_match:
            result["addressLocality"] = au_match.group(1).strip()
            result["addressRegion"] = au_match.group(2)
            result["postalCode"] = au_match.group(3)
            parts = parts[:-1]
        else:
            # 尝试从末尾提取邮政编码
            postal_pattern = r'(.+?)\s+(\d{3,6})$'
            postal_match = re.match(postal_pattern, last_part)
            
            if postal_match:
                result["addressLocality"] = postal_match.group(1).strip()
                result["postalCode"] = postal_match.group(2)
                parts = parts[:-1]
            else:
                # 如果没有找到邮政编码，则视为地区
                result["addressLocality"] = last_part
                parts = parts[:-1]
    
    # 提取街道地址（剩余部分）
    if parts:
        street_parts = []
        for part in parts:
            # 清理每个部分
            cleaned_part = part.strip()
            if cleaned_part:
                street_parts.append(cleaned_part)
        
        if street_parts:
            result["streetAddress"] = ", ".join(street_parts)
    
    # 清理空值
    result = {k: v for k, v in result.items() if v and v.strip()}
    
    # 确保@type始终存在
    if "@type" not in result:
        result["@type"] = "PostalAddress"
    
    return result