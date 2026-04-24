from langchain_core.tools import tool
import os
from langchain_community.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv

load_dotenv()

search_tool = TavilySearchResults(
    tavily_api_key=os.getenv("TAVILY_API_KEY"),
    max_results = 1,
    topic = "general",
    search_depth = "basic",
    include_raw_content = False,
    include_answer = True,
    include_images = False
)

@tool(description="根据用户需求联网搜索相应内容")
def search(content:str):
    result = search_tool.invoke(content)
    return result


if __name__ == '__main__':
    print(search("老弟的压压是什么梗"))
