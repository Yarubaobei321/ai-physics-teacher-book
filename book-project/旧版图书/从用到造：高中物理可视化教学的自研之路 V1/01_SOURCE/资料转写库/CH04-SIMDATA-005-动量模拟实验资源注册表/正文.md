export type SimulationGroupId = 'spring' | 'constraint' | 'moving-track';

export interface SimulationGif {
  label: string;
  href: string;
}

export interface MomentumSimulation {
  id: string;
  title: string;
  group: SimulationGroupId;
  modelLabel: string;
  summary: string;
  conservation: string;
  teachingPoint: string;
  href: string;
  gifs: SimulationGif[];
}

export interface SimulationGroup {
  id: SimulationGroupId;
  name: string;
  description: string;
}

export const simulationGroups: SimulationGroup[] = [
  {
    id: 'spring',
    name: '弹簧与相互作用',
    description: '从弹簧压缩、拉伸和分离过程理解动量守恒与机械能转化。'
  },
  {
    id: 'constraint',
    name: '轻绳与约束模型',
    description: '观察质心、水平动量和约束关系如何共同决定运动。'
  },
  {
    id: 'moving-track',
    name: '可移动曲面模型',
    description: '比较半圆槽、曲面小车和圆弧轨道中的共速、离轨与返回。'
  }
];

export const momentumSimulations: MomentumSimulation[] = [
  {
    id: 'spring-ball-block',
    title: '弹簧-小球（物块）模型',
    group: 'spring',
    modelLabel: '弹簧相互作用',
    summary: '把 A、B 和轻弹簧看成同一系统，比较接触弹簧碰撞和连接弹簧振动。',
    conservation: '水平方向动量守恒；理想弹簧和光滑水平面下机械能守恒。',
    teachingPoint: '看清“动能不一定守恒”，只有把弹性势能计入后机械能才守恒。',
    href: '/simulations/momentum/spring-ball-block-model.html',
    gifs: [
      {
        label: '接触弹簧：压缩后分离',
        href: '/simulations/momentum/exports/spring-contact-separation.gif'
      },
      {
        label: '连接弹簧：往复振动',
        href: '/simulations/momentum/exports/spring-connected-oscillation.gif'
      }
    ]
  },
  {
    id: 'ball-ring',
    title: '小球与小环的理想约束运动',
    group: 'constraint',
    modelLabel: '轻绳约束',
    summary: '小球和小环由不可伸长轻绳连接，小环套在光滑水平杆上。',
    conservation: '系统水平方向无外力，总水平动量守恒；忽略阻力时机械能守恒。',
    teachingPoint: '用质心线理解两物体水平位置和速度的反向配合。',
    href: '/simulations/momentum/ball-ring-model.html',
    gifs: [
      {
        label: '完整周期动画',
        href: '/simulations/momentum/exports/ball-ring-model.gif'
      }
    ]
  },
  {
    id: 'suspended-ring-pendulum',
    title: '悬绳小球-滑环模型',
    group: 'constraint',
    modelLabel: '摆与滑环',
    summary: '小球从最低点获得初速度后带动滑环运动，对比最高点共速和底端类弹性碰撞。',
    conservation: '初始水平动量来自小球，运动中系统水平动量和机械能共同约束速度。',
    teachingPoint: '最高点像完全非弹性碰撞，回到底端又呈现类弹性碰撞关系。',
    href: '/simulations/momentum/suspended-ring-pendulum-model.html',
    gifs: [
      {
        label: '完整周期动画',
        href: '/simulations/momentum/exports/suspended-ring-pendulum.gif'
      }
    ]
  },
  {
    id: 'ball-semicircular-groove',
    title: '小球与光滑半圆槽',
    group: 'moving-track',
    modelLabel: '半圆槽',
    summary: '小球从右上方进入可移动半圆槽，观察槽的往复运动和离槽后的竖直上抛。',
    conservation: '槽和球组成的系统水平方向动量守恒，重力势能与动能相互转化。',
    teachingPoint: '离槽瞬间切线竖直，再结合水平总动量为零，可解释水平速度为何为零。',
    href: '/simulations/momentum/ball-semicircular-groove-model.html',
    gifs: [
      {
        label: '题型一：右上沿释放',
        href: '/simulations/momentum/exports/ball-semicircular-groove-case1.gif'
      },
      {
        label: '题型二：高处释放',
        href: '/simulations/momentum/exports/ball-semicircular-groove-case2.gif'
      }
    ]
  },
  {
    id: 'ball-curved-cart',
    title: '小球滑上曲面小车',
    group: 'moving-track',
    modelLabel: '曲面小车',
    summary: '小球沿对称曲面小车上滑、下滑或越过右端，观察最高点共速和最大上升高度。',
    conservation: '系统水平方向动量守恒；把重力势能计入后机械能守恒。',
    teachingPoint: '用共速时刻判断最大高度，并比较低速返回和高速越过右端两种情形。',
    href: '/simulations/momentum/ball-curved-cart-model.html',
    gifs: [
      {
        label: '低速：左端返回',
        href: '/simulations/momentum/exports/ball-curved-cart-slow-left-return.gif'
      },
      {
        label: '高速：右端离开',
        href: '/simulations/momentum/exports/ball-curved-cart-fast-right-exit.gif'
      }
    ]
  },
  {
    id: 'slider-curved-track',
    title: '滑块-斜（曲）面模型',
    group: 'moving-track',
    modelLabel: '圆弧轨道',
    summary: '小球滑上静置于光滑水平面上的圆弧轨道，可能飞出、落回或返回底端。',
    conservation: '约束段水平方向动量守恒，含重力势能的机械能守恒。',
    teachingPoint: '把最高点共速和底端分离分别看成类完全非弹性、类弹性碰撞来理解。',
    href: '/simulations/momentum/slider-curved-track-model.html',
    gifs: [
      {
        label: '低速：未冲出轨道',
        href: '/simulations/momentum/exports/slider-curved-track-slow-ground.gif'
      },
      {
        label: '高速：飞出再落回',
        href: '/simulations/momentum/exports/slider-curved-track-fast-ground.gif'
      }
    ]
  }
];

export const simulationCount = momentumSimulations.length;
