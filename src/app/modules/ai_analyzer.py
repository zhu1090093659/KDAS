"""
AI分析模块 - KDAS证券分析工具

负责处理所有AI相关的功能，包括：
- AI智能推荐（日期推荐）
- AI状态分析（KDAS状态分析）
- 分析文本格式化和样式处理
- AI顾问实例管理
- 错误处理和备用方案

作者：KDAS团队
版本：2.0 (模块化重构版本)
"""

import os
import re
import json
import asyncio
import streamlit as st
from datetime import datetime, timedelta

# === KDAS包导入与初始化 ===
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from kdas import KDASAIAdvisor, KDASAnalyzer, get_ai_advisor, AIRecommendationEngine
    AI_ADVISOR_AVAILABLE = True
except ImportError:
    AI_ADVISOR_AVAILABLE = False
    KDASAIAdvisor = None
    KDASAnalyzer = None
    get_ai_advisor = None
    AIRecommendationEngine = None

class AIAnalysisManager:
    """AI分析管理器类，封装所有AI相关功能"""
    
    def __init__(self):
        """初始化AI分析管理器"""
        self.ai_available = AI_ADVISOR_AVAILABLE
        
        # 文本样式规则配置
        self.styling_rules = [
            ('多头', '🟢 **多头**'),
            ('空头', '🔴 **空头**'),
            ('支撑位', '🟢 **支撑位**'),
            ('压力位', '🔴 **压力位**'),
            ('阻力位', '🔴 **阻力位**'),
            ('突破', '⚡ **突破**'),
            ('趋势确认', '✅ **趋势确认**'),
            ('趋势反转', '🔄 **趋势反转**'),
            ('情绪宣泄', '😱 **情绪宣泄**'),
            ('震荡', '📊 **震荡**'),
            ('整理', '⏸️ **整理**'),
            ('风险', '⚠️ **风险**'),
            ('建议', '💡 **建议**'),
            ('策略', '🎯 **策略**'),
            ('关键位', '🔑 **关键位**'),
            ('收敛', '📐 **收敛**'),
            ('发散', '📏 **发散**'),
            ('观望', '👀 **观望**'),
            ('入场', '🚀 **入场**'),
            ('止损', '🛑 **止损**'),
            ('止盈', '✨ **止盈**'),
            ('KDAS', '📊 **KDAS**'),
            ('均线', '📈 **均线**'),
            ('多空力量', '⚖️ **多空力量**'),
            ('趋势行进', '📈 **趋势行进**'),
            ('趋势衰竭', '📉 **趋势衰竭**'),
            ('市场一致性', '🎯 **市场一致性**'),
            ('情绪积累', '📊 **情绪积累**'),
            ('盘整', '📊 **盘整**'),
            ('强势', '💪 **强势**'),
            ('弱势', '📉 **弱势**'),
            ('高位', '⬆️ **高位**'),
            ('低位', '⬇️ **低位**')
        ]
        
        # JSON字段映射配置
        self.field_mapping = {
            '状态': ('📊', 'KDAS状态分析'),
            '多空力量分析': ('⚖️', '多空力量对比'),
            '趋势方向判断': ('📈', '趋势方向判断'),
            '交易建议': ('💡', '交易策略建议'),
            '风险提示': ('⚠️', '风险评估提示'),
            '置信度': ('🎯', '分析置信度')
        }
        
        # 段落格式化图标配置
        self.paragraph_icons = {
            '1': '📊', '2': '⚖️', '3': '📈', 
            '4': '💡', '5': '🎯', '6': '⚠️'
        }
    
    def get_ai_advisor_instance(self, api_key, model):
        """获取AI顾问实例"""
        if not self.ai_available:
            return None
            
        try:
            # 使用kdas包的get_ai_advisor函数
            advisor = get_ai_advisor(api_key, model)
            return advisor
        except Exception as e:
            st.warning(f"创建AI顾问实例失败: {str(e)}")
            return None
    
    def generate_ai_recommendation(self, symbol, security_type, api_key, model, get_security_name_func, get_security_data_func):
        """
        生成AI日期推荐
        
        Args:
            symbol: 证券代码
            security_type: 证券类型
            api_key: API密钥
            model: AI模型
            get_security_name_func: 获取证券名称的函数
            get_security_data_func: 获取证券数据的函数
        """
        if not self.ai_available:
            return {
                'success': False,
                'error': 'AI功能不可用，请检查kdas包是否正确安装'
            }
        
        try:
            # 获取证券名称
            security_name = get_security_name_func(symbol, security_type)
            
            # 生成临时日期用于数据获取
            temp_dates = {f'day{i+1}': (datetime.now() - timedelta(days=30*i)).strftime('%Y%m%d') for i in range(5)}
            
            # 获取分析数据
            analysis_data = get_security_data_func(symbol, temp_dates, security_type)
            
            if analysis_data.empty:
                return {
                    'success': False,
                    'error': f'未找到该{security_type}的数据，请检查{security_type}代码是否正确'
                }
            
            ai_engine = AIRecommendationEngine(api_key, model)
            result = ai_engine.generate_kdas_recommendation(
                analysis_data, symbol, security_name, security_type
            )
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'AI推荐过程出现错误: {str(e)}'
            }
    
    def analyze_kdas_state_with_ai(self, processed_data, input_date, symbol, security_type, api_key, model, get_security_name_func):
        """
        使用AI分析KDAS状态
        
        Args:
            processed_data: 处理后的数据
            input_date: 输入日期
            symbol: 证券代码
            security_type: 证券类型
            api_key: API密钥
            model: AI模型
            get_security_name_func: 获取证券名称的函数
        """
        if not self.ai_available:
            return {
                'success': False,
                'error': 'AI功能不可用，请检查kdas包是否正确安装',
                'analysis': 'AI分析功能不可用'
            }
        
        try:
            # 获取证券名称
            security_name = get_security_name_func(symbol, security_type)
            
            analyzer = KDASAnalyzer(api_key, model)
            analysis_result = analyzer.analyze_kdas_state(
                processed_data, input_date, symbol, security_name, security_type
            )
            
            return analysis_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'AI分析过程出现错误: {str(e)}',
                'analysis': f'分析失败: {str(e)}'
            }
    
    def format_analysis_text(self, analysis_text):
        """统一的分析文本格式化函数，整合原有的多个格式化函数"""
        if not analysis_text or not analysis_text.strip():
            return "暂无分析内容"
        
        # 尝试从文本中提取JSON部分
        json_data = self._extract_json_from_text(analysis_text)
        
        if json_data:
            # 如果成功提取并解析JSON，则格式化展示
            return self._format_json_analysis(json_data)
        else:
            # 如果不是JSON格式，使用原有的文本格式化方法
            return self._format_plain_text_analysis(analysis_text)
    
    def _extract_json_from_text(self, text):
        """从文本中提取JSON部分并解析为字典"""
        try:
            # 方法1：尝试找到被```json包围的JSON
            json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
                return json.loads(json_str)
            
            # 方法2：尝试找到大括号包围的JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group().strip()
                return json.loads(json_str)
            
            # 方法3：尝试直接解析整个文本
            return json.loads(text.strip())
            
        except (json.JSONDecodeError, AttributeError):
            return None
    
    def _format_json_analysis(self, json_data):
        """格式化JSON格式的分析结果"""
        if not isinstance(json_data, dict):
            return "分析结果格式错误"
        
        formatted_content = []
        
        # 按预定义顺序展示字段
        for field_key, (icon, title) in self.field_mapping.items():
            if field_key in json_data:
                content = json_data[field_key]
                if content and str(content).strip():
                    # 格式化内容
                    formatted_content.append(f"#### {icon} {title}")
                    formatted_content.append("")
                    
                    # 应用文本样式
                    styled_content = self._apply_text_styling(str(content))
                    formatted_content.append(styled_content)
                    formatted_content.append("")  # 添加空行分隔
        
        # 处理其他未映射的字段
        for key, value in json_data.items():
            if key not in self.field_mapping and value and str(value).strip():
                formatted_content.append(f"#### 🔸 {key}")
                formatted_content.append("")
                styled_content = self._apply_text_styling(str(value))
                formatted_content.append(styled_content)
                formatted_content.append("")
        
        return '\n'.join(formatted_content)
    
    def _format_plain_text_analysis(self, analysis_text):
        """格式化普通文本格式的分析结果（保留原有逻辑）"""
        # 首先处理整体结构
        formatted_content = []
        
        # 按行分割并重新组织
        lines = analysis_text.split('\n')
        current_section = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_section:
                    # 处理当前积累的段落
                    section_text = ' '.join(current_section).strip()
                    if section_text:
                        formatted_content.append(self._format_paragraph(section_text))
                    current_section = []
                continue
            
            current_section.append(line)
        
        # 处理最后一个段落
        if current_section:
            section_text = ' '.join(current_section).strip()
            if section_text:
                formatted_content.append(self._format_paragraph(section_text))
        
        # 合并所有内容
        result = '\n\n'.join(formatted_content)
        
        # 全局样式优化
        result = self._apply_text_styling(result)
        
        return result
    
    def _format_paragraph(self, text):
        """格式化单个段落"""
        if not text.strip():
            return ""
        
        # 处理主要章节标题（如：1. **当前KDAS状态判断**）
        main_section_match = re.match(r'^(\d+)\.\s*\*\*(.*?)\*\*[:：]?(.*)', text)
        
        if main_section_match:
            num = main_section_match.group(1)
            title = main_section_match.group(2).strip()
            content = main_section_match.group(3).strip()
            
            icon = self.paragraph_icons.get(num, '🔸')
            
            result = f"#### {icon} {num}. {title}\n"
            if content:
                result += f"\n{content}"
            return result
        
        # 处理子标题（如：**多空力量分析**）
        subtitle_match = re.match(r'^\*\*(.*?)\*\*[:：]?(.*)', text)
        if subtitle_match:
            title = subtitle_match.group(1).strip()
            content = subtitle_match.group(2).strip()
            result = f"**🔸 {title}**"
            if content:
                result += f"\n\n{content}"
            return result
        
        # 处理引用内容
        if text.startswith('"') and text.endswith('"'):
            return f"> {text[1:-1]}"
        
        # 处理列表项
        if text.startswith('- '):
            return f"• {text[2:]}"
        
        # 处理普通段落
        return text
    
    def _apply_text_styling(self, text):
        """应用文本样式优化"""
        for old, new in self.styling_rules:
            # 只替换独立的词，避免重复替换
            text = re.sub(f'(?<!\\*){re.escape(old)}(?!\\*)', new, text)
        
        return text
    
    def run_integrated_analysis(self, security_type, symbol, api_key, model, manual_dates, get_security_name_func, get_security_data_func, calculate_cumulative_vwap_func):
        """
        运行集成的AI分析（包括日期推荐和状态分析）
        
        Args:
            security_type: 证券类型
            symbol: 证券代码
            api_key: API密钥
            model: AI模型
            manual_dates: 手动日期（备用）
            get_security_name_func: 获取证券名称的函数
            get_security_data_func: 获取证券数据的函数
            calculate_cumulative_vwap_func: 计算KDAS的函数
        """
        if not self.ai_available:
            return {
                'success': False,
                'error': 'AI功能不可用，请检查kdas包是否正确安装',
                'mode': 'ai_unavailable'
            }
        
        try:
            # 获取证券名称
            security_name = get_security_name_func(symbol, security_type)
            
            # 使用kdas包的集成功能
            advisor = self.get_ai_advisor_instance(api_key, model)
            if advisor is None:
                raise Exception("无法创建AI顾问实例")
            
            # 异步调用需要在同步函数中处理
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                kdas_result = loop.run_until_complete(
                    advisor.analyze_all_async(security_type, symbol, api_key, model)
                )
            finally:
                loop.close()
            
            if not kdas_result.get('success', False):
                # 如果AI分析失败，回退到手动模式
                if manual_dates:
                    df = get_security_data_func(symbol, manual_dates, security_type)
                    processed_data = calculate_cumulative_vwap_func(df, manual_dates)
                    
                    return {
                        'success': True,
                        'data': df,
                        'processed_data': processed_data,
                        'security_name': security_name,
                        'input_dates': manual_dates,
                        'recommendation_result': None,
                        'ai_analysis_result': None,
                        'mode': 'manual_fallback',
                        'ai_error': kdas_result.get('error', '未知错误')
                    }
                else:
                    return {
                        'success': False,
                        'error': f'AI分析失败: {kdas_result.get("error", "未知错误")}',
                        'mode': 'ai_failed'
                    }
            
            # 成功获得AI推荐，使用推荐的日期重新获取数据和计算KDAS
            recommended_dates_dict = kdas_result.get('input_dates', {})
            df = get_security_data_func(symbol, recommended_dates_dict, security_type)
            processed_data = calculate_cumulative_vwap_func(df, recommended_dates_dict)
            
            return {
                'success': True,
                'data': df,
                'processed_data': processed_data,
                'security_name': security_name,
                'input_dates': recommended_dates_dict,
                'recommendation_result': kdas_result.get('recommendation'),
                'ai_analysis_result': kdas_result.get('analysis'),
                'mode': 'ai_integrated',
                'recommended_dates': kdas_result.get('recommended_dates', [])
            }
            
        except Exception as e:
            # AI分析出错，如果有手动日期则回退
            if manual_dates:
                try:
                    security_name = get_security_name_func(symbol, security_type)
                    df = get_security_data_func(symbol, manual_dates, security_type)
                    processed_data = calculate_cumulative_vwap_func(df, manual_dates)
                    
                    return {
                        'success': True,
                        'data': df,
                        'processed_data': processed_data,
                        'security_name': security_name,
                        'input_dates': manual_dates,
                        'recommendation_result': None,
                        'ai_analysis_result': None,
                        'mode': 'manual_fallback',
                        'ai_error': str(e)
                    }
                except Exception as fallback_error:
                    return {
                        'success': False,
                        'error': f'AI分析失败且手动模式也失败: AI错误={str(e)}, 手动错误={str(fallback_error)}',
                        'mode': 'total_failure'
                    }
            else:
                return {
                    'success': False,
                    'error': f'AI集成分析失败: {str(e)}',
                    'mode': 'ai_failed'
                }

# === 全局AI分析管理器实例 ===
ai_manager = AIAnalysisManager()

# === 向后兼容的全局函数接口 ===
def get_ai_advisor_instance(api_key, model):
    """获取AI顾问实例 - 向后兼容接口"""
    return ai_manager.get_ai_advisor_instance(api_key, model)

def generate_ai_recommendation(symbol, security_type, api_key, model):
    """生成AI日期推荐 - 向后兼容接口"""
    # 需要导入数据处理函数
    from .data_handler import get_security_name, get_security_data
    return ai_manager.generate_ai_recommendation(symbol, security_type, api_key, model, get_security_name, get_security_data)

def analyze_kdas_state_with_ai(processed_data, input_date, symbol, security_type, api_key, model):
    """使用AI分析KDAS状态 - 向后兼容接口"""
    # 需要导入数据处理函数
    from .data_handler import get_security_name
    return ai_manager.analyze_kdas_state_with_ai(processed_data, input_date, symbol, security_type, api_key, model, get_security_name)

def format_analysis_text(analysis_text):
    """统一的分析文本格式化函数 - 向后兼容接口"""
    return ai_manager.format_analysis_text(analysis_text)

# === 内部函数的向后兼容接口 ===
def _extract_json_from_text(text):
    """从文本中提取JSON部分 - 向后兼容接口"""
    return ai_manager._extract_json_from_text(text)

def _format_json_analysis(json_data):
    """格式化JSON格式的分析结果 - 向后兼容接口"""
    return ai_manager._format_json_analysis(json_data)

def _format_plain_text_analysis(analysis_text):
    """格式化普通文本格式的分析结果 - 向后兼容接口"""
    return ai_manager._format_plain_text_analysis(analysis_text)

def _format_paragraph(text):
    """格式化单个段落 - 向后兼容接口"""
    return ai_manager._format_paragraph(text)

def _apply_text_styling(text):
    """应用文本样式优化 - 向后兼容接口"""
    return ai_manager._apply_text_styling(text)

# === AI可用性检查 ===
AI_ADVISOR_AVAILABLE = ai_manager.ai_available 