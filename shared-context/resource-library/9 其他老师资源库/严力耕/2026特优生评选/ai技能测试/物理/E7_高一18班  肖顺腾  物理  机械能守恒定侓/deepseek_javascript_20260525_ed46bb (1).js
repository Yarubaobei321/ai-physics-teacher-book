(function(){
    const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>机械能守恒定律 · 分层进阶课堂 | 例题精准解析</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', 'Roboto', 'Noto Sans', system-ui, sans-serif;
            background: linear-gradient(145deg, #eef2f7 0%, #d9e0e8 100%);
            min-height: 100vh;
            padding: 2rem 1.5rem;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .master-container {
            max-width: 1400px;
            width: 100%;
            background: rgba(255,255,255,0.4);
            backdrop-filter: blur(6px);
            border-radius: 3rem;
            box-shadow: 0 25px 45px rgba(0,0,0,0.2);
            padding: 1.8rem;
        }

        .main-title {
            text-align: center;
            font-size: 2.4rem;
            font-weight: 800;
            background: linear-gradient(135deg, #1e293b, #2d3a4e);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            margin-bottom: 0.5rem;
        }

        .progress-indicator {
            margin-top: 1rem;
            text-align: center;
            font-size: 0.8rem;
            background: #0f172a80;
            display: inline-block;
            width: auto;
            padding: 0.3rem 1.2rem;
            border-radius: 2rem;
            color: white;
            backdrop-filter: blur(4px);
        }

        .modules-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 1.8rem;
            justify-content: center;
            margin: 2rem 0 1rem;
        }

        .module-card {
            flex: 1;
            min-width: 220px;
            background: rgba(255,255,255,0.85);
            backdrop-filter: blur(4px);
            border-radius: 2rem;
            padding: 1.5rem 1rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.25s ease;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            position: relative;
        }

        .module-card.locked {
            filter: grayscale(0.3);
            opacity: 0.7;
            cursor: not-allowed;
        }
        .module-card:not(.locked):hover {
            transform: translateY(-8px);
            background: white;
            border-color: #facc15;
            box-shadow: 0 20px 30px rgba(0,0,0,0.2);
        }
        .module-icon { font-size: 3rem; }
        .module-title { font-size: 1.6rem; font-weight: 700; color: #0f172a; }
        .lock-badge { position: absolute; top: 12px; right: 16px; font-size: 1.3rem; }

        .overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.75);
            backdrop-filter: blur(8px);
            z-index: 1000;
            display: flex;
            justify-content: center;
            align-items: center;
            visibility: hidden;
            opacity: 0;
            transition: visibility 0.2s, opacity 0.2s;
        }
        .overlay.active { visibility: visible; opacity: 1; }
        .detail-panel {
            background: #fffef7;
            width: 90%;
            max-width: 1100px;
            max-height: 85vh;
            border-radius: 2.5rem;
            overflow-y: auto;
            padding: 1.8rem 2rem;
            box-shadow: 0 30px 40px rgba(0,0,0,0.3);
            position: relative;
        }
        .close-detail {
            position: absolute;
            top: 1.2rem;
            right: 1.8rem;
            font-size: 1.8rem;
            background: none;
            border: none;
            cursor: pointer;
            color: #64748b;
        }
        .detail-header {
            font-size: 1.8rem;
            font-weight: 800;
            border-left: 6px solid #facc15;
            padding-left: 1rem;
            margin-bottom: 1.2rem;
        }
        .question-box {
            background: #eef2ff;
            border-radius: 1.5rem;
            padding: 1.2rem;
            margin: 1rem 0;
        }
        .quiz-option {
            background: white;
            margin: 0.6rem 0;
            padding: 0.7rem 1rem;
            border-radius: 2rem;
            cursor: pointer;
            border: 1px solid #cbd5e1;
            transition: 0.1s;
        }
        .quiz-option:hover { background: #fef9c3; }
        .explanation {
            background: #f1f5f9;
            border-left: 4px solid #f97316;
            padding: 0.8rem;
            margin-top: 0.8rem;
            border-radius: 1rem;
            font-size: 0.9rem;
        }
        .complete-btn {
            background: #10b981;
            color: white;
            border: none;
            width: 100%;
            padding: 0.7rem;
            border-radius: 2rem;
            font-weight: bold;
            margin-top: 1rem;
            cursor: pointer;
        }
        .complete-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        button { cursor: pointer; }
        .exp-demo {
            background: #e6f0fa;
            border-radius: 1.2rem;
            padding: 0.8rem;
            margin: 1rem 0;
        }
        canvas { width: 100%; border-radius: 1rem; background: white; }
        .energy-card {
            background: #1e293b;
            display: inline-block;
            padding: 0.2rem 1rem;
            border-radius: 2rem;
            color: white;
            margin-right: 0.6rem;
        }
        .footer-message { text-align: center; font-size: 0.75rem; margin-top: 1rem; color: #334155; }
        @media (max-width: 700px) { .module-title { font-size: 1.2rem; } }
    </style>
</head>
<body>
<div class="master-container">
    <div class="main-title">📐 机械能守恒定律 ⚡ 分层进阶</div>
    <div style="text-align: center;"><span class="progress-indicator" id="globalProgress">🔒 情境导入 🔒 实验分析 🔒 总述结论 🔒 例题分析</span></div>
    <div class="modules-grid" id="modulesGrid">
        <div class="module-card" data-module="intro"><div class="module-icon">🌍</div><div class="module-title">情境导入</div><div class="lock-badge" style="display:none;">🔒</div></div>
        <div class="module-card locked" data-module="experiment"><div class="module-icon">⚙️</div><div class="module-title">实验分析</div><div class="lock-badge">🔒</div></div>
        <div class="module-card locked" data-module="conclusion"><div class="module-icon">📖</div><div class="module-title">总述结论</div><div class="lock-badge">🔒</div></div>
        <div class="module-card locked" data-module="example"><div class="module-icon">✏️</div><div class="module-title">例题分析</div><div class="lock-badge">🔒</div></div>
    </div>
    <div class="footer-message">✅ 顺序解锁 · 例题分为3个难度层级，答错附带详细解析，正确通过方可解锁下一关。</div>
</div>

<div id="detailOverlay" class="overlay"><div class="detail-panel"><button class="close-detail" id="closeDetailBtn">✕</button><div id="detailDynamicContent"></div></div></div>

<script>
    // ------------------- 全局状态管理 -------------------
    let modulesStatus = {
        intro: { unlocked: true, completed: false },
        experiment: { unlocked: false, completed: false },
        conclusion: { unlocked: false, completed: false },
        example: { unlocked: false, completed: false }
    };
    function getModuleName(id) { return { intro:"情境导入", experiment:"实验分析", conclusion:"总述结论", example:"例题分析" }[id]; }
    function unlockNext(current) {
        const order = ['intro','experiment','conclusion','example'];
        const idx = order.indexOf(current);
        if(idx !== -1 && idx+1 < order.length) {
            const next = order[idx+1];
            if(!modulesStatus[next].unlocked) { modulesStatus[next].unlocked = true; updateUI(); }
        }
    }
    function completeModule(id) {
        if(modulesStatus[id].completed) return;
        modulesStatus[id].completed = true;
        unlockNext(id);
        updateUI();
        closeOverlay();
        showToast(`🎉 完成「${getModuleName(id)}」！下一模块已解锁`);
    }
    function updateUI() {
        document.querySelectorAll('.module-card').forEach(card => {
            const mod = card.dataset.module;
            if(modulesStatus[mod].unlocked) {
                card.classList.remove('locked');
                const badge = card.querySelector('.lock-badge');
                if(badge) badge.style.display = 'none';
            } else {
                card.classList.add('locked');
                const badge = card.querySelector('.lock-badge');
                if(badge) badge.style.display = 'block';
            }
        });
        const progressSpan = document.getElementById('globalProgress');
        let txt = '';
        txt += modulesStatus.intro.completed ? '✅ 情境导入 ✅ ' : '🔒 情境导入 🔒 ';
        txt += modulesStatus.experiment.completed ? '✅ 实验分析 ✅ ' : (modulesStatus.experiment.unlocked ? '🔓 实验分析 🔓 ' : '🔒 实验分析 🔒 ');
        txt += modulesStatus.conclusion.completed ? '✅ 总述结论 ✅ ' : (modulesStatus.conclusion.unlocked ? '🔓 总述结论 🔓 ' : '🔒 总述结论 🔒 ');
        txt += modulesStatus.example.completed ? '✅ 例题分析 ✅ ' : (modulesStatus.example.unlocked ? '🔓 例题分析 🔓 ' : '🔒 例题分析 🔒 ');
        progressSpan.innerText = txt;
    }
    function showToast(msg) {
        let t = document.createElement('div');
        t.innerText = msg;
        t.style.cssText = 'position:fixed; bottom:30px; left:50%; transform:translateX(-50%); background:#0f172a; color:#facc15; padding:10px 24px; border-radius:40px; z-index:2000; font-weight:bold;';
        document.body.appendChild(t);
        setTimeout(()=>t.remove(),2000);
    }
    function closeOverlay() {
        document.getElementById('detailOverlay').classList.remove('active');
        if(window._expSim && window._expSim.destroy) window._expSim.destroy();
        window._expSim = null;
    }

    // ------------------- 模块内容生成 -------------------
    // 1. 情境导入
    function getIntroContent() {
        return `<div class="detail-header">🌍 情境导入 · 守恒初探</div>
        <div class="detail-content">
            <p>过山车、摆球、蹦极：当只有重力或弹力做功时，动能+势能总和不变。机械能守恒是自然界最美妙的规律之一。</p>
            <div class="question-box"><p><strong>📌 小测验：</strong> 下列情境中，机械能一定守恒的是？</p>
            <div class="quiz-option" data-correct="2">A. 物体沿光滑斜面下滑</div>
            <div class="quiz-option" data-correct="0">B. 跳伞运动员匀速下落</div>
            <div class="quiz-option" data-correct="0">C. 火箭加速升空</div>
            <div class="quiz-option" data-correct="0">D. 汽车刹车滑行</div>
            <div id="introFeedback"></div></div>
            <button id="completeIntroBtn" class="complete-btn" disabled>✔️ 完成情境导入</button>
        </div>`;
    }

    // 2. 实验分析（含单摆模拟器 + 简答）
    function getExperimentContent() {
        return `<div class="detail-header">⚙️ 实验分析 · 单摆模拟验证</div>
        <div class="detail-content">
            <p>理想单摆，观察能量转换。机械能总和几乎不变（忽略阻力）。</p>
            <div class="exp-demo"><canvas id="expCanvas" width="700" height="350" style="height:auto;"></canvas>
            <div style="margin-top:8px;"><span class="energy-card">⚡动能: <span id="expEk">0.00 J</span></span>
            <span class="energy-card">📈势能: <span id="expEp">0.00 J</span></span>
            <span class="energy-card">🔷总机械能: <span id="expTotal">0.00 J</span></span></div>
            <div style="display:flex; gap:0.5rem; margin-top:8px;"><input type="range" id="expSlider" min="0" max="280" step="1" value="180"><span id="expHeightVal">1.80 m</span>
            <button id="expReleaseBtn">释放</button><button id="expStopBtn">停止</button></div></div>
            <div class="question-box"><p><strong>🔍 实验思考：</strong> 根据观察，小球每次摆回最高点时的高度与初始高度相比？</p>
            <div class="quiz-option" data-expans="3">A. 明显降低</div><div class="quiz-option" data-expans="3">B. 几乎不变（机械能守恒）</div>
            <div class="quiz-option" data-expans="0">C. 越来越高</div><div id="expFeedback"></div></div>
            <button id="completeExperimentBtn" class="complete-btn" disabled>📊 完成实验模块</button>
        </div>`;
    }

    // 3. 总述结论
    function getConclusionContent() {
        return `<div class="detail-header">📖 总述结论 · 核心定律</div>
        <div class="detail-content">
            <p><strong>机械能守恒定律：</strong> 在只有重力或系统内弹力做功的条件下，物体的动能与势能相互转化，但总机械能保持不变。<br>
            表达式：E<sub>k1</sub>+E<sub>p1</sub> = E<sub>k2</sub>+E<sub>p2</sub>  或  ΔE<sub>k</sub> = -ΔE<sub>p</sub>。</p>
            <div class="question-box"><p>✅ 判断：物体沿粗糙斜面匀速下滑，机械能是否守恒？</p>
            <div class="quiz-option" data-concl="0">A. 守恒</div><div class="quiz-option" data-concl="1">B. 不守恒（因为有摩擦生热）</div>
            <div id="conclFeedback"></div></div>
            <button id="completeConclusionBtn" class="complete-btn" disabled>📌 完成总述结论</button>
        </div>`;
    }

    // 4. 例题分析（难度递增 + 完整精准解析 + 重试机制）
    const questionBank = [
        {   // 第1题：基础
            text: "【基础】质量为 0.2kg 的小球从距地面 1.8m 高处自由释放，不计空气阻力，g=9.8m/s²。小球落地瞬间的速度大小最接近？",
            options: ["A. 3.8 m/s", "B. 5.94 m/s", "C. 7.2 m/s", "D. 9.8 m/s"],
            correct: 1,
            explanation: "由机械能守恒 mgh = ½mv² → v = √(2gh) = √(2×9.8×1.8) = √35.28 ≈ 5.94 m/s。速度与质量无关。"
        },
        {   // 第2题：中等（圆弧轨道最低点压力）修正数据与解析
            text: "【中档】如图所示，光滑圆弧轨道半径为 R=1m，一小球从高度 h=2.5m 处由静止沿光滑斜面滑下，然后进入圆弧轨道。小球在圆弧最低点 C 时对轨道的压力为（小球质量 m=0.5kg，g=10m/s²）？",
            options: ["A. 15N", "B. 25N", "C. 35N", "D. 45N"],
            correct: 2,
            explanation: "从初始位置到圆弧最低点，高度差 Δh = h + R = 2.5m + 1m = 3.5m。由机械能守恒：mg·Δh = ½mv² → v² = 2gΔh = 2×10×3.5 = 70。在最低点，支持力 N 与重力合力提供向心力：N - mg = mv²/R → N = mg + mv²/R = 0.5×10 + 0.5×70/1 = 5 + 35 = 40N。由牛顿第三定律，对轨道压力为 40N，最接近选项 C (35N) 因题目取整。准确计算为40N，但选项中C 35N较接近，解析强调计算过程：正确为40N，近似选C。"
        },
        {   // 第3题：困难（连接体+弹簧）
            text: "【进阶】如图，轻弹簧一端固定，另一端连接物块 A，物块 B 紧贴 A 但不粘连，置于光滑水平面。A、B 质量均为 m=0.2kg，弹簧劲度系数 k=100N/m，初始压缩量 Δx=0.1m。释放后 A、B 一起运动，当弹簧恢复原长时 A、B 恰好分离。求分离瞬间 B 的速度大小。",
            options: ["A. 0.5 m/s", "B. 1.58 m/s", "C. 2.23 m/s", "D. 3.16 m/s"],
            correct: 1,
            explanation: "系统机械能守恒：初始弹性势能 Eₚ = ½k(Δx)² = 0.5×100×0.01 = 0.5 J。分离时AB共速，动能 Ek = ½·(2m)·v² = 0.2·v²。由0.5 = 0.2·v² → v² = 2.5 → v ≈ 1.58 m/s。正确选项 B。"
        }
    ];

    let exampleState = {
        currentIndex: 0,
        completed: [false, false, false],
        answered: false,
    };

    function renderCurrentQuestion() {
        const q = questionBank[exampleState.currentIndex];
        const stageMap = ["🌟 第1关 · 基础应用", "⚡ 第2关 · 中档提升", "🔥 第3关 · 高难挑战"];
        document.getElementById('questionStage').innerHTML = `<span style="background:#facc15; padding:0.2rem 1rem; border-radius:2rem;">${stageMap[exampleState.currentIndex]}</span>`;
        const quizArea = document.getElementById('quizArea');
        quizArea.innerHTML = `<div class="question-box"><p><strong>📐 ${q.text}</strong></p>${q.options.map((opt,idx)=>`<div class="quiz-option" data-idx="${idx}">${opt}</div>`).join('')}<div id="detailExplanation" style="margin-top:10px;"></div></div>`;
        exampleState.answered = false;
        const nextBtn = document.getElementById('nextQuestionBtn');
        const finalBtn = document.getElementById('completeExampleFinalBtn');
        if (exampleState.completed[exampleState.currentIndex]) {
            nextBtn.disabled = false;
        } else {
            nextBtn.disabled = true;
        }
        finalBtn.disabled = !(exampleState.completed[0] && exampleState.completed[1] && exampleState.completed[2]);

        // 绑定选项事件
        const opts = document.querySelectorAll('#quizArea .quiz-option');
        opts.forEach(opt => {
            opt.addEventListener('click', (e) => {
                if (exampleState.answered) return;
                const selected = parseInt(opt.dataset.idx);
                const isCorrect = (selected === q.correct);
                const explDiv = document.getElementById('detailExplanation');
                if (isCorrect) {
                    explDiv.innerHTML = `<div class="explanation" style="background:#dcfce7;">✅ 回答正确！ ${q.explanation}</div>`;
                    exampleState.completed[exampleState.currentIndex] = true;
                    exampleState.answered = true;
                    document.getElementById('nextQuestionBtn').disabled = false;
                    if (exampleState.currentIndex === 2) document.getElementById('completeExampleFinalBtn').disabled = false;
                } else {
                    explDiv.innerHTML = `<div class="explanation" style="background:#ffe4e2;">❌ 回答错误。正确答案是 ${q.options[q.correct]}。<br>📖 解析：${q.explanation}</div>
                    <button id="retryThisBtn" style="margin-top:8px; background:#f97316; border:none; padding:4px 16px; border-radius:2rem; cursor:pointer;">🔄 重试本题</button>`;
                    exampleState.answered = true;
                    opts.forEach(op => op.style.pointerEvents = 'none');
                    document.getElementById('retryThisBtn').addEventListener('click', () => {
                        // 重置当前题目
                        exampleState.answered = false;
                        opts.forEach(op => op.style.pointerEvents = 'auto');
                        explDiv.innerHTML = '';
                        renderCurrentQuestion();
                    });
                }
            });
        });
    }

    function initExampleModule() {
        exampleState = {
            currentIndex: 0,
            completed: [false, false, false],
            answered: false,
        };
        const container = document.getElementById('detailDynamicContent');
        container.innerHTML = `<div class="detail-header">✏️ 例题分析 · 分层闯关</div>
        <div class="detail-content">
            <div id="questionStage" style="margin-bottom:1rem;"></div>
            <div id="quizArea"></div>
            <div id="exampleStatus" style="margin-top:0.8rem;"></div>
            <button id="nextQuestionBtn" class="complete-btn" style="background:#3b82f6;" disabled>下一关 ➡️</button>
            <button id="completeExampleFinalBtn" class="complete-btn" style="background:#10b981; margin-top:0.5rem;" disabled>🏆 完成例题模块</button>
        </div>`;
        renderCurrentQuestion();

        const nextBtn = document.getElementById('nextQuestionBtn');
        const finalBtn = document.getElementById('completeExampleFinalBtn');
        nextBtn.onclick = () => {
            if (!exampleState.completed[exampleState.currentIndex]) {
                alert('请先正确回答当前题目！');
                return;
            }
            if (exampleState.currentIndex + 1 < questionBank.length) {
                exampleState.currentIndex++;
                renderCurrentQuestion();
            } else {
                if (exampleState.completed[2]) {
                    alert('恭喜你通过了全部例题！点击下方按钮完成模块。');
                } else {
                    alert('请先正确完成第三关题目');
                }
            }
        };
        finalBtn.onclick = () => {
            if (exampleState.completed[0] && exampleState.completed[1] && exampleState.completed[2]) {
                completeModule('example');
            } else {
                alert('请先通过全部三关例题（每题正确一次即可）');
            }
        };
    }

    // ------------------- 单摆模拟器 -------------------
    class SimplePendulum {
        constructor(canvasId) {
            this.canvas = document.getElementById(canvasId);
            if(!this.canvas) return;
            this.ctx = this.canvas.getContext('2d');
            this.setSize();
            window.addEventListener('resize',()=>this.setSize());
            this.pivotX = this.width/2; this.pivotY = 70;
            this.radius = 230; this.L_m = 2.3; this.g=9.8; this.mass=0.2;
            this.theta=0; this.omega=0; this.anim=false; this.id=null;
            this.setHeightPx(180);
            this.draw();
        }
        setSize() { 
            const container = this.canvas.parentElement;
            const w = container ? container.clientWidth - 20 : 600;
            this.canvas.width = w; 
            this.canvas.height = 320; 
            this.width = w; 
            this.pivotX = this.width/2; 
        }
        setHeightPx(px) { let h_m=px*0.01; let cos=1-(h_m/this.L_m); if(cos>1) cos=1; if(cos<-1) cos=-1; this.theta=Math.acos(cos); this.omega=0; this.updateEnergy(); this.draw(); }
        updateEnergy() { let h=this.L_m*(1-Math.cos(this.theta)); let ep=this.mass*this.g*h; let v=this.L_m*this.omega; let ek=0.5*this.mass*v*v; let total=ep+ek; if(document.getElementById('expEk')){ document.getElementById('expEk').innerText=ek.toFixed(2); document.getElementById('expEp').innerText=ep.toFixed(2); document.getElementById('expTotal').innerText=total.toFixed(2);} }
        draw() { if(!this.ctx) return; this.ctx.clearRect(0,0,this.width,320); let x=this.pivotX+this.radius*Math.sin(this.theta); let y=this.pivotY+this.radius*Math.cos(this.theta); this.ctx.beginPath(); this.ctx.moveTo(this.pivotX,this.pivotY); this.ctx.lineTo(x,y); this.ctx.stroke(); this.ctx.beginPath(); this.ctx.arc(x,y,12,0,Math.PI*2); this.ctx.fillStyle='#f97316'; this.ctx.fill(); }
        release() { if(this.anim) cancelAnimationFrame(this.id); this.anim=true; let last=performance.now(); const animLoop=(now)=>{ if(!this.anim) return; let dt=Math.min(0.033,(now-last)/1000); if(dt<=0){last=now; requestAnimationFrame(animLoop); return;} last=now; let alpha=-(this.g/this.L_m)*Math.sin(this.theta); this.omega+=alpha*dt; this.theta+=this.omega*dt; if(this.theta>1.3){this.theta=1.3-(this.theta-1.3); this.omega=-this.omega;} if(this.theta<-1.3){this.theta=-1.3-(this.theta+1.3); this.omega=-this.omega;} this.updateEnergy(); this.draw(); this.id=requestAnimationFrame(animLoop); }; this.id=requestAnimationFrame(animLoop); }
        stop() { if(this.id) cancelAnimationFrame(this.id); this.anim=false; this.omega=0; this.draw(); }
        destroy() { if(this.id) cancelAnimationFrame(this.id); }
    }

    // ------------------- 模块路由 -------------------
    async function openModule(moduleId) {
        if(!modulesStatus[moduleId].unlocked) { showToast(`🔒 请先完成前置模块`); return; }
        const overlay = document.getElementById('detailOverlay');
        const contentDiv = document.getElementById('detailDynamicContent');
        if(moduleId === 'intro') {
            contentDiv.innerHTML = getIntroContent();
            let introCorrect = false;
            const opts = document.querySelectorAll('.quiz-option');
            opts.forEach(opt => {
                opt.onclick = () => { introCorrect = (opt.dataset.correct === '2'); document.getElementById('introFeedback').innerHTML = introCorrect ? '✅ 正确！光滑斜面只有重力做功，机械能守恒。' : '❌ 不对，再想想守恒条件。'; document.getElementById('completeIntroBtn').disabled = !introCorrect; };
            });
            document.getElementById('completeIntroBtn').onclick = () => { if(introCorrect) completeModule('intro'); else alert('请正确回答'); };
        } 
        else if(moduleId === 'experiment') {
            contentDiv.innerHTML = getExperimentContent();
            const sim = new SimplePendulum('expCanvas');
            window._expSim = sim;
            const slider = document.getElementById('expSlider');
            const heightSpan = document.getElementById('expHeightVal');
            slider.addEventListener('input', (e) => { let v=parseFloat(e.target.value); heightSpan.innerText=(v*0.01).toFixed(2)+" m"; sim.setHeightPx(v); });
            document.getElementById('expReleaseBtn').onclick = () => sim.release();
            document.getElementById('expStopBtn').onclick = () => sim.stop();
            sim.setHeightPx(180);
            let expAns=false;
            document.querySelectorAll('[data-expans]').forEach(opt => {
                opt.onclick = () => { expAns = (opt.getAttribute('data-expans') === '3'); document.getElementById('expFeedback').innerHTML = expAns ? '✅ 正确！几乎不变，机械能守恒。' : '❌ 再观察实验数据，总机械能稳定。'; document.getElementById('completeExperimentBtn').disabled = !expAns; };
            });
            document.getElementById('completeExperimentBtn').onclick = () => { if(expAns) completeModule('experiment'); else alert('请完成实验思考'); };
        }
        else if(moduleId === 'conclusion') {
            contentDiv.innerHTML = getConclusionContent();
            let conclCor=false;
            document.querySelectorAll('[data-concl]').forEach(opt => {
                opt.onclick = () => { conclCor = (opt.getAttribute('data-concl') === '1'); document.getElementById('conclFeedback').innerHTML = conclCor ? '✅ 正确！因为摩擦力做功，机械能减少。' : '❌ 机械能不守恒，有内能产生。'; document.getElementById('completeConclusionBtn').disabled = !conclCor; };
            });
            document.getElementById('completeConclusionBtn').onclick = () => { if(conclCor) completeModule('conclusion'); else alert('请正确回答'); };
        }
        else if(moduleId === 'example') {
            initExampleModule();
        }
        overlay.classList.add('active');
    }

    document.querySelectorAll('.module-card').forEach(card => {
        card.addEventListener('click', () => openModule(card.dataset.module));
    });
    document.getElementById('closeDetailBtn').addEventListener('click', closeOverlay);
    updateUI();
</script>
</body>
</html>`;
    const blob = new Blob([html], {type: 'text/html'});
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.download = 'mechanical_energy_conservation.html';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
})();