"""共享 pytest 配置。

每个微服务的 main.py 采用服务内相对导入（`from core import ...` / `import models`），
仅在 `services/<svc>/` 位于 sys.path 时可解析。因此各服务 conftest 通过
`load_service_main()` 以唯一模块名加载 main.py，并在加载前清理 sys.modules 中
陈旧的 `core` / `models` 缓存，保证多服务测试互不污染。

建议分别运行各服务测试（微服务天然隔离）：
    pytest tests/auth_service/ -v
    pytest tests/kb_service/   -v
"""
import os
import sys
import importlib.util

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_service_main(service_name: str, module_alias: str):
    """以唯一模块名加载 services/<service_name>/main.py。

    处理服务内相对导入：把服务目录加入 sys.path，并清理 sys.modules 中
    上一个服务残留的 core / models 缓存，确保本次加载的是本服务的 core。
    返回的 module 对象在加载时已绑定自身 core/models 引用，后续清理不影响它。
    """
    service_dir = os.path.abspath(os.path.join(PROJECT_ROOT, "services", service_name))
    if service_dir not in sys.path:
        sys.path.insert(0, service_dir)

    # 清理上一个服务可能残留的 intra-service 模块缓存
    for mod_name in list(sys.modules):
        if mod_name in ("core", "models") or mod_name.startswith("core.") or mod_name.startswith("models."):
            del sys.modules[mod_name]

    main_path = os.path.join(service_dir, "main.py")
    spec = importlib.util.spec_from_file_location(module_alias, main_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
