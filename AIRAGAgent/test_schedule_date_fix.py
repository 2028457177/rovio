"""
测试课表查询日期转换修复
验证 get_schedule 函数能否正确处理日期字符串
"""
from AIRAGAgent.agent.tools.agent_tools import get_schedule

# 测试 1: 直接使用星期几数字（原有功能）
print("=" * 60)
print("测试 1: 使用星期几数字（原有功能）")
print("=" * 60)
result = get_schedule(3)  # 星期三
print(result)
print()

# 测试 2: 使用日期字符串（新功能）- 这是修复的关键
print("=" * 60)
print("测试 2: 使用日期字符串（新功能）- 模拟明天的课")
print("=" * 60)
# 假设今天是 2026-03-17（周二），明天是 2026-03-18（周三）
# get_current_month 会返回 "2026-03-18 开学第 X 周"
test_date_str = "2026-03-18 开学第 2 周"
result = get_schedule(test_date_str)
print(f"传入日期：{test_date_str}")
print(result)
print()

# 测试 3: 使用纯日期字符串
print("=" * 60)
print("测试 3: 使用纯日期字符串")
print("=" * 60)
test_date_str2 = "2026-03-18"
result = get_schedule(test_date_str2)
print(f"传入日期：{test_date_str2}")
print(result)
print()

# 测试 4: 错误处理 - 无效日期格式
print("=" * 60)
print("测试 4: 错误处理 - 无效日期格式")
print("=" * 60)
test_invalid = "invalid-date"
result = get_schedule(test_invalid)
print(f"传入日期：{test_invalid}")
print(result)
print()

print("=" * 60)
print("所有测试完成！")
print("=" * 60)
