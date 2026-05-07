import time
from langchain_core.tools import tool


@tool(description="给指定微信联系人发送指定内容的消息。需要微信桌面版已登录并打开。")
def send_wx_message(contact_name: str, message: str) -> str:
    """
    通过微信桌面版向指定联系人发送消息

    Args:
        contact_name: 微信联系人的昵称或备注名（用于搜索定位）
        message: 要发送的消息内容，支持中文

    Returns:
        发送结果信息
    """
    try:
        import uiautomation as auto

        wx_window = auto.WindowControl(Name="微信", ClassName="WeChatMainWndForPC")

        if not wx_window.Exists(timeout=1):
            return "未找到微信窗口，请确保微信桌面版已登录并打开"

        wx_window.SetActive()
        wx_window.MoveToTop()
        time.sleep(0.3)

        wx_window.SendKeys("{Ctrl}f")
        time.sleep(0.3)

        wx_window.SendKeys(contact_name)
        time.sleep(0.5)

        wx_window.SendKeys("{Enter}")
        time.sleep(0.4)

        auto.SetClipboardText(message)
        time.sleep(0.1)
        wx_window.SendKeys("{Ctrl}v")
        time.sleep(0.2)

        wx_window.SendKeys("{Enter}")
        time.sleep(0.2)

        return f"已成功向联系人 '{contact_name}' 发送消息"
    except Exception as e:
        return f"发送失败：{str(e)}"
