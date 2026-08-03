# 课表上传功能 + 移除硬编码开学日期

## Context

当前课表查询功能存在两个硬编码问题，导致只能在项目文件里手动放 Excel、开学日期写死无法适应新学期：

1. [agent_tools.py:214](file:///c:/Users/nxt/Desktop/lc-course/AIRAGAgent/agent/tools/agent_tools.py#L214) — `get_current_month` 写死 `start_date = "2026-03-09"` 用于算周次
2. [agent_tools.py:312](file:///c:/Users/nxt/Desktop/lc-course/AIRAGAgent/agent/tools/agent_tools.py#L312) — `get_schedule` 默认 `file = "C:/Users/nxt/Desktop/24级土木1班课表-2025-2026-2.xlsx"`

**目标**：在前端设置页加"课表设置"模块，每个用户上传自己的课表 Excel + 设置自己的开学日期；后端从 DB 按当前登录用户读取，完全移除两处硬编码。

**用户决策**：
- 归属模型：**按用户隔离**（每个用户上传自己的课表 + 开学日期，存到 users 表新字段）
- 兜底策略：**完全移除硬编码**（未上传时工具返回"未上传课表"友好提示，AI 引导用户去设置页）

**已有可复用资产**：
- [agent_tools.py:25](file:///c:/Users/nxt/Desktop/lc-course/AIRAGAgent/agent/tools/agent_tools.py#L25) `user_id_var: ContextVar[int]` — chat 流程在 [main.py:407](file:///c:/Users/nxt/Desktop/lc-course/AIRAGAgent/fastapi_app/main.py#L407) 已设置，工具内可拿到当前用户 ID
- [main.py:252-276](file:///c:/Users/nxt/Desktop/lc-course/AIRAGAgent/fastapi_app/main.py#L252) 头像上传接口 — 完整范式（校验、保存、返回 URL）
- [main.py:279-288](file:///c:/Users/nxt/Desktop/lc-course/AIRAGAgent/fastapi_app/main.py#L279) `/api/avatars/{filename}` 文件访问接口范式
- [connection.py:137](file:///c:/Users/nxt/Desktop/lc-course/AIRAGAgent/database/connection.py#L137) `_safe_add_column` 安全加列工具
- [models.py:505](file:///c:/Users/nxt/Desktop/lc-course/AIRAGAgent/database/models.py#L505) `update_avatar_url` DB 操作函数范式
- [auth.js:152](file:///c:/Users/nxt/Desktop/lc-course/frontend/src/api/auth.js#L152) `uploadAvatar` 前端 API 范式
- [SettingsView.vue](file:///c:/Users/nxt/Desktop/lc-course/frontend/src/views/SettingsView.vue) 已有模块化卡片结构（头像/密码/密保/设备/注销）

---

## 关键设计决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| 文件命名 | `schedule_{user_id}.xlsx`（覆盖式） | 文件名稳定，DB 只存相对路径；新上传直接覆盖同名文件，**无需清理旧文件**；课表是"当前生效"的单一资源，历史版本无价值 |
| DB 存储路径 | 相对路径 `schedules/schedule_42.xlsx` | 部署迁移不破坏数据；agent_tools 拼 `UPLOAD_DIR / rel_path` 得到绝对路径 |
| 开学日期提交 | 文件 + 日期合并 POST，另加 PATCH 单独改日期 | 日常只换日期不重传文件更轻量；上传时一并提交避免"半完成"状态 |
| `get_schedule` 的 `file_path` 参数 | 保留 | 向后兼容，未来可作为管理员/测试覆盖入口 |
| Excel 格式校验 | 接口内用 `pd.read_excel` 预校验列名含 `星期一~星期天` | 拒绝坏文件污染 DB |
| admin 端管理 | 暂不实现 | 用户自助上传 + 一键删除已覆盖 99% 场景，后续按需补 |
| `UPLOAD_DIR` 常量位置 | 抽到 `AIRAGAgent/utils/paths.py` | 避免 agent_tools 反向依赖 fastapi_app.main 造成循环 import |

---

## 实施清单（按文件）

### 1. 新建 `AIRAGAgent/utils/paths.py`

抽取 `UPLOAD_DIR` 常量供 main.py 和 agent_tools.py 共用，避免循环依赖：

```python
from pathlib import Path
# 项目根目录下的 uploads 文件夹
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
```

`main.py` 改为 `from AIRAGAgent.utils.paths import UPLOAD_DIR`，删除 L52-54 的本地定义。

### 2. `AIRAGAgent/database/connection.py` — DB 迁移

在 `init_db()` 的 users 表迁移块（L86-90 之后）追加 3 列：

```python
_safe_add_column(cursor, "users", "schedule_file", "VARCHAR(255) NOT NULL DEFAULT ''")
_safe_add_column(cursor, "users", "schedule_start_date", "DATE NULL")
_safe_add_column(cursor, "users", "schedule_uploaded_at", "DATETIME NULL")
```

### 3. `AIRAGAgent/database/models.py` — 新增 4 个函数

在 `update_avatar_url` 旁（L513 之后）追加，沿用 `with get_db() as conn` 范式：

- `update_schedule(user_id, file_path, start_date)` — 写入文件相对路径 + 开学日期 + 上传时间
- `update_schedule_start_date(user_id, start_date)` — 仅改开学日期
- `clear_schedule(user_id) -> Optional[str]` — 清除设置，返回旧文件相对路径供调用方 unlink
- `get_schedule_settings(user_id) -> dict` — 读取设置，返回 `{uploaded, file_path, start_date, uploaded_at, schedule_url}` 供前端回显和 agent_tools 内部使用

### 4. `AIRAGAgent/database/__init__.py`

在 import 列表追加 4 个新函数导出。

### 5. `AIRAGAgent/agent/tools/agent_tools.py` — 核心改造

**5.1** 顶部 import `from AIRAGAgent.utils.paths import UPLOAD_DIR`

**5.2** 在 `get_user_id` 工具下方（约 L207）新增辅助函数：

```python
def _load_user_schedule_path() -> tuple[str | None, str | None]:
    """从当前上下文读取用户的课表绝对路径 + 开学日期。
    返回 (abs_file_path, start_date_str)；未上传时返回 (None, None)。
    内部 lazy import 避免循环依赖。
    """
    uid = user_id_var.get()
    if uid is None:
        return None, None
    try:
        from AIRAGAgent.database.models import get_schedule_settings
        settings = get_schedule_settings(uid)
        if not settings["uploaded"] or not settings["file_path"]:
            return None, None
        return str(UPLOAD_DIR / settings["file_path"]), settings["start_date"]
    except Exception as e:
        logger.warning(f"[_load_user_schedule_path] 读取用户 {uid} 课表设置失败：{e}")
        return None, None
```

**5.3** 修改 `get_current_month`（L208-226）— 移除 L214 硬编码，改读 DB：

```python
@tool(description="wantday 作为用户想查询的日期与当前日期相差的天数，如明天是 1 后天是 2，大后天是 3，以此类推，如果是查看当天的日期则为 0")
def get_current_month(wantday: int) -> dict:
    now = datetime.now()
    target_date = now + timedelta(days=wantday)
    want_date_str = target_date.strftime("%Y-%m-%d")

    _, start_date_str = _load_user_schedule_path()
    if not start_date_str:
        return {
            "date": want_date_str,
            "error": "未上传课表",
            "hint": "请前往「设置 → 课表设置」上传你的课表 Excel 并设置开学日期",
            "week": None,
            "day": None,
        }

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    diff_days = (target_date - start_date).days
    week_number = (diff_days // 7) + 1

    weekday_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期天"]
    weekday = weekday_cn[target_date.weekday()]

    return {"date": want_date_str, "week": week_number, "day": weekday}
```

**5.4** 修改 `get_schedule`（L310-314）— 移除 L312 硬编码，改读 DB：

```python
if file_path is not None:
    file = file_path
else:
    db_file, _ = _load_user_schedule_path()
    if db_file is None:
        return [{
            "error": "未上传课表",
            "hint": "请前往「设置 → 课表设置」上传你的课表 Excel 文件",
        }]
    file = db_file
```

`get_schedule` 的 `file_path` 参数保留；其余解析逻辑不动。

### 6. `AIRAGAgent/skills/definitions.py` — 调整 prompt

修改 `SCHEDULE_SKILL_PROMPT`（L39-44），追加未上传时的引导话术：

```python
SCHEDULE_SKILL_PROMPT = """你现在帮用户查课表。步骤很简单：

1. get_current_month(wantday) 看看那天是第几周、星期几
2. get_schedule(week, day) 拿课表

别自己推算日期，老老实实调工具查。拿到课表直接列出来：课程名、时间、节次、地点。没课就说没课，别瞎分析。

如果工具返回 "未上传课表" 或 hint 字段，直接告诉用户：
"你还没有上传课表，请到「设置 → 课表设置」页面上传你的课表 Excel 文件并设置开学日期。"
不要编造课程信息，也不要尝试用其他方式查询。"""
```

### 7. `AIRAGAgent/fastapi_app/main.py` — 新增 4 个接口

放在 `user_upload_avatar` 之后（L276 附近），import 追加 `Form`：

- **POST `/api/user/schedule`** — multipart，入参 `file: UploadFile` + `start_date: str (Form)`
  - 校验后缀 `.xlsx/.xls`、大小 ≤ 2MB、开学日期格式 `YYYY-MM-DD`
  - 用 `pd.read_excel` 预校验 Excel 列名含 `星期一~星期天`
  - 保存到 `UPLOAD_DIR/schedules/schedule_{user_id}.xlsx`（覆盖式，文件名固定无需清旧）
  - 调 `update_schedule(user_id, "schedules/schedule_{user_id}.xlsx", start_date)` 写 DB
  - 返回 `{status, schedule_url: "/api/schedules/schedule_{user_id}.xlsx", start_date}`

- **PATCH `/api/user/schedule/start-date`** — 入参 `{start_date: str | null}`
  - 先校验用户已上传课表（`get_schedule_settings`），未上传则 400
  - 调 `update_schedule_start_date`

- **GET `/api/user/schedule`** — 返回 `get_schedule_settings` 结果（含 `schedule_url`）

- **DELETE `/api/user/schedule`** — 调 `clear_schedule` 拿旧相对路径，unlink 旧文件

- **GET `/api/schedules/{filename}`** — 完全照搬 `serve_avatar`（L279-288），从 `UPLOAD_DIR/schedules/` 提供文件

### 8. `frontend/src/api/auth.js` — 新增 4 个 API 封装

在 `uploadAvatar`（L169）之后追加，沿用 `authHeaders()` + `API_BASE` 范式：

- `getScheduleSettings()` — GET
- `uploadSchedule(file, startDate)` — POST FormData（file + start_date）
- `updateScheduleStartDate(startDate)` — PATCH JSON
- `deleteSchedule()` — DELETE

### 9. `frontend/src/views/SettingsView.vue` — 新增"课表设置"模块

**9.1** import 4 个新 API

**9.2** 新增状态：`scheduleForm`（file/fileName/startDate）、`scheduleState`（uploaded/start_date/uploaded_at/schedule_url）、`scheduleLoading`、`scheduleDeleting`

**9.3** template 新增 section（建议插在"密保问题"之后、"登录设备"之前），用与头像上传一致的结构：
- 已上传时展示：查看文件链接 + 上传时间
- 文件选择按钮（`accept=".xlsx,.xls"`，前端校验 ≤ 2MB）
- 开学日期 `<input type="date">`
- 操作按钮：上传/更新课表（主）、仅保存开学日期（次）、删除课表（危险）

**9.4** 新增逻辑函数：`loadScheduleSettings`、`onScheduleFileChange`、`saveSchedule`、`saveStartDateOnly`、`removeSchedule`

**9.5** `onMounted` 改造：并行调用 `loadScheduleSettings()`（与现有的 `loadSecurityStatus`、`loadDevices` 一起 `Promise.all`）

---

## 验证方案

按以下顺序本地验证（用 `lc-course-local-run` skill 启动）：

1. **DB 迁移**：启动后端，确认 `users` 表新增 3 列（`DESCRIBE users;`）
2. **未上传场景**：注册新用户 → 在 ChatView 问"明天有什么课" → AI 应回复"你还没有上传课表，请到设置页上传..."（不报错、不编造课程）
3. **上传流程**：进入 `/settings` → 课表设置模块 → 选 `24级土木1班课表-2025-2026-2.xlsx` + 开学日期 `2026-03-09` → 点上传 → 提示成功，状态展示"已上传"
4. **查询正常**：回到 ChatView 问"明天第 3 节什么课" → AI 应正确返回课程信息（与原硬编码行为一致）
5. **单独改日期**：设置页只改开学日期 → 不重传文件 → 课表查询结果按新日期算周次
6. **删除课表**：点删除 → 状态恢复"未上传" → 再问课表 → 回到"未上传"提示
7. **坏文件拒绝**：上传一个非课表 Excel（如随便造一个无 `星期一` 列的）→ 应返回 400 "Excel 列名不符合要求"
8. **前端构建**：`cd frontend && npm run build` 通过
