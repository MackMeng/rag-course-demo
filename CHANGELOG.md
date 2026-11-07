# 更新日志 / Changelog

本项目所有值得注意的变更都记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [v2.0.0] - 2026-11-07

### 新增 (Added)

- `app_main.py`：合并入口页面——主区域智能客服聊天，侧边栏知识库管理（上传/列表/删除/清空），两个流程同页协同
- `knowledge_base.py` 知识库全生命周期管理：
  - `list_documents()` 按 source 聚合库内文档（片段数、最近写入时间）
  - `delete_by_filename()` 按文件名删除全部片段并同步清理 md5 记录
  - `delete_all()` 清空整库（保留 collection 句柄，避免在线进程报 NotFoundError）
  - 命令行工具：`python knowledge_base.py --list / --delete 文件名 / --clear`
- 发布规范化文件：`README.md`、`CHANGELOG.md`、`requirements.txt`（锁版本）、`.env.example`、`LICENSE`（MIT）
- `.gitignore` 新增 `.env` 忽略规则，防止 API Key 泄漏

### 变更 (Changed)

- md5 去重记录格式升级为 `md5|文件名`：同一内容上传到不同文件名不再误判为重复
- 同名文件重新上传改为"先删旧片段、再写新片段"的更新语义，避免新旧两版同时被检索
- 类名重构：`KnowledgeBaseSergvice` → `KnowledgeBaseService`（修正拼写，同步所有引用）
- 配置路径锚定到 `config_data.py` 所在目录，避免不同工作目录启动时把向量库建到别处
- 调试脚本统一引用 `config.embedding_model` / `config.session_config`，消除硬编码模型名

### 修复 (Fixed)

- `config_data.py`：separators 列表中重复的中文问号 `？` 已去除
- `rag.py`：变量名 `Conservation_chain` → `conversation_chain`；提示词错别字"文档元素据"→"文档元数据"；无语义变量名 `temp1/temp2` → `extract_query/normalize_inputs`
- `file_history_store.py`：历史文件损坏时补充捕获 `json.JSONDecodeError`，与注释行为一致
- 全面统一 PEP 8 赋值/注释空格风格，清理空注释

## [v1.0.0] - 课程学习版（tag: `v1-course-original`）

### 新增 (Added)

- 基础 RAG 在线问答链路：向量检索 → Prompt 组装 → 通义千问流式生成
- 知识库离线上传：文本切分、md5 去重、Chroma 持久化
- 会话历史文件存储（JSONL）与多轮记忆
- Streamlit 双页面：`app_qa.py`（客服）、`app_file_upload.py`（上传）
- 修复课程代码中 4 个必修 bug

[//]: # (版本链接由 GitHub Release 提供，本地阅读时忽略)
