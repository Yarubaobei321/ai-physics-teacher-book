#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据 数据包.json 生成第06章离线 分析页.html（把真实构造/计算结果内联）。"""
import json, os

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "数据包.json"), "r", encoding="utf-8") as fh:
    data = json.load(fh)
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>第06章 · 视重（构造数据）分析页</title>
<style>
  :root{--bg:#f6f7f9;--card:#fff;--ink:#1f2430;--sub:#5b6472;--line:#e2e6ec;--accent:#2f6df0;--accent2:#c0392b;--warn:#b4690e}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,"PingFang SC","Microsoft YaHei",Segoe UI,sans-serif;font-size:14px;line-height:1.6}
  .wrap{max-width:1060px;margin:0 auto;padding:20px 18px 60px}
  h1{font-size:20px;margin:0 0 4px}
  h2{font-size:15px;margin:22px 0 10px;padding-left:9px;border-left:3px solid var(--accent)}
  .sub{color:var(--sub);font-size:12.5px;margin:0 0 14px}
  .ban{background:#fdecea;border:1px solid #f0b3aa;color:#a4261a;border-radius:8px;padding:9px 12px;font-size:13px;margin-bottom:14px;font-weight:600}
  .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:14px}
  canvas{width:100%;height:auto;display:block;background:#fff;border:1px solid var(--line);border-radius:8px}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th,td{border:1px solid var(--line);padding:6px 9px;text-align:right}
  th{background:#f0f3f7;text-align:center;color:#38414f}
  td.k{text-align:left;background:#fafbfc;font-weight:600}
  .toggles{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px}
  .toggles label{display:inline-flex;align-items:center;gap:5px;font-size:12.5px;border:1px solid var(--line);border-radius:999px;padding:3px 10px;cursor:pointer;background:#fff}
  .sw{width:12px;height:12px;border-radius:3px;display:inline-block}
  .hint{font-size:12.5px;color:var(--sub)}
  code{font-family:ui-monospace,Menlo,monospace;background:#f0f3f7;padding:1px 5px;border-radius:4px;font-size:12.5px}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  @media(max-width:720px){.grid2{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
  <h1>第06章 · 视重（超重/失重）构造数据练习</h1>
  <p class="sub">二阶巴特沃斯低通 4Hz / 2Hz × 单次前向(实时) / 前后向(零相位)；a = F/m − g；梯形积分 v0=0。</p>
  <div class="ban">数据身份：构造数据，非实测｜ 非严力耕老师装置的原始数据，也非本轮真实测量｜ 真实力/加速度硬件本轮未连接</div>

  <div class="card">
    <h2 style="margin-top:0">一、力 F(t)　单位 N</h2>
    <div class="toggles" id="tgForce"></div>
    <canvas id="cF" width="1000" height="330"></canvas>
  </div>

  <div class="card">
    <h2 style="margin-top:0">二、加速度 a(t)=F/m−g　单位 m/s²</h2>
    <div class="toggles" id="tgAcc"></div>
    <canvas id="cA" width="1000" height="330"></canvas>
  </div>

  <div class="card">
    <h2 style="margin-top:0">三、速度 v(t)=∫a dt（梯形积分，v₀=0）　单位 m/s</h2>
    <div class="toggles" id="tgVel"></div>
    <canvas id="cV" width="1000" height="330"></canvas>
  </div>

  <div class="card">
    <h2 style="margin-top:0">四、实际统计（由 分析程序.py 运行得到）</h2>
    <h2 style="margin-top:6px;border:0;padding:0;color:#38414f">力在各运动区间的均值 (N)</h2>
    <table id="tF"></table>
    <h2 style="margin-top:16px;border:0;padding:0;color:#38414f">加速度各区间均值 (m/s²)，以及 ∫a dt 与末速度</h2>
    <table id="tA"></table>
    <h2 style="margin-top:16px;border:0;padding:0;color:#38414f">速度各区间均值 (m/s)</h2>
    <table id="tV"></table>
    <h2 style="margin-top:16px;border:0;padding:0;color:#38414f">恒定力回归自检（恒定 4.9 N×301 点）</h2>
    <table id="tC"></table>
    <p class="hint">区间按<strong>运动状态</strong>划分：起始静止 [0,0.50)、正加速 [0.50,1.00)、匀速 [1.00,2.00)、负加速 [2.00,2.50)、结束静止 [2.50,3.00]。1–2 s 理想 a=0，物体<strong>匀速上升</strong>（v≠0），是受力平衡而非静止，故不叫“静止”。正、负加速平台<strong>分列</strong>，不合并平均。理想：静止/匀速 m·g=4.900 N；正加速 m(g+1)=5.400 N；负加速 m(g−1)=4.400 N。∫a dt 理想为 0，末速度理想为 0；含干扰/滤波后的偏离属真实结果，<strong>未做归零校正</strong>。</p>
  </div>

  <div class="card">
    <h2 style="margin-top:0">五、20 Hz 干扰处的幅频响应（按实际离散传递函数 H(e^{jω})）</h2>
    <table id="tR"></table>
    <p class="hint">按实际离散传递函数 <code>H(z)=(b0+b1z⁻¹+b2z⁻²)/(1+a1z⁻¹+a2z⁻²)</code> 取 <code>z=e^{jω}</code>：单次前向为 <code>|H(e^{jω})|</code>；前后向为 <code>|H(e^{jω})|²</code>（等效阶数翻倍）——<strong>两者幅频响应不同</strong>。非模拟域公式。</p>
  </div>

  <div class="card">
    <h2 style="margin-top:0">六、算法、初始化与端点处理</h2>
    <ul style="margin:0;padding-left:18px;font-size:13px">
      <li>构造：m=0.500 kg，g=9.80 m/s²，向上为正；t=i×0.01 s，i=0…300；<code>F_raw=F_ideal+0.05·sin(40πt)</code>（20 Hz 人为干扰）。</li>
      <li>滤波：二阶巴特沃斯低通 biquad（RBJ，Q=1/√2，双线性变换预畸变）。</li>
      <li>单次前向（实时，因果）：<code>y[n]=b0x[n]+b1x[n−1]+b2x[n−2]−a1y[n−1]−a2y[n−2]</code>；<strong>稳态初值</strong>（x[−1]=x[−2]=x[0]，y[−1]=y[−2]=x[0]·DC增益）。含 4.9 N 静重的力若用全零初值会制造近 −g 启动暂态（伪影），本页不使用。</li>
      <li>前后向零相位：前向 → 反转 → 同一次前向 → 反转；两次各用稳态初值；<strong>非因果</strong>，不适用于实时。</li>
      <li>端点处理：两端稳态初值，暂态很小；未采用 scipy 奇延拓，边缘仍有轻微差异。</li>
      <li>加速度 <code>a=F/m−g</code>；积分用<strong>实际时间</strong>梯形法，v₀=0，<strong>不</strong>强行让末速度归零。</li>
    </ul>
  </div>

  <div class="card">
    <h2 style="margin-top:0">七、文件</h2>
    <p class="hint">原始表 <code>原始表.csv</code>｜处理表 <code>处理表.csv</code>｜参数说明 <code>参数说明.md</code>｜实际检查 <code>统计与检查.md</code>｜计算程序 <code>分析程序.py</code>｜页面 <code>分析页.html</code></p>
  </div>
</div>

<script>
var DATA = __PAYLOAD__;
var COLORS = {
  ideal:"#2f6df0", raw:"#98a2b3",
  fwd4:"#c0392b", fb4:"#e07b39",
  fwd2:"#7d3cc0", fb2:"#1f8a4c"
};
var LABELS = {
  ideal:"理想", raw:"原始(含20Hz)",
  fwd4:"4Hz 单次前向", fb4:"4Hz 前后向零相位",
  fwd2:"2Hz 单次前向", fb2:"2Hz 前后向零相位"
};

function $(id){return document.getElementById(id);}

function drawChart(canvasId, series, ylab, tmax){
  var c=$(canvasId), ctx=c.getContext("2d");
  var W=c.width, H=c.height, pad={l:66,r:20,t:20,b:36};
  var pw=W-pad.l-pad.r, ph=H-pad.t-pad.b;
  ctx.clearRect(0,0,W,H); ctx.fillStyle="#fff"; ctx.fillRect(0,0,W,H);
  // y range
  var ymin=Infinity, ymax=-Infinity;
  series.forEach(function(s){ s.y.forEach(function(v){ if(v<ymin)ymin=v; if(v>ymax)ymax=v; }); });
  if(!isFinite(ymin)){ ymin=0; ymax=1; }
  if(ymin===ymax){ ymin-=1; ymax+=1; }
  var dy=(ymax-ymin)*0.08; ymin-=dy; ymax+=dy;
  // grid
  ctx.strokeStyle="#eceff4"; ctx.lineWidth=1; ctx.font="12px sans-serif"; ctx.fillStyle="#7b8493";
  for(var t=0;t<=5;t++){
    var val=ymin+(ymax-ymin)*t/5, y=pad.t+(ymax-val)/(ymax-ymin)*ph;
    ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(W-pad.r,y); ctx.stroke();
    ctx.textAlign="right"; ctx.fillText(val.toFixed(2), pad.l-8, y+4);
  }
  ctx.strokeStyle="#c3cad4"; ctx.beginPath(); ctx.moveTo(pad.l,pad.t); ctx.lineTo(pad.l,pad.t+ph); ctx.lineTo(W-pad.r,pad.t+ph); ctx.stroke();
  ctx.textAlign="center"; ctx.fillStyle="#7b8493";
  for(var k=0;k<=6;k++){ var tv=tmax*k/6, x=pad.l+tv/tmax*pw; ctx.fillText(tv.toFixed(1), x, pad.t+ph+18); }
  ctx.fillStyle="#5b6472"; ctx.fillText("时间 t (s)", pad.l+pw/2, H-6);
  ctx.textAlign="left"; ctx.fillText(ylab, pad.l, pad.t-6);
  // series
  series.forEach(function(s){
    ctx.strokeStyle=s.color; ctx.lineWidth=s.w||1.7; ctx.globalAlpha=s.alpha||1; ctx.beginPath();
    for(var i=0;i<s.t.length;i++){
      var x=pad.l+s.t[i]/tmax*pw, y=pad.t+(ymax-s.y[i])/(ymax-ymin)*ph;
      if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
    }
    ctx.stroke(); ctx.globalAlpha=1;
  });
}

function seriesFor(key, ykey){
  return {t:DATA.time_s, y:DATA[ykey], color:COLORS[key], w:(key==="raw"?1.2:1.8), alpha:(key==="raw"?0.75:1)};
}

function buildToggles(containerId, state, onChange){
  var box=$(containerId); box.innerHTML="";
  Object.keys(LABELS).forEach(function(k){
    var l=document.createElement("label");
    var sw=document.createElement("span"); sw.className="sw"; sw.style.background=COLORS[k];
    var cb=document.createElement("input"); cb.type="checkbox"; cb.checked=state[k];
    cb.addEventListener("change",function(){ state[k]=cb.checked; onChange(); });
    l.appendChild(cb); l.appendChild(sw); l.appendChild(document.createTextNode(LABELS[k]));
    box.appendChild(l);
  });
}

var stF={ideal:true,raw:true,fwd4:true,fb4:true,fwd2:false,fb2:false};
var stA={ideal:true,raw:true,fwd4:true,fb4:false,fwd2:false,fb2:false};
var stV={ideal:true,raw:true,fwd4:false,fb4:true,fwd2:false,fb2:false};

function keyToForce(k){ return {ideal:"force_ideal",raw:"force_raw",fwd4:"force_fwd4",fb4:"force_fb4",fwd2:"force_fwd2",fb2:"force_fb2"}[k]; }
function keyToAcc(k){ return {ideal:"a_ideal",raw:"acc_raw",fwd4:"acc_fwd4",fb4:"acc_fb4",fwd2:"acc_fwd2",fb2:"acc_fb2"}[k]; }
function keyToVel(k){ return {ideal:"v_ideal",raw:"v_raw",fwd4:"v_fwd4",fb4:"v_fb4",fwd2:"v_fwd2",fb2:"v_fb2"}[k]; }

function renderForce(){ var s=[]; Object.keys(stF).forEach(function(k){ if(stF[k]&&DATA[keyToForce(k)]) s.push(seriesFor(k,keyToForce(k))); }); drawChart("cF", s, "力 F (N)", 3.0); }
function renderAcc(){ var s=[]; Object.keys(stA).forEach(function(k){ if(stA[k]&&DATA[keyToAcc(k)]) s.push(seriesFor(k,keyToAcc(k))); }); drawChart("cA", s, "加速度 a (m/s²)", 3.0); }
function renderVel(){ var s=[]; Object.keys(stV).forEach(function(k){ if(stV[k]&&DATA[keyToVel(k)]) s.push(seriesFor(k,keyToVel(k))); }); drawChart("cV", s, "速度 v (m/s)", 3.0); }

// 若某些加速度列未内联，则由力换算补齐（保证图有三类）
(function ensureAcc(){
  function need(fKey,aKey){ if(!DATA[aKey] && DATA[fKey]) DATA[aKey]=DATA[fKey].map(function(f){return f/DATA.m - DATA.g;}); }
  need("force_ideal","a_ideal"); need("force_raw","acc_raw");
  need("force_fwd4","acc_fwd4"); need("force_fb4","acc_fb4");
  need("force_fwd2","acc_fwd2"); need("force_fb2","acc_fb2");
})();

buildToggles("tgForce", stF, renderForce);
buildToggles("tgAcc", stA, renderAcc);
buildToggles("tgVel", stV, renderVel);

// 表
function table(el, head, rows){
  var h="<tr>"+head.map(function(x){return "<th>"+x+"</th>";}).join("")+"</tr>";
  rows.forEach(function(r){
    h+="<tr>"+r.map(function(x,i){ return "<td"+(i===0?' class="k"':"")+">"+x+"</td>"; }).join("")+"</tr>";
  });
  el.innerHTML=h;
}
var WN = DATA.window_names;
table($("tF"), ["信号"].concat(WN.map(function(n){return "力 "+n;})),
  DATA.force_stats.map(function(s){ return [s.label].concat(s.wins.map(function(v){return v.toFixed(4);})); }));
table($("tA"), ["信号"].concat(WN.map(function(n){return "a "+n;})).concat(["∫a dt","末速度 v(T)"]),
  DATA.summary.map(function(s){ return [s.label].concat(s.a_wins.map(function(v){return v.toFixed(4);}))
    .concat([s.a_integral.toFixed(4), s.v_final.toFixed(4)]); }));
table($("tV"), ["信号"].concat(WN.map(function(n){return "v "+n;})),
  DATA.summary.map(function(s){ return [s.label].concat(s.v_wins.map(function(v){return v.toFixed(4);})); }));
table($("tC"), ["fc","单次前向最大偏离 (N)","前后向最大偏离 (N)","单次前向末速度 (m/s)","前后向末速度 (m/s)"],
  DATA.const_check.map(function(c){ return [c.fc+" Hz", c.fwd_max_dev.toExponential(3), c.fb_max_dev.toExponential(3),
    c.fwd_v_final.toExponential(3), c.fb_v_final.toExponential(3)]; }));
table($("tR"), ["截止 fc","单次前向 |H(20Hz)|","前向 dB","前后向 |H|²","前后向 dB"],
  DATA.resp.map(function(r){ return [r.fc+" Hz", r.fwd_at_20.toFixed(6), r.fwd_db.toFixed(2), r.fb_at_20.toFixed(6), r.fb_db.toFixed(2)]; }));

renderForce(); renderAcc(); renderVel();
</script>
</body>
</html>
"""

html = HTML.replace("__PAYLOAD__", payload)
with open(os.path.join(here, "分析页.html"), "w", encoding="utf-8") as fh:
    fh.write(html)
print("分析页.html written, size =", os.path.getsize(os.path.join(here, "分析页.html")))
