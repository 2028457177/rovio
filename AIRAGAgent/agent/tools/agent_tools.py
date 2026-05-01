import os
import re
import random
from datetime import datetime, timedelta

import docx
import requests
from typing import List, Dict, Any, Union
import pandas as pd
from datetime import date, datetime
from langchain_core.tools import tool
from AIRAGAgent.utils.config_handler import rag_conf
from AIRAGAgent.utils.logger_handler import logger
from AIRAGAgent.rag.rag_service import RagSummarizeService
from AIRAGAgent.utils.config_handler import agent_conf
from AIRAGAgent.utils.path_tool import get_abs_path

_rag_instance = None

def _get_rag():
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RagSummarizeService()
    return _rag_instance

user_ids = ["1001","1002","1003","1004","1005","1006","1007","1008","1009","1010",]

# month_arr = ["2025-01","2025-02","2025-03","2025-04","2025-05","2025-06","2025-07","2025-08","2025-09","2025-10","2025-11","2025-12"]


external_data = {}

@tool(description="从向量存储中检索参考资料")
def rag_summarize(query: str) -> str:
    return _get_rag().rag_summarize(query)


@tool(description="将城市名以城市编码的形式传入，获取指定城市的天气信息")
def get_weather(code: str) -> dict[str, Any]:
    """
    获取未来几天的天气预报
    :param code: 城市编码
    :return: 天气预报信息字典
    """
    key = rag_conf["gaode_api_key"]
    city_code = code

    # 使用extensions=all获取预报天气
    url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={key}&city={city_code}&extensions=all"

    response = requests.get(url, timeout=10)

    if response.status_code == 200:
        result = response.json()
        if result["status"] == "1":
            # 获取预报数据（完全按照你给的JSON结构）
            forecast_data = result["forecasts"][0]

            # 构建天气预报信息字典
            weather_info = {
                '查询时间': forecast_data['reporttime'],
                '地点': forecast_data['province'],
                '城市': forecast_data['city'],
                '城市编码': forecast_data['adcode'],
                '天气预报': []
            }

            # 遍历未来几天的预报（casts数组）
            for cast in forecast_data['casts']:
                daily_forecast = {
                    '日期': cast['date'],
                    #'星期': cast['week'],
                    '白天天气': cast['dayweather'],
                    '夜晚天气': cast['nightweather'],
                    '白天温度': float(cast['daytemp']),
                    '夜晚温度': float(cast['nighttemp']),
                    '白天风向': cast['daywind'],
                    '夜晚风向': cast['nightwind'],
                    '白天风力': cast['daypower'],
                    '夜晚风力': cast['nightpower']
                }
                weather_info['天气预报'].append(daily_forecast)

            return weather_info['天气预报']
        else:
            return {'error': f"API 返回错误：{result['info']}"}
    else:
        return {'error': f"请求失败，HTTP 状态码：{response.status_code}"}


@tool(description="获取用户所在城市信息，以纯字符串形式返回")
def get_user_location()-> Any | None:
    """
        通过 IP 地址获取当前位置的省市信息
        返回格式：某某省某某市（字符串）
    """
    try:
        # 使用高德地图 API 通过 IP 获取地理位置信息
        key = rag_conf["gaode_api_key"]
        url = f"https://restapi.amap.com/v3/ip?&output=json&key={key}"

        response = requests.get(url, timeout=5)
        data = response.json()

        if data.get('status') == '1':
            province = data.get('province', '')
            city = data.get('city', '')

            # 直接返回字符串格式：某某省某某市
            return f"{province}{city}"
        else:
            return "未知位置"

    except Exception :
        return "获取失败"



@tool(description="获取用户的ID，以纯字符串形式返回")
def get_user_id()->str:
    return random.choice(user_ids)

@tool(description="wantday 作为用户想查询的日期与当前日期相差的天数，如明天是 1 后天是 2，大后天是 3，以此类推，如果是查看当天的日期则为 0")
def get_current_month(wantday:int)-> dict:
    now = datetime.now()
    target_date = now + timedelta(days=wantday)
    want_date_str = target_date.strftime("%Y-%m-%d")

    start_date = datetime.strptime("2026-03-09", "%Y-%m-%d")
    diff_days = (target_date - start_date).days
    week_number = (diff_days // 7) + 1

    # 获取星期几的中文名
    weekday_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期天"]
    weekday = weekday_cn[target_date.weekday()]  # Monday=0, Sunday=6

    return {
        "date": want_date_str,
        "week": week_number,
        "day": weekday
    }

def generate_external_data():
    """
    {
        “user_id":{
            "month":{"特征":XXX，"效率":XXX，...}
            "month":{"特征":XXX，"效率":XXX，...}
            "month":{"特征":XXX，"效率":XXX，...}
            ...
        },
        “user_id":{
            "month":{"特征":XXX，"效率":XXX，...}
            "month":{"特征":XXX，"效率":XXX，...}
            "month":{"特征":XXX，"效率":XXX，...}
            ...
        },
        “user_id":{
            "month":{"特征":XXX，"效率":XXX，...}
            "month":{"特征":XXX，"效率":XXX，...}
            "month":{"特征":XXX，"效率":XXX，...}
            ...
        },
        ...
    }
    :return:
    """
    if not external_data:
        external_data_path = get_abs_path(agent_conf["external_data_path"])
        if not os.path.exists(external_data_path):
            raise FileNotFoundError(f"外部数据文件,{external_data_path}不存在。")

        with open(external_data_path,"r",encoding="utf-8") as f:
            for line in f.readlines()[1:]:
                arr: list[str] = line.strip().split(",")

                user_id: str = arr[0].replace('"',"")
                feature: str = arr[1].replace('"', "")
                efficiency: str = arr[2].replace('"', "")
                consumables: str = arr[3].replace('"', "")
                comparison: str = arr[4].replace('"', "")
                time: str = arr[5].replace('"', "")

                if user_id not in external_data:
                    external_data[user_id] = {}

                external_data[user_id][time] = {
                    "特征":feature,
                    "效率":efficiency,
                    "耗材":consumables,
                    "对比":comparison,
                }


@tool(description="从外部系统中获取用户的使用记录，以春字符串形式返回，如果未检索到返回空字符串")
def fetch_external_data(user_id:str,month:str)->str:
    generate_external_data()

    try:
        return external_data[user_id][month]
    except KeyError:
        logger.warning(f"[fetch_external_data],未能检索到用户:{user_id}在{month}的使用记录数据")
        return  ""


@tool(description="无入参，无返回值，调用后触发中间件自动为报告生成的场景动态注入，为后续提示词切换提供上下文信息")
def fill_context_for_report():
    return "fill_context_for_report己调用"



@tool(description="week表示学期的周传入1-7，表示周一到周日。day表示星期几传入字符串如“星期一”。")
def get_schedule(week: int, day: str, file_path: str = None) -> List[Dict[str, Any]]:
    """
    从课表Excel文件中查询指定周次和星期几的课程

    Args:
        week: 周次（整数，如1表示第1周）
        day: 星期几（字符串，如"星期一"、"星期二"等）
        file_path: Excel文件路径（可选，默认使用预设路径）

    Returns:
        课程信息列表，每个课程包含：时间段、课程名、节次、地点、属性等
    """
    # 使用默认文件路径或传入的路径
    if file_path is None:
        file = "C:/Users/nxt/Desktop/24级土木1班课表-2025-2026-2.xlsx"
    else:
        file = file_path
    # ========== 1. 辅助函数：解析周次字符串 ==========
    def _parse_weeks(week_str: str, week_type: str) -> List[int]:
        """
        解析周次字符串，生成具体的周次列表
        :param week_str: 如 "1-4,6-8,10"
        :param week_type: "周"、"单周" 或 "双周"
        :return: 排序后的周次列表
        """
        weeks_set = set()
        parts = week_str.split(',')
        for part in parts:
            if '-' in part:
                start, end = map(int, part.split('-'))
                weeks_set.update(range(start, end + 1))
            else:
                weeks_set.add(int(part))

        if week_type == '单周':
            weeks_set = {w for w in weeks_set if w % 2 == 1}
        elif week_type == '双周':
            weeks_set = {w for w in weeks_set if w % 2 == 0}

        return sorted(weeks_set)

    # ========== 2. 辅助函数：解析单元格内容 ==========
    def _parse_course_cell(cell_text: str) -> List[Dict[str, Any]]:
        """
        解析一个单元格内的所有课程（可能有多行）
        :param cell_text: 单元格原始文本
        :return: 课程信息列表
        """
        courses = []
        # 将 <br> 替换为换行符，并按行分割
        lines = cell_text.replace('<br>', '\n').split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 按 ◇ 分割，标准格式应有三个部分
            parts = line.split('◇')
            if len(parts) < 3:
                # 格式异常，跳过
                continue

            course_info = parts[0].strip()
            week_section = parts[1].strip()
            location = parts[2].strip()

            # 提取课程名（第一个 '[' 之前的内容）
            name = course_info.split('[')[0].strip()

            # 提取所有属性（中括号内的内容）
            attributes = re.findall(r'\[(.*?)\]', course_info)

            # 解析周次信息
            week_match = re.search(r'([\d,\-]+)\((周|单周|双周)\)', week_section)
            if week_match:
                week_str = week_match.group(1)
                week_type = week_match.group(2)
                weeks = _parse_weeks(week_str, week_type)
            else:
                weeks = []  # 无法解析，可能没有周次信息

            # 解析节次
            section_match = re.search(r'\[(\d{2})-(\d{2})节\]', week_section)
            if section_match:
                start_section = int(section_match.group(1))
                end_section = int(section_match.group(2))
            else:
                start_section = end_section = None

            courses.append({
                'name': name,
                'attributes': attributes,
                'weeks': weeks,
                'start_section': start_section,
                'end_section': end_section,
                'location': location,
                'raw': line
            })

        return courses

    # ========== 3. 辅助函数：格式化输出 ==========
    def _format_results(results: List[Dict[str, Any]]) -> str:
        """
        将查询结果格式化为易读的字符串
        """
        if not results:
            return "该时间段没有课程。"

        output = []
        output.append(f"找到 {len(results)} 门课程：")
        for i, r in enumerate(results, 1):
            output.append(f"\n--- 课程 {i} ---")
            output.append(f"时间段：{r['时间段']}")
            output.append(f"课程名：{r['课程名']}")
            output.append(f"节次：{r['节次']}")
            output.append(f"地点：{r['地点']}")
            output.append(f"属性：{', '.join(r['属性'])}")

        return '\n'.join(output)

    # ========== 4. 主查询逻辑 ==========

    # 星期映射（确保与表格列名一致）
    day_to_col = {
        '星期一': '星期一',
        '星期二': '星期二',
        '星期三': '星期三',
        '星期四': '星期四',
        '星期五': '星期五',
        '星期六': '星期六',
        '星期天': '星期天'
    }

    # 输入验证
    if day not in day_to_col:
        error_msg = f"错误：星期输入应为 {list(day_to_col.keys())} 之一"
        print(error_msg)
        return []

    try:
        # 读取Excel，跳过前两行，第三行作为列名，第一列作为行索引（时间段）
        df = pd.read_excel(file, header=2, index_col=0, sheet_name=0)
    except FileNotFoundError:
        print(f"错误：找不到文件 '{file}'")
        return []
    except Exception as e:
        print(f"读取文件失败：{e}")
        return []

    # 确保列名正确（去除可能的空格）
    df.columns = df.columns.str.strip()
    if day not in df.columns:
        print(f"错误：表格中找不到列 '{day}'")
        return []

    # 获取指定列的数据
    day_series = df[day]
    results = []

    # 遍历每个时间段（行）
    for time_slot, cell in day_series.items():
        if pd.isna(cell):
            continue

        # 解析该单元格中的所有课程
        courses = _parse_course_cell(str(cell))

        # 筛选出当前周有课的课程
        for course in courses:
            if week in course['weeks']:
                results.append({
                    '时间段': time_slot,
                    '课程名': course['name'],
                    '节次': f"{course['start_section']}-{course['end_section']}节" if course[
                        'start_section'] else '未知',
                    '地点': course['location'],
                    '属性': course['attributes'],
                    '原始信息': course['raw']  # 包含原始数据，方便调试
                })

    # 可以选择是否打印结果
    # print(_format_results(results))

    # 如果没有找到课程，返回友好的提示信息
    if not results:
        print(f"第{week}周{day}没有课程安排")
    
    return results