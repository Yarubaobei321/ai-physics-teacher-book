import { momentumSimulations } from './simulations';
import { gaokaoSimulationItems } from './gaokao-simulations';

export const resourceCategories = [
  { id: 'simulation', label: '模拟演示' },
  { id: 'experiment', label: '实验记录' },
  { id: 'hardware', label: '硬件制作' },
  { id: 'research', label: '教学研究' }
] as const;

export type ResourceCategory = typeof resourceCategories[number]['id'];
export interface TeachingResource {
  id: string;
  title: string;
  description: string;
  category: ResourceCategory;
  topic: string;
  requirement: string;
  href: string;
  keywords?: string;
}

// 只维护各工具的入口与使用条件；模型标题和专题沿用已有台账。
const tools: TeachingResource[] = [
  { id: 'falling-body', title: '落体法验证机械能守恒', description: '填写纸带位置，计算速度与能量变化，并导出实验结果。', category: 'experiment', topic: '机械能 · 纸带实验', requirement: '手动录入测量数据', href: '/online-lab/falling-body/', keywords: '打点计时器 重锤 势能 动能' },
  { id: 'gravity', title: '测量重力加速度 g', description: '从五种实验方案中选择一种，记录数据、作图并比较结果。', category: 'experiment', topic: '新高一 · 项目式学习', requirement: '按所选方案准备器材', href: '/project-learning/new-grade-one/', keywords: '单摆 手机 视频 自由落体 弹簧测力计' },
  { id: 'dis', title: '网页版 DIS：连接传感器开始测量', description: '采集力、距离或光电门数据，记录曲线并导出 CSV。', category: 'experiment', topic: '传感器 · 实时采集', requirement: 'ESP32 · 兼容蓝牙浏览器', href: '/dis/', keywords: '速度 位移 力 时间 BLE Web Bluetooth' },
  { id: 'smart-car', title: '智能小车：从原理到教学控制台', description: '了解电路、结构与程序，再进入教学控制台。', category: 'hardware', topic: 'ESP32 · 智能控制', requirement: '先读制作说明', href: '/maker/smart-car/', keywords: '机器人 科创 编程 避障' },
  { id: 'curved-ramp', title: '沿曲线运动验证机械能守恒', description: '比较圆柱体下降的高度与到达光电门时的速度。', category: 'experiment', topic: '机械能 · 曲面下滑', requirement: '可手动录入或连接光电门', href: '/online-lab/curved-ramp/', keywords: '圆柱体 DIS 势能 动能 双头光电门' },
  { id: 'air-track', title: '气垫导轨验证系统机械能守恒', description: '保留同次实验的两次速度，比较系统动能与重力势能变化。', category: 'experiment', topic: '机械能 · 气垫导轨', requirement: '可手动录入或连接光电门', href: '/online-lab/air-track/', keywords: '滑块 重锤 双头光电门 系统' },
  { id: 'grade-two', title: '力学综合探究实验', description: '用数据和图像分析力学问题，整理探究报告。', category: 'experiment', topic: '新高二 · 项目式学习', requirement: '按所选方案准备器材', href: '/project-learning/new-grade-two/', keywords: '暑假 作业 力学 综合' },
  { id: 'programming', title: '在线编程：给 ESP32 写入程序', description: '选择 MicroPython 模板，通过浏览器串口写入程序与库。', category: 'hardware', topic: 'ESP32 · MicroPython', requirement: 'USB 连接 · 兼容串口浏览器', href: '/programming/', keywords: '烧录 固件 编程 Web Serial' },
  { id: 'ultrasonic', title: '超声波小车网页实验室', description: '连接 ESP32，烧录程序并观察超声波采集的数据曲线。', category: 'hardware', topic: '超声波 · 数据采集', requirement: 'ESP32 · 超声波传感器', href: '/project-learning/ultrasonic-lab/', keywords: '距离 位移 速度 串口 DIS' },
  { id: 'dis-course', title: '从传感器到数字化实验', description: '了解 ESP32 与超声波传感器组成的实验方案。', category: 'hardware', topic: 'DIS · 项目式学习', requirement: '阅读器材与连接说明', href: '/project-learning/dis-sensor/', keywords: '课程 小车 传感器' },
  { id: 'mars-rover', title: '尘光一号：火星车制作与地面站', description: '了解能源管理、环境感知和控制系统，再进入地面站。', category: 'hardware', topic: 'ESP32 · 综合制作', requirement: '先读作品说明', href: '/maker/mars-rover/', keywords: '科创 太阳能 追光 机器人 除尘' },
  { id: 'student-ai', title: '学生 AI 素养评价', description: '沿着对话、首版、提交版与优化对照，查看匿名作品的形成过程。', category: 'research', topic: 'AI 协作 · 教学研究', requirement: '代号展示 · 不设排名', href: '/simulations/student-ai-lab/', keywords: 'DeepSeek 人工智能 作品 对话 评价' }
];

const momentum: TeachingResource[] = momentumSimulations.map((model) => ({
  id: `momentum-${model.id}`, title: model.title, description: model.summary,
  category: 'simulation', topic: `动量 · ${model.modelLabel}`, requirement: '无需硬件',
  href: model.href, keywords: `${model.conservation} ${model.teachingPoint}`
}));

const gaokao: TeachingResource[] = gaokaoSimulationItems.map((model) => {
  if (!model.href) throw new Error(`高考模型缺少资源入口：${model.id}`);
  return {
    id: `gaokao-${model.id}`, title: model.title, description: model.interaction,
    category: 'simulation', topic: `${model.year} 高考 · ${model.topic}`,
    requirement: '无需硬件', href: model.href, keywords: `${model.chapters} 高考真题 智启格物`
  };
});

// 默认先呈现不同用途的资源，搜索覆盖完整索引。
const featured = ['momentum-spring-ball-block', 'falling-body', 'gaokao-15-01-01', 'gravity', 'dis', 'smart-car'];
export const teachingResources = [...tools, ...momentum, ...gaokao].sort((a, b) => {
  const rank = (id: string) => featured.includes(id) ? featured.indexOf(id) : featured.length;
  return rank(a.id) - rank(b.id);
});
