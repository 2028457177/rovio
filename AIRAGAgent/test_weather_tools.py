#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
天气工具测试脚本
验证get_weather和get_user_location工具的功能和优雅降级机制
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from AIRAGAgent.agent.tools.agent_tools import get_weather, get_user_location
from AIRAGAgent.utils.logger_handler import logger

def test_weather_tool():
    """测试天气查询工具"""
    print("=" * 50)
    print("测试天气查询工具")
    print("=" * 50)
    
    # 测试多个城市
    test_cities = ["北京", "上海", "广州", "深圳", "杭州"]
    
    for city in test_cities:
        print(f"\n📍 查询城市: {city}")
        try:
            result = get_weather(city)
            print(result)
            print("-" * 30)
        except Exception as e:
            print(f"❌ 查询失败: {e}")

def test_location_tool():
    """测试位置获取工具"""
    print("\n" + "=" * 50)
    print("测试位置获取工具")
    print("=" * 50)
    
    try:
        location = get_user_location()
        print(f"📍 当前位置: {location}")
    except Exception as e:
        print(f"❌ 获取位置失败: {e}")

def test_degradation_mechanism():
    """测试优雅降级机制"""
    print("\n" + "=" * 50)
    print("测试优雅降级机制")
    print("=" * 50)
    
    # 测试不存在的城市（应该触发降级）
    fake_city = "不存在的城市123"
    print(f"📍 查询不存在的城市: {fake_city}")
    
    try:
        result = get_weather(fake_city)
        print(result)
        # 检查是否包含"模拟数据"标识
        if "模拟数据" in result:
            print("✅ 优雅降级机制正常工作")
        else:
            print("⚠️  未检测到模拟数据标识")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def main():
    """主测试函数"""
    print("🤖 开始测试天气相关工具...")
    
    # 测试天气查询
    test_weather_tool()
    
    # 测试位置获取
    test_location_tool()
    
    # 测试降级机制
    test_degradation_mechanism()
    
    print("\n" + "=" * 50)
    print("✅ 所有测试完成!")
    print("=" * 50)

if __name__ == "__main__":
    main()