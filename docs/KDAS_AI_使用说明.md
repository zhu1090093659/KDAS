# KDAS智能分析系统使用说明

## 概述

KDAS智能分析系统是一个基于AI的证券技术分析工具，能够自动推荐KDAS（Key Date Average Settlement）关键日期并进行深度市场状态分析。

## 主要功能

1. **自动数据获取**: 根据证券代码自动获取历史价格数据
2. **AI日期推荐**: 使用大语言模型智能推荐5个最佳KDAS起始日期
3. **KDAS计算**: 自动计算累计成交量加权平均价格
4. **状态分析**: 基于KDAS理论进行深度市场状态分析
5. **批量处理**: 支持同时分析多个证券

## 快速开始

### 1. 单个证券分析

```python
from kdas_ai_advisor import analyze_security_kdas
import asyncio

async def main():
    result = await analyze_security_kdas(
        security_type="股票",      # 证券类型: "股票" 或 "ETF"
        symbol="000001",          # 证券代码
        api_key="your-api-key",   # AI API密钥
        model="deepseek-r1"       # AI模型 (可选)
    )
    
    if result['success']:
        print("✅ 分析成功!")
        print(f"证券名称: {result['security_info']['name']}")
        print(f"推荐日期: {result['recommended_dates']}")
        print(f"当前价格: ¥{result['data_summary']['current_price']:.3f}")
        
        # 查看推荐理由
        if result['recommendation']['success']:
            print(f"\n推荐理由:\n{result['recommendation']['reasoning']}")
        
        # 查看KDAS状态分析
        if result['analysis']['success']:
            print(f"\nKDAS状态分析:\n{result['analysis']['analysis']}")
    else:
        print(f"❌ 分析失败: {result['error']}")

# 运行分析
asyncio.run(main())
```

### 2. 批量证券分析

```python
from kdas_ai_advisor import batch_analyze_securities
import asyncio

async def batch_main():
    # 定义要分析的证券列表
    securities = [
        {"security_type": "股票", "symbol": "000001"},  # 平安银行
        {"security_type": "ETF", "symbol": "159915"},   # 创业板ETF
        {"security_type": "股票", "symbol": "000858"},  # 五粮液
    ]
    
    # 批量分析
    results = await batch_analyze_securities(securities, "your-api-key")
    
    # 处理结果
    for i, result in enumerate(results):
        security = securities[i]
        print(f"\n{i+1}. {security['security_type']} {security['symbol']}:")
        
        if result['success']:
            print(f"   ✅ {result['security_info']['name']}")
            print(f"   推荐日期: {result['recommended_dates']}")
            print(f"   当前价格: ¥{result['data_summary']['current_price']:.3f}")
        else:
            print(f"   ❌ 分析失败: {result['error']}")

# 运行批量分析
asyncio.run(batch_main())
```

## 返回结果结构

```python
{
    'success': True,                    # 分析是否成功
    'timestamp': '2025-01-XX XX:XX:XX', # 分析时间戳
    'security_info': {                  # 证券基本信息
        'symbol': '000001',
        'name': '平安银行',
        'type': '股票'
    },
    'recommended_dates': [              # AI推荐的5个关键日期
        '2024-09-24',
        '2024-11-07',
        '2024-12-17',
        '2025-04-07',
        '2025-04-23'
    ],
    'input_dates': {                    # 用于KDAS计算的日期格式
        'day1': '20240924',
        'day2': '20241107',
        'day3': '20241217',
        'day4': '20250407',
        'day5': '20250423'
    },
    'recommendation': {                 # 日期推荐详情
        'success': True,
        'dates': [...],
        'reasoning': '详细的推荐理由和技术依据',
        'confidence': 'high'            # 置信度: high/medium/low
    },
    'analysis': {                       # KDAS状态分析
        'success': True,
        'analysis': 'JSON格式的详细分析结果，包含状态判断、多空力量分析、交易建议等'
    },
    'data_summary': {                   # 数据摘要
        'total_records': 365,
        'date_range': '2024-01-01 至 2025-01-XX',
        'current_price': 12.345
    }
}
```

## 支持的证券类型

- **股票**: A股上市公司股票
- **ETF**: 交易型开放式指数基金

## 配置要求

### 1. API密钥
需要有效的AI API密钥，支持的模型包括：
- `deepseek-r1` (默认)
- `gpt-4`
- `gpt-3.5-turbo`
- 其他兼容OpenAI API的模型

### 2. 依赖库
```bash
pip install openai pandas numpy akshare streamlit
```

### 3. 网络要求
- 能够访问AI API服务
- 能够访问akshare数据源获取证券数据

## 使用示例

### 运行内置示例
```bash
python kdas_ai_advisor.py
```

### 运行测试脚本
```bash
python test_kdas_advisor.py
```

## 注意事项

1. **API密钥安全**: 请妥善保管您的API密钥，不要在代码中硬编码
2. **数据缓存**: 系统会自动缓存证券数据，首次运行可能需要较长时间
3. **异步调用**: 所有分析函数都是异步的，需要使用`await`调用
4. **网络稳定**: 确保网络连接稳定，避免数据获取失败
5. **代码格式**: 证券代码支持6位数字格式，如"000001"

## 错误处理

系统提供完善的错误处理机制：

- **API密钥无效**: 返回相应错误信息
- **证券代码不存在**: 自动处理并提示
- **网络连接问题**: 提供详细的错误描述
- **数据获取失败**: 包含具体的失败原因

## 技术支持

如果在使用过程中遇到问题，请检查：

1. API密钥是否有效
2. 网络连接是否正常
3. 证券代码是否正确
4. 依赖库是否正确安装

## 更新日志

- **v1.0**: 初始版本，支持基本的KDAS分析功能
- **v1.1**: 添加批量分析功能
- **v1.2**: 优化错误处理和用户体验 