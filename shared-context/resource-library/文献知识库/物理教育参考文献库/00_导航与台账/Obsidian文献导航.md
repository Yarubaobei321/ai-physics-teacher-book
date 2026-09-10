# Obsidian 文献导航

> 原生视图：![[文献筛选.base]]。以下 Dataview 查询用于兼容和快速嵌入。

## 优先使用

```dataview
TABLE authors AS 作者, year AS 年份, source AS 来源, source_priority AS 来源等级, evidence_grade AS 证据等级, relevance AS 相关性
FROM "项目资源库/文献知识库/物理教育参考文献库"
WHERE type = "literature" AND (favorite = true OR ((source_priority = "A" OR source_priority = "B") AND (evidence_grade = "A" OR evidence_grade = "B") AND relevance = "高"))
SORT source_priority ASC, year DESC
```

## 待核验

```dataview
TABLE authors AS 作者, source AS 来源, metadata_status AS 题录状态, citation_ready AS 引用就绪
FROM "项目资源库/文献知识库/物理教育参考文献库"
WHERE type = "literature" AND metadata_status != "已核验"
SORT literature_id ASC
```

## 引用就绪

```dataview
TABLE authors AS 作者, year AS 年份, source AS 来源, citation_gbt7714 AS "GB/T 7714"
FROM "项目资源库/文献知识库/物理教育参考文献库"
WHERE type = "literature" AND citation_ready = true
SORT source ASC, year DESC
```
