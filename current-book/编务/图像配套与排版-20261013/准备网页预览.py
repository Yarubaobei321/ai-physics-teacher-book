from 执行 import *
V=R/'网页预览';V.mkdir(exist_ok=True)
paths={
 'ch02':S/'01-入门与纸带/output/小车纸带记录页.html',
 'ch05':S/'05-数据与传感器/output/05-超声波/index.html',
 'ch06':S/'05-数据与传感器/output/06-视重数据/分析页.html',
 'ch07':S/'05-数据与传感器/output/07-机械能/index.html',
 'ch08':Path('/Users/yaril/个人文档/3 写作/微信文章项目/文章重写/02-物理可视化教学系列/实操/20261001-WorkBuddy续作/教程/配套/课堂示例/index.html'),
 'ch09':S/'02-力学与电容器/output/第09章/spring-collision.html',
 'ch10':S/'03-水槽预测与测点/output/第12章/tank-prediction.html',
 'ch11':S/'03-水槽预测与测点/output/第13章/photo-annotation.html',
 'ch12':S/'03-水槽预测与测点/output/第14章/tank-measured-compare.html',
 'ch14':P/'正文/第16章-活版电路拼图/配套/电容电流积分.html',
 'ch17':P/'正文/第20章-审学生的AI作品/配套/输入/自编审核练习.html'
}
for key,src in paths.items():
 q=V/key;q.mkdir(exist_ok=True);shutil.copy2(src,q/'index.html')
shutil.copy2(S/'03-水槽预测与测点/output/第13章/original.jpg',V/'ch11/original.jpg')
(R/'预览映射.json').write_text(json.dumps({k:str(v) for k,v in paths.items()},ensure_ascii=False,indent=2))
print('预览目录只含11个目标HTML和1张必需原照，无目录外内容')
