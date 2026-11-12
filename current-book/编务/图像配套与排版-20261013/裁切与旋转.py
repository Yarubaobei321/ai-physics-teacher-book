from 执行 import *
from PIL import Image,ImageOps
log=[]
def out(ch,rel,fn):
 p=P/'正文'/ch/rel;im=ImageOps.exif_transpose(Image.open(p));q=p.with_name(p.stem+'-v2.png');new=fn(im);new.save(q)
 edit(p.parent.parent/'正文.md',[(rel,str(q.relative_to(p.parent.parent)))])
 log.append({'source':str(p),'size':im.size,'new':str(q),'new_size':new.size})
def join_vertical(images,gap=18):
 w=max(x.width for x in images);h=sum(x.height for x in images)+gap*(len(images)-1)
 im=Image.new('RGB',(w,h),'white');y=0
 for x in images:im.paste(x,((w-x.width)//2,y));y+=x.height+gap
 return im
out('第01章-准备好工作区','本轮配图/首次调用.png',lambda im:join_vertical([im.crop((500,130,1975,365)),im.crop((415,1260,1990,1535))]))
out('第02章-打点计时器纸带','本轮配图/WorkBuddy文件交付.png',lambda im:im.crop((75,690,1210,988)))
out('第06章-超重与失重','assets/超失重仪-网页控制与监测.jpg',lambda im:im.crop((278,84,1371,889)))
out('第08章-可动圆弧轨道','assets/09-自由轨道1比3最高点.png',lambda im:im.crop((0,0,im.width,1250)))
out('第18章-3D建模和3D打印','assets/ESP32-同角度改后.jpg',lambda im:im.crop((210,70,930,1320)))
out('第18章-3D建模和3D打印','assets/色环第一轮试样-放进水里.jpg',lambda im:im.crop((0,205,im.width,1330)))
out('第12章-描绘仪的原理与改进','assets/平行板实测-通用坐标纸.jpg',lambda im:im.transpose(Image.Transpose.ROTATE_270))
# 两章共用错误图：只去底部下载按钮，保留全部红黄蓝色环及左右被改乱的刻度
for ch,rel in [('第01章-准备好工作区','assets/AI试稿-红线接错.jpg'),('第13章-二十组同时测量','assets/AI连线试稿-红线接错.jpg')]:
 out(ch,rel,lambda im:im.crop((0,0,im.width,1433)))
# 纸带图：真实浏览器结果区与学生结论栏上下拼接
im=join_vertical([Image.open(R/'纸带-结果.png'),Image.open(R/'纸带-结论.png')])
q=P/'正文/第02章-打点计时器纸带/本轮配图/纸带计算结果-v2.png';im.save(q)
edit(q.parent.parent/'正文.md',[('本轮配图/纸带计算结果.jpg','本轮配图/纸带计算结果-v2.png')])
(R/'裁切记录.json').write_text(json.dumps(log,ensure_ascii=False,indent=2))
print(json.dumps(log,ensure_ascii=False,indent=2))
