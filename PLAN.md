# M2 学习计划：企业知识库问答系统（RAG）

> **30 天（2026-10）构建一个可实测的企业级 RAG 系统**
>
> **最后更新**：2026-10（计划 v1.1 —— 依据 2026 企业级 RAG 研究修正）
> **当前进度（2026-10-13）**：Day 0—6 基础练习与固定100题集完成。按用户调整的审核安排，Day 7 主要项目知识已完成：检索指标、100题自定义生成评分、拒答汇总、1条用户初次评分及39条AI复核、RAGAS通过M1/DeepSeek及本地BGE的两个指标最小接入和实际对照。总结见 examples/day7/day7_summary.md。Day 8 已开始，基线草稿 examples/day8/baseline_v1.md 固定了现有结果、生成调用p50与费用估算；统一实验入口和完整链路计时尚未完成。40条独立人工标尺与外部课程仍是未完成验证项，小样例RAGAS不能当成100题框架评测，不宣称原计划全部验收通过。
> **上位文件**：《A 层 Agent 应用工程 6 个月冲刺执行手册》—— 本计划是其中 **M2（项目 2）** 的展开

> **执行补充（2026-10-10）**：Day 1 聚焦 M1 调用接口与依赖打通，Day 2 用 fastembed 直接接入本地 BGE-small 并完成最小 RAG；EmbeddingProvider 通用接口抽象留到 Day 8 的重构阶段。开发期用 `../m1` editable 依赖，不要求立即发布 0.2.0；交付时另行验证可安装的发布版本。旧正文中的 DashScope 默认方案不作为当前执行方案。JSON 实测结果与测试记录见 NOTES.md。

---

> **审核执行调整（用户确认，2026-10-12）**：40 条审核中的 1 条由用户初次评分，剩余 39 条委托助手完成 AI 复核。与 DeepSeek 的单维度一致率为 89.74%/92.31%/89.74%，整条全部一致为 31/39。已完成本次委托，记录见 examples/day7/ai_review_summary.md；该比较不能记为 40 条独立人工校准，课程可继续推进，独立人工标尺作为尚未完成的验证项保留。

> **Day 8 最新补充（2026-10-13）**：配置类、可复用检索类、共享单题流程、单题及批量实验入口已接通；一次真实单题生成与完整链路计时成功。top3/top5各完成100题本地检索，排名与原基线一致，对照见 examples/day8/top3_top5_retrieval.md。此前“统一入口和完整链路计时尚未完成”已推进为：批量完整生成对照、评分及费用汇总仍待完成；单题成功耗时不能替代100题RAG p50。

> **Day 8 完整对照补充（2026-10-13）**：top3/top5各完成100题真实完整RAG生成和相同规则模型评分，成功100/100、评分格式合法100/100；完整链路p50为0.825/0.728秒，输入token34936/48513，裁判正确性均分1.86/1.96。报告见 examples/day8/top3_top5_full_comparison.md。发现裁判误判并另存5条助手复核，原分数保留；不把均分当独立人工准确率，不把一次顺序运行当稳定速度结论。费用仅估算成功生成且非账单。此前补充中的批量对照待完成项已推进，双实现provider/向量库对照仍未执行。

## 🎯 总目标

构建一个**企业知识库问答系统**，让用户上传企业文档后能用自然语言提问，并得到**带引用来源**的答案。

### 手册规定的硬指标（不可打折）

| 项 | 手册要求 |
|---|---|
| 项目定级 | **T1 核心必考**（A 层岗位必考项） |
| 技术栈 | Python + FastAPI + **LangChain** + **Chroma** + **BGE-large-zh** |
| 代码量 | **1500 ~ 2000 行** |
| 语料 | **阿里云 / 腾讯云公开文档**实测 |
| 验收 | **LLM-as-Judge 评估准确率 > 70%** |
| 交付物 | 完整 README + Demo 演示 |
| 面试亮点 | 采用**混合检索 + 重排序**策略，缓解 RAG 幻觉、召回缺失、切片不合理等工程痛点 |

### 功能清单（手册原文 7 条）

1. 文档上传 PDF / Word / Markdown
2. 多策略文本自动切片
3. Embedding 生成与向量入库
4. **BM25 + 向量混合检索**
5. **Rerank 重排序**
6. 流式回答 + **引用来源标注**
7. 简易 Web UI

### 贯穿简历主线（面试固定叙事）

> 从 **LLM 调用层（M1）** → **RAG 知识库（M2）** → **MCP 标准化工具（M3）** → **多智能体协作（M3-M4）** → **可视化工作流平台（M4）**，
> 完整实现 AI Agent 应用全链路。

**所以 M2 的产物必须是一条链上的一环，不能是孤岛** —— 见下面「架构定位」。

---

## 🔧 技术栈：手册 vs 研究证据（v1.1 修正说明）

> 研究给出了 2026 年的一手证据，与手册的部分指定**有冲突**。处理原则：
> **理解深度优先，同时对简历保留手册要求的字面技术栈。**

| 项 | 手册指定 | 研究结论 | **本计划采用** |
|---|---|---|---|
| RAG 主框架 | LangChain | ⚠️ 不要把 LangChain 当**主框架** —— 抽象会掩盖所有细节，面试答不上"RRF 怎么实现的" | **核心链路全手写**；Day 29 做一天 **LangChain 对照实验** |
| 向量库 | Chroma | Chroma 学习友好（~100K 规模），但 sqlite-vec 更简单。**两家在国内企业都不是主流**（ES/Milvus 才是） | **Chroma**（满足手册）+ **抽象出 VectorStore 接口** |
| Embedding | BGE-large-zh | ✅ BGE 仍是中文主力；但 **DashScope `text-embedding-v4` 有 OpenAI 兼容端点**，M1 零改造即可用，且**一次调用同时产出 dense + sparse**（天然适合混合检索） | **双实现**：DashScope API（默认，快）+ 本地 BGE（可切换，免费离线） |
| Rerank | （未指定） | **`qwen3-rerank`**（OpenAI 兼容端点）或 `bge-reranker-v2-m3`（Apache 2.0，最强开源） | 二选一，Day 13 定 |
| 混合检索 | BM25 + 向量 | ✅ 确认有效；**RRF 融合用排名倒数，不用分数归一化** | **手写 BM25（SQLite FTS5）+ 手写 RRF** |
| 部署 | （M4 才要求 Docker） | Docker = 本阶段**陷阱**（Windows 环境成本高，8000 chunk 用不上） | **不做 Docker**，改为写明技术选型理由 |

### ⭐ 最关键的技术发现：DeepSeek 没有 embedding 模型

> 官方 [issue #806](https://github.com/deepseek-ai/DeepSeek-V3/issues/806) 确认：**DeepSeek 没有任何 embedding 模型**。

**这直接决定了 M2 的第一个架构演进**：

```
M1（现状）：一个 provider 概念 = 调模型
M2（必须）：拆成两个独立可配置的 provider
   ├── ChatProvider      （DeepSeek / MiniMax）   ← 生成答案、查询改写、评测裁判
   └── EmbeddingProvider （DashScope / 本地 BGE） ← 只负责向量化
```

> 📌 **这是 M1→M2 第一个真实的架构演进点，不是课程练习题。**
> 面试可讲："我原本以为 provider 抽象是统一的，做 RAG 才发现**生成模型和向量模型是两个独立的供应市场**，
> 所以我把抽象拆成了两层。"

**另外**：MiniMax 有 embedding（`embo-01`，1536 维），但**请求格式非标准**（body 用 `texts` 不是 `input`，返回 `vectors` 不是 `data`），
M1 的 `openai` SDK 直接调会失败 → **建议 MiniMax 只做 chat**。

---

## 🧭 核心原则

### 继承 M1 的四条

> **先跑通，再抽象；先单模型，再多模型；先 CLI，再工程化；先核心能力，再补方法论。**

### M2 新增五条（为 RAG 定制）

| 原则 | 含义 | 为什么 RAG 特别需要 |
|---|---|---|
| ⭐ **先最笨的，再最聪明的** | 先"全文塞进 prompt"，再切分 → 再检索 → 再重排 | 每一步都要亲眼看到"上一步为什么不够" |
| ⭐⭐ **先有评测，再谈优化** | **评测集必须在 Day 6-8 建好** | 没有评测的 RAG 优化 = 盲人调音。**这是全课程的转折点** |
| ⭐ **一次只改一个变量** | 任何改动都要跑同一套评测，记录 delta | 同时改 3 个变量 = 无法归因，是 RAG 最常见的自我欺骗 |
| **手写一遍核心，再用框架对照** | 切分、BM25、RRF、余弦，先自己写 | 面试问的是"内部是什么"，不是"你调过什么 API" |
| **不做过早优化** | 8000 个 chunk 不需要 ANN 索引、不需要 Milvus | sqlite-vec 实测 10K 向量 **9ms p50**（暴力扫描）—— 这个数字本身就是面试答案 |

---

## 🏗️ 架构定位

```
M1 llm_toolkit  ← 模型调用层（已交付）
   │  提供：多 provider 调用 / 重试 / 日志 / 成本统计 / 异常体系
   ▼
M2 【本项目】企业知识库问答
   │  提供：检索能力 —— 对外暴露 search(query, filters) -> list[Chunk]
   ▼
M3 MCP Server  ← 把 M2 的检索能力包装成标准化工具（M2 Day 25 先预演一次）
   ▼
M4 Agent 平台  ← 把 M3 的工具接进可视化工作流
```

### 分层职责

| 层 | 用谁 | 理由 |
|---|---|---|
| **生成**（答案、查询改写、评测裁判） | **M1**（ChatProvider） | 简历主线；复用重试/日志/成本 |
| **向量化**（文档、查询） | **M2 新增 EmbeddingProvider** | DeepSeek 没有；必须独立 |
| 向量存储 | **Chroma** | 手册指定；仅作存储层 |
| 关键词检索 | **SQLite FTS5**（手写 BM25） | 零新依赖；M1 已在用 SQLite |
| **混合/重排/编排** | **全部手写** | 面试深度所在 |

### 🔧 M1 需要先补的接口缺口（Day 1 的活）

M1 现在的 `call()` 签名是 `call(messages, stream=False)`，**参数太少，撑不住 RAG**：

| 缺什么 | RAG 为什么需要 |
|---|---|
| `model` 是**类属性**，调用时改不了 | 便宜模型做查询改写、贵模型做生成 |
| 没有 `temperature` | RAG 答案生成要**低温度** |
| 没有 `max_tokens` | 控制成本与截断 |
| 没有 `response_format` | **查询改写 / 评测裁判要结构化 JSON 输出** |
| 流式没有 `stream_options={"include_usage": True}` | 流式拿不到 usage → 成本统计断掉 |

**处理方式**：在 m1 仓库扩展 `call()` → 发 `chujie-llm-toolkit` **0.2.0** → m2 依赖它。

---

## 🤝 学习与协作方式（重要 —— 上下文压缩后请遵守）

> 这一节记录的是**学习者的偏好和项目的实际节奏**，比技术细节更容易在上下文压缩后丢失。

### 学习者画像

- **太原理工大学 211 本科大二**，目标：**AI Agent 暑期实习 Offer**
- 目标公司：Dify / FastGPT / 字节扣子 / 腾讯元宝 / 智谱 / 月之暗面 等 30 家
- **Agent 小白**：没有 agent 库/框架的使用经验（LangChain 也是第一次正经用）
- **Python 基础在建立中**：概念能懂，但细节容易忘，需要反复确认
- **每天按"课程天数"编号推进**，不是按日历天

### 代码由谁写（关键）

| 情况 | 谁写 |
|---|---|
| **有学习价值的新代码** | ⭐ **学习者手抄**（AI 给完整代码 + 逐行讲解） |
| **重复性/样板代码** | 学习者可能说"帮我做"，这时才代劳 |
| **发现 bug 的修复** | 先给"找到什么 → 改成什么"，学习者自己改；说"帮我改"时代劳 |
| **纯配置/环境操作** | 可以直接代劳 |

**⚠️ M1 期间曾发生过**：AI 一次性把所有代码都写完了，学习者要求"还原"，因为**手抄是学习方式**。
**默认行为：不要主动写项目代码，先给代码。**

### 讲解风格（学习者明确要求过）

| 要求 | 说明 |
|---|---|
| ⭐ **通俗、从零开始** | 讲新概念时**不能假设已有基础**（讲 embedding 时不能假设懂向量空间） |
| ⭐ **先给大纲再讲细节** | 学习者说过："你没告诉我我们要做的大体上是什么" → **每讲一个阶段，先给地图** |
| **善用类比 + 实验** | 学习者反馈"实验证明"比"空口解释"有效得多。**RAG 尤其适合做实验** |
| **错了就承认** | AI 表述不准确时要明确纠正，不要含糊过去 |
| **不要一次灌太多** | 分阶段推进，每阶段一个小目标 |

### 学习者的提问特点

- **喜欢追问"为什么"**
- **会抓出 AI 的表述不精确**
- **会主动总结自己的理解，让 AI 验证**：这时要**逐条评估对错**
- **怕重复劳动**：连续几个"同样的改动"时会说"看明白了，你帮我做"

### 每日固定节奏（手册规定，每日有效 4 小时）

| 时段 | 内容 | 时长 | 归属 |
|---|---|---|---|
| 19:00-19:30 | LeetCode 1 道中等题 | 30 min | 独立线（累计目标 55 道/月） |
| **19:30-21:00** | **M2 项目开发** | **90 min** | ⭐ **本计划主战场** |
| **21:00-22:00** | **M2 技能学习** | **60 min** | ⭐ **本计划技能清单** |
| 22:00-23:00 | Octop Maintainer 社区 | 60 min | 独立线（本月挂钩 RAG） |

- 周末：项目集中开发 + 知识复盘，8-10 h
- **本月 Octop 产出方向（手册规定）**：知识库**切片**、**召回逻辑**优化 → 匹配 M2 的 RAG

> ⚠️ **时间预算的现实含义**：项目只有 **90 min/天 × 30 天 ≈ 45 小时**。
> 所以每天的任务必须**能在 90 分钟内看到可见进展**。

### 技术环境备忘

| 项 | 说明 |
|---|---|
| **uv** 包管理 | `uv run` 会先同步项目；纯检查用 `.\.venv\Scripts\python.exe -m xxx` |
| **PowerShell 控制台是 GBK** | 读 UTF-8 文件时中文乱码，**是显示问题不是文件问题** |
| **PowerShell 5.1** | 不支持三元运算符 `? :` |
| **长命令输出别接 `\| Select-Object -Last N`** | 看起来像卡死 → 用 `*> out.txt` 再 `Get-Content` |
| ⭐ **HuggingFace 下载慢/不通** | BGE 模型走镜像：`HF_ENDPOINT=https://hf-mirror.com`，或用 **ModelScope** |
| ⭐ **BGE-large-zh 约 1.3 GB** | **先用 `bge-small-zh-v1.5` 跑通，最后再换 large** |
| **VS Code 装了 Pylance** | 内核是 Pyright |
| **服务器占端口 8000 时会锁文件** | 此时 `uv add` 可能失败 → 用 `uv pip install` |

### 交流语言

**中文**（技术术语保留英文原词）

---

## 📊 30 天进度总览（v1.1 已重排）

| 阶段 | 天数 | 主题 | 状态 |
|---|---|---|---|
| ① 起步 | Day 0-2 | 环境 + **最笨的 RAG**（单文件，零抽象） | ⬜ 未开始 |
| ② 加维度 | Day 3-5 | Prompt + 摄取 + 切片（**仍不抽象**） | ⬜ 未开始 |
| ③ **评测** ⭐⭐ | **Day 6-8** | **评测系统 —— 全课程的转折点** | ⬜ 未开始 |
| ④ **检索攻坚** ⭐⭐ | **Day 9-15** | 向量 / BM25 / RRF / Rerank / 父子 / **Contextual Retrieval** | ⬜ 未开始 |
| ⑤ 生产化 | Day 16-20 | 高级摄取 / 增量索引 / 权限 / 查询改写 / 引用拒答 | ⬜ 未开始 |
| ⑥ 服务 | Day 21-23 | FastAPI + SSE + Web UI + 可观测性 + 成本 | ⬜ 未开始 |
| ⑦ 前沿 | Day 24-26 | 工具路由 / **MCP** / Agentic RAG + GraphRAG | ⬜ 未开始 |
| ⑧ 收尾 | Day 27-30 | 合规安全 / 面试弹药 / **LangChain 对照** / README | ⬜ 未开始 |

> **天数分配依据（研究给出的回报排序）**：
> 评测 3 天（不可压缩）+ 检索质量 7 天（**最高回报**）+ 生产化 5 天 + 服务 3 天 + 前沿 3 天 + 收尾 4 天 + 基础 5 天。

---

## 🗓️ 30 天详细计划

> 每天两个格子：**【项目 90min】** 主战场，**【技能 60min】** 对应手册 M2 必学技能与必看资源。

---

## ① 起步（Day 0-2）· 先跑通，零抽象

**阶段目标**：让一个**单文件、线性、没有抽象**的 RAG 跑通端到端。

> 📌 **研究给的明确纪律**：D1 **不要**写 `BaseRetriever` / `VectorStoreProtocol` / 依赖注入。
> **60 行 `rag.py` + 一个线性 `main()` 就够了。** 第一次重构要等到 **Day 8**（评测建好之后）——
> 因为只有那时候你才知道**哪些变化点是真的**，哪些是想多了。

#### Day 0 · 仓库与环境
- **【项目 90min】**
  - 建 `D:\develop\m2`，`uv init`，抄 M1 的 `pyproject.toml`（pytest / coverage / mypy / pyright 严格配置）
  - 装依赖：`chromadb` / `sentence-transformers` / `pypdf` / `python-docx` / `jieba` / `fastapi`
  - 把 M1 装进来：`uv add chujie-llm-toolkit`
  - `.env`（`.gitignore`）+ 创建 `NOTES.md`
- **【技能 60min】** 画一张 **RAG 全景图**，标出每一步"如果不做会怎样"
- **产出**：能跑的空项目 + RAG 全景图
- **面试考点**：RAG 解决大模型的哪两个根本问题？（知识截止 + 无私有知识/幻觉）

#### Day 1 · 扩展 M1 + 拆出 EmbeddingProvider ⭐
- **【项目 90min】**
  - 在 m1 仓库给 `call()` 加 `temperature` / `max_tokens` / `response_format` / `model` 覆盖
  - 补测试（M1 的习惯：改动必须带测试）→ `uv build` → 发 **0.2.0**
  - **实证 DeepSeek 没有 embedding**：试着调一下 `/v1/embeddings`，看它报什么错（**留下截图/日志**）
  - 设计 `EmbeddingProvider` 抽象（**照抄 M1 的 provider 模式**），先只实现 DashScope
- **【技能 60min】** 读 Anthropic Prompt Engineering 前 1 小时
- **产出**：M1 0.2.0 发布 + 一个可用的 EmbeddingProvider
- **面试考点**：⭐ **为什么生成模型和向量模型要拆成两层抽象？**（供应市场不同：DeepSeek 不做 embedding）

#### Day 2 · 最笨的 RAG（60 行，端到端）⭐
- **【项目 90min】**
  - 单文件 `rag.py`：读 1 份 Markdown → 切片 → 调 embedding → 存 Chroma → 检索 → DeepSeek 生成 → CLI 打印
  - **先做对照组**：把全文直接塞进 prompt 是什么效果？记录下来
  - 写进 `NOTES.md`：**"全文塞入"的三个致命问题**
- **【技能 60min】** 读 Anthropic Prompt Engineering 第 2 小时
- **产出**：**端到端能跑的单文件 RAG** + 失败记录
- **面试考点**：为什么不直接把文档塞进 prompt？**长上下文能替代 RAG 吗？**（见下面的"长上下文四层回答"）

---

## ② 加维度（Day 3-5）· 仍然不抽象

#### Day 3 · Prompt 工程 + 结构化输出
- **【项目 90min】**
  - RAG 专用系统提示词：**只依据给定资料**、**必须给引用编号**、**没有就说不知道**
  - 用 M1 新加的 `response_format` 做**查询改写器**（口语 → 检索友好，输出 JSON）
  - 处理边界：refusal（模型拒绝时 `content` 为 null）、JSON 截断
- **【技能 60min】** Anthropic Prompt Engineering 第 3-4 小时
- **面试考点**：`json_object` vs `json_schema`？**strict 模式保证什么、不保证什么？**

#### Day 4 · 文档摄取（基础）
- **【项目 90min】**
  - Markdown（最干净）→ PDF（`pypdf` / `pdfplumber`）→ Word（`python-docx`）
  - 统一成内部结构：`{text, source, page, heading_path}`
  - **元数据要有标题层级路径**（如 `计费 > 按量付费 > 带宽`）
- **【技能 60min】** LangChain `Document` 对象概念（`page_content` + `metadata`）
- **面试考点**：PDF 解析的经典坑？（扫描件要 OCR、表格结构丢失、双栏串行、页眉页脚污染、**中文断行**）

#### Day 5 · 切片 ⭐（中文特化）
- **【项目 90min】**
  - 手写固定长度切分 → 亲眼看到它**把一句话劈成两半**
  - 手写递归切分，**分隔符必须中文优先**：`["\n\n", "\n", "。", "！", "？", "；", "，", ""]` ← **`。` 必须在 `，` 前面**
  - ⚠️ **中文用字符数不是 token**（中文 tokenizer 差异极大）：**300-500 汉字 / chunk，overlap 从 0 开始**
  - 表格 → 整块保留为 Markdown；合同/法规 → 按 `第X条` 切
- **【技能 60min】** 读 Chroma 切分实验报告（[evaluating-chunking](https://www.trychroma.com/research/evaluating-chunking)）
- **产出**：中文切片器 + 一份"为什么这么切"的记录
- **面试考点**：⭐⭐ **chunk size 怎么定？overlap 有什么用、什么时候不该用？**
  （可引用硬数据：**overlap 400 在所有非 recall 指标上垫底；Recursive-200/overlap-0 性价比最高；默认语义切分器低于调好的 Recursive**）

---

## ③ 评测系统（Day 6-8）⭐⭐⭐ · 全课程的转折点

> 📌 **研究原话**：这是"整个课程的分水岭 —— 之前你只能'跑'，之后你才能'改进'"。
> **从 Day 8 起，任何改动都必须跑同一套评测。**

#### Day 6 · 构造 100 题中文评测集
- **【项目 90min】**
  - ⭐ **分层构造 100 题**（研究给的配比）：
    | 类型 | 数量 |
    |---|---|
    | 单跳事实 | 40 |
    | 多跳 | 20 |
    | 对比 | 15 |
    | 表格/数值 | 15 |
    | **应当拒答** | **10** |
  - 构造方法：LLM 合成（要求"**只能依据给定文本回答**"）→ **人工验证检索相关性**
  - ⚠️ **"应当拒答"这一类最常被漏掉，也最常被面试官问**（"你怎么知道它该说不知道？"）
- **【技能 60min】** 学习**评测集规模的含义**：30-50 题只能分辨 >10% 差异；**100-200 题能分辨 5-10%**；500+ 才能分辨 2-3%
- **面试考点**：没有标注数据怎么造评测集？为什么必须含"拒答"类？

#### Day 7 · 实现指标（检索 / 生成分开测）⭐⭐
- **【项目 90min】**
  - **检索指标**（便宜、可重复、不用 LLM）：`Recall@5` / `Recall@20` / `nDCG@10` / `MRR`
  - **生成指标**：`Faithfulness`（忠实度=幻觉检查）/ `Answer Relevancy`
  - ⚠️ **RAGAS 默认用 OpenAI 当裁判** —— **必须换成 DeepSeek**（网络 + 成本）
    👉 **这正是展示 M1 价值的地方：把 RAGAS 的裁判 LLM 通过 M1 的 provider 注入**
  - ⚠️ **裁判要校准**：人工标注 40 条作标尺 → 算**裁判与人的一致率**（>80% 才能信）
- **【技能 60min】** 读 RAGAS 文档（[docs.ragas.io](https://docs.ragas.io)）
- **面试考点**：⭐⭐ **为什么必须把检索和生成分开测？**（context recall 只有 0.6 时，answer relevancy 再高也没意义）
- **面试考点**：⭐⭐ **LLM-as-Judge 的坑？**（位置偏差→交换顺序求平均；自我偏好→换模型家族；长度偏差→rubric 里明确惩罚冗余；评委必须比被测模型更强；**算术题别用 LLM 判**；中文语料必须用中文裁判）

#### Day 8 · 基线报告 + 重构（⭐ 唯一的第一次抽象时机）
- **【项目 90min】**
  - 出**第一份完整报告**：`recall@5` / `recall@20` / `nDCG@10` / `faithfulness` / **p50 延迟** / **单次成本**
  - 搭好 **ablation 框架**：`python -m m2.eval --config A` 一键跑对比
  - ⭐ **现在才做第一次重构**：把真正的变化点抽出来（切片策略 / provider / 向量库）
  - **重构标准（研究原话）**：**"我需要同时存在两个实现来跑 ablation"** —— 这才是抽象的正当理由
- **【技能 60min】** 学习"**基线**"的意义：没有基线的优化无法证明有效
- **产出**：⭐ **基线报告 + 可复用的评测/ablation 框架**
- **面试考点**：你的基线是多少？每个改动带来多少提升、多少延迟代价？

---

## ④ 检索质量攻坚（Day 9-15）⭐⭐ · 回报最高的 7 天

> 📌 纪律：**一次只改一个变量，每次改完跑同一套评测，记录 delta。**

#### Day 9 · 向量检索 + Embedding 选型
- **【项目 90min】**
  - 用 numpy **手写余弦相似度**（10 行），验证"意思相近 = 向量接近"
  - 亲眼看到它失败的地方：**否定句、反义词**（"不能用" vs "能用"）
  - 接入 DashScope `text-embedding-v4`（OpenAI 兼容端点，M1 零改造）；
     ⚠️ 注意 **query / document 非对称处理**（`text_type` 参数；不同模型的指令前缀不同，**这是 #1 静默 bug**）
- **【技能 60min】** 读 [阿里云 embedding 文档](https://www.alibabacloud.com/help/en/model-studio/embedding)（维度选项 / batch / 价格 / `output_type`）
- **面试考点**：⭐ 为什么用余弦相似度不是欧氏距离？归一化做了什么？**维度怎么选？**（1024 是一般均衡点）**换 embedding 模型为什么要全量重建索引？**

#### Day 10 · Chroma 入库 + 元数据
- **【项目 90min】**
  - 建 collection，写入 chunk + embedding + metadata，**持久化**（重启可读）
  - 试 **metadata 过滤**（只在某个产品/某个层级里检索）
  - 换成 `bge-small-zh-v1.5` 本地模型（走 hf-mirror / ModelScope），对比质量与速度
- **【技能 60min】** 读向量库选型对比（[腾讯云中文对比](https://cloud.tencent.cn/developer/article/2697120)）
- **产出**：可持久化、可过滤的向量库
- **面试考点**：⭐⭐ **Chroma / FAISS / Milvus / pgvector 怎么选？**
  （可用硬数据：**sqlite-vec 10K 向量 9ms p50、100K 向量 890ms —— 没有 ANN 索引，是暴力扫描**。
  结论：**100K 以下讨论 ANN 索引是过早优化**，而**过滤能力才是分水岭**）

#### Day 11 · 手写 BM25
- **【项目 90min】**
  - 从 TF-IDF 推演到 BM25（**为什么需要 TF 饱和 + 文档长度归一化**）
  - 手写 BM25（~40 行）；中文分词用 `jieba`
  - 或者直接用 **SQLite FTS5**（零新依赖，M1 已在用 SQLite）
  - **观察 BM25 强在哪**：专有名词、错误码、API 名、型号数字
- **【技能 60min】** 读 LangChain `BM25Retriever` 实现，和自己的对照
- **面试考点**：⭐ **BM25 的 k1、b 分别控制什么？**向量检索普及了，BM25 为什么没死？（中文专有名词/缩写问题严重）

#### Day 12 · 手写 RRF + 混合检索 ⭐⭐
- **【项目 90min】**
  - **手写 RRF**（~10 行）：`score = Σ 1/(k + rank)`，k=60
  - 跑 ablation：**纯向量 / 纯 BM25 / RRF 混合** 三方对比
  - 记录典型案例（**含产品编码的查询从 0.3 → 0.9** 这类）
- **【技能 60min】** 读 [EnsembleRetriever](https://python.langchain.com/) 对照
- **产出**：⭐ **混合检索模块 + 三方对照数据**
- **面试考点**：⭐⭐⭐ **RRF 公式是什么？为什么用排名倒数而不是加权平均分数？**
  （答：cosine 和 BM25 的量纲/分布完全不同、不可比；RRF 只用排名，鲁棒且零调参。
  举例：**一个被 dense 排第 1、BM25 排第 50 的文档 vs 一个两边都排第 5 的文档**）

#### Day 13 · Rerank 重排序 ⭐⭐
- **【项目 90min】**
  - 讲清 **bi-encoder**（分别编码、可预计算、快、粗）vs **cross-encoder**（一起编码、慢、准）
  - 接入 `bge-reranker-v2-m3`（Apache 2.0，8192 ctx）或 `qwen3-rerank`（OpenAI 兼容端点）
  - 流程：混合召回 top-20~100 → 重排 → 取 top-5
  - **观察 top-k 变化**：重排前第 7 名 → 重排后第 1 名
  - ⚠️ **生产细节（面试加分）**：**重排超时必须降级为不重排的结果**（不能因为重排服务挂了就报错）；**超长 chunk 会被静默截断，要监控**
- **【技能 60min】** 读 reranker 对比（[2026 四方对比](https://pythondatabench.com/article/reranking-rag-python-cohere-bge-jina-colbert-2026)）
- **面试考点**：⭐⭐⭐ **为什么要两阶段？为什么不能直接用 cross-encoder 检索全库？**重排的延迟代价？
  （**决策规则**：`recall@50 > 0.85 且 recall@5 < 0.65` → 加重排收益最大；`recall@5 > 0.85` → 收益很小）

#### Day 14 · 父子文档（small-to-big）
- **【项目 90min】**
  - chunks 表加 `parent_id`：**小块检索（精确）→ 返回父块给模型（完整）**
  - **中文场景特别有效**：`第5条` 引用 `第2条` 的定义 —— 小块精确命中，父块带回定义
  - 跑 ablation
- **【技能 60min】** 读 LangChain `ParentDocumentRetriever` 对照
- **面试考点**：为什么"小块检索、大块返回"有效？

#### Day 15 · Contextual Retrieval ⭐⭐⭐（单项 ROI 最高）
- **【项目 90min】**
  - 给每个 chunk **前置 50-100 token 的语境说明**（"这段出自哪篇文档的哪一节"），**embedding 和 BM25 索引都要用**
  - 效果数据（[Anthropic](https://www.anthropic.com/engineering/contextual-retrieval)）：**失败率 -35%（仅 contextual embedding）/ -49%（+ contextual BM25）/ -67%（+ rerank）**
  - ⚠️ **实现要点**：
    1. 中文 prompt，且**要求模型只输出语境、不要重复 chunk**（否则 embedding 被稀释）
    2. **把一篇文档的所有 chunk 批量放进一次请求**（文档只传一次）→ **DeepSeek 的上下文缓存是自动的 → 成本极低**
    3. **生成时要在 prompt 里区分"语境"和"chunk"**
  - **测量 token 消耗与成本**，写进记录（Anthropic 数据：$1.02 / 1M 文档 token）
- **【技能 60min】** 对比 **Late Chunking**（+2.7~3.6% rel nDCG@10，零 LLM 成本，但**对 BM25 无帮助**）
- **产出**：⭐ Contextual Retrieval 实现 + 成本/收益数据
- **面试考点**：⭐⭐ **Contextual Retrieval 为什么比 Late Chunking 好？**（它也修好了 BM25 索引）

---

## ⑤ 生产化（Day 16-20）

#### Day 16 · 高级文档解析（中文特化）
- **【项目 90min】**
  - 用 **MinerU** 或 **Docling** 替换 `pypdf`（中文首选 MinerU）
  - 扫描件 → PaddleOCR
  - **中文清洗**：全角→半角（数字字母，保留中文全角标点）、跨页重复页眉页脚按频率删除、
    **合并 PDF 断行（中文连接不加空格）**、**删目录页**（TOC 污染检索）
  - ⭐ **做一张表格"修复前 vs 修复后"的对比图** —— 放在作品集里非常有效
- **【技能 60min】** 读中文 PDF 解析工具对比
- **面试考点**：RAG 系统的"垃圾进垃圾出"体现在哪？

#### Day 17 · 增量索引与版本
- **【项目 90min】**
  - **内容 hash 去重**：`doc_id = sha256(file_content)`；未变则跳过（省 embedding 成本）
  - **文档版本**：`status(active/superseded)` + `effective_from/to`，默认只检索 active
  - 变化 → 新版本，旧的标 superseded 但**不立即删**
  - ⭐ **演练一次"embedding 模型升级"**：双写新索引 → 切换 → 删旧（**新旧索引绝不能混用，向量空间不同**）
- **【技能 60min】** 成本估算：重建 1 亿 token 到 `text-embedding-v4` ≈ **$7.2**
- **面试考点**：⭐ 文档更新了怎么办？**换 embedding 模型要做什么？**（全量重建 + 不能混用）

#### Day 18 · 权限与多租户
- **【项目 90min】**
  - `tenant_id` 写进**检索函数的签名**（**必填，不是可选参数** → 调用方无法忘记）
  - ACL：chunk 上带 `acl_groups` / `owner_id` / `sensitivity`
  - SQL 行级过滤：`WHERE tenant_id = ? AND (acl_groups && user_groups OR owner_id = ?)`
  - ⭐ **CI 里加"越权测试"**：用 A 的凭据查 B 的文档，断言结果为空
- **【技能 60min】** 学习"**为什么权限必须在检索层做，不能写进 prompt**"（prompt injection 可绕过）
- **面试考点**：⭐⭐⭐ **pre-filter vs post-filter？**（post-filter 在严格权限下会把结果过滤空；纯 pre-filter 在高选择性时慢；生产用 filter-aware ANN）

#### Day 19 · 查询理解
- **【项目 90min】**
  - **查询改写**：多轮对话的指代消解（"它的价格呢" → "X产品的价格"）—— **中文口语→书面的收益比英文更大**
  - **Self-Query**：自然语言 → `{语义查询, metadata 过滤条件}`（用结构化输出）
  - 多查询 / HyDE（⚠️ HyDE **有引入幻觉的风险**，方向错了会更差）
  - 跑 ablation
- **【技能 60min】** 学习"什么时候**不该**改写"（规则门控：查询 <5 字符或含代词才改写）
- **面试考点**：查询改写为什么能提升召回？**多轮的检索该怎么做？**

#### Day 20 · 引用、拒答与幻觉治理 ⭐
- **【项目 90min】**
  - **强制逐句引用** `[1][2]` + **事后校验每个引用编号真实存在**（编造的编号可程序化检出）
  - **充分性检查**：让模型先判断"给定资料够不够"（多 1 次调用但可靠得多）
  - **拒答阈值** + 评测集里的"应拒答"题来测**拒答的精确率与召回率**
  - ⭐ **幻觉的四类根因**（这个分类法本身就是面试答案）：
    | 根因 | 修哪里 |
    |---|---|
    | ① 检索没找到（context recall 低） | **修检索**，不是修 prompt |
    | ② 找到了但被淹没（lost in the middle） | 减少 top-k、加重排、**关键内容放头尾** |
    | ③ 找到了模型没用（指令遵循失败） | 强制逐句引用、结构化输出 |
    | ④ 模型编造（真的不在上下文里） | 拒答机制 |
- **【技能 60min】** 读 [Chroma Context Rot](https://www.trychroma.com/research/context-rot)
- **面试考点**：⭐⭐⭐ **幻觉怎么防？**（能说出四类根因、并指出**三类要修检索而不是 prompt** —— 这是"有生产意识"的分界线）

---

## ⑥ 服务（Day 21-23）

#### Day 21 · FastAPI + SSE
- **【项目 90min】**
  - 端点：`/api/upload` / `/api/index` / **`/api/ask`（SSE 流式）** / `/api/sources`
  - 复用 M1 经验：`lifespan` 管理模型加载、全局异常处理器、结构化错误
  - ⚠️ **embedding / rerank 模型必须在 `lifespan` 里只加载一次**
- **【技能 60min】** 复习 M1 的 SSE 与 lifespan
- **面试考点**：SSE vs WebSocket？流式怎么和"必须先完成的检索"串起来？

#### Day 22 · Web UI
- **【项目 90min】**
  - 复用 M1 的原生 HTML/CSS/JS 路线（零前端依赖，省时间）
  - 三块：上传区 / 对话区 / **引用面板**
  - **引用可点击 → 跳到原文位置**
  - ⭐ **可视化检索过程**：召回了哪几段、重排前后排名变化 —— **演示效果拉满**
- **【技能 60min】** 流式渲染、滚动、loading 状态
- **产出**：可演示的 Web 界面
- **面试考点**：怎么把"检索过程"变成**用户可感知的信任**？

#### Day 23 · 可观测性与成本
- **【项目 90min】**
  - 追踪（**自托管 Langfuse 或 Arize Phoenix**，国内可用），或最小方案：JSONL 事件流 + 回放 CLI
  - 记录检索快照到日志（排障必需）
  - **缓存**：embedding 缓存（`sha256(text) -> vector` 存 SQLite）、**验证 prompt 缓存命中**（看 `cached_tokens`）
  - ⭐ **出成本/延迟报告**
- **【技能 60min】** 学习延迟预算：改写 150-400ms / embedding 20-80ms / 向量检索 5-50ms / BM25 5-30ms / RRF <5ms / rerank 85-210ms / 首 token 300-800ms
- **面试考点**：⭐ **单次查询成本多少？大头在哪？**（生成占 ~90%，所以 **prompt 缓存收益最大**）
- **面试考点**：优化顺序？（**① 流式输出（感知延迟减半，零成本）② prompt 缓存 ③ 并行（dense 与 BM25 并行、多查询并行）④ 只在必要时改写查询 ⑤ 减少 top-k**）

---

## ⑦ 前沿（Day 24-26）· 「知道 + 能判断」，不是「精通」

#### Day 24 · 什么时候**不该**用向量检索
- **【项目 90min】**
  - 语料有强结构时（表格/代码/结构化日志），**精确检索 / regex / SQL 往往更好、更快、更新**
  - 加一条**最小的 text-to-SQL 路径**（一张表就够）：`"上个季度各部门报销总额"` 这类问题向量检索根本答不了
  - 做一层**工具路由**：结构化查询优先，向量检索兜底
- **【技能 60min】** 读 Anthropic 的 just-in-time retrieval 思路（[context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)）
- **面试考点**：⭐⭐ **什么时候不该用 RAG / 向量检索？**（能说出"Claude Code 用 glob/grep 而不是向量检索"这个例子）

#### Day 25 · 把检索暴露成 MCP Server ⭐（为 M3 预演）
- **【项目 90min】**
  - 暴露三个工具：`search_knowledge_base(query, filters)` / `get_document(doc_id)` / `list_documents()`
  - 理解 MCP 三大原语：**Tools / Resources / Prompts**
  - ⚠️ **2026-07-28 版的 MCP 已改为无状态**（删了 `initialize` 握手和 session，新增 `server/discover`）
  - 用 Claude Desktop 或自写 client 验证一次
- **【技能 60min】** 读 [MCP 官方文档](https://modelcontextprotocol.io/)
- **产出**：⭐ **可被任意 MCP client 复用的检索服务**（M3 直接接上）
- **面试考点**：⭐ **MCP 是什么？**（"MCP 管 agent↔tool，A2A 管 agent↔agent"）**为什么这家公司的 Agent 要能插拔工具？**

#### Day 26 · Agentic RAG 概念 + GraphRAG 一天 demo
- **【项目 90min】**
  - **Agentic RAG 的最小实现**：**充分性检查 + 一轮补充检索**（不要多 agent）
    （Google 数据：**+34% 准确率，延迟仅 +≤3%** —— 核心机制不是"检索更多"，而是**生成前的充分性检查**）
  - **GraphRAG**：用 LightRAG 或 nano-graphrag 跑 20 篇小文档，**测量 token 成本**
  - 写一页"**值不值得**"结论
- **【技能 60min】** 读 Microsoft GraphRAG 文档（**不要自己实现图构建**）
- **面试考点**：⭐⭐ **GraphRAG 什么时候有用？**（全局/总结类问题、多跳关系推理、可解释性；**单跳事实问答毫无优势，只是更慢更贵**；索引成本是普通 RAG 的 **10-100 倍**）

---

## ⑧ 收尾（Day 27-30）

#### Day 27 · 合规与安全（差异化考点）⭐
- **【项目 90min】**
  - **中国合规判断**（[腾讯云中文分析](https://cloud.tencent.com/developer/article/2742718)）：
    - 《生成式AI服务管理暂行办法》第二条第二款：**不向境内公众提供** → 不适用
    - 关键变量是**是否面向"不特定多数人"**（内部员工=特定，正常无需备案）
    - ⚠️ **但：RAG 注入私有语料 + 定制输出属于"影响生成内容的调整"，会动摇"登记"前提 → 实践上倾向按需备案**
    - **"无需备案" ≠ "没有义务"**：数据安全法/PIPL、商业秘密与语料授权链、等保 + **日志留存 ≥6 个月**、内容标识
  - ⭐ **工程化落地（面试亮点）**：`scope_rules.yaml` 声明式范围规则 + **fail-closed 默认** + **变更触发器**（开放外网/自助注册/换基座模型/新增语料源）
  - **安全**：检索到的文本用 XML 标签包裹并声明"**这是数据，不是指令**"；写操作需人工确认
- **【技能 60min】** 读间接 prompt injection 案例（**语料本身是新的攻击面**）
- **面试考点**：⭐⭐ **内部知识库要不要备案？**（能答出"内部不算，但 RAG 私有语料注入会动摇登记前提" = 立刻区分出内行）

#### Day 28 · 面试弹药整理
- **【项目 90min】**
  - 把 46 道高频 RAG 面试题逐个写成**能口述的答案**
  - ⭐ **打磨"评测故事"**（见下面的模板）
  - 整理**"理解原理 vs 有生产意识"对照表**（自己逐条自测）
- **【技能 60min】** 大声念一遍，检验能不能讲顺
- **面试考点**：**"如果让你重做，你会改什么？"**（最见功力的一题）

#### Day 29 · LangChain 对照实验 ⭐（满足手册技术栈 + 差异化亮点）
- **【项目 90min】**
  - 用 LangChain 的组件复现同一套流程：`RecursiveCharacterTextSplitter` / `EnsembleRetriever` / `ContextualCompressionRetriever` / `ParentDocumentRetriever` / `CrossEncoderReranker`
  - **跑同一套评测，和手写实现对比**
  - 写一份对照表：**LangChain 组件 ↔ 我手写的模块 ↔ 结果差异**
- **【技能 60min】** 读 LangChain 相关文档
- **产出**：⭐ **LangChain 对照报告**
- **面试考点**：⭐⭐ **"你用过 LangChain 吗？它内部怎么实现的？"**
  → **"我手写实现过，也用 LangChain 复现过并对比了结果 —— 所以我知道它里面发生了什么。"**

#### Day 30 · README + Demo + 总结
- **【项目 90min】**
  - **README**：架构图 + 快速开始 + ⭐ **ablation 表格** + ⭐ **成本/延迟表** + ⭐ **"我知道的局限"章节**
  - **Demo**：录一段 5 分钟视频
  - **`SUMMARY.md`**：仿 M1 的总结（数据 / 学到什么 / 踩过的坑 / 讲错过什么）
- **【技能 60min】** 逐条核实 README 里每个声明（抄 M1 的**探针**习惯 —— M1 就是靠它抓到"文档撒谎"）
- **【Octop 挂钩】** 提 RAG 相关 PR（切片 / 召回逻辑优化）
- **产出**：README + Demo + SUMMARY

---

## 📇 面试数字卡（背下来）

| 主题 | 数字 |
|---|---|
| **切分** | 策略差异可达 **9% recall**；**Recursive-200/overlap-0 性价比最高**；800/400 垫底；默认语义切分器低于调好的 Recursive |
| **Contextual Retrieval** | 失败率 **-35% / -49% / -67%**；成本 **$1.02 / 1M 文档 token** |
| **Late Chunking** | **+2.7~3.6%** rel nDCG@10；零 LLM 成本；**对 BM25 无帮助** |
| **Rerank** | **+6~10 NDCG@10（0.514 → 0.612）**；Cohere 85ms / $2 per 1k；BGE-v2-m3 140ms / ~$0.10 |
| **Agentic RAG** | Google **+34% 准确率**，跨语料 90.1%，延迟 +≤3% |
| **Context Rot** | **18 个模型全部随长度单调下降**；针-问题相似度越低降得越快 |
| **Embedding** | `text-embedding-v4` **$0.072/1M**、1024 维默认、batch 10、8192 token、可选 dense+sparse；智谱 embedding-3 **¥0.5/1M**；**DeepSeek 没有 embedding** |
| **向量库** | **sqlite-vec：10K 向量 9ms p50 / 100K 向量 890ms**（暴力扫描，无 ANN 索引） |
| **维度存储** | 10M × 1024 维 × float32 = **40GB**；int8 → 10GB；MRL 降到 512 + int8 → 5GB |
| **成本** | 生成占 **~90%**；国产模型 + 本地 embedding + 本地向量库 ≈ **¥0.003 / 查询** |
| **决策规则** | `recall@50 > 0.85 且 recall@5 < 0.65` → **加重排收益最大** |
| **评测集规模** | 30-50 题分辨 >10%；**100-200 题分辨 5-10%**；500+ 分辨 2-3% |
| **合规** | 备案 6-8 个月 / 登记 1-3 个月；**RAG 私有语料注入动摇登记前提**；日志留存 ≥6 个月 |

## 🗣️ "理解原理" vs "有生产意识"（自测表）

| 主题 | ❌ 只懂原理 | ✅ 有生产意识 |
|---|---|---|
| 切片 | "512 token" | "中文我用**字符数**做锚点，切了 400 字符并做了 ablation" |
| 向量库 | "Milvus 最强" | "我只有 8000 个 chunk，sqlite-vec 9ms，Milvus 在这个量级是运维负担" |
| 评测 | "RAGAS 有 4 个指标" | "我**分开测检索和生成**，裁判换成 DeepSeek，**裁判与人工一致率 85%**" |
| 重排 | "cross-encoder 更准" | "重排超时**降级为不重排**；超长 chunk 会被静默截断，我监控这个" |
| 幻觉 | "加一句别乱编" | "幻觉有**四类根因，三类要修检索不是 prompt**" |
| 权限 | "加个 user_id 过滤" | "权限必须**在 DB 层 pre-filter**，绝不能写'请不要提及'在 prompt 里" |
| 成本 | "用便宜的模型" | "**¥0.003/查询，90% 是生成**，所以 prompt 缓存收益最大" |
| 失败 | "效果还行" | "recall 0.79，延迟 890ms，**10 道拒答题有 3 道没拒答**" |
| 长上下文 | "1M 上下文不需要 RAG 了" | "**Context Rot 证明性能随长度单调下降**；1M 是'能读'，不是'能找到'" |
| 合规 | 完全不提 | "内部使用不适用暂行办法，**但 RAG 私有语料注入会动摇登记前提**" |

## 🎤 可信的"评测故事"模板（面试直接讲）

> "我建了一个 **100 题的中文 golden set**，按类型分层：40 单跳事实、20 多跳、15 对比、15 表格数值、**10 应当拒答**。
> ground truth 是 LLM 合成后我人工验证了检索相关性。
> 我**分开评测检索和生成**：检索用 recall@5/recall@20/nDCG@10，生成用 RAGAS 的 faithfulness 和 answer relevancy，
> **裁判换成 DeepSeek**（成本和网络原因，不用 OpenAI）。
>
> 基线纯向量 + recursive-800/400：**recall@5 = 0.62**。
> 换成 recursive-400/overlap-0 + 父子文档：**recall@5 → 0.71**。
> 加 BM25 + RRF：**recall@5 → 0.79**，其中**含产品编码的查询从 0.3 涨到 0.9**。
> 加 bge-reranker-v2-m3：**nDCG@10 从 0.58 → 0.71**，**faithfulness 从 0.82 → 0.91**。
> 代价：**p50 延迟从 480ms 涨到 890ms**，单次 embedding+rerank 成本约 **¥0.0008**。
>
> 我也清楚这些数字的边界：**100 题只能分辨 5-10% 的差异**，而且我的**裁判与人工一致率只有 85%**，
> 所以我的结论只限于'**大于 5% 的提升**'。"

**这 6 个加分点**：分层评测集、含拒答题、检索/生成分开、真实数字（含延迟与成本）、裁判换成国产模型、**主动声明置信边界**。

---

## 🎓 验收标准

| 标准 | 目标 | 校验 |
|---|---|---|
| 代码量 | **1500 ~ 2000 行** | `scripts/count_lines.py`（抄 M1） |
| 文档上传 | PDF / Word / Markdown | 手工 + 测试 |
| 多策略切片 | ≥3 种 + **对照实验数据** | `NOTES.md` |
| 向量入库 | Chroma 持久化 + metadata 过滤 | 测试 + 重启验证 |
| **混合检索** | BM25 + 向量 + **手写 RRF** + 三方对照 | 实验记录 |
| **Rerank** | 接入 + 前后对照 + **超时降级** | 实验记录 |
| **Contextual Retrieval** | 实现 + **成本/收益数据** | 实验记录 |
| 流式 + 引用 | 引用可溯源 + **编号校验** | Demo |
| 拒答 | 拒答精确率/召回率（用 10 道拒答题测） | 评测报告 |
| **LLM-as-Judge** | **准确率 > 70%** + **裁判一致率 >80%** | `scripts/eval.py` |
| **ablation 表** | 每个技术的 delta（recall / nDCG / 延迟 / 成本） | README |
| Web UI | 上传 / 问答 / 引用面板 / 检索过程 | Demo |
| 权限 | 检索层 pre-filter + **越权测试在 CI 里** | CI |
| MCP | 检索暴露为 MCP server，可被外部 client 调用 | 演示 |
| **LangChain 对照** | 手写 vs LangChain 组件的结果对比 | 对照报告 |
| README | 架构图 + ablation 表 + 成本表 + **局限章节** | 探针逐条核实 |
| 测试覆盖率 | > 60%（分支） | `pytest --cov-fail-under=60` |
| mypy / pyright | 0 错误 | 抄 M1 严格配置 |
| CI | GitHub Actions 全绿 | 抄 M1 的 4 组合矩阵 |
| **面试问答手册** | 46 题 + 评测故事能口述 | 自测 |

---

## ⚠️ 风险与陷阱清单

> 前 12 条是 RAG 领域最常见的失败模式（现象 → 根因 → 修法），后 6 条是**本阶段明确不做的事**。

### 失败模式（把这张表当排障手册）

| # | 现象 | 根因 | 修法 |
|---|---|---|---|
| 1 | 检索到的 chunk 全是"它/该公司/上述"没有指代对象 | 切片破坏了上下文 | **Contextual Retrieval** 或父子文档 |
| 2 | 搜错误码 `TS-999` 搜不到 | 纯向量丢失精确匹配 | **混合检索 + BM25** |
| 3 | 改了管线但不知道变好还是变坏 | **没有评测集** | **先建 100 题 golden set**（Day 6-8） |
| 4 | 答案引用"见第X条"但用户找不到 | 元数据被忽略 | page/section/heading 进 metadata + 前端跳转 |
| 5 | 答案**就在**上下文里但模型说没有 | lost in the middle / context rot | 减 top-k、**关键内容放头尾**、加重排。**不要"再多塞点"** |
| 6 | 中文文档效果差 | 跨语言不匹配 / tokenizer 低效 | 多语言模型（bge-m3 / Qwen3-Embedding）、验证 tokenizer |
| 7 | PDF 表格错乱、数字丢失 | PDF 解析垃圾进垃圾出 | **MinerU/Docling**、表格转 Markdown、数值问题考虑 text-to-SQL |
| 8 | 同一个答案出现 5 次 | 重复 chunk（overlap 太大 / 重复文档） | **overlap 先设 0**、内容 hash 去重、检索后按 parent_id 去重 |
| 9 | 文档更新了但答案还是旧的 | 索引过期 | 增量索引 + 版本管理（Day 17） |
| 10 | 问知识库外的问题，模型自信地编 | 没有拒答路径 | 充分性检查 + **拒答评测题** + 引用校验 |
| 11 | 所有相似度都挤在 0.7 附近 | embedding/query 不对称 | 统一 query/document 处理，用模型的 `instruct` / `text_type` |
| 12 | 堆了 ***很多技术但收益不叠加*** | **一次改了多个变量** | ⭐ **一次只改一个变量，每次跑同一套评测** |

### ❌ 本阶段明确不做（研究列出的低价值项）

| 不做 | 为什么 |
|---|---|
| **Docker / Milvus / K8s** | Windows 环境成本高，8000 chunk 根本用不上；**README 里写清 Milvus 的定位即可** |
| **自己实现 GraphRAG** | 索引成本 10-100 倍，单跳问答零收益；**一天概念 + LightRAG demo 就够** |
| **微调 embedding 模型** | 要 500-1000 标注对 + GPU，收益小于**加一个 reranker** |
| **ColPali / 多模态检索** | GPU 门槛 + 索引膨胀；**把精力花在 MinerU 的文本层质量上** |
| **复杂多 Agent 编排** | 单跳问答不需要，调试地狱，面试官会问"为什么要多个 agent" |
| **追 MTEB 第一名** | 公开榜单不能替代自己的领域评测；**换模型必须全量重建索引** |
| **用 20%+ 的大 overlap** | 数据证明 IoU/Precision 崩塌 |
| **把权限控制写进 prompt** | 安全漏洞，可被 injection 绕过 |
| **用 OpenAI 当 RAGAS 裁判** | 国内成本 + 网络不稳 → **换成 DeepSeek / Qwen，通过 M1 注入** |
| **同时改 3 个变量** | 无法归因 |

---

## 📁 预期项目结构

```
m2/
├── src/kb/
│   ├── providers/            # ⭐ EmbeddingProvider（DashScope / 本地 BGE）
│   ├── ingest/               # 解析 / 清洗 / 元数据
│   ├── chunking/             # 多策略切片（中文特化）
│   ├── store/                # VectorStore 抽象 + Chroma 实现
│   ├── retrieve/             # 向量 / BM25 / RRF / Rerank / 父子 / Contextual
│   ├── generate/             # 提示词 / 引用 / 拒答 / 充分性检查
│   ├── context/              # ⭐ context_builder（token 预算 + 排序 + 引用标注）
│   ├── eval/                 # LLM-as-Judge + 指标 + ablation
│   ├── api/                  # FastAPI（SSE）
│   ├── mcp/                  # ⭐ MCP server（为 M3 预演）
│   └── web/static/index.html # 前端（复用 M1 原生路线）
├── tests/                    # 含越权测试
├── scripts/
│   ├── download_docs.py      # 拉语料
│   ├── build_index.py
│   ├── eval.py               # ⭐ 出评测报告
│   └── count_lines.py
├── experiments/              # ⭐ 对照实验记录（进 git）
├── data/                     # 语料与索引（.gitignore）
├── scope_rules.yaml          # ⭐ 合规声明式规则
├── .github/workflows/ci.yml
├── pyproject.toml
├── PLAN.md                   # 本文件
├── NOTES.md                  # 每日实验记录与失败教训
├── SUMMARY.md
└── README.md
```

---

## 📌 待确认

| # | 事项 | 当前默认 |
|---|---|---|
| 1 | LangChain 用法 | **核心手写 + Day 29 对照实验** |
| 2 | 向量库 | **Chroma**（手册指定）+ 抽象接口 |
| 3 | Embedding | **DashScope `text-embedding-v4` 为主**，本地 BGE 为备选 |
| 4 | Rerank | `bge-reranker-v2-m3` 或 `qwen3-rerank`（Day 13 定） |
| 5 | 语料 | 阿里云/腾讯云某产品公开文档（Day 4 定） |
| 6 | m2 包名 | `kb` |
