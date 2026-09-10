export interface RubricCriterion {
  name: string;
  points: number;
  description: string;
}

export interface ResearchDimension {
  id: string;
  name: string;
  points: number;
  description: string;
}

export interface ResearchTrack {
  id: 'A' | 'B';
  name: string;
  points: number;
  summary: string;
  dimensions: ResearchDimension[];
}

export const literacyPage = {
  title: '学生 AI 素养评价',
  eyebrow: 'STUDENT AI LITERACY',
  description:
    '基于真实人机对话、版本演进与可运行作品，观察学生如何定义问题、诊断修改、核验结果，并把 AI 输出转化为可用于学习的交互网页。',
  scope: '77 份代号化作品 · 8 个学科 · 不设排名',
  disclaimer:
    '页面展示的是 AI 研究性评分，不是学校五位评委产生的正式成绩，也不用于给学生排队或划等级。'
} as const;

export const fieldTask = {
  duration: '50 分钟',
  tool: 'DeepSeek 网页版',
  deliverable: '单文件、可交互的 HTML 知识科普网页',
  description:
    '学生从高考学科中选择一个熟悉的知识点、概念、模型或现象，通过与 DeepSeek 多轮交流，生成初版并持续修正，最终提交可独立打开的网页。',
  steps: [
    '选择一个明确的学科知识主题',
    '向 DeepSeek 提出首轮网页需求',
    '运行初版，继续对话并修正问题',
    '提交最终单文件 HTML 与对话记录'
  ]
} as const;

export const originalRubric: RubricCriterion[] = [
  {
    name: '主题与知识准确性',
    points: 30,
    description: '主题明确聚焦；知识内容准确，符合高中阶段要求；讲解逻辑清晰、层次分明。'
  },
  {
    name: 'AI 工具使用能力',
    points: 25,
    description: '指令清晰有效；能修正 AI 输出的问题；能整合信息形成完整作品，不盲目照搬。'
  },
  {
    name: '交互设计合理性',
    points: 25,
    description: '交互服务于知识理解；操作简单直观；响应正常，无明显故障。'
  },
  {
    name: '页面呈现与可读性',
    points: 15,
    description: '排版整洁；字体大小合适；重点突出；图文搭配合理。'
  },
  {
    name: '创意与亮点',
    points: 5,
    description: '具有独特讲解视角或巧妙交互，能帮助读者快速理解复杂知识点。'
  }
];

export const originalScoringProcedure =
  '原规则规定由 5 位评委独立打分，去掉一个最高分和一个最低分后，对其余 3 个分数取平均值。本研究库没有收录这组正式评委成绩。';

export const researchTracks: ResearchTrack[] = [
  {
    id: 'A',
    name: '人机协作过程',
    points: 60,
    summary: '只依据学生可见对话与版本证据，评价学生怎样提出要求、发现问题、修正和验收。',
    dimensions: [
      {
        id: 'A1',
        name: '问题定义与规格前置',
        points: 15,
        description: '首问是否说清主题、受众、核心交互、约束与验收。'
      },
      {
        id: 'A2',
        name: '迭代诊断与纠错',
        points: 15,
        description: '是否依据可观察问题提出定向修复，而不是只要求笼统美化。'
      },
      {
        id: 'A3',
        name: '学科建模表达',
        points: 12,
        description: '是否主动表达学科关系、条件、边界、术语或可计算规则。'
      },
      {
        id: 'A4',
        name: '验收与数据校验',
        points: 12,
        description: '是否主动测试功能，并用答案、事实、读数或判据核对结果。'
      },
      {
        id: 'A5',
        name: '版本与取舍',
        points: 6,
        description: '是否比较版本、保护已有成果，并作出范围或方案取舍。'
      }
    ]
  },
  {
    id: 'B',
    name: '最终作品质量',
    points: 40,
    summary: '只依据学生提交最终版与浏览器核验，评价作品是否准确、可教、可用、可访问。',
    dimensions: [
      {
        id: 'B1',
        name: '学科正确性',
        points: 15,
        description: '按各学科可核验清单检查知识、事实、规则、读数或模型硬伤。'
      },
      {
        id: 'B2',
        name: '教学可用性',
        points: 10,
        description: '页面能否形成观察、操作、记录、解释或自测等学习活动。'
      },
      {
        id: 'B3',
        name: '交互完整性',
        points: 8,
        description: '关键控件是否经过实测，参数、反馈与页面状态是否一致。'
      },
      {
        id: 'B4',
        name: '呈现与可访问性',
        points: 7,
        description: '检查排版、单位、响应式、文字替代与键盘焦点等基础质量。'
      }
    ]
  }
];

export const evidenceRules = [
  '过程分只取自可见的人机对话与可追溯版本，不把模型隐藏推理当作学生能力证据。',
  '成品分只依据学生提交最终版及浏览器核验，不用成品观感反推学生的对话过程。',
  'A 轨与 B 轨分别取证、分别计分；缺少证据时如实标记，不根据印象补分。',
  '各学科共用 60 + 40 的结构，A3、A4 与 B1 使用相应学科的可核验口径。'
] as const;

export const researchBoundary = [
  '作品只显示 P / B / M / C / H / G / L / E 学科代号，不显示姓名与班级。',
  '最优提示词由评审依据证据重构，并非学生现场原始提示词。',
  'DeepSeek 优化作品用于呈现规格前置后的研究对照；由于模型版本、生成时限等条件并未完全控制，不作单一因果归因。',
  '分数用于教学诊断与论文研究，不显示名次，也不把区间解释为学生等级。'
] as const;

export const evidenceSequence = [
  '关键对话与可展开完整对话',
  'DeepSeek 第一版与学生提交最终版',
  'AI 研究性评分与维度证据',
  '评审重构的最优提示词',
  'DeepSeek 根据最优提示词生成的优化对照'
] as const;

export const scoreBands = [
  { label: '90–100', min: 90, max: 100 },
  { label: '80–89', min: 80, max: 89 },
  { label: '70–79', min: 70, max: 79 },
  { label: '60–69', min: 60, max: 69 },
  { label: '0–59', min: 0, max: 59 }
] as const;

type UnknownRecord = Record<string, unknown>;

export interface ScoreSummary {
  total: number;
  trackA: number | null;
  trackB: number | null;
}

export interface CatalogEvidence {
  hasConversation: boolean;
  hasVersionComparison: boolean;
  hasOptimalPrompt: boolean;
  hasDeepseekOptimized: boolean;
  singleStage: boolean;
  firstVersionMatchesSubmission: boolean;
  conversationLastVersionDiffers: boolean;
}

export interface StudentAiCatalogItem {
  alias: string;
  subject: string;
  subjectLabel: string;
  topic: string;
  score: ScoreSummary | null;
  evidence: CatalogEvidence;
}

export interface StudentAiSubject {
  id: string;
  label: string;
  count: number;
}

export interface StudentAiCatalog {
  count: number;
  items: StudentAiCatalogItem[];
  subjects: StudentAiSubject[];
}

function asRecord(value: unknown): UnknownRecord {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as UnknownRecord)
    : {};
}

function asText(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value.trim() ? value.trim() : fallback;
}

function asFiniteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function readTrackScore(value: unknown): number | null {
  const direct = asFiniteNumber(value);
  if (direct !== null) return direct;
  return asFiniteNumber(asRecord(value).score);
}

function readScore(reviewValue: unknown): ScoreSummary | null {
  const review = asRecord(reviewValue);
  const total = asFiniteNumber(review.totalScore);
  if (total === null) return null;

  return {
    total,
    trackA: readTrackScore(review.trackA),
    trackB: readTrackScore(review.trackB)
  };
}

function readBoolean(record: UnknownRecord, key: string): boolean {
  return record[key] === true;
}

function readCatalogItem(value: unknown): StudentAiCatalogItem | null {
  const item = asRecord(value);
  const alias = asText(item.alias);
  const subject = asText(item.subject);
  if (!alias || !subject) return null;

  const badges = asRecord(item.badges);
  const assets = asRecord(item.assets);
  const evidenceStatus = asRecord(item.evidenceStatus);
  const submittedRelationship = asText(evidenceStatus.submittedRelationship);

  const hasConversation =
    readBoolean(badges, 'hasFullConversation') ||
    readBoolean(badges, 'hasConversation') ||
    Boolean(assets.conversationFull) ||
    Boolean(assets.conversation);
  const hasDeepseekFirst =
    readBoolean(badges, 'hasDeepseekFirst') || Boolean(assets.deepseekFirst);
  const hasStudentFinal =
    readBoolean(badges, 'hasStudentFinal') || Boolean(assets.studentFinal);

  return {
    alias,
    subject,
    subjectLabel: asText(item.subjectLabel, subject),
    topic: asText(item.topic, '未命名作品'),
    score: readScore(item.review),
    evidence: {
      hasConversation,
      hasVersionComparison: hasDeepseekFirst && hasStudentFinal,
      hasOptimalPrompt:
        readBoolean(badges, 'hasOptimalPrompt') || Boolean(assets.optimalPrompt),
      hasDeepseekOptimized:
        readBoolean(badges, 'hasDeepseekOptimized') || Boolean(assets.deepseekOptimized),
      singleStage: readBoolean(evidenceStatus, 'singleStage'),
      firstVersionMatchesSubmission: readBoolean(
        evidenceStatus,
        'firstVersionMatchesSubmission'
      ),
      conversationLastVersionDiffers:
        evidenceStatus.conversationLastVersionMatchesSubmission === false ||
        submittedRelationship === 'different-from-conversation-last'
    }
  };
}

export function readStudentAiCatalog(source: unknown): StudentAiCatalog {
  const root = asRecord(source);
  const items = (Array.isArray(root.items) ? root.items : [])
    .map(readCatalogItem)
    .filter((item): item is StudentAiCatalogItem => item !== null);

  const declaredSubjects = (Array.isArray(root.subjects) ? root.subjects : [])
    .map((value): StudentAiSubject | null => {
      const subject = asRecord(value);
      const id = asText(subject.id);
      if (!id) return null;
      return {
        id,
        label: asText(subject.label, id),
        count:
          asFiniteNumber(subject.count) ?? items.filter((item) => item.subject === id).length
      };
    })
    .filter((subject): subject is StudentAiSubject => subject !== null);

  const subjects = declaredSubjects.length
    ? declaredSubjects
    : Array.from(new Set(items.map((item) => item.subject))).map((id) => ({
        id,
        label: items.find((item) => item.subject === id)?.subjectLabel ?? id,
        count: items.filter((item) => item.subject === id).length
      }));

  return {
    count: asFiniteNumber(root.count) ?? items.length,
    items,
    subjects
  };
}
