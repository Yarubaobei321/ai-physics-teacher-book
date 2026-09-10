# 可运行原型

## 它做什么

- 校验题目数量不超过 10；
- 校验版本 ID、父版本和血缘是否完整；
- 重算登记过的算式，发现数据—答案不一致；
- 比较必要条件与题面条件；
- 检查唯一答案／开放答案的结构是否自洽；
- 比较目标认知动作与题面实际动作；
- 检查来源、课堂时间、材料和安全字段；
- 生成 Markdown、CSV、版本谱系 SVG 和最终版 v-t 参考图。

它不判断题目是否真的“更好”，也不替代课标审读、物理模型审查、版权签字和课堂试测。

## 运行审核

在项目根目录运行：

```bash
python3 02_PROTOTYPE/pipeline.py audit
```

默认读取 `02_PROTOTYPE/sample/lineage.json`，输出到 `03_RECORDS/generated/`。也可以指定其他文件：

```bash
python3 02_PROTOTYPE/pipeline.py audit --input 你的lineage.json --output 输出目录
```

## 生成候选工作单

原型不会替教师自动写完整题目，但能根据策略生成一张必须补全的候选工作单：

```bash
python3 02_PROTOTYPE/pipeline.py propose --question Q001 --parent Q001-O --strategy data_image
```

可用策略：`situation`、`question_chain`、`data_image`、`open_task`。工作单输出到屏幕，不会改原数据。

## 运行测试

```bash
python3 -m unittest discover -s 02_PROTOTYPE/tests -v
```

## 给教师的最小编辑规则

1. 复制一份 `sample/lineage.json`；
2. 每道原题放在一个 `question_id` 下；
3. 修订时新建版本，填写 `parent_id`，不要覆盖旧版；
4. `required` 是得出结论必须具备的条件，`present` 是题面已经明确给出的条件；
5. 答案模式可写 `unique`、`open` 或 `mixed`；混合题要逐小问登记唯一答案和开放答案空间；
6. 只把简单数值复算写入 `physics_checks`；物理模型判断写入 `declared_reviews.physics_truth.reason`；
7. 教师最终处置只能写 `baseline`、`rejected`、`returned` 或 `provisional_final`。
