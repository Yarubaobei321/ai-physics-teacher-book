## 2026-10-01 运动测速定时采集与两版网页烧录

正式release：`20261001-motion-time-windows-versions`，基于`20261001-ultrasonic-web-flash`限定覆盖14文件，旧release完整保留。motion-compare／motion-ultrasonic两页支持1～60秒采集、自动停止、重复试次保留和显示起止时刻裁剪，区间外点不参与坐标缩放。USB异常JSON跳过后可由有效读数恢复提示。两测量页与USB烧录页均显示GPIO与接线；烧录页可选第一版v10（超声波＋激光，USB）／第二版v11.1（单超声波＋蓝牙）。两版均限定经典ESP32、4MB，下载SHA-256和板上MD5校验后显示成功。

已验证：构建0错误、npm test、diff check、实际控制代码5秒／10秒和范围外异常点回归、两版固件文件校验及替身串口写入流程、14个公开文件哈希和脚本类型、38URL缓存刷新，正式超声波页导入已有50点实测试次后1～2秒仅显示11点。新ESP32实际网页烧录及本轮硬件USB／BLE采集尚未执行；内置浏览器PNG预览成功但下载事件无文件，外部浏览器另存待现场确认。证据与本轮源码前后快照在智能硬件课程项目的第二版测速目录`docs/deployment/time-windows/`。

# 数智育才门户项目摘要

## 2026-10-10 学生静电场笔记专题已上线

入口 https://shuzhiyucai.cn/notes/20261010/ 。发布版本`20261010-electrostatics-notes-highschool`（最新只更新示范HTML/PDF；六概念图用高中公式，第07节只留电容）。初次发布基于`20261001-motion-time-windows-versions`只新增119个专题文件，原1179文件指纹不变。按用户明确指定的讲评页公开范围，含36人评分与原处批注PDF、10人未见文件核对名单、13班4份笔记、精简7页示范网页/PDF及二维码；本地评分Excel和名单Excel未公开。课堂模型不含匀强场，示范以公式图表为主，无匀强场和错题整理专题，不使用微积分表达；六概念图仍保留U=Ed及适用条件。源码位于`public/notes/20261010`，可再制作来源在班级管理/学生笔记。

现有网站构建157页与测试通过；公网119个资源可访问，入口/示范/二维码哈希核对通过，390px排版、查分、放大及双电荷方向切换已验。Nginx检查重载和发布后Cloudflare清缓存成功，旧版本保留；未验证校网、学生真机或课堂效果，未提交推送Git。完整记录：`/Users/yaril/个人文档/1 班级管理/学生笔记/outputs/20261010-静电场笔记评分/发布记录.md`。


## 2026-10-01 超声波短时测速连接修复已上线

当前发布`20261001-ultrasonic-ble-mime-fix`，保留上一发布`20261001-ultrasonic-ble-v2`。入口`/online-lab/motion-ultrasonic/`；初次发布.mjs被发送为application/octet-stream，造成USB与BLE点击处理未加载。修复限于此页面HTML和两个带版本的.js脚本，未改服务器全局配置。最终构建0错误、网站检查、公开文件哈希及JavaScript类型通过；正式页面已显示连接功能就绪，蓝牙按钮点击进入选择Motion-Ultrasonic流程。尚未在正式来源完成硬件配对采集。主项目过程与证据位于智能硬件选修课王硕项目第二版的docs/deployment/mime-fix/；未提交或推送Git。

## 2026-09-30 拍照重建与电极方向更新已上线

当前线上版本为 `20260930-photo-reconstruction`，以 `20260930-electrostatics-measured-photos` 为基线，仅更新14个实验室及离线缓存文件。入口 https://shuzhiyucai.cn/electrostatics/lab/ ：“实测与重建 → 拍照识别”，采纳测点后切换“电势地形”，可按实物选择电极方向。构建、网站检查及23项本机照片识别/重建/方向检查通过；Nginx检查与重载、34 URL缓存刷新成功，14个公网文件哈希一致，公网浏览器拍照入口与新版本标记核对通过。五组实测图及双路测速内容保留，旧release可回滚。未推送GitHub，未做手机相机、平板、校网或物理精度验收。详见[发布记录](review/photo-reconstruction-release-20260930/review.md)。

## 2026-09-30 静电场实验室增加“电极方向”（开发记录，现已随上述版本发布）

场图下方新增“电极方向”下拉框（正端在左/上/右/下），平面图、地形、照片校正图随实物方向旋转；计算仍在模型坐标中进行（只取90°整数倍，无插值），测点按坐标纸坐标保存。改动限于 `public/electrostatics/lab` 的12个文件，已重新生成离线清单（代码版本 a22218b4899a，数据版本未变）。开发阶段 `check:public`、`npm test` 通过；五张坐标纸实测照片重建结果与手动旋转测点逐位一致。构建与发布状态见上方，未推送、未实机验收。详见 [记录](review/electrostatics-orientation-20260930/README.md)。

已发布[五组实测与等势线标注](https://shuzhiyucai.cn/online-lab/electrostatics/measurements/)，静电场专题已增加入口。提供5张高清PNG、网页预览及ZIP下载；原图及内部制作记录未公开。13个公网文件与发布包指纹一致，构建及网站测试通过，浏览器已核对。版本20260930-electrostatics-measured-photos，保留20260929-motion-compare供回滚。

## 2026-09-29 双路测速网页已上线

当前线上版本为 `20260929-motion-compare`，以 `20260929-site-refactor` 为基线仅更新9个文件。正式入口 `/online-lab/motion-compare/`，在线实验室栏目已加入卡片；使用现有 ultrasonic-laser-oled-v10 固件，通过USB同时显示超声波和激光距离、速度。构建、现有测试、Nginx与缓存刷新通过，9个公网文件哈希一致，Chrome界面已核验；本轮未重烧固件或在公网来源重新连接硬件，未推送GitHub。旧版保留。详见 [发布记录](review/motion-compare-release-20260929/review.md)。

## 2026-09-29 现役页面重构与离线功能上线

用户确认仅更新现役页面、此次重构和离线功能；历史静电场八模块、自由电荷工作台、实时测速台与图书高考模拟未上线。已部署 `20260929-site-refactor`，以 `20260928-electrostatics-principle-p2` 为基线更新 180 个文件，新版移除 129.0 MiB 冗余水槽母版，旧版完整保留。Nginx 检查/重载、Cloudflare 360 URL 清缓存、154 个公网文件哈希和 16 项桌面/窄屏浏览器检查通过。

GitHub 源码已推送独立分支 `codex/site-refactor-release-20260929`（实现提交 `010071f6057a83ab1481e567831af57bfd6ef76a`），main 未合并；197 个文件哈希核对一致。分支仅包含现役源码依赖，737 份外部运行资源有校验清单及恢复脚本。原工作区所有历史候选保留，仅修复教学设计公开副本的本机 Word 断链并重生成离线清单。22 项单元、59 项本地浏览器、22 项离线操作检查通过；独立推送源码构建 65 Astro 路由及对应测试通过。尚未验证真实设备、平板实机、校网与课堂效果。完整记录见 [审阅与发布记录](review/refactor-release-20260929/review.md)。


## 2026-09-28 高考题 / 游戏同步与平板离线缓存（本地完成，待用户审阅）

把作者本机最新的高考题专区（17 个文件，白底三栏版）和电势漫游（修复放置中断后视角被锁，2 个文件）同步进 `public/electrostatics/{exam,game}`，逐题教学设计无变化；同步脚本 `scripts/sync-electrostatics-sources.mjs` 保留站点适配。新增平板课前页 `/electrostatics/offline/`：Service Worker 缓存优先，分 10 组把实验室、5 个水槽布局、高考题、游戏、教学设计下载到本机（79 MB），逐文件核对大小、可重算哈希校验、可清除；代码与数据分开缓存，网站更新时增量迁移已下载内容。详见 [记录](review/electrostatics-offline-20260928/README.md) 与 [docs/electrostatics-offline.md](docs/electrostatics-offline.md)。

本地检查：`npm run test:offline`（真实 Chromium：下载 → 校验 → 断网打开各页面与水槽数据 → 损坏检测 → 模拟更新 → 清除）、`npm test`、单元与浏览器检查通过。未在真实平板上试过，未测校园网，未部署，未提交 Git；发布须成套上线 `sw.js`、清单与变化页面。

## 2026-09-28 重构第一阶段（本地完成，待用户审阅）

按 `review/refactor-audit-20260928/review.md` 完成阶段 0–5 中可本机落地的部分，行为不变、首页未动：vitest 与 `test:e2e`；`src/lib/devices/`（串口、蓝牙、光电门协议，两套固件格式统一解析并补单元测试）和 `src/lib/labs/`（能量计算、能量柱状图、导出），三个机械能实验合计约 5200 → 2830 行；`check:public` 类型检查棘轮；静电场水槽母版 `*.bin` 移到 `data-src/`（逐字节核对一致，`public/electrostatics` 209 → 79 MB）；栏目归属改读 `site.ts`；科创天地页拆出数据与脚本；页头、卡片等视觉统一。详见 [记录](review/refactor-phase1-20260928/README.md)。

本地检查：构建 0 errors，`npm test`、单元 22 项、浏览器 59 项及硬件、静电场、高考入口检查均通过。未连接真实设备，未提交 Git，未部署，未做手机或课堂验收。

## 2026-09-28 全站重构审查（仅建议）

只读审查，给出分阶段重构方案。主要问题：三套机械能实验与 DIS 面板重复实现串口 / 蓝牙 / 图表 / 导出，且两份光电门串口解析出现 us 与 s 单位分歧（后经核对是两套固件格式，见上方重构记录）；`public/` 中约 6000 行无类型 JS；`verify-site.mjs` 以源码字符串断言为主；`public/electrostatics` 与智能硬件资源共约 360 MB 未纳入版本管理。详见 [审查记录](review/refactor-audit-20260928/review.md)。

## 2026-09-28 静电场原理教学页与新版专题已上线（当前）

阿里云当前版本为 `20260928-electrostatics-principle-p2`。教学页 `/online-lab/electrostatics/principle/`、四部分专题 `/online-lab/electrostatics/` 已上线；在线实验室新增卡片，模拟实验室移除原卡片，旧 `/electrostatics/` 保留跳转。按线上基线选择性更新并保留旧 release；未发布其它草稿，未 Git 提交或推送。构建与完整网站测试通过；按用户最后指令停止后续检查并完成 Cloudflare 全站强制 purge，最终修正版未另作浏览器回归。详见 [发布记录](review/electrostatics-online-lab-20260928/review.md)。

## 2026-09-27 静电场专题、新 Logo 与课堂二维码已上线（历史版本）

已上线 https://shuzhiyucai.cn/electrostatics/ ，包含现役 Opus 实验室、23 道题与逐题教学设计、电势漫游。首页二维码现直达 https://shuzhiyucai.cn/electrostatics/lab/ ，已解码核验；按用户最新要求移除反馈模板和链接。E“彩页才” Logo 同步全站与 ESP32 图标。当前 release 为 `20260927-electrostatics-logo-p4`，旧版本与配置保留。

本轮按线上基线选择性发布，未发布其它本地待办，未 Git 提交或推送；193 个来源文件未改。构建、网站测试、284 项公网资源核对、普通 Chrome 操作验证通过。水槽数据分层分块无损读取并自动重试，60 项逐字节比对一致；当前网络下部分场景首次载入仍超过一分钟，课前应在实际课堂设备和网络预先打开。手机真机、校网多人并发、实体精度及课堂效果未验收。详见 [本轮上线记录](review/electrostatics-launch-20260927/review.md)。


## 2026-09-27 官方 Logo 改为 E「彩页才」（已随本轮上线）

用户选定 E（B 保留作备选），要求只改本地项目。`public/logo.svg` 与 PNG/WebP 已替换为 E，与选样页 Canvas 版本像素对照一致。ESP32 图标、清单和 `sw.js` 已同步，缓存名为 `esp32-showcase-3ce4e07c4f84e49e`。Hero 替代文字和相关文档已更新。`npm run build`（153 路由，0 errors）、`npm test`、`npm run test:hardware` 通过；生产预览中检查了页头、窄屏、放大查看、高考页头和 ESP32 页。未提交 Git，未部署，线上仍是旧标志。记录与 Y1 备份见 `review/logo-official-20260927/`。

## 2026-09-27 彩色 Logo 第四轮候选

按用户要求做了“简单、彩色、含育才 / YC / 物理 / 智能硬件”的八款 Canvas 标志 A–H，入口是 `review/logo-color-20260927/index.html`（说明见同目录 README）。页面支持深色和单色切换、小尺寸与页头 / 首页示意，可导出透明 PNG。已用无头 Chrome 查看三种状态，40 个导出文件和 390 px 窄屏均无问题。官方标志仍为 Y1，网站源码未改，未部署。新增 `CLAUDE.md`，导入 `AGENTS.md` 并补充命令与架构要点。

## 2026-09-20 教育学闪卡上线

已按用户授权将静态闪卡部署到 https://shuzhiyucai.cn/flashcards/ ，版本 `20260920-172713-flashcards`。发布以服务器当前 `20260915-teaching-images` 为基线，只新增 `flashcards/` 六个文件，原有 564 个文件哈希不变；旧版本保留。Nginx 检查、重载、Cloudflare 缓存清理、18 项公网入口/文件检查和线上 Chrome 保存、测验、笔记、下载备份及窄屏操作通过。

维护副本为 `public/flashcards/`；主项目与核对记录位于 `/Users/yaril/个人文档/李雅儒/学习闪卡/`，详细部署记录是该项目 `闪卡试用版/review/deployment.md`。54 张已核对卡片、66 道自编题；学习记录和笔记只存在浏览器，可 JSON 备份，不提供云端学习后台。手机实机与学习效果待试用。门户构建、现有测试和 diff 检查通过；没有发布其他本地未上线专题，没有提交或推送 Git。

## 2026-09-19 官方 Logo：Y1「双页舒展」

用户已确定 Y1 为唯一官方标志，替代此前 A4 主选；G1、G3 继续作为历史备选保留。矢量原稿为 `public/logo.svg`，使用约定见 `docs/official-logo.md`。已同步网站 PNG / WebP、兼容旧地址和 ESP32 公开编程图标，保留首页布局。GitHub 同步与验证状态见 `review/logo-official-20260919/review.md`；本轮未操作线上服务器。

### 设计过程（历史记录）

第三轮最新入口 `review/logo-exploration-20260919/round-3/index.html`：按用户提出的“打开的书形成短脚 Y，上方是才字”制作 Y1—Y8 八款；用户强调重点为 Y 的书本识别与美观后，统一上方才字，仅变化下方页形，并加入“只看书页 Y”功能。新款待用户选择，原 A4 / G1 / G3 和此前已选包保留。交互、统一字形、资源与透明格式检查通过；未替换网站、未部署。

用户最新裁决：A4「书中有才」为主选，G1「开角才印」、G3「镂空才印」保留。已选素材入口 `review/logo-exploration-20260919/selected/README.md`，另有独立素材压缩包；15 个图形文件与第二轮原件逐一哈希核对一致。尚未替换网站或部署。

第二轮历史：用户选中 A（书页）、G（才字印）继续探索。最新入口 `review/logo-exploration-20260919/round-2/index.html`，各四款变式，保留原版并增加任选两款比较；15 项浏览器检查及 SVG / PNG 检查通过，现以以上用户裁决为准。

使用已安装的 `op7418/logo-generator-skill` 制作 A–H 八款独立矢量候选，入口为 `review/logo-exploration-20260919/index.html`，含蓝色 / 黑色 / 反白、收藏、网站页头和小尺寸预览；配套 SVG、透明 PNG 与总览。13 项浏览器交互检查及文件格式 / 透明度检查通过。当前只交付非公开选样资料，未替换标志、未部署；具体说明见该目录 README。

## 2026-09-19 自由电荷工作台（本地可操作样板，待用户审美与教学评价）

新增 `/simulations/electrostatics/workbench/`，按用户确认先完成一个独立样板，保留原八模块作对照。可添加、拖动和独立编辑至多8个源电荷；二维场图、任意平面电荷布局的三维电势地形、连线/中垂线/坐标轴截线图和同一探针联动。场源与试探电荷分开；单位就地解释；E/F独立显示；零场点周围留出清楚空隙；地形截口保持开放，不画假平顶。

核心为 `src/lib/electrostatics/free-charges.ts` 与 `src/components/electrostatics/workbench/`。新增25项独立数值检查，全专题现为108项检查及五水槽跨端对照；构建152路由，现有门户测试通过。已实际操作宽屏、818px窗口及390px窄屏，检查拖动、键盘、同点换试探电荷、三维点选、曲线联动、恢复、全屏及PNG/CSV导出。说明和截图见 `review/electrostatics-workbench/review.md`。没有将这些开发检查等同于用户审美认可、真实手机触摸或课堂效果；未部署，未改动Python工具包。

## 2026-09-19 静电场精修（功能原型，视觉与教学表达未验收）

最新用户反馈覆盖此前“发布候选”的判断：二维主图缺乏视觉层次，零场点附近的场线与坐标轴造成穿过零点的观感，nC 等单位缺少解释，三维地形与控件仍过于粗糙。已有数值、构建和浏览器检查记录保留，但不作为视觉或教学表达合格的证据。当时用户新增自由放置、拖动并独立调整源电荷的需求，预设模型不支持。后续已按上方记录完成独立工作台，原八模块的视觉与教学评价仍以用户反馈为准。

在既有八模块上补齐电势页与图像页的连线/中垂线同步图：φ 与有符号 Ex/Ey 分量共用 `sampleField`，可叠加 |E|、点击或拖动联动探针。点源排除区断线，纵轴可调且明确标出显示截断；横轴支持 0.25—128 倍，零场点自动选择可容纳它的最小倍率。`field-lines.ts` 统一场线方向与孤立解析零场点，区分同号中间根、异号弱侧根、等量异号无有限根及连续无场区域；二维主视野半宽上限 100 m，超出定位范围会提示并保留探针，不把根夹到边界。

试探电荷分为符号、大小和撤去，E/F 可独立开关；撤去电荷仍保留 P 点的 E、φ。做功页 P、高亮路径和累计功按同一进度联动。三维电势地形默认 asinh 高度、可选线性；排除区和范围外网格留空，不画成平顶，实际 φ 读数不受高度映射改写。场景共享保留 `s`，新增版本化 `axisGraph` 和 `terrain` 参数，主分享事件收集各模块当前设置。

`npm run test:electrostatics` 本轮已通过：40 项解析物理 + 3 项粒子 + 18 项场线/零场点 + 16 项轴向图 + 6 项三维电势地形，共 83 项，另含五种水槽 Python/TypeScript 跨端对照。源码与复现入口见 `docs/electrostatics.md`；本轮记录为 `review/electrostatics-refinement/review.md`。八页均完成1014px桌面与390px窄屏截图检查，分享恢复和导出已实际操作验证；最终构建与现有门户测试通过；本轮未部署、未作实物或课堂验收，下面既有部署和其他专题记录保持有效。

## 2026-09-18 静电场章节（本地发布候选）

新增 `/simulations/electrostatics/` 及八个独立实验入口，已接入模拟实验室和教学资源搜索。包括场强、电势三维/截面/地形、路径做功、方向分量图像、五布局虚拟描绘仪、解析导体、电容器/RC及粒子运动。公开活动为基于教材研究的重新设计题，源资料定位只放在内部文档。

共用模型位于 `src/lib/electrostatics/`，水槽案例的唯一源为 `src/data/electrostatics/tank-cases.json`。`tools/electrostatics-python/` 是非公开工具包，保留旧版16项回归及原程序，另有五布局求解、图件、实际比例PDF、CSV和独立压缩包。未找回原COMSOL工程；示例几何尚未实物定标。

复现数值检查：`npm run test:electrostatics`；网站检查仍用 `npm run build`、`npm test`。使用说明与模型边界见 `docs/electrostatics.md`，本轮软件/浏览器验证与选择性发布清单见 `review/electrostatics/review.md`。未操作线上服务器，未作课堂或实物测量验证；保留工作树原有其他改动。

最新修复（2026-09-14）：线上版本20260914-school-home。简介改为育才一中科技教育门户网站；新二维码指向 /?v=20260914-school，图片为home-qr-school-20260914.png。Nginx HTML改为no-store/no-cache/max-age=0；源站已验证no-store，但公网仍被CDN覆盖为max-age=14400；当前令牌无缓存设置编辑权限，不能宣称公网缓存已修复。旧的4小时浏览器缓存不能从服务器撤回，用户可通过新链接/新二维码首次绕过。

最新发布状态：2026-09-14 已上线 `20260914-smart-hardware`，基于线上 `20260702-141121` 选择性合入，未发布其他本地新专题。当前线上55项器件、原版模型教学图、智能硬件影像馆、公开Blockly和首页二维码；项目式学习暂时隐藏。发布与回滚记录见 `review/hardware-showcase/release/README.md`。


## 2026-09-14 展示范围调整

按最新反馈，公开目录精简为55项器件，32件保留完整教学三视图。排除杜邦线、RGB LED及灯条、电源与驱动、机械与执行器；同一器件保留一个版本，OLED保留自有教学版、两针LED保留红色、数字麦克风保留已焊版。原素材未删除，三支成片保留。教学图下不再重复编号说明；首页首屏增加“智能硬件实验室”；公开Blockly每次进入默认混合视图，手写草稿仍恢复。

本次构建及门户测试、新增7组产物检查、21项公开编程/课程测试通过；浏览器确认默认混合视图、图下重复说明移除、首屏入口正确。未上线。下方早期数量与四按钮约定为调整前记录。


门户采用 Astro 静态页面，维护入口见 AGENTS.md 与 README.md，页面结构见 docs/architecture.md。首页保留校园大图；项目式学习、科创天地、在线实验室与模拟实验室继续使用现有入口。

## 智能硬件实验室（2026-09-14）

已完成本地集成 `/maker/smart-hardware/`：课程概览与三个精选案例、独立器件3D和教学图、育才蓝三支影片，以及 `/esp32/` 公开编程体验。按用户最新要求，器件目录、详情和学生端器件选择不展示组合体；三支原成片保留。

资源由 `scripts/sync-hardware-assets.py` 从 Blender 源库按白名单导出；源模型、教学图和教材不在门户修改。页面从 `src/data/generated/hardware-catalog.json` 读取，公开副本为 `public/maker/smart-hardware/catalog.json`，大媒体使用哈希路径。

学生端由 ESP32Blockly 的 `tools/export-showcase.mjs` 导出公开静态版本。公开版不连接课堂设备，课堂源项目保留已有功能。教材仅使用第一篇学习路线与精选案例，不公开整篇或PDF。

## 验证与交付

必跑 `npm run build`、`npm test`；本专题增加 `npm run validate:hardware-assets` 和 `npm run test:hardware`。本地生产预览用 `npm run review:site`，只监听回环地址。功能与浏览器验收最终记录在 `review/hardware-showcase/review.md`。

本次未发布线上网站。当前工作树还包含其他尚未发布的专题，未来发布须与线上基线比较并明确增量范围，不可直接将全部本地页面发布。

影像栏目统一命名为“智能硬件影像馆”。当前公开展示版将GLB与高清教学图发送给浏览器，不能防止访客保存；原始Blender工程未导出。防复制改造尚未实施，仍仅本地预览。

公开展示候选小样：`/maker/smart-hardware/public-preview/B-PH-001/`，共3个器件，低面数模型和署名阅读图，未替换全库。重建与限制见review/public-showcase/README.md。正式上线必须用只含展示衍生物的干净发布集。

2026-09-14：首页隐藏项目式学习入口与板块，资源搜索同步移除；projectLearningVisible=false，原专题路由跳回首页，源码保留。公开展示小样归档至review/public-showcase，实际器件继续上一版。首页右上角二维码指向https://shuzhiyucai.cn/，支持悬停/点击放大；本轮仍未上线。

## 2026-09-15 教学标注图版（覆盖以上旧展示范围）

按用户最新要求，公开器件库只保留32件器件的96张教学标注图；3D查看器、GLB地址及无标注器件撤下。导出流程仅复制教学图与原有三支影片，旧导出资源移至 review/hardware-showcase/withdrawn-assets（非公开），Blender原件保持不变。公开Blockly索引仅保留32件器件的详情链接。页面展示与下载保护是两件事：图片仍可保存或截图，已被下载的模型无法收回。

本地构建、门户现有测试、7组专题检查与资源完整性验证通过，学生端23项相关测试通过；浏览器已验证正面大图、点击放大及390px窄屏无横向溢出。线上切换与旧模型地址验证状态见 review/hardware-showcase/teaching-images-release.md。

2026-09-15 已发布20260915-teaching-images，242项外网核查通过：旧55个GLB在两个域名均410，32详情与96教学图可访问；564个发布文件哈希完全一致。

## 实时测距与测速（2026-09-18）

新增 `/online-lab/motion-meter/`，从在线实验室进入。通过 Web Serial 读取现有 Arduino CSV，显示距离、5 点拟合速度、温湿度与两条时间曲线，支持冻结、CSV/日志导出和原始日志导入。本地构建与 Chrome 真机读取已验证，尚未发布。用法见 `docs/motion-meter.md`，验收见 `review/motion-meter/review.md`，算法检查 `node scripts/test-motion-meter.mjs`。

测量页增加 `MotionPrinciples.astro` 图解：往返测距、速度符号、五点最小二乘、反射时刻近似与窗口中心、温度/标定/角度修正边界。候选修正仅解释，不改变实时算法。

## 2026-09-19 网站宣传片（独立视频工程）

用户指定的 `guizang-product-video-skill` 已安装到用户级 `~/.codex/skills/guizang-product-video-skill`，固定上游版本 `c45aab4599bc6e883a6f6ea9d82f49ecdde1c8d0`；安装后的59个文件与上游核对一致。视频工程为 `video/数智育才宣传片-20260919/`，成品入口与验证见其中 `README.md`、`review.md`。

按用户确认沿用育才蓝与真实界面，横版60秒，展示已公开的动量模型、机械能表格/能量图、器件教学图库、积木编程与科创实训照片。视频副本挂载原页面/样式，示例数据明确标示；静电学、测速、真题与学生评价候选不进入本片。网站原代码、依赖和线上发布保持原状态；视频未上传或公开发布。复现从视频工程运行 `npm ci`、`npm run build` 与 README 中的混音、渲染命令。

- 2026-09-21：motion-compare现为超声波+VL53L0X，真实USB读数验证；1.2秒时间窗口及显示抑抖门限。源码与说明见docs/motion-meter.md、public/code/motion-compare。本轮仅本地，不部署。

- 2026-09-21 测速v9：motion-compare同步一帧孤立点确认、运动3点/静止长窗口算法，原始数据与处理后时间戳可导出；激光长距离配置已获得140/140有效输出，但两路距离不一致、动态准确度未验证。未部署。
