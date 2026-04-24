# AIRAGAgent 实时数据工具使用说明

## 功能概述

本项目已成功集成了实时数据获取功能，包括：
- 🌤️ **实时天气查询** - 获取指定城市的当前天气状况
- 📍 **实时位置定位** - 获取用户的地理位置信息  
- ⏰ **实时时间获取** - 获取准确的当前时间和日期

## 技术架构

### 核心组件

1. **`utils/api_tools.py`** - API工具模块
   - 统一封装外部API调用
   - 实现异常处理和优雅降级机制
   - 提供数据格式化功能

2. **`agent/tools/agent_tools.py`** - Agent工具模块
   - 包含可供Agent调用的工具函数
   - 集成实时数据工具
   - 保持向后兼容性

3. **配置文件** - `config/agent.yml`
   - API配置参数
   - 工具启用配置
   - 降级策略设置

## 使用方法

### 1. 天气查询工具
```python
from AIRAGAgent.agent.tools.agent_tools import get_weather

# 查询北京天气
weather_info = get_weather("北京")
print(weather_info)
```

### 2. 位置获取工具
```python
from AIRAGAgent.agent.tools.agent_tools import get_user_location

# 获取用户当前位置
location_info = get_user_location()
print(location_info)
```

### 3. 时间获取工具
```python
from AIRAGAgent.agent.tools.agent_tools import get_current_time

# 获取当前时间信息
time_info = get_current_time()
print(time_info)
```

## API详情

### 天气API (`wttr.in`)
- **功能**：获取全球城市天气信息
- **返回数据**：温度、湿度、风速、气压、能见度等
- **格式**：JSON格式，自动解析为易读文本

### 位置API (`ip-api.com`)  
- **功能**：基于IP地址获取地理位置
- **返回数据**：城市、国家、地区、经纬度、时区等
- **精度**：基于网络IP定位，精度约为城市级别

## 优雅降级机制

当外部API不可用时，系统会自动切换到模拟数据模式：

1. **网络异常检测** - 自动捕获请求超时、连接失败等异常
2. **模拟数据生成** - 提供合理的随机模拟数据
3. **用户友好提示** - 明确标识数据来源（实时/模拟）
4. **日志记录** - 记录降级事件便于监控

### 降级示例
```
城市：北京
天气：晴天
温度：26°C (体感温度：24°C)
湿度：45%
风速：3 km/h
气压：1015 hPa
能见度：12 km
更新时间：2026-02-11 20:30:15 (模拟数据)
```

## 测试验证

### 运行测试脚本
```bash
cd AIRAGAgent
python test_realtime_tools.py
```

### 测试内容包括
- ✅ API连通性测试
- ✅ 工具函数功能验证  
- ✅ 多城市并发查询测试
- ✅ 优雅降级机制验证

## 配置说明

### 主要配置项 (`config/agent.yml`)

```yaml
realtime_api:
  weather:
    base_url: http://wttr.in
    timeout: 5          # 请求超时时间(秒)
    max_retries: 3      # 最大重试次数
  
  location:
    base_url: http://ip-api.com/json
    timeout: 5
    max_retries: 3
    
  degradation:
    enable: true                    # 是否启用降级机制
    mock_data_probability: 0.1      # 模拟数据使用概率
```

## 注意事项

### 网络要求
- 需要能够访问外部API服务
- 建议配置适当的网络代理（如需要）

### 性能考虑
- 设置了合理的超时时间避免阻塞
- 实现了重试机制提高成功率
- 缓存机制减少重复请求

### 安全建议
- 生产环境中建议使用HTTPS API
- 可配置API密钥认证
- 建议添加请求频率限制

## 故障排除

### 常见问题

1. **API请求失败**
   - 检查网络连接
   - 验证防火墙设置
   - 查看日志文件

2. **数据格式异常**
   - 检查API响应格式是否变更
   - 更新解析逻辑
   - 验证降级数据格式

3. **性能问题**
   - 调整超时设置
   - 优化重试策略
   - 考虑添加缓存层

### 日志查看
```python
from AIRAGAgent.utils.logger_handler import logger

# 查看详细日志信息
logger.info("实时工具调用详情")
```

## 扩展建议

### 可添加的功能
- 📱 手机号码归属地查询
- 💰 汇率实时查询
- 📈 股票价格查询
- 🌍 多语言翻译服务
- 🔍 搜索引擎集成

### 架构优化
- 添加缓存层提高响应速度
- 实现批量API调用
- 增加异步处理能力
- 完善监控告警机制

---
*本文档最后更新：2026-02-11*