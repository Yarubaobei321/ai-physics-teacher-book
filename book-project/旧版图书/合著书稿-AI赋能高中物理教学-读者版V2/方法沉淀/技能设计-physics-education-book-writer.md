# `physics-education-book-writer`技能设计

## 目标

把物理教育图书从“AI拼接稿”推进为有真实问题、可追溯证据、物理正确、跨章不重复且能连续阅读的书稿。

## 建议触发语句

- “按两轮写法补齐这本物理教学书。”
- “审查这一章有没有把设计写成实施。”
- “核对真题、公式、实验和网页模型。”
- “为全书确定重复案例的唯一主章。”
- “把实验数据、失败记录和硬件制作增厚到章节中。”
- “生成面向作者的书稿介绍和终审清单。”

## 拟建结构

```text
physics-education-book-writer/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── two-pass-writing.md
│   ├── material-growth.md
│   ├── evidence-and-language.md
│   ├── physics-and-exam-gates.md
│   ├── narrative-and-dedup.md
│   └── author-handoff.md
├── scripts/
│   ├── audit_manuscript.py
│   └── validate_review_ledger.py
└── assets/
    ├── chapter-review-card.md
    ├── chapter-material-growth-map.md
    ├── cross-chapter-ledger.md
    └── author-final-checklist.md
```

## 自动检查的合理边界

脚本可以稳定检查：章节数、审核卡数、图片路径、公式定界符、段落长度、生产语言、重复术语、题目ID、事实档案状态和台账字段。

脚本还可以统计内容来源类型，提示某章是否只有观点解释而缺少题源、数据、装置、失败和产物。该统计用于寻找新的根，不能自动命令“扩写到某字数”。

脚本不能裁定：物理模型是否真的正确、课堂是否发生、作者声音是否真实、图片是否取得法律授权。它只能把这些项目路由到独立审读或作者清单。

## 前向测试

技能完成后，用一份未泄露诊断结论的章节副本测试：

1. 能否发现受力漏项或符号口径混用；
2. 能否区分构造反例与真实母案例；
3. 能否把设计场景降级为方案语气；
4. 能否生成唯一主落点矩阵；
5. 能否输出简洁、可执行的作者交接材料。

测试产物放在临时目录，不覆盖正文。技能通过结构校验和前向测试后再进入工作区`.agents/skills/`。
