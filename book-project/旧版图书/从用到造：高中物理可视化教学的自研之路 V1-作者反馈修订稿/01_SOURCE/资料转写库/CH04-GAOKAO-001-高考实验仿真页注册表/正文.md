export type GaokaoSimulationStatus = 'available';

export interface GaokaoSimulationItem {
  id: string;
  year: number;
  title: string;
  topic: '实验测量' | '碰撞与动量' | '电磁过程' | '传感与控制' | '振动与波';
  chapters: string;
  interaction: string;
  status: GaokaoSimulationStatus;
  href?: string;
}

export const gaokaoSimulationItems: GaokaoSimulationItem[] = [
  {
    id: '15-01-01',
    year: 2026,
    title: '薄膜冲击发光与压缩时间',
    topic: '实验测量',
    chapters: '序言、第1—3、5章',
    interaction: '视频位移、接触前速度、力脉冲与压缩时间估测',
    status: 'available',
    href: '/simulations/gaokao/2026-film-impact/'
  },
  {
    id: '02-01-02',
    year: 2024,
    title: '安全带锁止与安全气囊',
    topic: '碰撞与动量',
    chapters: '第2—4章',
    interaction: '敏感球受力、斜面角与力—时间面积',
    status: 'available',
    href: '/simulations/gaokao/2024-seatbelt-airbag/'
  },
  {
    id: '15-01-05',
    year: 2022,
    title: '小球与橡胶碰撞',
    topic: '实验测量',
    chapters: '第5章',
    interaction: '光电门时间、速度与机械能损失',
    status: 'available',
    href: '/simulations/gaokao/2022-rubber-collision/'
  },
  {
    id: '15-01-02',
    year: 2025,
    title: '小车与吸能材料',
    topic: '碰撞与动量',
    chapters: '第5、17章',
    interaction: '三次遮光、动量与动能保留率',
    status: 'available',
    href: '/simulations/gaokao/2025-energy-absorber/'
  },
  {
    id: '10-02-01',
    year: 2024,
    title: '电磁俘能器',
    topic: '电磁过程',
    chapters: '第6章',
    interaction: '磁场分界移动、磁通量与方向判断',
    status: 'available',
    href: '/simulations/gaokao/2024-electromagnetic-harvester/'
  },
  {
    id: '10-03-01',
    year: 2025,
    title: '电磁称重装置',
    topic: '电磁过程',
    chapters: '第6章',
    interaction: '安培力与动生电动势双过程消元',
    status: 'available',
    href: '/simulations/gaokao/2025-electromagnetic-scale/'
  },
  {
    id: '15-02-06',
    year: 2021,
    title: '热敏电阻',
    topic: '传感与控制',
    chapters: '第3、7章',
    interaction: '欧姆挡预判、比较测阻与 R—T 标定',
    status: 'available',
    href: '/simulations/gaokao/2021-thermistor/'
  },
  {
    id: '15-02-05',
    year: 2022,
    title: '弹性导电绳',
    topic: '传感与控制',
    chapters: '第3、7章',
    interaction: '保持同一电压的两次测流、R—L 标定与迟滞对比',
    status: 'available',
    href: '/simulations/gaokao/2022-conductive-rope/'
  },
  {
    id: '15-02-04',
    year: 2023,
    title: '盐水电导率',
    topic: '传感与控制',
    chapters: '第3章',
    interaction: '开关状态、电阻反演与温度条件',
    status: 'available',
    href: '/simulations/gaokao/2023-saltwater-conductivity/'
  },
  {
    id: '15-02-03',
    year: 2024,
    title: '光源跟踪装置',
    topic: '传感与控制',
    chapters: '第3、7章',
    interaction: '双光敏差分、死区、方向与闭环',
    status: 'available',
    href: '/simulations/gaokao/2024-light-tracker/'
  },
  {
    id: '15-02-02',
    year: 2025,
    title: '涡流制动装置',
    topic: '电磁过程',
    chapters: '第3、6章',
    interaction: 'B—I 标定、转速衰减与制动比较',
    status: 'available',
    href: '/simulations/gaokao/2025-eddy-current-brake/'
  },
  {
    id: '15-02-01',
    year: 2026,
    title: '棉花回潮率',
    topic: '传感与控制',
    chapters: '第3、7章',
    interaction: '压力标定、替代测阻与回潮率定标',
    status: 'available',
    href: '/simulations/gaokao/2026-cotton-moisture/'
  },
  {
    id: '06-03-05',
    year: 2021,
    title: '算盘算珠碰撞',
    topic: '碰撞与动量',
    chapters: '第5章延伸、第8章',
    interaction: '摩擦—碰撞—摩擦与阈值初速度',
    status: 'available',
    href: '/simulations/gaokao/2021-abacus-collision/'
  },
  {
    id: '06-02-01',
    year: 2023,
    title: '电动窗帘',
    topic: '碰撞与动量',
    chapters: '第5章延伸、第8章',
    interaction: '外力冲量、粘连碰撞与动量变化',
    status: 'available',
    href: '/simulations/gaokao/2023-electric-curtain/'
  },
  {
    id: '06-03-04',
    year: 2026,
    title: '球形机器人',
    topic: '碰撞与动量',
    chapters: '第5章延伸、第8章',
    interaction: '摆锤、挡板碰撞、腾空与落地分离',
    status: 'available',
    href: '/simulations/gaokao/2026-spherical-robot/'
  },
  {
    id: '13-02-05',
    year: 2022,
    title: '软绳简谐波',
    topic: '振动与波',
    chapters: '第9章',
    interaction: '波形传播、质点振动、频率与波长',
    status: 'available',
    href: '/simulations/gaokao/2022-rope-wave/'
  },
  {
    id: '13-02-02',
    year: 2024,
    title: '简谐横波波形图',
    topic: '振动与波',
    chapters: '第9章',
    interaction: '波形图与振动图同步及指定时刻位移',
    status: 'available',
    href: '/simulations/gaokao/2024-wave-snapshot/'
  },
  {
    id: '13-01-02',
    year: 2021,
    title: '竖直弹簧振子',
    topic: '振动与波',
    chapters: '第9章',
    interaction: '位移、相位、速度与动能',
    status: 'available',
    href: '/simulations/gaokao/2021-spring-oscillator/'
  },
  {
    id: '13-01-01',
    year: 2025,
    title: '受迫振动与多普勒',
    topic: '振动与波',
    chapters: '第9章',
    interaction: '驱动频率、共振条件与接收频率',
    status: 'available',
    href: '/simulations/gaokao/2025-forced-doppler/'
  },
  {
    id: '13-02-03',
    year: 2023,
    title: '回声探测器',
    topic: '振动与波',
    chapters: '第9章',
    interaction: '波长、回声时间与频率变化',
    status: 'available',
    href: '/simulations/gaokao/2023-echo-sounder/'
  }
];

export const availableGaokaoSimulations = gaokaoSimulationItems.filter(
  (item) => item.status === 'available'
);
