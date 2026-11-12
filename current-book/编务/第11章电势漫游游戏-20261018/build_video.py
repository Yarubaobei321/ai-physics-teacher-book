# 合成《电势漫游》宣传片：真实录像分段＋字幕卡＋片头片尾＋游戏音效。输出 1080p 和 720p。
import json, os, shutil, subprocess, bisect
from PIL import Image
FF="/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"; FPS=30; SFX="/Users/yaril/Documents/“AI赋能教师”专项培训/精品课/静电场分组实验/静电场体验游戏/assets/sfx/"
def fr(scene,t): # 场景相对时间 t 处的录像帧
    j=json.load(open(f"rec/{scene}/frames.json")); return j
cache={}
def frame_at(scene,t):
    if scene not in cache:
        j=json.load(open(f"rec/{scene}/frames.json")); ts=[f["t"] for f in j["frames"]]; cache[scene]=(j,ts)
    j,ts=cache[scene]; T=ts[0]+t; i=max(0,bisect.bisect_right(ts,T)-1); return f"rec/{scene}/{j['frames'][i]['f']}"
def ev(scene,name,k=0):
    j=json.load(open(f"rec/{scene}/frames.json")); e=[x["t"] for x in j["events"] if x["name"]==name]; return e[k]-j["frames"][0]["t"] if len(e)>k else None
# 时间线：(类型, 参数, 时长, 字幕[(起,止,卡片id)], 音效[(相对秒, 文件)])
TL=[]
def seg(scene,a,b,caps=(),sfx=()): TL.append(("rec",(scene,a),b-a,list(caps),[(t-a,f) for t,f in sfx if a<=t<=b]))
def card(cid,dur,sfx=()): TL.append(("card",cid,dur,[],list(sfx)))
card("title",3.6,[(0.2,"level.wav")])
seg("s1-intro",0.0,2.3,[(0.3,2.3,"c-intro1")])
seg("s1-intro",3.8,10.4,[(0,3.4,"c-intro1"),(3.4,6.6,"c-intro2"),(0,6.6,"n-height")])
L=ev("s2-howto","launch"); A=ev("s2-howto","placed")
seg("s2-howto",5.0,18.6,[(0,A-5.0+1.0,"c-how1"),(A-5.0+1.0,L-5.0,"c-how2"),(L-5.0,13.6,"c-how3")],[(L,"launch.wav")])
L1=ev("s3-level","launch",0); B=ev("s3-level","barrier"); L2=ev("s3-level","launch",1); C=ev("s3-level","clear")
seg("s3-level",5.2,19.0,[(0,B-5.2+1.2,"c-lv1"),(B-5.2+1.2,13.8,"c-lv2"),(0,13.8,"t-level")],[(L1,"launch.wav"),(B,"barrier.wav"),(L2,"launch.wav"),(C,"clear.wav"),(C+0.9,"star.wav")])
L=ev("s4-rings","launch"); C=ev("s4-rings","clear")
seg("s4-rings",1.0,9.4,[(0,8.4,"c-rings"),(0,8.4,"t-level")],[(L,"launch.wav"),(C,"clear.wav"),(C+0.9,"star.wav")])
L=ev("s5-fieldline","launch"); C=ev("s5-fieldline","clear")
seg("s5-fieldline",L-1.0,C+1.6,[(0,C-L+2.6,"c-line")],[(L,"launch.wav"),(C,"clear.wav")])
L=ev("s6-first","launch")
seg("s6-first",L-0.6,L+9.6,[(0,10.2,"c-orbit")],[(L,"launch.wav")])
seg("s7-walk",6.6,12.4,[(0,5.8,"c-walk")],[(6.8,"step.wav"),(8.0,"step.wav"),(9.2,"ring.wav"),(10.6,"ring.wav")])
seg("s8-lens",8.6,18.6,[(0,10,"c-lens")],[(8.9,"zap.wav")])
seg("s9-outro",3.8,14.2,[(0,3.5,"w1"),(3.5,6.9,"w2"),(6.9,10.4,"w3")])
card("end",4.6,[(0.2,"clear.wav")])
out="vframes"; shutil.rmtree(out,ignore_errors=True); os.makedirs(out)
caps={}; 
def cap(cid):
    if cid not in caps: caps[cid]=Image.open(f"cards/{cid}.png").convert("RGBA")
    return caps[cid]
n=0; audio=[]; t_glob=0.0; XF=0.35
prev_last=None
for kind,arg,dur,clist,sfx in TL:
    N=int(round(dur*FPS))
    for s,f in sfx: audio.append((t_glob+s,f))
    for k in range(N):
        t=k/FPS
        if kind=="card": im=cap(arg).convert("RGB")
        else:
            scene,a=arg; im=Image.open(frame_at(scene,a+t)).convert("RGB")
            if im.size!=(1920,1080): im=im.resize((1920,1080))
            base=im.convert("RGBA")
            for s,e,cid in clist:
                if s-0.01<=t<=e:
                    al=min(1,(t-s)/0.3,(e-t)/0.3) if cid.startswith(("c-","w")) else 1
                    al=max(0,min(1,al)); c=cap(cid)
                    if al<1: c=c.copy(); c.putalpha(c.getchannel("A").point(lambda v:int(v*al)))
                    base=Image.alpha_composite(base,c)
            im=base.convert("RGB")
        if prev_last is not None and k<int(XF*FPS):
            im=Image.blend(prev_last,im,(k+1)/(int(XF*FPS)+1))
        im.save(f"{out}/{n:06d}.jpg",quality=92); n+=1
    prev_last=im; t_glob+=N/FPS
total=n/FPS; print("frames",n,"seconds",round(total,1))
json.dump({"total":total,"audio":audio},open("timeline.json","w"),ensure_ascii=False,indent=1)
# 音频：静音底轨＋音效
ins=["-f","lavfi","-t",f"{total:.2f}","-i","anullsrc=r=48000:cl=stereo"]; fl=[]
for i,(t,f) in enumerate(audio):
    ins+=["-i",SFX+f]; fl.append(f"[{i+1}:a]aresample=48000,volume=0.8,adelay={int(t*1000)}|{int(t*1000)}[a{i}]")
mix="".join(f"[a{i}]" for i in range(len(audio)))
fc=";".join(fl)+f";[0:a]{mix}amix=inputs={len(audio)+1}:normalize=0,alimiter=limit=0.9[aout]"
subprocess.run([FF,"-loglevel","error","-y",*ins,"-filter_complex",fc,"-map","[aout]","-t",f"{total:.2f}","-c:a","aac","-b:a","160k","audio.m4a"],check=True)
subprocess.run([FF,"-loglevel","error","-y","-framerate",str(FPS),"-i",f"{out}/%06d.jpg","-i","audio.m4a","-c:v","libx264","-preset","slow","-crf","20","-pix_fmt","yuv420p","-threads","4","-c:a","copy","-shortest","-movflags","+faststart","电势漫游-宣传片-1080p.mp4"],check=True)
subprocess.run([FF,"-loglevel","error","-y","-i","电势漫游-宣传片-1080p.mp4","-vf","scale=1280:-2","-c:v","libx264","-crf","25","-preset","medium","-threads","4","-c:a","copy","-movflags","+faststart","电势漫游-宣传片-720p.mp4"],check=True)
print("done")
