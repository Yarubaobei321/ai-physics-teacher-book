export const site = {
  name: '育才物理创新实验室',
  intro:
    '一名高中物理老师的个人兴趣站点，记录我在物理实验、创新教具和数字化实验（DIS）方面的探索与制作。',
  // ICP 备案号：备案通过后填入（如 '粤ICP备XXXXXXXX号'）。留空则页脚不显示，切勿提前填未通过的号。
  icp: '',
  // 公安联网备案号：上线 30 日内办理后填入（如 '粤公网安备 44XXXXXXXXXXXX号'）。留空则不显示。
  police: '',
  nav: [
    { label: '首页', href: '/' },
    { label: '项目式学习', href: '/project-learning/' },
    { label: '科创天地', href: '/maker/' },
    { label: '在线实验室', href: '/online-lab/' },
    { label: '模拟实验室', href: '/simulations/' }
  ],
  directions: [
    {
      title: '创新实验开发',
      text: '围绕真实物理问题设计实验方案，用数据采集和可视化让规律更清楚。'
    },
    {
      title: '创新教具制作',
      text: '用 ESP32、传感器和 3D 打印等工具，把想法做成能在课堂中使用的装置。'
    },
    {
      title: '实验记录分享',
      text: '把实验过程、实验数据和改进思路整理记录，方便复用和迭代。'
    }
  ]
};
