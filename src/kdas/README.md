# KDAS智能分析系统

KDAS (Key Date Average Settlement) 是一个基于AI的证券技术分析和交易体系分析工具包。

## 📋 主要功能

- 🤖 **AI智能推荐** - 基于技术分析智能推荐KDAS关键日期
- 📊 **技术指标分析** - 综合价格、成交量、趋势等多维度分析
- 📈 **KDAS状态分析** - 深度分析当前KDAS交易状态和策略建议
- 🔄 **异步批量处理** - 支持多个证券的并发分析
- 💹 **多证券类型** - 支持股票、ETF等各类证券

## 🚀 快速开始

### 安装

```bash
pip install kdas
```

### 基本使用

```python
import asyncio
from kdas import analyze_security_kdas, batch_analyze_securities

# 单个证券分析
async def main():
    result = await analyze_security_kdas(
        security_type="股票",
        symbol="000001", 
        api_key="your-api-key"
    )
    
    if result['success']:
        print("推荐日期:", result['recommended_dates'])
        print("分析结果:", result['analysis'])
    else:
        print("分析失败:", result['error'])

asyncio.run(main())

# 批量分析
async def batch_main():
    securities = [
        {"security_type": "股票", "symbol": "000001"},
        {"security_type": "ETF", "symbol": "159915"}
    ]
    
    results = await batch_analyze_securities(securities, "your-api-key")
    for result in results:
        if result['success']:
            print(f"{result['security_info']['name']}: {result['recommended_dates']}")

asyncio.run(batch_main())
```

### 命令行使用

```bash
# 分析单个证券
kdas-analyze --api-key YOUR_API_KEY analyze 股票 000001

# 批量分析（从文件）
kdas-analyze --api-key YOUR_API_KEY batch --file securities.json

# 保存结果到文件
kdas-analyze --api-key YOUR_API_KEY analyze 股票 000001 --output result.json
```

## 📦 模块结构

```
kdas/
├── __init__.py           # 包初始化和公共API
├── advisor.py            # 主控制器
├── utils.py              # 工具函数
├── technical_analysis.py # 技术分析模块
├── ai_recommendation.py  # AI推荐引擎
├── kdas_analysis.py      # KDAS状态分析
├── data_handler.py       # 数据处理模块
└── cli.py               # 命令行接口
```

## 🔧 高级使用

### 使用特定组件

```python
from kdas import TechnicalAnalyzer, AIRecommendationEngine, KDASAnalyzer

# 技术分析
analyzer = TechnicalAnalyzer()
technical_data = analyzer.analyze_technical_indicators(df)

# AI推荐
ai_engine = AIRecommendationEngine(api_key="your-key")
recommendation = await ai_engine.generate_kdas_recommendation_async(
    df, symbol, name, security_type
)

# KDAS分析
kdas_analyzer = KDASAnalyzer(api_key="your-key")
analysis = await kdas_analyzer.analyze_kdas_state_async(
    df, input_dates, symbol, name, security_type
)
```

### 自定义配置

```python
from kdas import KDASAIAdvisor

# 创建自定义顾问实例
advisor = KDASAIAdvisor(
    api_key="your-api-key",
    model="gpt-4"  # 使用不同的AI模型
)

result = await advisor.analyze_all_async("股票", "000001", "your-api-key")
```

## 📊 返回结果结构

```python
{
    'success': True/False,
    'security_info': {
        'symbol': '证券代码',
        'name': '证券名称', 
        'type': '证券类型'
    },
    'recommended_dates': ['2024-01-01', '2024-02-01', ...],  # AI推荐的5个日期
    'input_dates': {'day1': '20240101', ...},  # 用于KDAS计算的日期格式
    'recommendation': {  # 日期推荐详情
        'success': True,
        'dates': [...],
        'reasoning': '推荐理由',
        'confidence': 'high/medium/low'
    },
    'analysis': {  # KDAS状态分析
        'success': True,
        'analysis': 'JSON格式的详细分析结果'
    },
    'data_summary': {
        'total_records': 数据条数,
        'date_range': '数据时间范围',
        'current_price': 当前价格
    }
}
```

## ⚙️ 配置要求

### 依赖包

- pandas >= 1.3.0
- numpy >= 1.20.0
- openai >= 1.0.0
- streamlit >= 1.0.0
- akshare >= 1.8.0

### API配置

需要配置OpenAI兼容的API密钥：

```python
import os
os.environ['OPENAI_API_KEY'] = 'your-api-key'
```

## 📝 注意事项

1. 需要有效的AI API密钥
2. 需要安装akshare库用于获取证券数据
3. 首次运行会下载证券基础信息，可能需要一些时间
4. 支持的证券类型：股票、ETF
5. 所有分析函数都是异步的，需要使用await调用

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 👥 作者

KDAS Team 