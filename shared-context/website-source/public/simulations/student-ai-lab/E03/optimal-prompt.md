# E03 · 动词作非谓语 · 评审重构的最优提示词

> 这是活动结束后依据评审证据重构的研究提示词，不属于学生现场原始提示词。

请生成一个纯 HTML+CSS+JS 单文件网页，零外链、零素材依赖，双击即可在浏览器打开。

一、主题与受众：面向高中英语课堂的"动词作非谓语"交互网页。学习目标：学生通过读总述、看四大板块（作状语/作定语/作主宾表/作补语）讲解与固定搭配、易错警示与真题、做综合测验、订正错题，掌握非谓语三种形式的用法区别与逻辑主语一致规则。

二、语法规则与例句规格（例句本身语法错=fail；固定搭配错如 enjoy to do=fail；讲法取舍属"不判错区"不判错）：
- 三种形式区别须正确陈述（核心 A3 补全）：不定式 to do 表目的/将来/具体；动名词 doing 名词性质，表习惯/抽象；现在分词 doing 表主动/进行；过去分词 done 表被动/完成。
- 作成分规则（核心 A3 补全）：单个分词作定语前置、分词短语作定语后置；作状语表时间/原因/结果/条件/让步/伴随；make sb do（被动加 to，即 be made to do）；get/have sth done；with+n.+to do 表将来未做、with+n.+doing 表正在进行、with+n.+done 表被动完成。
- 固定搭配须正确（核心 B1 fail 规避）：enjoy/finish/mind/practice 接 doing；decide/hope/refuse/promise 接 to do；forget to do（忘记要做）vs forget doing（忘记做过）；regret to do（遗憾要做）vs regret doing（后悔做过）；need/want/require doing=need to be done；be worth doing；It's no use doing；It takes sb...to do。
- 逻辑主语一致（核心 A3 补全）：分词作状语时其逻辑主语须与主句主语一致，否则为垂悬分词错（如错例："Walking down the street, the trees were beautiful."——分词逻辑主语 trees 不能 walk）；独立成分例外：generally speaking、judging from、to tell the truth 等不受主句主语限制。
- 易错警示：-ing 修饰物 vs -ed 修饰人（a boring movie / a bored audience）；be used to doing（习惯于）vs used to do（过去常常）vs be used to do（被用来）。
- 例句本身须语法正确、拼写无误，且能说明对应规则；高考真题题干须规范。

三、交互与教学功能：①总述（4 类形式定义+经典对比例句，如 "I forgot to lock the door." vs "I forgot locking the door."）；②四大板块（作状语/作定语/作主宾表/作补语），每板块含核心讲解＋固定搭配＋易错警示＋5 道标明来源（如 2025 新高考一卷）的高考真题；③综合测验 10 题；④渐进式反馈：选错 1 次提示"再想想"并点出题目类型，连错 2 次才揭示正确答案＋深度解析并自动入错题本；⑤错题本：点击错题条目唤起重做模态框，做对则从错题本移除、做错则保留；⑥全局/板块计分＋重置按钮。

四、工程与呈现约束：布局分"6 锚点导航／总述＋4 板块卡片／综合测验／侧边栏错题本"多层；1440×900 分辨率下无遮挡、无溢出；卡片化分区、渐变标题、侧边栏错题本布局清晰；含移动端 viewport meta 与 800px 断点；所有导航、单选、重做选项为真实 button/radio 且键盘可达（重做模态框选项**不得用 div 实现**，须用 button 或含 role/键盘事件的元素）；答错揭示反馈不得出现"A. A. Seen"双字母冗余（一次性显示"A. Seen"即可）；正文字号≥0.9rem；无外链字体/外链 JS 库。

五、验收清单（生成后请逐条自检，并在代码之外用文字报告每条结果）：
1. 三种形式区别核对（核心 B1 grammar-rule 规避 + A3 补全）：核对总述与各板块讲解中 to do/doing/done 的用法区别陈述——不定式表目的/将来/具体、动名词表习惯/抽象、现在分词表主动/进行、过去分词表被动/完成——无错；
2. 固定搭配核对（核心 B1 fail 规避）：核对固定搭配栏全部条目——enjoy doing/finish doing/mind doing（不得出现 enjoy to do）；decide to do/hope to do；forget to do vs doing、regret to do vs doing；need doing=need to be done；be worth doing；It's no use doing——逐条报告；
3. 逻辑主语与易错点核对（A3 补全）：核对"分词作状语逻辑主语须与主句主语一致"陈述；列举垂悬分词错例；核对 -ing 修饰物 vs -ed 修饰人、be used to doing vs used to do vs be used to do 区分陈述；
4. 真题答案-解析同源核对（核心 A4 补全 + B1 exercise-consistency）：对全部 30 题（4 板块×5+综合 10）逐题核对正确选项确实正确、解析与答案一致且能说明所授规则——adv Q1 Seen（被动）、Q2 to catch（目的）、Q5 enjoying（伴随）；attr Q1 to be held（将来被动）、Q3 to answer（序数词）；subobj Q1 crying（It's no use doing）、Q3 to become（表语将来）；comp Q1 written（get sth done）、Q2 singing（hear sb doing）、Q4 clean（make sb do）；mixed Q1 Having waited（主动完成先于）、Q2 boring/bored（-ing 物/-ed 人）、Q5 Not having finished（否定完成式）、Q9 to tell（regret to do）、Q10 not to play（warn sb not to do）——逐题报告答案与所授规则条目的对应；
5. 渐进式反馈与错题本判定核对（A4 补全 + B3 规避）：实测任一题——错 1 次显示"再想想"+题目类型提示但不揭示答案、连错 2 次揭示答案+深度解析+自动入错题本；点击错题本条目唤起重做模态框，做对则移除、做错则保留；重做选项键盘可达；
6. 工程核对（B3/B4 规避）：6 锚点导航、30 题单选、全局/板块计分、重置、清空错题本、点击错题本唤起重做模态框、重做提交判定各操作一次，0 console errors；重做模态框选项为 button 或 role=button 元素（非裸 div）；答错揭示反馈无双字母冗余；正文字号≥0.9rem；无外链请求。
