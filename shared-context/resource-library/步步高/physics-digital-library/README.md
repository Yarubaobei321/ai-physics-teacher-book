# 步步高高中物理数字资料库

本目录把个人本地保存的步步高高中物理 Word 资料建立为可追溯、可逐步处理的资料库。V1 以 `sources/sources.jsonl` 为权威来源清单，提供 Word→Markdown、原始媒体提取、保守题目结构化、知识点候选、SQLite 本地索引、复核队列和质量报告；自动结果仍必须经过人工复核才能进入 `reviewed` 或 `published`。

## 先从这里看

- [人工复核入口：原始 Word、转换正文和每道题目卡可直接对照](</Users/yaril/个人文档/3 写作/项目资源库/步步高/physics-digital-library/reviews/人工复核入口.md>)。先看四份代表资料；每一行都能直接打开对应原文、正文或题目卡。
- [处理质量报告](</Users/yaril/个人文档/3 写作/项目资源库/步步高/physics-digital-library/reports/quality-report.md>)。先看“转换/结构化失败或阻断”，再看“需人工核对”和“保守未拆题”，不要把三者混为一谈。
- [资料库使用说明](</Users/yaril/个人文档/3 写作/项目资源库/步步高/physics-digital-library/README.md>)。需要按课时、知识点或题型查找时，再使用本页后面的查询命令。

每一道已识别题目都能追溯到其来源 Word：题目卡的 `source_id` 对应来源清单中的完整路径，`source_location` 给出转换正文中的行号；人工复核入口已把这些跳转链接整理好。

## 使用与版权边界

- 资料仅供个人本地教学、备课、研究和受控的 AI 辅助处理使用。
- 原始 Word 的版权归原权利人；不得将原件、批量转换结果或题目内容公开发布、分发、商业出售或上传到未获授权的平台。
- **不要删除原始 Word。** `raw/` 中只有 7 个指向原始资料目录的软链接，不保存任何 `.docx` 备份；删掉原始 Word 会让这些链接失效，也会失去资料库的可追溯来源和重建输入。构建器从不写入 `raw/` 或任何 Word；它只读取七个批准链接 `bbg-2026-yilun`、`bbg-required-1..3`、`bbg-elective-1..3`，并忽略 `legacy-*` 和 `project-docs`。每个批准链接的文本必须精确为 `../../<来源目录>`，且解析后的目录必须精确等于正式资料库父目录下的同名来源；子目录和文件链接一律不跟随。
- 常规构建产物只写入本目录内的受控路径。唯一例外是已确认使用的“旁置 Markdown”工具：它只在每个 `.docx` 同目录新增或刷新带生成标记的同名 `.md` 阅读副本，绝不改动 Word、`raw/` 链接或已有普通 Markdown；同名普通 Markdown、符号链接和越界路径都会停止该文件的写入。
- 任何未来的共享或发布，必须先完成版权核验、个人信息检查和人工复核。

## 目录

```text
physics-digital-library/
├── raw/                    # 7 个批准的脚本只读输入链接；legacy/project-docs 不扫描（忽略）
├── sources/                # 原始 Word 的 sources.jsonl 清单
├── schemas/                # source、document、question、knowledge、model、review Schema
├── records/documents/      # Word 提取后的 Markdown 与文档记录
├── questions/              # 保守切分的题目记录
├── knowledge/              # 知识点候选与受控知识点记录
├── models/                 # 物理解题模型记录（当前为空，非 AI 模型）
├── reviews/                # 人工复核记录与 review-queue.jsonl 待办队列
├── reports/                # 来源统计、阶段日志、质量报告和队列摘要
├── assets/                 # 提取图片等派生产物（忽略）
├── indexes/                # 本地 SQLite 索引（忽略）
├── scripts/                # 纯 Python 标准库工具
└── tests/                  # 离线 unittest 回归测试
```

### 为什么转换结果集中放在这里

原始 Word 是资料来源；这里保存的是由它们生成的 Markdown、题目卡、图片记录和处理状态。把这些派生产物集中放在资料库内，有三个作用：不改动原始资料目录；同一题能稳定关联到来源、图片和复核记录；需要重建索引时能从同一处读取权威数据。`raw/` 不是 Word 的副本，也不是第二套资料目录。

你提出的“Markdown 放在每个 Word 同目录”更适合日常浏览。正式资料库仍是唯一权威记录；已在 616 份原始 Word 旁生成同名、标明“自动生成”的 Markdown 阅读副本。这样可以从 Finder 直接打开，又不会让题目 ID、复核记录和索引分散。阅读副本不复制图片，图片仍位于本资料库的 `assets/` 中，链接已改为本机可直接读取的路径。

### 旁置 Markdown 阅读副本

每份 `.docx` 的同目录现在有一个同名 `.md`。这些副本合计 `13,381,554` 字节（约 `12.76 MiB`）；它们只包含 Markdown 文本和相对图片链接，不复制任何 Word 或图片。完整统计见 `reports/sidecar-markdown-materialization.json`。

需要重建或检查时，默认命令只预览，不会写文件：

```bash
# 预览 616 份来源将如何处理；不写任何文件
python3 项目资源库/步步高/physics-digital-library/scripts/materialize_sidecar_markdown.py

# 确认预览后，才创建/刷新本工具生成的旁置 Markdown
python3 项目资源库/步步高/physics-digital-library/scripts/materialize_sidecar_markdown.py --apply
```

命令只会刷新文件首行带 `physics-digital-library-sidecar` 标记的阅读副本；已有普通 `.md`、符号链接或异常路径会保留不动并在统计中标出。若只想检查或生成某一类资料，可加 `--profile teacher`、`--profile gaokao` 或 `--profile textbook`；需要给 Agent 读取结果时加 `--json`。

### `models/` 是什么

`models/` 预留给“物理解题模型”，例如受力分析、匀变速直线运动、平抛运动、闭合电路等；它不是 AI 模型文件夹。V1 只支持题目直接关联这类模型，不做复杂知识图谱。目前还没有经过人工确认的模型记录，所以这里为 0 条，按模型筛题不会得到结果。

## 运行

在工作区根目录执行。以下命令只读取 `raw/` 中已登记的 Word，并把生成物写入本正式资料库：

```bash
python3 -m unittest discover -s 项目资源库/步步高/physics-digital-library/tests -v
python3 项目资源库/步步高/physics-digital-library/scripts/build_manifest.py
python3 项目资源库/步步高/physics-digital-library/scripts/validate_library.py
```

### 转换与结构化

`run_pipeline.py` 默认一次只处理 1 份，方便先验收样本；批量时必须显式给出数量。它按来源哈希和阶段日志断点续跑，未变化的成功来源会跳过。

```bash
# 先处理一个指定来源或一个小批次
python3 项目资源库/步步高/physics-digital-library/scripts/run_pipeline.py --source-id 'src.bbg.<64位SHA-256>'
python3 项目资源库/步步高/physics-digital-library/scripts/run_pipeline.py --profile teacher --limit 10 --workers 2

# 分资料类型完成全量处理时，分别显式指定上限
python3 项目资源库/步步高/physics-digital-library/scripts/run_pipeline.py --profile teacher --limit 101 --workers 2
python3 项目资源库/步步高/physics-digital-library/scripts/run_pipeline.py --profile gaokao --limit 72 --workers 2
python3 项目资源库/步步高/physics-digital-library/scripts/run_pipeline.py --profile textbook --limit 443 --workers 2
```

转换阶段优先使用锁定的 `@firecrawl/anydoc@0.1.7`，并从 DOCX 的 OpenXML 媒体目录提取原图；TIFF/TIFF 会另外尝试生成 PNG 展示副本。题目边界不可靠、答案配对不可靠、图片/表格/公式异常时，内容会保留在文档 Markdown，并标记异常或进入人工复核，不会静默遗漏。

### 质量报告与人工复核

```bash
python3 项目资源库/步步高/physics-digital-library/scripts/generate_report.py
python3 项目资源库/步步高/physics-digital-library/scripts/generate_review_queue.py
```

- [人工复核入口](</Users/yaril/个人文档/3 写作/项目资源库/步步高/physics-digital-library/reviews/人工复核入口.md>) 是日常查看质量的第一入口：它把原始 Word、转换后正文、文档状态卡和每道题的题目卡放在同一页，并附带可点击的正文行号。
- `reports/quality-report.{json,md}` 给出教师用书 `101`、高考题 `72`、必修/选修资料 `443` 的处理情况。报告中的“需人工核对（自动标记）”是图、公式、表格、答案或题目边界的提醒，**不等于转换失败**；“保守未拆题”表示证据不足的编号区块没有被猜成题，但原文仍保留在 Markdown，**不等于内容丢失**。真正需要先处理的是“转换/结构化失败或阻断”。
- `reviews/review-queue.jsonl` 是待办队列：每类资料中已生成且可读取的 document 与 question 至少抽取 10%，并将所有已发现异常和失败来源一并列入。所有队列项固定为 `pending_manual_review`，不含人工 reviewer、decision 或“已审通过”字段。
- `reports/review-queue-summary.json` 记录每一层的候选数、最低抽检数、实际抽检数和覆盖率。抽样由稳定哈希决定，相同输入重复运行得到相同队列。
- 队列不是 `review.schema.json` 所定义的人工审结记录。只有实际人工核对完成后，才可在 `reviews/` 新建带真实 reviewer、decision、summary 和 issues 的 review JSON，并据此推进 `reviewed` 或 `published` 状态。

### 无异常来源转入待审（目录等无题资料）

有些来源已经完成结构化、没有 `exceptions`，但还停留在 `ai_structured`（例如目录资料）。先用下面的单来源入口生成预览；确认后才加 `--apply`：

```bash
python3 项目资源库/步步高/physics-digital-library/scripts/review_workflow.py admit-source \
  --source-id 'src.bbg.<64位SHA-256>' \
  --operator '你的姓名或固定标识' \
  --summary '结构化完成，转入人工复核。'

# 确认预览后才执行；一次只处理一份来源
python3 项目资源库/步步高/physics-digital-library/scripts/review_workflow.py admit-source \
  --source-id 'src.bbg.<64位SHA-256>' \
  --operator '你的姓名或固定标识' \
  --summary '结构化完成，转入人工复核。' \
  --apply
```

该动作会把该来源的 `document` 和当前全部 `question`（若有）从 `ai_structured` 一步转为 `pending_manual_review`，并在 `reports/review-admissions/` 留下审计。它不会创建人工 `review`、不会伪造 reviewer/decision、不会清空问题，也不会修改 `raw/`。有 `exceptions` 的来源必须保留异常并走常规复核，不可用此入口绕过。

### 单题人工复核（正式入口）

不要手工编辑题目状态，也不要把队列项复制成“已通过”。先为一份来源或一条题目生成只读核对单；核对单只写在 `reviews/worklists/`，不会改变任何状态：

```bash
# 终端阅读某一来源的全部当前 document/question；没有写入动作
python3 项目资源库/步步高/physics-digital-library/scripts/review_workflow.py checklist \
  --source-id 'src.bbg.<64位SHA-256>'

# 留下一份本地 Markdown 核对单，便于逐题勾核
python3 项目资源库/步步高/physics-digital-library/scripts/review_workflow.py checklist \
  --source-id 'src.bbg.<64位SHA-256>' \
  --output 'reviews/worklists/<来源短名>-人工核对.md'
```

核对后，先运行提交预览。预览不会写 review JSON 或改目标状态；确认无误后才加 `--apply`。一次命令只能处理一条 `document` 或 `question`，不能批量放行：

```bash
# 真实人工通过后的预览：单题进入 reviewed
python3 项目资源库/步步高/physics-digital-library/scripts/review_workflow.py submit \
  --target-id 'q.src.bbg.<64位SHA-256>.001' \
  --reviewer '你的姓名或固定标识' \
  --decision approved --status reviewed \
  --summary '已对照原始 Word 核对题干、答案、解析、公式和知识点。'

# 确认预览后，才真正写入 review JSON 并更新这一题
python3 项目资源库/步步高/physics-digital-library/scripts/review_workflow.py submit \
  --target-id 'q.src.bbg.<64位SHA-256>.001' \
  --reviewer '你的姓名或固定标识' \
  --decision approved --status reviewed \
  --summary '已对照原始 Word 核对题干、答案、解析、公式和知识点。' \
  --apply

# reviewed 后，单独再提交 published；题目必须已有 knowledge_id，且没有未解决问题
python3 项目资源库/步步高/physics-digital-library/scripts/review_workflow.py submit \
  --target-id 'q.src.bbg.<64位SHA-256>.001' \
  --reviewer '你的姓名或固定标识' \
  --decision approved --status published \
  --summary '复查无遗留问题，允许作为个人本地稳定检索记录。' \
  --apply
```

- `approved` 不允许带未解决 `--issue`；目标现有异常未修复时也不能通过。
- 如果人工核对确认某条既有异常已经在该题上解决，必须把它原样逐项写为 `--resolve-issue '现有异常文本'`；工具会将这些已解决项保留在正式 review JSON 的 `resolved_issues` 中。未逐项确认的异常不能被静默清除。
- `needs_changes` / `rejected` 必须保留至少一条 `--issue`，并让目标保持 `pending_manual_review`；`blocked` 同样必须写明原因。
- 单题 `published` 不会把整份 Word、同来源其他题目或 `sources/sources.jsonl` 自动标记为已发布。这样能避免代表样本通过后误把全库当作人工验收完成。
- 本入口的范围是代表样本的 `document` / `question` 逐条复核；来源级 `sources/sources.jsonl` 的全量发布需要确认该来源的全部文档、题目和异常均已审结后，再走单独的发布门。当前不要手工改来源状态来绕过这一条件。
- 每次提交后运行 `validate_library.py`，并在需要让 SQLite 反映最新状态时运行 `build_index.py`、`generate_report.py`。

### 建索引与本地查询

SQLite 只是可重建索引，JSON/Markdown 和来源清单仍是权威数据。每次新增或修复记录后重建：

```bash
python3 项目资源库/步步高/physics-digital-library/scripts/build_index.py

# 按资料类型/关键词浏览来源；--json 供 Agent 调用
python3 项目资源库/步步高/physics-digital-library/scripts/query_library.py source --profile teacher --keyword '牛顿' --json

# 按课时或章节浏览
python3 项目资源库/步步高/physics-digital-library/scripts/query_library.py lesson --lesson 11 --chapter '牛顿' --json

# 按知识点、模型、题型、来源或关键词筛题
python3 项目资源库/步步高/physics-digital-library/scripts/query_library.py question --knowledge 'kn.bbg.<知识点ID>' --type '实验题' --json

# 从题目反查知识点
python3 项目资源库/步步高/physics-digital-library/scripts/query_library.py knowledge --question 'q.src.bbg.<64位SHA-256>.001' --json
```

查询命令默认输出可阅读文本；添加 `--json` 输出机器可读结果。Agent 应先查询来源或课时，再按返回的相对路径按需读取单份记录，禁止将整库原始内容上传、公开或注入到不受控的第三方服务。

`build_manifest.py` 只在正式 `physics-digital-library` 根中运行，逐个扫描七个批准 `raw/` 链接下的 `.docx`；子目录和文件符号链接均不跟随。它以文件完整 SHA-256 生成 `src.bbg.<64位小写十六进制>`，并稳定排序写入 `sources/sources.jsonl` 与 `reports/source-inventory.json`。路径均为相对于本目录的 `raw/...`，绝不写入绝对路径或 `..`。重复运行不改变字节内容。

当前全库应为：教师用书 `101`、2020–2024 高考题 `72`、必修/选修资料 `443`，合计 `616`。

题目记录的 ID 固定为 `q.<source_id>.<NNN>`，例如 `q.src.bbg.<64位SHA-256>.001`；其中嵌入的 `source_id` 必须与题目记录的 `source_id` 相同。

## 状态机

所有六类记录统一使用以下状态；状态只能反映已完成的工作，不能替代人工验收：

```text
discovered → raw_extracted → ai_structured → pending_manual_review → reviewed → published
                    └──────────────────────────────→ blocked
```

- `discovered`：已入库、尚未提取；source 清单的初始状态。
- `raw_extracted`：原始 Word 已被转换并保留可追溯位置。
- `ai_structured`：已由程序或 AI 形成结构化候选记录。
- `pending_manual_review`：等待人工核对题干、答案、公式、图片或标签。
- `reviewed`：人工已核对，尚未作为稳定可用数据发布。
- `published`：可用于本地检索或组卷；题目必须至少关联一个 `knowledge_id`。
- `blocked`：缺少原件、公式/图片无法可靠解析、版权或其他问题阻止继续处理。

## 资料分类与元数据

构建器仅按路径分类，不读取或推断 Word 正文：

| profile | 原始范围 | 数量 |
|---|---|---:|
| `teacher` | `2026 大一轮/教师用书Word版文档/` | 101 |
| `gaokao` | `2026 大一轮/2020-2024物理高考题/` | 72 |
| `textbook` | 步步高必修/选修六册 | 443 |

路径元数据会保留资料周期、试卷年份、课程册别、目录优先的章节、课时号、原始版本提示和来源形态。目录章节与文件名冲突时，以目录为准，并记录其来源。
