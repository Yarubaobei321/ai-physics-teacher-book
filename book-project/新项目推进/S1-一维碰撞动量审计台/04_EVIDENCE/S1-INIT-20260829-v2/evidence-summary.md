# 证据包：S1 一维碰撞动量审计台

- evidence_id：`evidence-20260829T121301Z`
- 原始需求：在新项目推进目录中新建S1独立工作目录，有价值的成果及时落盘，并保留具有分析价值的过程材料。
- 创建时间：2026-08-29T12:13:01.197472+00:00
- 当前验证状态：`verified`（仅指工作区初始化）
- 隐私状态：`cleared`

## 已记录的验证说明
- 工作区目录和入口文件已创建并核对。
- `事实源.yaml` 成功解析，含 4 项事实和 3 项公式；登记的 6 个本地来源路径均存在。
- 本包 12 项材料逐项 SHA-256 与 manifest 一致，Git 状态记录为 0 项。
- 网页、物理教师终审和课堂效果均未测试。
- v1证据包误带父仓无关Git状态；v2改用非Git上下文生成，缩小到12项S1材料。

## 失败与修正路径
- 第一次生成的 v1 manifest 误带父级写作仓库的大量无关 Git 状态。v2 使用非 Git 上下文重建，保留同样的 12 项 S1 材料，避免把父仓状态当成 S1 证据。

## 材料清单
- `artifact-001`：`artifacts/001-事实源.yaml`，SHA-256 `83426d9b2660b9a80eb2443ab0bab10f2551f59a6bf8146d4af2b4e123018673`
- `artifact-002`：`artifacts/002-人机共同审核方案.md`，SHA-256 `a32ce781ef9e2f3828dd3e2fdedf946b0034b520d4cb270d762bc2c1f89e4676`
- `artifact-003`：`artifacts/003-项目任务书.md`，SHA-256 `8419ef1e8fef190ab620663d7f90428ed2821da889d7fcc97cf4f6970f76197d`
- `artifact-004`：`artifacts/004-README.md`，SHA-256 `afa0c0cc13be4517da96cec577dba61f36a49c5cb0a7f645cd4d7a0cf088588b`
- `artifact-005`：`artifacts/005-价值生长台账.md`，SHA-256 `85738985bdf039d623e85b22953a8b0533a5b396b6bab1f1e33a1b5c7c31e414`
- `artifact-006`：`artifacts/006-决策记录.md`，SHA-256 `ba7d461eabc94919c16af812ed695fc0594e4f59acd8a4d705781bd120f738a7`
- `artifact-007`：`artifacts/007-反馈与版本记录.md`，SHA-256 `3236b82914adb6f18524d081492bcc0ac0d6679572fb7bc0075dad5f2e1386ec`
- `artifact-008`：`artifacts/008-失败与修正记录.md`，SHA-256 `f8b0cc27a8b67280490f10e1f105a5124f743127afe19985e781eb538df17ab6`
- `artifact-009`：`artifacts/009-项目日志.md`，SHA-256 `9f7149cfd8184801928227d8ab35e73870e52b0e2212c752c4d70469e37d313e`
- `artifact-010`：`artifacts/010-入书价值候选.md`，SHA-256 `50b65448232d75886804aca27746db4f7673cba3c365e39c67093d4728c1ceb7`
- `artifact-011`：`artifacts/011-AGENTS.md`，SHA-256 `0ddf4c3570c6cd7aad7928ee7c73a990cf89b098fdc796af4b3200818bb2d8d4`
- `artifact-012`：`artifacts/012-README.md`，SHA-256 `e42d8c2bd112cbf6fb813d926afe6a7c44fb95d4575faa50fa17d721d4e548f3`

## 使用边界
- 软件测试通过不等于实体器材或课堂行为通过。
- 发布前请完成脱敏、授权和回滚检查。
- 本包证明工作区、立项基线与记录机制已经落盘，不证明网页已经实现、物理教师已经终审或课堂效果已经产生。
