// 项目式学习：面向高一新生的暑假项目式探究作业
// 内容来源：高中物理暑假项目式探究素养学习、测定重力加速度 g 更多实验方案详细指南、
//           实验方案-超声波追踪小车运动（育才物理创新实验室）

export type GravityMethod = {
  id: string;
  name: string;
  badge: string;
  difficulty: number; // 1-3，越大越难
  recommended?: boolean;
  image: {
    src: string;
    alt: string;
  };
  formula: string; // 含 HTML：<span class="formula-frac">、<sub>、<sup>
  formulaNote?: string; // 公式补充（含 HTML）
  principle: string;
  symbols: [string, string][]; // 符号含义，symbol 含 HTML
  gear: string[];
  steps: string[];
  cautions: string[];
  errors: string[];
  advantage: string;
  scene: string;
};

export type ProjectTrack = {
  id: string;
  tag: string;
  title: string;
  audience: string;
  summary: string;
  href: string;
  status: string;
  accent: 'blue' | 'amber' | 'emerald';
};

export type WorkbenchInput = {
  key: string;
  label: string;
  unit: string;
  step?: string;
  min?: string;
};

export type WorkbenchConfig = {
  id: string;
  title: string;
  subtitle: string;
  kind:
    | 'phone-slowmo'
    | 'pendulum'
    | 'accelerometer'
    | 'water-drop'
    | 'spring-scale'
    | 'ht2'
    | 't2l'
    | 'fm'
    | 't2m'
    | 'momentum';
  chart: 'g-bars' | 'scatter' | 'momentum-bars';
  xLabel?: string;
  yLabel?: string;
  resultLabel: string;
  inputs: WorkbenchInput[];
  sampleRows: Record<string, number>[];
  notes: string[];
};

export const projectTracks: ProjectTrack[] = [
  {
    id: 'new-grade-one',
    tag: '第一类',
    title: '新高一：测量深圳本地重力加速度 g',
    audience: '初升高学生',
    summary:
      '从手机慢动作、单摆、手机传感器、滴水和弹簧测力计五种方案中至少完成一种，并在网页中填写数据、自动计算 g 值、导出图表和 CSV。',
    href: '/project-learning/new-grade-one/',
    status: '进入新高一项目',
    accent: 'blue'
  },
  {
    id: 'new-grade-two',
    tag: '第二类',
    title: '新高二：力学综合探究实验',
    audience: '高一升高二学生',
    summary:
      '在测 g 升级版基础上，进入平抛、机械能守恒、动量守恒、弹簧振子和单摆控制变量等综合实验，重点训练图像法和误差分析。',
    href: '/project-learning/new-grade-two/',
    status: '进入新高二项目',
    accent: 'amber'
  },
  {
    id: 'dis-sensor',
    tag: '第三类',
    title: 'DIS传感器实验：ESP32 + 超声波小车',
    audience: '科创兴趣学生（跨年级）',
    summary:
      '使用 ESP32 与 HC-SR04P 超声波传感器采集小车运动数据，在网页端实时绘制 x-t、v-t 图，分析匀速和匀变速直线运动。',
    href: '/project-learning/dis-sensor/',
    status: '进入传感器项目',
    accent: 'emerald'
  }
];

// 五种测 g 方案：推荐方案（手机慢动作）+ 单摆 / 手机传感器 / 滴水 / 弹簧测力计
export const gravityMethods: GravityMethod[] = [
  {
    id: 'phone-slowmo',
    name: '手机慢动作摄像法测自由落体',
    badge: '推荐方案',
    difficulty: 1,
    recommended: true,
    image: {
      src: '/images/project-learning/experiments/新高一方案一.webp',
      alt: '手机慢动作摄像法测自由落体实验示意图'
    },
    formula: 'g = <span class="formula-frac"><span>2h</span><span>t<sup>2</sup></span></span>',
    formulaNote: '由自由落体位移公式 h = <span class="formula-frac"><span>1</span><span>2</span></span>g t<sup>2</sup> 变形得到',
    principle:
      '物体由静止开始自由下落，忽略空气阻力时满足自由落体位移公式，变形即可解出重力加速度。用 240fps 慢动作录下重物下落全程，逐帧计数得到下落总时间 t，配合卷尺测得下落高度 h，便能算出本地 g 值。',
    symbols: [
      ['h', '物体下落竖直高度，单位 m'],
      ['t', '物体完整下落的总时间，单位 s（t = 总帧数 n ÷ 帧率）'],
      ['g', '本地重力加速度，单位 m/s²']
    ],
    gear: [
      '智能手机（支持 120fps / 240fps 慢动作拍摄）',
      '金属钥匙串（小重物，减小空气阻力影响）',
      '卷尺、书本（固定手机支架）',
      '白纸、马克笔（墙面高度标记）'
    ],
    steps: [
      '选取平整垂直墙面，用马克笔标记上下两个点位，卷尺多次测量两点竖直距离，记录下落高度 h。',
      '将手机倚靠书本固定，镜头正对标记区域，保证完整拍摄重物下落全程，开启高帧率慢动作模式。',
      '手紧贴上方标记处静止释放钥匙，不施加向上或向下推力，完整录制下落至地面的全过程。',
      '回放录像逐帧计数：记录重物释放至落地的总帧数 n，由 t = n ÷ 帧率 计算下落总时间。',
      '重复完整实验 3 次，分别记录数据并单独计算每组 g 值，最后取平均值减小偶然误差。'
    ],
    cautions: [
      '释放重物时必须保持初速度为 0，避免人为施加推力造成数据偏差。',
      '拍摄画面完整包含高度标记，保证竖直下落轨迹清晰无遮挡。',
      '优先选用 240fps 高帧率模式，帧数越多，时间测量精度越高。',
      '卷尺测量高度时视线与刻度平齐，减少长度读数误差。'
    ],
    errors: [
      '系统误差：重物下落受空气阻力干扰。',
      '人为偶然误差：释放存在初速度、视频帧数计数出错、卷尺读数偏差。',
      '装置误差：手机倾斜导致高度测量并非纯竖直距离。'
    ],
    advantage: '器材最易得、过程直观，是暑假作业的首选方案。',
    scene: '人人可做的首选方案'
  },
  {
    id: 'pendulum',
    name: '单摆法',
    badge: '经典严谨',
    difficulty: 2,
    image: {
      src: '/images/project-learning/experiments/新高一方案二.webp',
      alt: '单摆法测量重力加速度实验示意图'
    },
    formula: 'g = <span class="formula-frac"><span>4π<sup>2</sup>L</span><span>T<sup>2</sup></span></span>',
    formulaNote: '由单摆周期公式 T = 2π√(L / g) 变形得到',
    principle:
      '单摆在摆角很小（θ < 5°）时近似做简谐运动，周期与摆长满足周期公式，变形即可解出 g。其中 L 为摆长（悬挂点到摆球质心的距离），T 为单摆完成一次全振动的周期。',
    symbols: [
      ['L', '摆长，悬挂点到摆球质心的距离，单位 m'],
      ['T', '单摆完成一次全振动的周期，单位 s'],
      ['g', '本地重力加速度，单位 m/s²']
    ],
    gear: [
      '细缝纫线或钓鱼线（约 1–1.5 m）',
      '金属螺母或小钢球（充当摆球）',
      '卷尺、智能手机秒表',
      '铅笔或筷子（悬挂支点）、量角器 / 手机量角 App'
    ],
    steps: [
      '细线一端系紧螺母，另一端绑在铅笔上，将铅笔水平架于门框顶部或固定在桌沿，确保摆球可在竖直平面内自由摆动。',
      '用卷尺测量悬挂点到螺母中心的距离记为摆长 L，重复测量 3 次取平均值。',
      '将摆球拉至偏离竖直方向约 3°–5°（小角度）静止释放（不要推），让其自然摆动。',
      '待摆动稳定后用秒表计时 30 个全振动的总时间 t，计算单次周期 T = t / 30。',
      '重复实验 3 次，分别计算每组 g 值后取平均值。'
    ],
    cautions: [
      '摆角必须控制在 5° 以内，角度过大会使周期公式失效。',
      '摆球应在同一竖直平面内摆动，发现画圈应重新释放。',
      '计时应从摆球经过最低点（速度最快处）开始，位置判断最准。',
      '选用细而轻的线、小而重的球，更接近理想单摆模型。'
    ],
    errors: [
      '系统误差：摆角偏大导致周期偏长，测得 g 偏小；摆线有质量和弹性使等效摆长不准。',
      '人为偶然误差：秒表启停反应延迟、计数出错、摆长测量不到球心。',
      '装置误差：悬挂点不牢导致有效摆长变化；摆球出平面做圆锥运动。'
    ],
    advantage: '原理清晰、过程完整，适合追求严谨探究的同学。',
    scene: '追求完整探究过程'
  },
  {
    id: 'accelerometer',
    name: '手机加速度传感器法',
    badge: '操作极简',
    difficulty: 1,
    image: {
      src: '/images/project-learning/experiments/新高一方案三.webp',
      alt: '手机加速度传感器法测量重力加速度实验示意图'
    },
    formula: 'g = a<sub>z</sub>',
    formulaNote: '手机水平静置时 z 轴加速度读数即为 g',
    principle:
      '智能手机内置三轴加速度传感器（MEMS 加速度计），可直接测量手机所受加速度。手机水平静置时传感器测得的合加速度即为 g。进阶法：让手机自由下落到软垫上，下落阶段处于失重状态，分析加速度–时间图像即可读取自由落体阶段的加速度。',
    symbols: [
      ['a<sub>z</sub>', '传感器 z 轴（竖直方向）加速度读数，单位 m/s²'],
      ['g', '本地重力加速度，单位 m/s²']
    ],
    gear: [
      '智能手机（安卓或 iPhone 均可）',
      '物理传感器 App（推荐 phyphox，免费开源）',
      '厚海绵垫或叠放的枕头（缓冲落地）',
      '卷尺'
    ],
    steps: [
      '方法 A 静态测量：打开 phyphox，选择"加速度（含 g）"模块。',
      '将手机平放在水平桌面上，开始记录，静置 10 秒后停止。',
      '查看 z 轴读数（约 9.8 m/s²），取 10 秒内平均值作为 g。',
      '方法 B 自由落体（进阶）：铺好至少 20 cm 厚软垫，设置最高采样率，约 1 m 高度松手让手机落下。',
      '在加速度–时间图像中找到读数接近 0 的平台段，重复 3 次取平均。'
    ],
    cautions: [
      '使用"含 g"模式时静态读数直接为 g；"不含 g"模式静态读数为 0。',
      '手机必须保持水平，倾斜会使 z 轴分量不等于 g 全量。',
      '自由落体法务必做好缓冲保护，避免手机屏幕碎裂。',
      '不同手机传感器精度不同，中高端机精度通常更高。'
    ],
    errors: [
      '系统误差：传感器零点漂移与出厂校准偏差。',
      '装置误差：手机未水平放置导致重力分量分配到多个轴。',
      '人为偶然误差：自由落体释放时手施加额外力、图像区间选取不准。'
    ],
    advantage: '操作极简，几分钟即可拿到数据。',
    scene: '快速获取数据'
  },
  {
    id: 'water-drop',
    name: '滴水法',
    badge: '创意趣味',
    difficulty: 3,
    image: {
      src: '/images/project-learning/experiments/新高一方案四.webp',
      alt: '滴水法测量重力加速度实验示意图'
    },
    formula: 'g = <span class="formula-frac"><span>2h</span><span>t<sup>2</sup></span></span>',
    formulaNote: '相邻两滴间隔 t 即一滴自由下落时间，由 h = <span class="formula-frac"><span>1</span><span>2</span></span>g t<sup>2</sup> 得到',
    principle:
      '调节水龙头（或输液管阀门）滴速，使上一滴水恰好落到接水盘的同时下一滴刚好从滴口脱落。此时相邻两滴的时间间隔 t 恰等于一滴水自由下落到盘面所用时间。测量滴口到水面竖直高度 h，即可解出 g。',
    symbols: [
      ['h', '滴口到接水盘水面的竖直高度，单位 m'],
      ['t', '相邻两滴的时间间隔，单位 s'],
      ['g', '本地重力加速度，单位 m/s²']
    ],
    gear: [
      '可调节流速的水龙头或一次性输液器',
      '金属盘或碟子（接水，落水声清脆便于判断）',
      '卷尺、智能手机秒表',
      '椅子或梯子（调节高度）'
    ],
    steps: [
      '接水金属盘放在地面正下方，卷尺测量滴口到盘面竖直高度 h，重复 3 次取平均。',
      '缓慢调节滴速，仔细看和听：一滴落盘发出"嘀"声的同时恰好看到下一滴脱落，即滴速调到位。',
      '反复微调，直到"滴落声"与"新滴脱落"严格同步。',
      '滴速稳定后用秒表计连续 50 滴的总时间 t₀，单滴间隔 t = t₀ / 50。',
      '重复实验 3 次（每次重新调节滴速），分别计算 g 后取平均。'
    ],
    cautions: [
      '调节滴速是本实验最关键也最耗时的步骤，需在安静环境中操作。',
      '使用输液器比水龙头更易精细调节，推荐优先使用。',
      '高度 h 建议设置在 1.0–1.5 m 之间。',
      '接水盘用金属材质，声音清脆便于判断同步时刻。'
    ],
    errors: [
      '系统误差：水滴受空气阻力，实际加速度略小于 g，测量值偏小。',
      '人为偶然误差：判断"同步"主观性强，不同人感知存在差异。',
      '装置误差：滴速在实验中可能缓慢漂移（水压变化）；高度起止点不精确。'
    ],
    advantage: '创意独特、趣味性强，适合喜欢动手调试的同学。',
    scene: '喜欢动手调试'
  },
  {
    id: 'spring-scale',
    name: '弹簧测力计 + 已知质量法',
    badge: '原理最直接',
    difficulty: 1,
    image: {
      src: '/images/project-learning/experiments/新高一方案五.webp',
      alt: '弹簧测力计加已知质量法测量重力加速度实验示意图'
    },
    formula: 'g = <span class="formula-frac"><span>F</span><span>m</span></span>',
    formulaNote: '由重力公式 G = mg，静止时测力计示数 F = G 变形得到；进阶取 F–m 图像斜率',
    principle:
      '竖直悬挂已知质量 m 的物体，静止时弹簧测力计示数 F 即等于重力 G，故可解出 g。进阶：以质量 m 为横轴、读数 F 为纵轴作图，过原点直线的斜率 k 即为 g，图像法比逐组取平均更能减小随机误差。',
    symbols: [
      ['F', '弹簧测力计读数，即物体所受重力，单位 N'],
      ['m', '物体质量，用电子秤精确标定，单位 kg'],
      ['g', '本地重力加速度，单位 m/s²']
    ],
    gear: [
      '弹簧测力计（量程 5 N 或 10 N）',
      '厨房电子秤（精度 0.1 g 或 1 g）',
      '不同质量重物 3–5 个（如装不同量水的水瓶、金属块）',
      '细线'
    ],
    steps: [
      '用电子秤逐个称量重物质量 m（换算为 kg），每个测 3 次取平均。',
      '将弹簧测力计竖直悬挂并检查归零，若未归零记录零点偏差后续修正。',
      '用细线把重物挂在挂钩上，待指针完全静止后读取示数 F，视线与刻度盘垂直。',
      '依次悬挂不同质量重物，分别记录 F 和对应 m。',
      '对每组计算 g = F/m 取平均；进阶用 F–m 图像拟合直线，斜率即 g。'
    ],
    cautions: [
      '弹簧测力计使用前必须校零，使用中不得超过量程。',
      '读数时测力计必须竖直且静止，重物晃动应等待静止。',
      '电子秤标定时确保秤台水平且已去皮归零。',
      '选用不同质量梯度的重物，数据点分布越均匀，拟合越准。'
    ],
    errors: [
      '系统误差：测力计刻度标定不准、弹簧老化弹性系数变化。',
      '人为偶然误差：读数视差、重物晃动时急于读数。',
      '装置误差：电子秤精度有限、测力计分度值较大。'
    ],
    advantage: '原理最直接，可作为其他方案的对照验证实验。',
    scene: '验证其他方案结果'
  }
];

export const methodComparison = gravityMethods.map((m) => ({
  name: m.name,
  difficulty: '★★★'.slice(0, m.difficulty) + '☆☆☆'.slice(0, 3 - m.difficulty),
  advantage: m.advantage,
  scene: m.scene
}));

export const reportSpec = {
  cover: ['项目探究名称', '完成日期'],
  body: [
    ['情境引入（50 字左右）', '结合跳楼机 / 高空下落等生活实例，说明测量本地重力加速度的实际意义。'],
    ['实验方案与原理', '说明所选方案的理由，书写核心公式并标注各物理量含义。'],
    ['器材清单', '如实列出实验使用的全部工具。'],
    ['实验操作步骤', '分点记录实际操作流程，配套 3–5 张实拍图（装置、测量、读数、数据记录等）。'],
    ['数据处理与误差分析', '设计表格记录原始数据，分步计算每组 g、平均 g，对比标准值算百分误差。'],
    ['结论与反思（100–150 字）', '写明实测平均 g 值，指出最大误差来源，提出优化改进方案。']
  ] as [string, string][],
  bonus: '制作 1–2 分钟实验短视频，完整展示装置搭建、下落拍摄、帧数读数等关键过程，画面配简单文字说明（可选加分项）。',
  submit: '将探究报告与实验短视频整理归档，妥善保存原始数据与图片，方便后续复盘与改进。',
  rewards: [
    '优秀方案会在本站「实验记录分享」中整理展示，供后续同类实验参考。'
  ]
};

export const previewQuestions = [
  '自主预习高中物理必修一前两章，梳理运动学公式及标准重力加速度取值。',
  '自主推导本实验核心公式，理清推导逻辑，理解运动学公式适用条件。',
  '思考题①：你测得的深圳 g 平均值与 9.8 m/s² 相比偏大还是偏小？结合操作分析误差来源。',
  '思考题②：若将本套器材带到月球重复实验，测得的重力加速度会如何变化？说明原理。'
];

// ===== 选做科创实验：ESP32 + HC-SR04P 超声波追踪小车运动 =====

export const ultrasonicExperiment = {
  title: 'ESP32 + 超声波传感器追踪小车运动',
  image: {
    src: '/images/project-learning/experiments/esp32-hc-sr04p-overview.webp',
    alt: 'ESP32 超声波传感器追踪小车运动实验示意图'
  },
  goal:
    '用 ESP32 + HC-SR04P 超声波传感器实时追踪运动小车的位置，自动采集位移–时间数据，验证匀速直线运动和匀变速直线运动规律，绘制 x-t 图和 v-t 图。',
  formula: 'd = <span class="formula-frac"><span>v<sub>声</sub> · Δt</span><span>2</span></span>',
  formulaNote: 'v<sub>声</sub> ≈ 340 m/s（20℃ 空气中声速），Δt 为超声波往返时间',
  principle:
    'HC-SR04P 发射 40kHz 超声波脉冲并接收回波，测量往返时间 Δt，据此算出传感器到小车的距离。ESP32 每隔 50 ms 测一次，即得位移–时间序列：x-t 为直线说明匀速运动，斜率为速度 v；x-t 为抛物线说明匀变速运动，差分得 v-t 图，其斜率即加速度 a。',
  gear: [
    ['ESP32 开发板', 'ESP32-38Pin CH340 TYPE-C', '18 元'],
    ['扩展板', 'ESP32-38Pin 扩展板（配套）', '7 元'],
    ['HC-SR04P 超声波模块', '3.3V–5.5V 宽电压版，探测 2–400 cm', '5 元'],
    ['杜邦线', '40P 母对母杜邦线', '4 元'],
    ['长直轨道', '窗帘导轨 / 铝型材 / 光滑木板，长 1–2 m', '自制'],
    ['小车', '玩具小车或自制滑块，背面贴硬纸板增大反射面', '自备'],
    ['书本', '3–5 本，垫高轨道一端制造倾斜面', '自备'],
    ['Type-C 数据线 + 电脑', '必须是数据线（非纯充电线）', '自备']
  ] as [string, string, string][],
  cost: '总电子器材成本约 30 元',
  wiring: [
    ['VCC', '3V3（3.3V 供电，重要！不要接 5V）'],
    ['GND', 'GND'],
    ['Trig', 'G5（GPIO 5）'],
    ['Echo', 'G18（GPIO 18）']
  ] as [string, string][],
  experiments: [
    {
      tag: '实验 A',
      name: '匀速直线运动',
      points: [
        '轨道水平放置在桌面或地面（用手机水平仪校准）。',
        '传感器固定在轨道一端，探头朝向轨道方向。',
        '上传采集程序，打开串口监视器（波特率 115200）。',
        '小车距传感器约 10 cm，背面贴 10cm×10cm 硬纸板增大反射面。',
        '按 BOOT 开始采集，给小车一个均匀推力让它匀速滑离传感器。',
        '到达末端后再按 BOOT 停止，复制 CSV 数据。'
      ]
    },
    {
      tag: '实验 B',
      name: '匀变速直线运动',
      points: [
        '用书本垫高轨道一端，形成 5°–15° 倾斜面。',
        '传感器固定在高端（斜面顶部），探头朝下坡方向。',
        '小车放在传感器下方约 5–10 cm 处。',
        '按 BOOT 开始采集，松手释放小车（不要推！保证初速度为 0）。',
        '小车自然加速下滑，到底端后按 BOOT 停止。',
        '复制 CSV 数据。每个实验重复 3 次取最完整的一组分析。'
      ]
    }
  ],
  cautions: [
    '传感器对准：超声波束约 15° 扩散角，探头必须正对小车运动方向。',
    '反射面：小车背面贴的硬纸板要大且垂直于运动方向，效果远好于圆形物体。',
    '最小距离：HC-SR04P 盲区约 2–3 cm，小车起始位置距传感器至少 5 cm。',
    '轨道平直：轨道弯曲会让小车偏离声束，数据出现异常跳点。',
    '匀变速实验：释放时手不能施力，保证初速度为 0；倾角 < 15°。',
    '数据清洗：个别跳变异常值（错误回波）在处理时手动删除离群点。'
  ],
  thinking: [
    '你测得的匀变速运动加速度 a 与理论值 g·sinθ 相比偏大还是偏小？分析可能原因。',
    '若把采样间隔从 50 ms 改为 20 ms，对实验精度有何影响？会不会引入新问题？',
    '超声波速度 v = 331.3 + 0.606T（T 为室温 ℃），35°C 时声速是多少？用修正值重算距离与默认 340 m/s 差多少？',
    '（进阶）能否用本装置测重力加速度 g？提示：改变倾角 θ 做多组实验，以 sinθ 为横轴、a 为纵轴作图，斜率是什么？'
  ]
};

// 采集程序源码（MicroPython）：上传到 ESP32 后，持续通过串口输出
// time_ms,distance_cm 的 CSV，网页端负责开始/停止记录与作图。
export const collectorProgram = `# ============================================
# 超声波追踪小车运动 - 数据采集（MicroPython）
# 上传后持续打印 CSV：time_ms,distance_cm
# 由网页实验室负责「开始记录 / 停止记录」与作图
# ============================================
from machine import Pin, time_pulse_us
import time

trig = Pin(5, Pin.OUT)    # Trig -> G5
echo = Pin(18, Pin.IN)    # Echo -> G18

def measure_cm():
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)
    # 等待回波，超时 30ms（约 5m）
    dur = time_pulse_us(echo, 1, 30000)
    if dur < 0:
        return -1.0
    return dur * 0.0343 / 2.0   # 声速 343 m/s，往返除以 2，单位 cm

print("time_ms,distance_cm")   # CSV 表头
start = time.ticks_ms()
while True:
    t = time.ticks_diff(time.ticks_ms(), start)
    d = measure_cm()
    if 0 < d < 400:            # 有效范围 0–400 cm
        print("{},{:.2f}".format(t, d))
    time.sleep_ms(50)          # 采样间隔 50ms（约 20Hz）`;

export const sampleUniformData = `time_ms,distance_cm
0,10.2
50,15.4
100,20.1
150,25.3
200,30.0
250,35.2
300,40.1
350,45.0
400,50.3
450,55.1
500,60.2
550,65.0
600,70.4
650,75.1
700,80.0`;

export const sampleAcceleratedData = `time_ms,distance_cm
0,6.0
50,6.6
100,7.5
150,8.9
200,10.6
250,12.7
300,15.2
350,18.1
400,21.4
450,25.1
500,29.2
550,33.7
600,38.6
650,43.9
700,49.6`;

export const gradeOneWorkbenches: WorkbenchConfig[] = [
  {
    id: 'phone-slowmo',
    title: '手机慢动作摄像法数据表',
    subtitle: '填写下落高度、逐帧数和帧率，网页自动计算下落时间、每组 g 值和相对 9.8 m/s² 的误差。',
    kind: 'phone-slowmo',
    chart: 'g-bars',
    resultLabel: '平均 g',
    inputs: [
      { key: 'h', label: '下落高度 h', unit: 'm', step: '0.01', min: '0' },
      { key: 'frames', label: '总帧数 n', unit: '帧', step: '1', min: '1' },
      { key: 'fps', label: '帧率', unit: 'fps', step: '1', min: '1' }
    ],
    sampleRows: [
      { h: 1.2, frames: 119, fps: 240 },
      { h: 1.2, frames: 118, fps: 240 },
      { h: 1.2, frames: 120, fps: 240 }
    ],
    notes: ['公式：t = n / fps，g = 2h / t²。', '如果三组 g 值离散很大，优先检查释放是否有初速度、帧数是否数错。']
  },
  {
    id: 'pendulum',
    title: '单摆法数据表',
    subtitle: '填写摆长、若干次全振动总时间和振动次数，网页自动计算周期 T 与 g。',
    kind: 'pendulum',
    chart: 'g-bars',
    resultLabel: '平均 g',
    inputs: [
      { key: 'L', label: '摆长 L', unit: 'm', step: '0.001', min: '0' },
      { key: 'totalTime', label: '总时间', unit: 's', step: '0.01', min: '0' },
      { key: 'cycles', label: '全振动次数', unit: '次', step: '1', min: '1' }
    ],
    sampleRows: [
      { L: 0.82, totalTime: 54.4, cycles: 30 },
      { L: 0.82, totalTime: 54.2, cycles: 30 },
      { L: 0.82, totalTime: 54.6, cycles: 30 }
    ],
    notes: ['公式：T = 总时间 / 次数，g = 4π²L / T²。', '摆角建议控制在 5° 内，摆长要量到摆球质心。']
  },
  {
    id: 'accelerometer',
    title: '手机加速度传感器数据表',
    subtitle: '填写三轴加速度读数，网页自动计算合加速度 g = √(ax² + ay² + az²)。',
    kind: 'accelerometer',
    chart: 'g-bars',
    resultLabel: '平均合加速度',
    inputs: [
      { key: 'ax', label: 'ax', unit: 'm/s²', step: '0.01' },
      { key: 'ay', label: 'ay', unit: 'm/s²', step: '0.01' },
      { key: 'az', label: 'az', unit: 'm/s²', step: '0.01' }
    ],
    sampleRows: [
      { ax: 0.04, ay: -0.03, az: 9.79 },
      { ax: 0.02, ay: 0.01, az: 9.81 },
      { ax: -0.03, ay: 0.02, az: 9.8 }
    ],
    notes: ['手机静止水平放置时，合加速度接近当地 g。', '如果使用“不含 g”的加速度模式，静止读数会接近 0，不适用于这张表。']
  },
  {
    id: 'water-drop',
    title: '滴水法数据表',
    subtitle: '填写滴口高度、多滴总时间和滴数，网页自动计算单滴间隔 t 与 g。',
    kind: 'water-drop',
    chart: 'g-bars',
    resultLabel: '平均 g',
    inputs: [
      { key: 'h', label: '滴落高度 h', unit: 'm', step: '0.01', min: '0' },
      { key: 'totalTime', label: '多滴总时间', unit: 's', step: '0.01', min: '0' },
      { key: 'drops', label: '滴数', unit: '滴', step: '1', min: '1' }
    ],
    sampleRows: [
      { h: 1.25, totalTime: 25.2, drops: 50 },
      { h: 1.25, totalTime: 25.5, drops: 50 },
      { h: 1.25, totalTime: 25.3, drops: 50 }
    ],
    notes: ['公式：t = 总时间 / 滴数，g = 2h / t²。', '滴速同步判断主观性强，建议安静环境下反复微调。']
  },
  {
    id: 'spring-scale',
    title: '弹簧测力计图像法数据表',
    subtitle: '填写质量和测力计读数，网页逐组计算 g，并用 F-m 图像拟合斜率作为 g。',
    kind: 'spring-scale',
    chart: 'scatter',
    xLabel: '质量 m / kg',
    yLabel: '拉力 F / N',
    resultLabel: 'F-m 拟合斜率',
    inputs: [
      { key: 'm', label: '质量 m', unit: 'kg', step: '0.001', min: '0' },
      { key: 'F', label: '拉力 F', unit: 'N', step: '0.01', min: '0' }
    ],
    sampleRows: [
      { m: 0.1, F: 0.98 },
      { m: 0.2, F: 1.96 },
      { m: 0.3, F: 2.93 },
      { m: 0.4, F: 3.92 }
    ],
    notes: ['图像法：F = gm，过原点直线斜率约为 g。', '质量点分布越均匀，拟合结果越稳定。']
  }
];

export const gradeTwoUpgradeTasks = [
  {
    title: 'A 类：测量 g 值（高二升级版）',
    text: '任选新高一方案继续升级，重点不是“再做一遍”，而是使用图像法、有效数字和多方案对比来提升数据处理质量。',
    points: ['用 h-t²、T²-L 或 F-m 图像求斜率。', '至少比较两种实验方案，说明系统误差方向。', '报告中保留原始数据，不只写整理后的结论。']
  },
  {
    title: 'B 类：力学综合实验',
    text: '围绕必修一、必修二和选择性必修一内容，完成一个能体现建模、测量、作图和误差分析的综合实验。',
    points: ['水平抛体运动：测初速度并验证运动独立性。', '验证机械能守恒：优先使用本站在线实验室已有方案。', '碰撞中的动量守恒：对比碰前碰后总动量。', '弹簧振子和单摆控制变量：用图像判断变量关系。']
  }
];

export const gradeTwoExperiments = [
  {
    code: 'B1',
    title: '水平抛体运动：测量初速度与验证独立性原理',
    image: {
      src: '/images/project-learning/experiments/新高二B1.webp',
      alt: '水平抛体运动实验示意图'
    },
    goal: '固定小球离开桌面的初速度，改变桌面高度，检验水平方向匀速直线运动与竖直方向自由落体运动是否相互独立。',
    formula: 'v₀ = x√(g/2h)，x² = (2v₀²/g)h',
    principle: '小球从桌边水平飞出后，竖直方向满足 h = 1/2gt²，水平方向满足 x = v₀t。消去时间 t 后，可以由落点距离 x 和桌面高度 h 求初速度；若固定 v₀ 改变 h，x²-h 图像应接近过原点直线。',
    gear: ['光滑斜面或硬纸板轨道', '小钢球或玻璃弹珠', '碳纸与白纸', '卷尺', '不同高度桌面或台阶'],
    steps: ['搭建斜面，使小球从同一高度释放后水平飞出桌面。', '在地面铺白纸和碳纸，记录小球落点。', '测量桌面高度 h 与水平飞行距离 x，固定高度重复 5 次。', '改变桌面高度重复实验，比较 x² 与 h 的关系。'],
    dataTips: ['固定高度时求平均水平距离和标准差，判断落点离散程度。', '不同高度时画 x²-h 散点图，拟合斜率 k = 2v₀²/g。', '若图线不通过原点，重点检查释放高度是否一致、桌边是否水平、落点测量基准是否准确。'],
    workbenchHint: '可使用下方 h-t² 或自建 x²-h 表格完成图像法分析。',
    link: ''
  },
  {
    code: 'B2',
    title: '验证机械能守恒定律',
    image: {
      src: '/images/project-learning/experiments/新高二B2.webp',
      alt: '验证机械能守恒定律实验示意图'
    },
    goal: '改变释放高度，测量小球或小车底端速度，用 v²-h 图像判断重力势能减少量是否主要转化为动能。',
    formula: 'mgh = 1/2mv²，v² = 2gh',
    principle: '若摩擦、空气阻力和转动动能影响较小，小球从高度 h 由静止释放到底端时满足 mgh = 1/2mv²。因此 v² 与 h 应近似成正比，斜率理论值为 2g。',
    gear: ['光滑斜面轨道', '小车或小球', '手机慢动作摄像', '卷尺', '量角器或高度标尺'],
    steps: ['搭建斜面轨道，在底端水平段标出两条间距已知的速度测量线。', '用手机慢动作拍摄小球通过底端标记段的过程。', '改变释放高度 h，逐组计算底端速度 v。', '绘制 v²-h 图像，比较斜率与 2g 的偏差。'],
    dataTips: ['记录释放高度、标记间距、通过帧数、帧率和底端速度。', '若实际斜率小于 2g，通常要讨论摩擦、转动动能和测速误差。', '机械能守恒类实验优先使用本站已有在线实验室完成更完整的数据处理。'],
    workbenchHint: '优先进入在线实验室，那里已有机械能守恒表格、图像和导出功能。',
    link: '/online-lab/mechanical-energy/'
  },
  {
    code: 'B3',
    title: '碰撞中的动量守恒',
    image: {
      src: '/images/project-learning/experiments/新高二B3.webp',
      alt: '碰撞中的动量守恒实验示意图'
    },
    goal: '用两个小球碰撞前后的水平飞行距离间接表示速度，比较碰前和碰后总动量是否近似相等。',
    formula: 'm₁v₁ + m₂v₂ = m₁v₁′ + m₂v₂′',
    principle: '当水平方向合外力可忽略时，两球组成的系统总动量近似守恒。若碰撞前后都从同一高度水平飞出，飞行时间相同，水平距离与水平速度成正比，因此可用 m·x 的和来比较碰撞前后动量。',
    gear: ['两个大小接近的钢球或玻璃弹珠', '斜面与水平槽', '碳纸与白纸', '电子秤', '卷尺'],
    steps: ['称量入射球 m₁ 和靶球 m₂ 的质量。', '先测 m₁ 不碰撞时的水平飞行距离 x₀。', '把 m₂ 放在轨道末端静止，让 m₁ 从同一高度释放并发生碰撞。', '记录碰后 m₁ 和 m₂ 的落点距离 x₁′、x₂′，重复多次取平均。'],
    dataTips: ['比较 m₁x₀ 与 m₁x₁′ + m₂x₂′ 的相对偏差。', '速度方向要先规定，若碰后反弹，需要把对应距离或速度记为负方向。', '偏差大时检查碰撞是否正碰、轨道是否水平、桌面边缘是否改变小球方向。'],
    workbenchHint: '可使用下方“碰撞动量守恒对比表”输入质量和速度；若用落点距离代替速度，保持单位一致即可。',
    link: ''
  },
  {
    code: 'B4',
    title: '弹簧振子：探究周期与质量的关系',
    image: {
      src: '/images/project-learning/experiments/新高二B4.webp',
      alt: '弹簧振子探究周期与质量关系实验示意图'
    },
    goal: '改变悬挂质量，测量弹簧振子的周期，用 T²-m 图像求弹簧劲度系数并分析截距含义。',
    formula: 'T = 2π√(m/k)',
    principle: '理想弹簧振子的周期满足 T = 2π√(m/k)，变形得 T² = (4π²/k)m。因此 T²-m 图像应接近直线，斜率 k′ = 4π²/k，可反推出弹簧劲度系数 k。',
    gear: ['弹簧或弹簧测力计中的弹簧', '不同质量钩码或螺母', '电子秤', '手机秒表', '固定支架或门框挂钩'],
    steps: ['将弹簧竖直固定，下端依次悬挂不同质量。', '轻轻拉下重物后释放，控制振幅不要过大。', '每组记录 20 次全振动总时间，计算周期 T。', '至少测 5 组质量，绘制 T²-m 图像。'],
    dataTips: ['用斜率求 k = 4π²/k′，不要只比较周期大小。', '截距不为 0 时，可讨论弹簧自身质量、计时反应和振幅过大的影响。', '同一组质量建议至少重复 2 次，避免个别计时误差影响拟合。'],
    workbenchHint: '可直接使用下方“弹簧振子 T²-m 图像”工作台。',
    link: ''
  },
  {
    code: 'B5',
    title: '单摆探究：周期与摆长、摆角、质量的关系',
    image: {
      src: '/images/project-learning/experiments/新高二B5.webp',
      alt: '单摆控制变量探究实验示意图'
    },
    goal: '通过三组控制变量实验，判断单摆周期主要由摆长决定，并观察小角度条件的适用范围。',
    formula: 'T = 2π√(L/g)',
    principle: '小角度条件下，单摆周期近似满足 T = 2π√(L/g)，与摆球质量无关；当摆角增大时，小角度近似失效，周期会出现可观察的变化。',
    gear: ['细线', '不同质量摆球或螺母', '量角器', '卷尺', '手机秒表', '固定支架'],
    steps: ['实验 a：固定质量和摆角，改变摆长，验证 T² 与 L 的线性关系。', '实验 b：固定摆长和摆角，改变摆球质量，观察周期是否基本不变。', '实验 c：固定摆长和质量，改变摆角，观察大角度下周期变化。', '每组至少计时 20 或 30 次全振动，减少人为反应误差。'],
    dataTips: ['实验 a 画 T²-L 图像，斜率可用于反算 g。', '实验 b 用列表对比不同质量周期，重点写“是否在误差范围内相同”。', '实验 c 要明确小角度通常取 10°以内，大角度偏离应作为讨论重点。'],
    workbenchHint: '实验 a 可使用下方“T²-L 图像法测 g”工作台；实验 b、c 建议在报告中列表对比。',
    link: ''
  }
];

export const gradeTwoWorkbenches: WorkbenchConfig[] = [
  {
    id: 'ht2',
    title: 'h-t² 图像法测 g',
    subtitle: '自由落体满足 h = 1/2gt²。以 t² 为横轴、h 为纵轴，拟合斜率 k 后 g = 2k。',
    kind: 'ht2',
    chart: 'scatter',
    xLabel: 't² / s²',
    yLabel: '高度 h / m',
    resultLabel: '由斜率得到的 g',
    inputs: [
      { key: 'h', label: '高度 h', unit: 'm', step: '0.01', min: '0' },
      { key: 't', label: '时间 t', unit: 's', step: '0.001', min: '0' }
    ],
    sampleRows: [
      { h: 0.4, t: 0.286 },
      { h: 0.8, t: 0.404 },
      { h: 1.2, t: 0.495 },
      { h: 1.6, t: 0.572 }
    ],
    notes: ['图线越接近过原点直线，说明自由落体模型越可信。', '若低高度点偏差大，常见原因是释放时刻和落地时刻判断不准。']
  },
  {
    id: 't2l',
    title: 'T²-L 图像法测 g',
    subtitle: '单摆小角度周期满足 T² = (4π²/g)L。拟合 T²-L 斜率后 g = 4π²/k。',
    kind: 't2l',
    chart: 'scatter',
    xLabel: '摆长 L / m',
    yLabel: 'T² / s²',
    resultLabel: '由斜率得到的 g',
    inputs: [
      { key: 'L', label: '摆长 L', unit: 'm', step: '0.001', min: '0' },
      { key: 'T', label: '周期 T', unit: 's', step: '0.001', min: '0' }
    ],
    sampleRows: [
      { L: 0.5, T: 1.42 },
      { L: 0.7, T: 1.68 },
      { L: 0.9, T: 1.9 },
      { L: 1.1, T: 2.1 }
    ],
    notes: ['改变摆长时，摆角和摆球质量应保持不变。', '摆角过大会让周期偏大，从而导致 g 偏小。']
  },
  {
    id: 'fm',
    title: 'F-m 图像法测 g',
    subtitle: '重物静止时 F = mg。以 m 为横轴、F 为纵轴，拟合斜率就是 g。',
    kind: 'fm',
    chart: 'scatter',
    xLabel: '质量 m / kg',
    yLabel: '拉力 F / N',
    resultLabel: 'F-m 拟合斜率',
    inputs: [
      { key: 'm', label: '质量 m', unit: 'kg', step: '0.001', min: '0' },
      { key: 'F', label: '拉力 F', unit: 'N', step: '0.01', min: '0' }
    ],
    sampleRows: [
      { m: 0.1, F: 0.99 },
      { m: 0.2, F: 1.95 },
      { m: 0.3, F: 2.94 },
      { m: 0.5, F: 4.91 }
    ],
    notes: ['测力计没有校零时，图像截距会明显偏离 0。', '用斜率比逐组 F/m 平均更能抵抗读数偶然误差。']
  },
  {
    id: 't2m',
    title: '弹簧振子 T²-m 图像',
    subtitle: '弹簧振子满足 T² = (4π²/k)m。拟合斜率可反推出弹簧劲度系数 k。',
    kind: 't2m',
    chart: 'scatter',
    xLabel: '质量 m / kg',
    yLabel: 'T² / s²',
    resultLabel: '等效弹簧劲度系数 k',
    inputs: [
      { key: 'm', label: '质量 m', unit: 'kg', step: '0.001', min: '0' },
      { key: 'T', label: '周期 T', unit: 's', step: '0.001', min: '0' }
    ],
    sampleRows: [
      { m: 0.05, T: 0.45 },
      { m: 0.1, T: 0.63 },
      { m: 0.15, T: 0.77 },
      { m: 0.2, T: 0.89 }
    ],
    notes: ['保持同一根弹簧，只改变悬挂质量。', '若质量很小，弹簧自身质量会带来明显系统偏差。']
  },
  {
    id: 'momentum',
    title: '碰撞动量守恒对比表',
    subtitle: '填写两个物体碰撞前后速度，网页自动比较碰前总动量和碰后总动量。',
    kind: 'momentum',
    chart: 'momentum-bars',
    resultLabel: '平均相对偏差',
    inputs: [
      { key: 'm1', label: 'm1', unit: 'kg', step: '0.001', min: '0' },
      { key: 'u1', label: 'u1', unit: 'm/s', step: '0.01' },
      { key: 'm2', label: 'm2', unit: 'kg', step: '0.001', min: '0' },
      { key: 'u2', label: 'u2', unit: 'm/s', step: '0.01' },
      { key: 'v1', label: 'v1', unit: 'm/s', step: '0.01' },
      { key: 'v2', label: 'v2', unit: 'm/s', step: '0.01' }
    ],
    sampleRows: [
      { m1: 0.2, u1: 0.8, m2: 0.2, u2: 0, v1: 0.05, v2: 0.72 },
      { m1: 0.3, u1: 0.6, m2: 0.2, u2: 0, v1: 0.18, v2: 0.62 },
      { m1: 0.2, u1: 0.7, m2: 0.3, u2: 0, v1: -0.1, v2: 0.5 }
    ],
    notes: ['速度方向要先规定正方向，反向运动填负值。', '偏差大时先检查碰撞是否近似水平、摩擦是否很小、速度测量点是否一致。']
  }
];

export const gradeTwoReportSpec = {
  structure: [
    '封面：项目名称、完成日期。',
    '摘要：用 100 字以内说明研究问题、方法和主要结论。',
    '实验原理：写出模型假设、公式推导和变量定义。',
    '实验装置与步骤：配 2-4 张装置或数据采集照片。',
    '数据记录：保留原始数据表，不允许只写整理后的结果。',
    '数据处理：至少包含一张图像法图表和误差分析。',
    '结论与反思：说明结论可信度、最大误差来源和改进方案。'
  ],
  reminders: [
    '有效数字要和仪器精度匹配。',
    '图像横纵轴必须写物理量和单位。',
    '用斜率求物理量时，要写清楚斜率与物理量的关系。',
    '出现离群点可以剔除，但必须说明理由。'
  ]
};
