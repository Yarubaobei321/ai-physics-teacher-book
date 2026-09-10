(function (root, factory) {
  const data = factory();
  if (typeof module === "object" && module.exports) module.exports = data;
  else root.S4_DATA = data;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  return {
    meta: {
      project: "S4 个性化学习路径最小引擎",
      version: "0.1.0",
      rulesetVersion: "rules-0.1.0",
      contentVersion: "mechanical-energy-0.1.0",
      unit: "机械能守恒的条件判断与解题路径选择",
      declaredSyntheticOnly: true,
      networkRequired: false,
      boundary:
        "仅用合成画像演示透明规则流程；不代表真实学生状态，不证明推荐有效，教师保留最终决定。",
    },

    concepts: [
      {
        id: "K1",
        order: 1,
        title: "研究对象与系统",
        short: "先说清机械能属于谁",
        prerequisiteIds: [],
        rationale: "系统边界会影响势能归属、外力做功与守恒条件。",
      },
      {
        id: "K2",
        order: 2,
        title: "能量项与表达",
        short: "识别动能、重力势能与弹性势能",
        prerequisiteIds: ["K1"],
        rationale: "列式前要知道每个状态有哪些机械能，以及它属于哪个系统。",
      },
      {
        id: "K3",
        order: 3,
        title: "外力做功与守恒条件",
        short: "区分受力、做功与能量转移",
        prerequisiteIds: ["K1"],
        rationale: "机械能守恒取决于系统边界和做功情况，不取决于是否“看见其他力”。",
      },
      {
        id: "K4",
        order: 4,
        title: "初末状态表征",
        short: "把速度、高度和形变量放入状态表",
        prerequisiteIds: ["K2", "K3"],
        rationale: "状态表把物理过程转成可核对的能量清单。",
      },
      {
        id: "K5",
        order: 5,
        title: "列式与方法选择",
        short: "守恒时列守恒式，不守恒时换方法",
        prerequisiteIds: ["K4"],
        rationale: "规律选择要跟系统和条件一致，不能先写公式再补理由。",
      },
      {
        id: "K6",
        order: 6,
        title: "结果与边界复核",
        short: "检查单位、符号、特殊值和能量去向",
        prerequisiteIds: ["K5"],
        rationale: "结果检查能暴露零势能面、符号或条件被误用的情况。",
      },
    ],

    resources: [
      {
        id: "R01",
        title: "先画系统圈：机械能属于谁",
        type: "2分钟图解",
        minutes: 2,
        conceptIds: ["K1"],
        summary: "用三个自编小情境练习给物体、地球和弹簧画系统边界。",
        content:
          "先圈出研究系统，再问三件事：哪些能量包含在系统内？哪些力来自系统外？外力是否做功？系统圈改变时，能量账本也会改变。",
        sourceType: "self-authored",
        rightsNote: "S4原型自编文字与示意，不含教材原题或图件。",
      },
      {
        id: "R02",
        title: "势能不是物体的随身标签",
        type: "概念辨析",
        minutes: 3,
        conceptIds: ["K1", "K2"],
        summary: "辨析重力势能、弹性势能的系统归属。",
        content:
          "重力势能描述物体与地球相对位置，弹性势能描述发生形变部分的相互作用。把势能写进哪一本能量账，要先说明系统。",
        sourceType: "self-authored",
        rightsNote: "S4原型自编解释。物理表述待教师审读。",
      },
      {
        id: "R03",
        title: "有力不等于做功",
        type: "反例卡",
        minutes: 3,
        conceptIds: ["K3"],
        summary: "比较支持力垂直位移、拉力做功和阻力做功三种情况。",
        content:
          "判断条件时不要数“有几个力”，要看系统外的力是否在所研究过程中做功。支持力可能不做功；拉力或阻力若做功，会改变系统机械能。",
        sourceType: "self-authored",
        rightsNote: "S4原型自编反例，不复用教材例题。",
      },
      {
        id: "R04",
        title: "把摩擦做功放回能量账",
        type: "错误分析",
        minutes: 4,
        conceptIds: ["K3", "K5"],
        summary: "展示含摩擦过程为何不能直接写初末机械能相等。",
        content:
          "若系统外摩擦力做负功，机械能的变化需要与外力做功对应。此时可以用动能定理或更一般的能量关系，不能把不守恒过程硬写成守恒。",
        sourceType: "self-authored",
        rightsNote: "S4原型自编错误分析。",
      },
      {
        id: "R05",
        title: "零势能面改变了什么",
        type: "一分钟对照",
        minutes: 2,
        conceptIds: ["K2", "K4"],
        summary: "改变参考面后比较势能值与势能差。",
        content:
          "换零势能面会改变每个状态的势能数值，但同一过程的势能差不随之改变。列式时保持同一参考面，并重点核对初末差值。",
        sourceType: "self-authored",
        rightsNote: "S4原型自编对照。",
      },
      {
        id: "R06",
        title: "初末状态能量表",
        type: "可复用模板",
        minutes: 4,
        conceptIds: ["K2", "K4"],
        summary: "用两列表格记录速度、高度、形变量和能量项。",
        content:
          "先写初态和末态，再逐项填写v、h、形变量、Ek、Ep。未知量用符号保留；不存在的能量项写0并说明原因。最后才写关系式。",
        sourceType: "self-authored",
        rightsNote: "S4原型自编模板，可在作者确认后另行决定出版授权。",
      },
      {
        id: "R07",
        title: "竖直抛球：只比较两个状态",
        type: "自编示例",
        minutes: 5,
        conceptIds: ["K4", "K5"],
        summary: "用无具体数值的竖直抛球情境演示状态表和守恒式。",
        content:
          "忽略空气阻力，选球与地球为系统。初态有动能，最高点速度为0；用同一零势能面写出两状态的机械能，再比较。示例只演示结构，不作为教材题。",
        sourceType: "self-authored",
        rightsNote: "S4原型自编无数值情境。",
      },
      {
        id: "R08",
        title: "什么时候改用动能定理",
        type: "方法选择表",
        minutes: 4,
        conceptIds: ["K3", "K5"],
        summary: "从系统、外力做功和所求量判断是否换方法。",
        content:
          "机械能守恒条件清楚且只关心初末状态时可优先用守恒；系统外力做功不可忽略时，先考虑动能定理或功能关系；信息不足时先补条件，不强行选公式。",
        sourceType: "self-authored",
        rightsNote: "S4原型自编方法表。",
      },
      {
        id: "R09",
        title: "三步结果复核",
        type: "检查卡",
        minutes: 3,
        conceptIds: ["K6"],
        summary: "检查单位、极端情况与能量去向。",
        content:
          "第一步看单位与正负号；第二步把初速度或高度取特殊值，看结果是否合理；第三步问机械能增加或减少时，能量从哪里进入或去向哪里。",
        sourceType: "self-authored",
        rightsNote: "S4原型自编检查卡。",
      },
      {
        id: "R10",
        title: "规律选择一页图",
        type: "流程清单",
        minutes: 3,
        conceptIds: ["K1", "K3", "K5", "K6"],
        summary: "把系统—条件—状态—列式—复核连成一页。",
        content:
          "圈系统→列系统外做功→判断守恒条件→列初末能量表→选择守恒式或其他规律→做结果与边界检查。任一步证据不足，都可以停下补查。",
        sourceType: "self-authored",
        rightsNote: "S4原型自编流程。",
      },
    ],

    checks: [
      {
        id: "C01",
        title: "研究对象与守恒条件分拣",
        minutes: 5,
        targetConceptIds: ["K1", "K3"],
        prompt:
          "阅读三个自编情境：理想竖直抛球、粗糙斜面下滑、光滑圆弧运动。分别圈出系统，列出系统外做功，并写“可用机械能守恒／不可直接用／信息不足”及一句理由。",
        rubric:
          "只观察是否明确系统、是否依据做功判断条件；不根据一次结果推断真实认知原因。",
        sourceType: "self-authored",
        rightsNote: "S4原型自编任务，无外部题库内容。",
      },
      {
        id: "C02",
        title: "初末状态能量表",
        minutes: 6,
        targetConceptIds: ["K2", "K4"],
        prompt:
          "对一个无具体数值的竖直抛球过程，自选并声明零势能面，填写初态/最高点的速度、高度、动能、重力势能，并写出哪些量为0及理由。",
        rubric:
          "观察能量项、状态量与参考面是否一致；计算熟练度不作为本任务结论。",
        sourceType: "self-authored",
        rightsNote: "S4原型自编任务。",
      },
      {
        id: "C03",
        title: "守恒列式与替代规律选择",
        minutes: 7,
        targetConceptIds: ["K3", "K5"],
        prompt:
          "比较同一物体在无阻力与存在不可忽略阻力的两段运动。分别选择机械能守恒、动能定理或“先补条件”，写出符号关系式并说明选择依据。",
        rubric:
          "观察规律选择是否与系统和做功条件一致；不要求使用固定解题格式。",
        sourceType: "self-authored",
        rightsNote: "S4原型自编任务。",
      },
      {
        id: "C04",
        title: "换条件后的边界复核",
        minutes: 6,
        targetConceptIds: ["K5", "K6"],
        prompt:
          "给一个已写好的守恒解答依次加入空气阻力、改变零势能面、改变系统边界。逐项判断原关系是否仍可用，并指出需要修改的地方或缺失证据。",
        rubric:
          "观察是否能区分不影响结论的改动与破坏条件的改动；鼓励标出不确定。",
        sourceType: "self-authored",
        rightsNote: "S4原型自编任务。",
      },
    ],

    bundles: [
      { id: "B-K1-A", targetConceptId: "K1", title: "先圈系统，再做三情境分拣", resourceIds: ["R01"], checkId: "C01" },
      { id: "B-K1-B", targetConceptId: "K1", title: "核对势能归属，再复核系统边界", resourceIds: ["R02"], checkId: "C01" },
      { id: "B-K2-A", targetConceptId: "K2", title: "辨析能量归属，再填状态表", resourceIds: ["R02", "R05"], checkId: "C02" },
      { id: "B-K2-B", targetConceptId: "K2", title: "直接用能量表暴露缺项", resourceIds: ["R06"], checkId: "C02" },
      { id: "B-K3-A", targetConceptId: "K3", title: "比较“受力”与“做功”", resourceIds: ["R03", "R04"], checkId: "C01" },
      { id: "B-K3-B", targetConceptId: "K3", title: "从不守恒反例选择替代规律", resourceIds: ["R08"], checkId: "C03" },
      { id: "B-K4-A", targetConceptId: "K4", title: "先填状态表，再解释两个状态", resourceIds: ["R06"], checkId: "C02" },
      { id: "B-K4-B", targetConceptId: "K4", title: "用无数值示例检查状态表达", resourceIds: ["R07"], checkId: "C02" },
      { id: "B-K5-A", targetConceptId: "K5", title: "在守恒式与动能定理之间作选择", resourceIds: ["R08", "R10"], checkId: "C03" },
      { id: "B-K5-B", targetConceptId: "K5", title: "用完整示例复核规律选择", resourceIds: ["R07"], checkId: "C03" },
      { id: "B-K6-A", targetConceptId: "K6", title: "做单位、特殊值与能量去向检查", resourceIds: ["R09"], checkId: "C04" },
      { id: "B-K6-B", targetConceptId: "K6", title: "用一页流程复盘全部边界", resourceIds: ["R10"], checkId: "C04" },
    ],

    verificationCheckByConcept: {
      K1: "C01",
      K2: "C02",
      K3: "C03",
      K4: "C02",
      K5: "C03",
      K6: "C04",
    },

    profiles: [
      {
        id: "SYN-A",
        title: "合成画像A｜条件判断证据待加强",
        note: "本画像完全虚构，只为演示规则。",
        declaredSynthetic: true,
        targetConceptId: "K6",
        initialEvents: [
          { id: "EA-01", checkId: "C01", conceptResults: { K1: "pass", K3: "partial" }, note: "能圈出系统，但把“存在支持力”直接当成不守恒理由。" },
          { id: "EA-02", checkId: "C02", conceptResults: { K2: "pass", K4: "pass" }, note: "能量项和初末状态表在本次任务中完整。" },
          { id: "EA-03", checkId: "C03", conceptResults: { K5: "partial" }, note: "守恒情境能列式，含阻力情境的方法选择犹豫。" },
        ],
      },
      {
        id: "SYN-B",
        title: "合成画像B｜能量表达证据待加强",
        note: "本画像完全虚构，只为演示规则。",
        declaredSynthetic: true,
        targetConceptId: "K6",
        initialEvents: [
          { id: "EB-01", checkId: "C01", conceptResults: { K1: "pass", K3: "pass" }, note: "本次能按系统外做功说明守恒条件。" },
          { id: "EB-02", checkId: "C02", conceptResults: { K2: "not-yet", K4: "partial" }, note: "把最高点动能写为非零，并漏写零势能面。" },
          { id: "EB-03", checkId: "C03", conceptResults: { K5: "partial" }, note: "方法方向合理，但能量项缺失导致关系式不完整。" },
        ],
      },
      {
        id: "SYN-C",
        title: "合成画像C｜证据不足，先补检查",
        note: "本画像完全虚构，只为演示“未知不等于不会”。",
        declaredSynthetic: true,
        targetConceptId: "K6",
        initialEvents: [
          { id: "EC-01", checkId: "C04", conceptResults: { K6: "partial" }, note: "只有一次结果复核记录，不能反推前置节点。" },
        ],
      },
    ],
  };
});
