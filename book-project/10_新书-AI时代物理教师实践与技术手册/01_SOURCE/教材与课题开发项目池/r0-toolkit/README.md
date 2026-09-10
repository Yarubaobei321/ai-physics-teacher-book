# R0物理模型卡与测量链工具包

> 状态：**R0结构候选**。这里只证明字段、示例和针对性校验脚本能够在本地工作；不代表高中物理教师签发，不代表跨项目共享复用已经成立，也不代表任何课堂、DIS设备或学习效果已验证。

## 这次只解决什么

本目录把四道验收门中的物理模型卡，以及项目组合`U02／U04`提出的最小审核字段，压缩成两份可机器读取的结构：

1. `physics-model-card.schema.json`：记录研究对象、系统边界、区间、假设、变量和单位、数据身份、核心关系、边界、独立真值、五类测试、四门状态与停止条件；
2. `measurement-dataset.schema.json`：记录实测／合成／模型身份、设备、校准、原始文件哈希、通道、直接／代理／派生量、变换、人工处置、异常与结论上限。

当前两个例子分别来自：

- S1一维碰撞动量审计台的v0.3自动预审事实和测试；弹性通式、真实操作、教学与发布仍保持待教师／作者确认；
- 一份明确标为`synthetic`的等质量弹性碰撞位置序列；它只用于验证测量链结构，不冒充传感器或DIS实测。

## 目录

```text
r0-toolkit/
├── README.md
├── package.json
├── schemas/
│   ├── physics-model-card.schema.json
│   └── measurement-dataset.schema.json
├── examples/
│   ├── s1-collision-model-card.json
│   ├── synthetic-collision-measurement-dataset.json
│   └── synthetic-collision-positions.csv
└── tests/
    ├── validate.mjs
    └── fixtures/
        ├── invalid-model-card.json
        └── invalid-measurement-dataset.json
```

## 验证

在本目录运行：

```bash
npm test
```

验证器无第三方依赖，检查：

- 两份JSON Schema自身可解析且保留关键字段；
- S1模型卡满足R0关键约束，但不得把`teacher_review_pending`误写成物理门通过；
- 合成数据集的身份、设备类型、校准状态、通道角色、原始CSV哈希和人工删点留痕一致；
- 两个故意非法样例必须被拒绝，避免“验证器永远说通过”。

这是针对当前两份Schema的最小验证器，不是完整JSON Schema标准实现。将来如果进入真实平台，应采用成熟的JSON Schema验证库，并增加版本迁移、签名、权限、隐私和设备台架测试。

## 当前不能说什么

- 不能说S1已经由物理教师终审；当前四门均未获得完整人工签发。
- 不能说合成CSV来自光电门、视频、传感器或学生实验。
- 不能说这两个Schema已经适配机械能、电磁感应、气体实验或不同厂商DIS。
- 不能说字段完整就等于数据可信、模型正确或教学有效。

## 下一门

先请另一位高中物理教师逐项审读S1模型卡，留下“通过／退回／暂停待确认／停止”之一及证据。之后只选择一套真实但可脱敏的机械能或光电门数据，复制而非覆盖原件，用同一测量链结构做第一次跨对象试填；成功前继续保持R0。
