/* 本版新编教学模型。SI单位；与真实实验数据分开。 */
(function(root){
'use strict';
function finite(...xs){if(xs.some(x=>!Number.isFinite(x)))throw Error('请完整填写有限数值。');}
function positive(...xs){finite(...xs);if(xs.some(x=>x<=0))throw Error('频率、周期数、质量、电阻等须大于零。');}
function paper(p){let {f,n,g,a0,a1,a2,b0,b1,b2}=p;positive(f,n,g);finite(a0,a1,a2,b0,b1,b2);if(!Number.isInteger(n))throw Error('周期数须为正整数。');if(!(a0<a1&&a1<a2&&b0<b1&&b1<b2&&b1>a1))throw Error('每组三点须递增，B须在A之后；两组允许共用点。');let T=n/f,vA=(a2-a0)/100/(2*T),vB=(b2-b0)/100/(2*T),dh=(b1-a1)/100,potential=g*dh,kinetic=(vB*vB-vA*vA)/2;return {T,vA,vB,dh,potential,kinetic,D:potential-kinetic};}
function spring({m,k,A,t}){positive(m,k);finite(A,t);if(A<0||t<0)throw Error('振幅和时间不可为负。');let w=Math.sqrt(k/m),T=2*Math.PI/w,x=A*Math.cos(w*t),v=-A*w*Math.sin(w*t),a=-w*w*x,K=m*v*v/2,U=k*x*x/2;return {w,T,x,v,a,K,U,E:K+U};}
function potential({a,b,p,U}){finite(a,b,p,U);if(!(a<p&&p<b))throw Error('观察点必须严格位于两板之间：a < p < b。');if(U<0)throw Error('本练习使用非负端电压。');return {V:U*(p-a)/(b-a),E:U/((b-a)/100),d:b-a};}
function rc({R,C,U,V0,dt,mode}){positive(R,C);finite(U,V0,dt);if(U<0||dt<0)throw Error('电源电压和时间间隔不可为负。');if(!['charge','discharge'].includes(mode))throw Error('未知开关状态。');let target=mode==='charge'?U:0,tau=R*C,V=target+(V0-target)*Math.exp(-dt/tau),i=(target-V)/R;return {V,i,tau,energy:C*V*V/2};}
const api={paper,spring,potential,rc};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.Physics=api;
})(typeof window!=='undefined'?window:globalThis);
