import json,sys,subprocess,os
d=sys.argv[1]; n=int(sys.argv[2]) if len(sys.argv)>2 else 12
j=json.load(open(f"rec/{d}/frames.json")); fr=j["frames"]; t0=fr[0]["t"]; T=fr[-1]["t"]-t0
picks=[]; 
for k in range(n):
    tt=t0+T*k/(n-1); f=min(fr,key=lambda x:abs(x["t"]-tt)); picks.append((f["f"],f["t"]-t0))
os.makedirs("sheets",exist_ok=True)
args=[]
for f,_ in picks: args+=["-i",f"rec/{d}/{f}"]
cols=4; rows=(n+cols-1)//cols
fc="".join(f"[{i}:v]scale=480:-1,drawtext=text='{picks[i][1]:.1f}s':x=8:y=8:fontsize=22:fontcolor=yellow[v{i}];" for i in range(n))
fc+="".join(f"[v{i}]" for i in range(n))+f"xstack=inputs={n}:layout="+"|".join(f"{(i%cols)*480}_{(i//cols)*270}" for i in range(n))
subprocess.run(["/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg","-loglevel","error","-y",*args,"-filter_complex",fc,"-frames:v","1",f"sheets/{d}.jpg"],check=True)
print(f"sheets/{d}.jpg", [round(p[1],1) for p in picks], j["events"])
