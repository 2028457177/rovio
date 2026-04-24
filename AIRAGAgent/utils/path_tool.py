"""
为整个项目提供统一的绝对路径
"""
import os


def get_project_root():
    """
    获取项目根目录
    :return:
    """
    # 获取当前文件绝对路径
    current_file = os.path.abspath(__file__)
    # 获取文件所在的文件夹绝对路径
    current_dir = os.path.dirname(current_file)
    #获取项目的根目录
    project_root = os.path.dirname(current_dir)
    return project_root


def get_abs_path(relative_path:str)->str:
    """
    获取绝对路径
    :param relative_path: 相对路径
    :return:
    """
    # 获取项目根目录
    project_root = get_project_root()
    # 获取绝对路径
    abs_path = os.path.join(project_root, relative_path)
    return abs_path

if __name__ == '__main__':
    print(get_abs_path("config/config.txt"))