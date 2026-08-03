# Rovio · 多智能体协同自动化办公助手

基于 **微服务 + Supervisor-Worker 多智能体编排** 的自动化办公助手。用户一句话即可触发"规划 → 多 Agent 并行执行 → 反思修订 → 汇总"的完整工作流，集成 RAG 知识库、联网搜索、代码沙箱、网页抓取、产物管理、长期记忆等能力，全程流式可观测。

---

## 一、架构总览

```
                              ┌──────────────────────────────────────┐
                              │           前端  Vue 3 + Vite          │
                              │  ChatView / KbManager / AdminView ... │
                              └───────────────────┬──────────────────┘
                                                  │  /api/*  (SSE 流式)
                                                  ▼
                                          ┌───────────────┐
                                          │     Nginx     │  按 URL 前缀路由 + gzip
                                          └───────┬───────┘
                ┌─────────────────────────┼─────────────────────────────────┐
                ▼                         ▼                                 ▼
        ┌──────────────┐         ┌──────────────────┐               ┌──────────────┐
        │ auth_service │         │  chat_service    │               │  kb_service  │
        │   :8001      │         │     :8003       │               │    :8004     │
        │ JWT 签发/校验 │         │  Orchestrator    │               │ 多知识库 RAG │
        │ 注册/登录/找回│         │  Supervisor 入口  │               │ 文档索引/检索│
        └──────┬───────┘         └────────┬─────────┘               └──────┬───────┘
               │                          │                                │
               │                  ┌───────┴────────────────────────┐       │
               │                  ▼                                ▼       │
        ┌──────┴───────┐  ┌──────────────────┐            ┌──────────────┐ │
        │ user_service │  │   AIRAGAgent     │            │ file_service │ │
        │   :8002      │  │  Orchestrator +  │            │    :8006     │ │
        │ 用户档案/会话 │  │  SubAgent Workers│            │ 文件上传/下载 │ │
        └──────────────┘  └────────┬─────────┘            └──────────────┘ │
                                  │                                         │
                                  ▼                                         ▼
                        ┌─────────────────────┐                  ┌──────────────────┐
                        │  admin_service      │ ◀── Redis PubSub │  ChromaDB        │
                        │     :8005           │     事件聚合      │  (kb 向量存储)   │
                        │ 统计/审计/限流       │                  └──────────────────┘
                        └─────────────────────┘

  ── 每个微服务独立 MySQL 库 (lc_auth / lc_user / lc_chat / lc_kb / lc_admin) ──
```

### Supervisor-Worker 多智能体编排（chat_service 内）

```
POST /api/chat  ──→  Orchestrator.execute_stream()

   ┌──────────────────────────────────────────────────────────────┐
   │  1. Planner 规划器   (流式 reasoning_content → 解析 JSON 计划) │
   │     • 召回长期记忆注入上下文                                    │
   │     • 输出 PlanSpec → 持久化 plans + plan_steps 表              │
   │     • 闲聊 1 步无 SubAgent；独立子任务并行；有依赖加 depends_on │
   └──────────────────────────────────────────────────────────────┘
                                ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  2. Executor + Reflector 主循环  (while not plan.is_all_done) │
   │     get_ready_steps()  ← 依赖感知调度                          │
   │     ├─ 单 ready: _execute_step → _reflect                     │
   │     │    ├─ subagent 空  → Orchestrator LLM 直接回答           │
   │     │    └─ subagent 非空 → SubAgentRunner.execute_stream      │
   │     └─ 多 ready: _execute_steps_parallel  (ThreadPool max=5)  │
   │                                                                │
   │     Reflector.action:  accept │ retry(≤1) │ revise(≤2) │ ask_user│
   └──────────────────────────────────────────────────────────────┘
                                ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  3. Finalizer 汇总器   (单步复用 / 多步 LLM 整合)              │
   │     • 每步结果落盘 tasks/<plan_id>/plan_results/step_<idx>.md │
   │     • 下游 step 任务描述注入前序步骤文件路径 + 摘要           │
   └──────────────────────────────────────────────────────────────┘
                                ▼
                   SSE:  thinking / plan_created / step_* /
                         plan_reflecting / plan_revised / plan_completed
```

### 内置 SubAgent Worker 清单（10 个）

| category   | name     | 能力                              | 典型工具链                                       |
|------------|----------|-----------------------------------|---------------------------------------------------|
| domain     | weather  | 天气查询                          | get_user_location → get_city_code → get_weather   |
| domain     | schedule | 课表/日程查询                     | get_current_month → get_schedule                  |
| domain     | report   | 工作报告生成                      | fetch_external_data → create_artifact             |
| domain     | knowledge| 知识库检索                        | rag_summarize                                     |
| domain     | document | Word 文档自动填充                 | auto_fill_word                                    |
| domain     | search   | 联网搜索                          | search (Tavily)                                   |
| builtin    | codexec  | 代码执行沙箱 (Python / shell)    | run_python_code / run_shell_command / install_package |
| builtin    | browser  | 网页抓取 (含真实浏览器渲染+反爬)  | fetch_url / fetch_url_rendered / screenshot_url   |
| memory     | memory   | 长期记忆管理 (事实/偏好/项目)    | remember / recall / forget                        |
| artifact   | artifact | 产物管理 (doc/code/sheet/note)    | create_artifact / list_artifacts / get_artifact   |

---

## 二、核心特性

- **Supervisor-Worker 编排**：Planner 规划 → Executor 执行 → Reflector 反思 → Finalizer 汇总，支持计划修订（≤2 次）与单步重试（≤1 次）
- **并行执行**：无依赖子任务通过 `ThreadPoolExecutor` 并行调度，`ContextVar` 按线程拷贝避免竞态
- **跨步骤数据交接**：每步结果落盘 + 下游任务描述注入前序步骤文件路径与摘要，codexec 子进程 cwd 锁定到 `tasks/<plan_id>/`
- **多知识库 RAG**：全局/个人知识库隔离，Chroma 集合 `kb_store` 按 `kb_id/doc_id` 元数据隔离，嵌入提供者可在 Ollama/DashScope 间切换
- **代码沙箱**：本地 subprocess 执行 Python/shell，AST 危险调用告警 + 黑名单 + 超时 + 输出截断
- **流式可观测**：SSE 协议暴露 `plan_created / step_started / step_thinking / step_output / plan_reflecting / plan_revised / plan_completed` 全链路事件
- **微服务绝对解耦**：每个服务自带 `core/` 独立库，配置纯环境变量驱动，无共享包依赖

---

## 三、技术选型

| 层级 | 技术 | 选型理由 |
|------|------|----------|
| 前端框架 | Vue 3 + Vite | 组合式 API + `<script setup>` 简洁；Vite 冷启动快、HMR 即时；生态成熟 |
| 路由/状态 | Vue Router + Composables | 轻量，无需引入 Pinia/Vuex；`useChat` 组合式函数集中管理流式状态 |
| Markdown | markdown-it + 流式节流 50ms | 避免逐 token 重渲染；支持代码高亮与 GFM |
| 长列表 | vue-virtual-scroller | 对话消息虚拟滚动，仅渲染可视区 DOM |
| 构建优化 | Vite manualChunks | 拆 `vue-vendor` 独立 chunk；大型组件 `defineAsyncComponent` 懒加载 |
| 后端框架 | FastAPI + Uvicorn | 原生 async + SSE 流式；Pydantic 类型校验；OpenAPI 文档自动生成 |
| 智能体编排 | LangGraph + LangChain | `create_agent` + 中间件链（ToolCallLimit / 监控 / 提示词切换）；声明式图执行 |
| LLM | DeepSeek (thinking 模式) | 推理能力强；thinking 模式可流式推送 `reasoning_content` 作为思考过程 |
| 向量库 | ChromaDB | 轻量嵌入式，无独立服务依赖；多集合隔离 |
| 嵌入 | Ollama / DashScope | Ollama 本地零成本；DashScope 远程兜底，可热切换 |
| 数据库 | MySQL (每服务独立库) | 强一致 + 事务；服务级隔离避免跨域耦合 |
| 缓存/事件 | Redis (Pub/Sub + 缓存) | 会话消息缓存、限流计数；chat → admin 事件聚合解耦 |
| 鉴权 | JWT (HS256) | 无状态、可跨服务；`device_token` 支持多端登录管理 |
| 代码沙箱 | subprocess + AST 检查 | 不引入 docker 额外依赖；黑名单 + 超时 + 截断兜底 |
| 浏览器自动化 | Playwright | 真实浏览器渲染绕过反爬；stealth 反检测（抹掉 `navigator.webdriver`） |
| 包管理 | uv + uv.lock | 极快的依赖解析与安装；锁定文件保证环境一致 |

---

## 四、本地启动

### 4.1 前置依赖

- Python ≥ 3.13、Node.js ≥ 18、MySQL 8、Redis 7
- 可选：Ollama（本地嵌入，需拉取 `nomic-embed-text`）
- 可选：DashScope API Key（远程嵌入/对话，见 `AIRAGAgent/config/rag.yml`）

### 4.2 后端配置

复制配置模板并填写：

```powershell
Copy-Item deploy\backend\.env.example deploy\backend\.env
# 编辑 .env：MYSQL_PASSWORD / JWT_SECRET_KEY / DEEPSEEK_API_KEY / EMBEDDING_API_KEY 等
```

关键字段（详见 `deploy/backend/.env.example`）：

| 变量 | 说明 |
|------|------|
| `MYSQL_HOST/PORT/USER/PASSWORD` | MySQL 连接（5 个服务库 + 1 个文件服务） |
| `JWT_SECRET_KEY` | JWT 签名密钥（所有服务需一致） |
| `DEEPSEEK_API_KEY` | DeepSeek 对话模型 API Key |
| `EMBEDDING_API_KEY` | DashScope 嵌入 API Key（Ollama 模式可留空） |
| `INTERNAL_HOST` | 微服务互调主机（本地 `127.0.0.1`） |

### 4.3 安装依赖

```powershell
# Python 依赖（用清华镜像加速）
uv sync

# 前端依赖
cd frontend; npm install; cd ..
```

### 4.4 启动微服务（本地 6 服务 + 前端）

PowerShell 一键启动（加载 `.env` → 设进程级环境变量 → 逐个 `Start-Process`）：

```powershell
.\deploy\backend\start_microservices.bat
```

或用服务自带脚本单独启动（每个服务目录可独立拷贝运行）：

```powershell
cd services\auth_service ; .\start.bat
cd services\user_service ; .\start.bat
cd services\chat_service; .\start.bat   # 需 PYTHONPATH 指向项目根
cd services\kb_service  ; .\start.bat   # 需 PYTHONPATH 指向项目根
cd services\admin_service; .\start.bat
cd services\file_service; .\start.bat
```

启动前端开发服务器（内置微服务直连代理，无需 nginx）：

```powershell
cd frontend; npm run dev   # http://localhost:5173
```

### 4.5 验证

```powershell
# 健康检查（6 服务都应返回 200 + redis connected）
foreach ($p in 8001..8006) { Invoke-RestMethod "http://localhost:$p/api/health" }

# 打开前端
start http://localhost:5173
```

### 4.6 生产部署

- 后端：`deploy/deploy_to_server.py`（paramiko SFTP 上传 + systemd 重启，目标 `81.70.100.57`）
- 前端：`vite build` 产物部署到 `/var/www/lc-course-frontend/`，nginx 配置见 `deploy/frontend/nginx.conf`
- systemd 单元必须用独立目录模式：`WorkingDirectory=services/<svc>` + `ExecStart=...uvicorn main:app --app-dir ...`

---

## 五、项目结构

```
lc-course/
├── AIRAGAgent/                 # 智能体引擎包（被 chat_service / kb_service 复用）
│   ├── agent/
│   │   ├── orchestrator.py     # Supervisor 主循环（Planner/Executor/Reflector/Finalizer）
│   │   ├── plan.py             # Plan / PlanStep 数据模型 + 持久化
│   │   ├── sub_agent.py        # SubAgent / Registry / Runner / 并行执行器
│   │   ├── sub_agents/builtin.py  # 10 个内置 SubAgent 注册
│   │   └── tools/              # codexec / browser / memory / artifact / search ...
│   ├── kb/                     # 多知识库 RAG 服务层 + 数据模型
│   ├── rag/                    # 向量存储 + RAG 检索
│   ├── model/factory.py        # LLM / 嵌入工厂
│   ├── database/connection.py  # pymysql 连接 + init_db 建表
│   ├── config/                 # agent.yml / chroma.yml / rag.yml / mysql.yml ...
│   └── prompts/                # 系统提示词模板
├── services/                   # 6 个微服务（每个自带 core/ 独立库，绝对解耦）
│   ├── auth_service/   (:8001) # 注册/登录/JWT/找回密码/设备管理
│   ├── user_service/   (:8002) # 用户档案/会话/反馈
│   ├── chat_service/  (:8003) # /api/chat SSE 入口 → Orchestrator
│   ├── kb_service/    (:8004) # 多知识库 CRUD + 文档索引/检索
│   ├── admin_service/ (:8005) # 统计/审计/限流（订阅 Redis 事件）
│   └── file_service/  (:8006) # workspace 文件浏览/下载
├── frontend/                   # Vue 3 + Vite 前端
├── tests/                      # pytest 测试（auth_service / kb_service）
├── deploy/                     # 部署脚本 + nginx 配置 + .env 模板
├── uploads/                    # 用户上传文件（kb 文档 / 头像 / 截图）
├── workspace/                  # AI 工作区（按用户/日期/计划隔离）
└── pyproject.toml              # uv 依赖管理
```

详见 [项目结构介绍.md](项目结构介绍.md)。

---

## 六、测试

为核心服务建立 pytest 测试体系（auth_service / kb_service），覆盖鉴权、CRUD、权限边界等关键路径：

```powershell
# 安装测试依赖
uv pip install pytest httpx

# 运行全部测试（需本地 MySQL 可达）
pytest tests/ -v

# 运行单个服务测试
pytest tests/auth_service/ -v
pytest tests/kb_service/   -v
```

测试使用独立的 `lc_auth_test` / `lc_kb_test` 数据库，每个 session 自动建表、每个测试自动清理数据，不污染业务库。测试结构与覆盖范围详见 `tests/` 目录。

---

## 七、关键设计文档

- [项目结构介绍.md](项目结构介绍.md) — 完整目录与模块说明
- [AIRAGAgent/agent/orchestrator.py](AIRAGAgent/agent/orchestrator.py) — Supervisor-Worker 编排核心
- [AIRAGAgent/agent/plan.py](AIRAGAgent/agent/plan.py) — Plan/PlanStep 数据模型
- [deploy/backend/.env.example](deploy/backend/.env.example) — 环境变量配置模板
