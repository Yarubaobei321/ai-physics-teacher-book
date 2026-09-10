const fs=require('fs'), vm=require('vm');
const code=fs.readFileSync('/tmp/workbuddy-review-20260905/original.js','utf8');
const nodes={};
function node(id){return nodes[id]||(nodes[id]={value:'',textContent:'',innerHTML:'',style:{},events:{},classList:{add(){},remove(){},contains(){return false}},addEventListener(k,f){this.events[k]=f},querySelectorAll(){return []},focus(){},reset(){}})}
const doc={getElementById:node,addEventListener(){}};
vm.runInNewContext(code,{document:doc,window:{print(){}}});
const keys=['m','g','h1','h2','v1','v2'];
function run(name,values){keys.forEach((k,i)=>node('in_'+k).value=String(values[i]));node('in_m').events.input();return {name,input:values,dEp:node('out_dEp').textContent,dEk:node('out_dEk').textContent,diff:node('out_diff').textContent,relative:node('out_rel').textContent,warning:node('boundaryWarn').innerHTML}}
const results=[run('正常下降，仅为核算样例',[0.2,9.8,0.5,0,1,3]),run('质量缺失',['',9.8,0.5,0,1,3]),run('负质量',[-0.2,9.8,0.5,0,1,3]),run('零质量',[0,9.8,0.5,0,1,3]),run('负重力加速度',[0.2,-9.8,0.5,0,1,3]),run('零重力加速度',[0.2,0,0.5,0,1,3]),run('高度顺序错误',[0.2,9.8,0,0.5,1,3]),run('下降却减速',[0.2,9.8,0.5,0,3,1])];
if(results[0].dEp!=='0.98'||results[0].dEk!=='0.8'||results[0].diff!=='0.18')throw Error('正常核算不一致');
if(results[1].dEp!=='—'||results[1].dEk!=='—')throw Error('缺失值处理不一致');
fs.writeFileSync('图书出版/真实实践文章池/review/WorkBuddy首轮生成与教材核查-2026-09-05/assets/数值边界核查.json',JSON.stringify({method:'执行原HTML脚本，使用最小DOM模拟；不代表真实浏览器测试。所有数值均为合成核算输入，不是实测实验数据。',results},null,2));
console.log(JSON.stringify(results,null,2));
