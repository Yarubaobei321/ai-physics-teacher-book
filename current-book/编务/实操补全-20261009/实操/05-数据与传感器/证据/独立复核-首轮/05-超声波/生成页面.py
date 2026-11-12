#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据 数据包.json 生成离线 index.html（把真实复算结果内联，无需联网）。"""
import json, os

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "数据包.json"), "r", encoding="utf-8") as fh:
    data = json.load(fh)

payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>第05章 · 超声波历史记录复算</title>
<style>
  :root{--bg:#f6f7f9;--card:#fff;--ink:#1f2430;--sub:#5b6472;--line:#e2e6ec;--accent:#2f6df0;--accent2:#c0392b;--warn:#b4690e}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,"PingFang SC","Microsoft YaHei",Segoe UI,sans-serif;font-size:14px;line-height:1.6}
  .wrap{max-width:1060px;margin:0 auto;padding:20px 18px 60px}
  h1{font-size:20px;margin:0 0 4px}
  h2{font-size:15px;margin:22px 0 10px;padding-left:9px;border-left:3px solid var(--accent)}
  .sub{color:var(--sub);font-size:12.5px;margin:0 0 14px}
  .ban{background:#fff3e0;border:1px solid #f0c98a;color:#8a5a00;border-radius:8px;padding:8px 12px;font-size:13px;margin-bottom:14px;font-weight:600}
  .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:14px}
  .row{display:flex;flex-wrap:wrap;gap:14px;align-items:center}
  button{padding:7px 13px;border-radius:7px;border:1px solid #cfd6df;background:#fff;color:var(--ink);font-size:13px;cursor:pointer}
  button:hover{background:#f0f3f7}
  button.on{background:var(--accent);border-color:var(--accent);color:#fff}
  select,input[type=number]{padding:6px 8px;border:1px solid #cfd6df;border-radius:6px;font-size:13px;background:#fff;color:var(--ink)}
  canvas{width:100%;height:auto;display:block;background:#fff;border:1px solid var(--line);border-radius:8px}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th,td{border:1px solid var(--line);padding:6px 9px;text-align:right}
  th{background:#f0f3f7;text-align:center;color:#38414f}
  td.k{text-align:left;background:#fafbfc;font-weight:600}
  .stat b{font-family:ui-monospace,Menlo,monospace}
  .legend{font-size:12.5px;color:var(--sub);margin-top:8px}
  .hint{font-size:12.5px;color:var(--sub)}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  @media(max-width:720px){.grid2{grid-template-columns:1fr}}
  code{font-family:ui-monospace,Menlo,monospace;background:#f0f3f7;padding:1px 5px;border-radius:4px;font-size:12.5px}
  .slider{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
  .slider input[type=range]{width:280px}
  .mono{font-family:ui-monospace,Menlo,monospace}
</style>
</head>
<body>
<div class="wrap">
  <h1>第05章 · 超声波测距历史记录复算</h1>
  <p class="sub">距离用固定声速 343 m/s 复算；速度用连续 5 个有效点对（距离 m，板端时间 s）做最小二乘斜率。</p>
  <div class="ban">数据身份：2026-09-18 历史记录复算（非本轮新测量）｜ 声速固定 343 m/s，未按当前气温改写历史数据</div>

  <div class="card">
    <div class="row" style="justify-content:space-between">
      <div class="row">
        <button id="btnFixed" class="on">固定平面 30cm</button>
        <button id="btnMotion">往返（远离-停住-靠近）</button>
      </div>
      <div class="row">
        <label class="hint">时间区间</label>
      </div>
    </div>
    <div class="slider" style="margin-top:12px">
      <span class="hint">起</span><input type="range" id="rng0"><span class="mono" id="lab0"></span>
      <span class="hint">止</span><input type="range" id="rng1"><span class="mono" id="lab1"></span>
      <button id="btnReset">全时段</button>
      <button id="btnCsv">导出当前区间 CSV</button>
    </div>
  </div>

  <div class="card">
    <h2 style="margin-top:0">距离 (mm) — 上</h2>
    <canvas id="cDist" width="1000" height="300"></canvas>
    <div class="legend" id="lgDist"></div>
  </div>

  <div class="card">
    <h2 style="margin-top:0">速度 (mm/s) — 下</h2>
    <canvas id="cVel" width="1000" height="300"></canvas>
    <div class="legend" id="lgVel"></div>
  </div>

  <div class="card">
    <h2 style="margin-top:0">实际统计（样本标准差用 N-1）</h2>
    <div class="grid2">
      <table>
        <tr><th colspan="2">距离</th></tr>
        <tr><td class="k">有效点数</td><td id="s_nv"></td></tr>
        <tr><td class="k">均值 (mm)</td><td id="s_dm"></td></tr>
        <tr><td class="k">样本标准差 (mm)</td><td id="s_ds"></td></tr>
      </table>
      <table>
        <tr><th colspan="2">5 点窗口速度</th></tr>
        <tr><td class="k">速度点数</td><td id="s_nve"></td></tr>
        <tr><td class="k">均值 (mm/s)</td><td id="s_vm"></td></tr>
        <tr><td class="k">样本标准差 (mm/s)</td><td id="s_vs"></td></tr>
      </table>
    </div>
    <p class="hint" id="stopThr"></p>
  </div>

  <div class="card">
    <h2 style="margin-top:0">方法、单位与限制</h2>
    <ul style="margin:0;padding-left:18px;font-size:13px">
      <li>只分析 <code>kind=U</code> 行；<code>kind=D</code> 为温湿度行，其温度<strong>不</strong>用于改写历史距离。</li>
      <li>距离复算：<code>distance_mm = pulse_us × 343 / 2000</code>；时间用板端触发时间 <code>t_s = t_us / 1e6</code>（两种时间不混用）。</li>
      <li>速度 = 连续 5 个有效点「距离(m)~板端时间(s)」最小二乘斜率，标注在窗口时间均值处；无效点/缺号/时间倒退会重置窗口，前 4 点为空白（不填 0）。</li>
      <li>符号阈值：<code>|v| ≤ 阈值(3×静止速度标准差) 判“停住”，否则按正负判 远离/靠近</code>。停住附近噪声会造成频繁翻转。</li>
      <li>窗口斜率只是<strong>窗口内局部变化率</strong>，<strong>不能</strong>当作任意运动全程“位移/总时间”平均速度。</li>
      <li>“约 30cm”的点距非精密距离标准；静止记录只用于检验重复性与实现，不能据此声称动态准确度。</li>
    </ul>
  </div>
</div>

<script>
var DATA = __PAYLOAD__;
var cur = DATA.files.fixed;
var curKey = "fixed";
var lo = 0, hi = 0, t0 = 0, tmin = 0, tmax = 1;
var N = 0;

function $(id){return document.getElementById(id);}

function setupRange(){
  N = cur.t_s.length;
  t0 = cur.t_s[0];
  tmin = 0;
  tmax = cur.t_s[N-1] - t0;
  lo = tmin; hi = tmax;
  var r0=$("rng0"), r1=$("rng1");
  r0.min=tmin; r0.max=tmax; r0.step=tmax/2000; r0.value=lo;
  r1.min=tmin; r1.max=tmax; r1.step=tmax/2000; r1.value=hi;
  updateLabels();
}
function updateLabels(){
  $("lab0").textContent = lo.toFixed(2)+" s";
  $("lab1").textContent = hi.toFixed(2)+" s";
}
function idxRange(){
  // 取相对时间落在 [lo,hi] 的点
  var i0=0, i1=N-1;
  for(var i=0;i<N;i++){ if(cur.t_s[i]-t0>=lo){ i0=i; break; } }
  for(var j=N-1;j>=0;j--){ if(cur.t_s[j]-t0<=hi){ i1=j; break; } }
  return [i0,i1];
}

function drawAxis(ctx, W, H, pad, xs, ys, color, ylab, xmin, xmax){
  ctx.clearRect(0,0,W,H);
  ctx.fillStyle="#fff"; ctx.fillRect(0,0,W,H);
  var plotW=W-pad.l-pad.r, plotH=H-pad.t-pad.b;
  var ymin=Math.min.apply(null,ys), ymax=Math.max.apply(null,ys);
  if(ymin===ymax){ ymin-=1; ymax+=1; }
  var dy=(ymax-ymin)*0.1; ymin-=dy; ymax+=dy;
  ctx.strokeStyle="#eceff4"; ctx.lineWidth=1; ctx.font="12px sans-serif"; ctx.fillStyle="#7b8493";
  for(var t=0;t<=5;t++){
    var val=ymin+(ymax-ymin)*t/5, y=pad.t+(ymax-val)/(ymax-ymin)*plotH;
    ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(W-pad.r,y); ctx.stroke();
    ctx.textAlign="right"; ctx.fillText(val.toFixed(1), pad.l-8, y+4);
  }
  ctx.strokeStyle="#c3cad4"; ctx.beginPath(); ctx.moveTo(pad.l,pad.t); ctx.lineTo(pad.l,pad.t+plotH); ctx.lineTo(W-pad.r,pad.t+plotH); ctx.stroke();
  // x ticks
  ctx.textAlign="center"; ctx.fillStyle="#7b8493";
  for(var k=0;k<=5;k++){
    var rv=xmin+(xmax-xmin)*k/5, x=pad.l+(rv-xmin)/(xmax-xmin||1)*plotW;
    ctx.fillText(rv.toFixed(1), x, pad.t+plotH+18);
  }
  ctx.fillStyle="#5b6472"; ctx.textAlign="center"; ctx.fillText("相对首点时间 t (s)", pad.l+plotW/2, H-6);
  ctx.textAlign="left"; ctx.fillText(ylab, pad.l, pad.t-8);
}
function drawSeries(ctx, W, H, pad, xs, ys, color, xmin, xmax){
  var plotW=W-pad.l-pad.r, plotH=H-pad.t-pad.b;
  var ymin=Math.min.apply(null,ys), ymax=Math.max.apply(null,ys);
  if(ymin===ymax){ ymin-=1; ymax+=1; }
  var dy=(ymax-ymin)*0.1; ymin-=dy; ymax+=dy;
  ctx.strokeStyle=color; ctx.lineWidth=1.6; ctx.beginPath();
  for(var i=0;i<xs.length;i++){
    var x=pad.l+(xs[i]-xmin)/(xmax-xmin||1)*plotW;
    var y=pad.t+(ymax-ys[i])/(ymax-ymin)*plotH;
    if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  }
  ctx.stroke();
}
function render(){
  var r = idxRange(); var i0=r[0], i1=r[1];
  var pad={l:64,r:20,t:22,b:34};
  var xmin = cur.t_s[i0]-t0, xmax = cur.t_s[i1]-t0; if(xmax<=xmin) xmax=xmin+1e-6;

  // distance
  var dctx=$("cDist").getContext("2d");
  var Wd=$("cDist").width, Hd=$("cDist").height;
  var dxs=[], dys=[];
  for(var i=i0;i<=i1;i++){ if(cur.distance_mm[i]!==null){ dxs.push(cur.t_s[i]-t0); dys.push(cur.distance_mm[i]); } }
  if(dxs.length>1){
    drawAxis(dctx,Wd,Hd,pad,dxs,dys,"#2f6df0","距离 (mm)",xmin,xmax);
    drawSeries(dctx,Wd,Hd,pad,dxs,dys,"#2f6df0",xmin,xmax);
    $("lgDist").textContent="距离 (mm)，点数 "+dxs.length+"；数据身份：2026-09-18历史记录复算（声速 343 m/s）";
  } else { dctx.clearRect(0,0,Wd,Hd); $("lgDist").textContent="该区间无距离点"; }

  // velocity
  var vctx=$("cVel").getContext("2d");
  var Wv=$("cVel").width, Hv=$("cVel").height;
  var vxs=[], vys=[];
  for(var j=i0;j<=i1;j++){ if(cur.vel_mm_s[j]!==null){ vxs.push(cur.center_t_s[j]-t0); vys.push(cur.vel_mm_s[j]); } }
  if(vxs.length>1){
    drawAxis(vctx,Wv,Hv,pad,vxs,vys,"#c0392b","速度 (mm/s)",xmin,xmax);
    drawSeries(vctx,Wv,Hv,pad,vxs,vys,"#c0392b",xmin,xmax);
    $("lgVel").textContent="5 点窗口速度 (mm/s)，窗口数 "+vxs.length+"；数据身份：2026-09-18历史记录复算";
  } else { vctx.clearRect(0,0,Wv,Hv); $("lgVel").textContent="该区间无速度点"; }

  // stats (全时段，不随区间变化——统计针对整段记录)
  var s=cur.stats;
  $("s_nv").textContent=s.n_valid;
  $("s_dm").textContent=s.dist_mean_mm.toFixed(3);
  $("s_ds").textContent=s.dist_std_mm.toFixed(4);
  $("s_nve").textContent=s.n_vel;
  $("s_vm").textContent=s.vel_mean_mm_s.toFixed(4);
  $("s_vs").textContent=s.vel_std_mm_s.toFixed(4);
  $("stopThr").textContent="符号阈值（远离/停住/靠近）= 静止记录速度样本标准差×3 = "+DATA.stop_threshold_mm_s.toFixed(4)+" mm/s。统计针对整段记录，不随查看区间变化。";
}

function sel(k){ curKey=k; cur=DATA.files[k]; setupRange(); render();
  $("btnFixed").className = (k==="fixed"?"on":"");
  $("btnMotion").className = (k==="motion"?"on":"");
}

$("rng0").addEventListener("input",function(e){ lo=parseFloat(e.target.value); if(lo>hi){lo=hi;e.target.value=lo;} updateLabels(); render(); });
$("rng1").addEventListener("input",function(e){ hi=parseFloat(e.target.value); if(hi<lo){hi=lo;e.target.value=hi;} updateLabels(); render(); });
$("btnReset").addEventListener("click",function(){ lo=tmin;hi=tmax;$("rng0").value=lo;$("rng1").value=hi;updateLabels();render(); });
$("btnFixed").addEventListener("click",function(){ sel("fixed"); });
$("btnMotion").addEventListener("click",function(){ sel("motion"); });

function csvCell(s){ s=(s===null||s===undefined)?"":String(s); if(/[",\\n]/.test(s)) return '"'+s.replace(/"/g,'""')+'"'; return s; }
$("btnCsv").addEventListener("click",function(){
  var r=idxRange(); var i0=r[0], i1=r[1];
  var L=[];
  L.push(["# 数据身份","2026-09-18历史记录复算"].map(csvCell).join(","));
  L.push(["# 源文件",cur.file].map(csvCell).join(","));
  L.push(["# 声速(m/s)",343].map(csvCell).join(","));
  L.push(["# 时间区间(s, 相对首点)",lo.toFixed(3),hi.toFixed(3)].map(csvCell).join(","));
  L.push(["逐点局部序号","设备seq","t相对(s)","t_us","distance_mm","vel_mm_s"].map(csvCell).join(","));
  for(var i=i0;i<=i1;i++){
    L.push([i+1, cur.seq[i], (cur.t_s[i]-t0).toFixed(6), (cur.t_s[i]*1e6).toFixed(0),
            cur.distance_mm[i]===null?"":cur.distance_mm[i].toFixed(3),
            cur.vel_mm_s[i]===null?"":cur.vel_mm_s[i].toFixed(4)].map(csvCell).join(","));
  }
  var blob=new Blob(["\\uFEFF"+L.join("\\r\\n")],{type:"text/csv;charset=utf-8"});
  var a=document.createElement("a"); a.href=URL.createObjectURL(blob);
  a.download=(curKey==="fixed"?"固定平面":"往返")+"-区间"+lo.toFixed(1)+"-"+hi.toFixed(1)+"s.csv";
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(function(){URL.revokeObjectURL(a.href);},1000);
});

sel("fixed");
</script>
</body>
</html>
"""

html = HTML.replace("__PAYLOAD__", payload)
with open(os.path.join(here, "index.html"), "w", encoding="utf-8") as fh:
    fh.write(html)
print("index.html written, size =", os.path.getsize(os.path.join(here, "index.html")))
