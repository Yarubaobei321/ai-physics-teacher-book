
(function () {
  "use strict";

  var form = document.getElementById("obsForm");

  /* ---------- 文本框随内容增高，保证打印时不截断 ---------- */
  function autoGrow(el) {
    el.style.height = "auto";
    el.style.height = el.scrollHeight + "px";
  }
  var tas = form.querySelectorAll("textarea");
  Array.prototype.forEach.call(tas, function (t) {
    autoGrow(t);
    t.addEventListener("input", function () { autoGrow(t); });
  });

  /* ---------- 数值格式化 ---------- */
  function fmt(n) {
    if (!isFinite(n)) return "—";
    if (n === 0) return "0";
    var a = Math.abs(n);
    if (a >= 1e-3 && a < 1e6) return String(Number(n.toPrecision(4)));
    return Number(n.toPrecision(3)).toExponential(2);
  }
  function num(id) {
    var v = document.getElementById(id).value.trim();
    if (v === "") return NaN;
    var n = Number(v);
    return isFinite(n) ? n : NaN;
  }

  /* ---------- 按公式做算术 ---------- */
  var warn = document.getElementById("boundaryWarn");
  var calcIds = ["in_m", "in_g", "in_h1", "in_h2", "in_v1", "in_v2"];

  function recalc() {
    var m = num("in_m"), g = num("in_g");
    var h1 = num("in_h1"), h2 = num("in_h2");
    var v1 = num("in_v1"), v2 = num("in_v2");

    var dEp = document.getElementById("out_dEp");
    var dEk = document.getElementById("out_dEk");
    var dif = document.getElementById("out_diff");
    var rel = document.getElementById("out_rel");

    var okEp = isFinite(m) && isFinite(g) && isFinite(h1) && isFinite(h2);
    var okEk = isFinite(m) && isFinite(v1) && isFinite(v2);

    var epVal = okEp ? m * g * (h1 - h2) : NaN;
    var ekVal = okEk ? 0.5 * m * (v2 * v2 - v1 * v1) : NaN;

    dEp.textContent = okEp ? fmt(epVal) : "—";
    dEk.textContent = okEk ? fmt(ekVal) : "—";

    if (okEp && okEk && epVal !== 0) {
      var d = epVal - ekVal;
      dif.textContent = fmt(d);
      rel.textContent = fmt(d / epVal * 100);
    } else {
      dif.textContent = "—";
      rel.textContent = "—";
    }

    /* 物理边界提示：本页公式只覆盖物体下降（h1 > h2） */
    var msgs = [];
    if (isFinite(h1) && isFinite(h2) && h1 <= h2) {
      msgs.push("本页公式适用于<b>物体下降</b>的情形，要求 h₁ &gt; h₂。当前 h₁ ≤ h₂，请检查两个状态的设定或高度读数。");
    }
    if (okEp && epVal < 0) {
      msgs.push("Δ<i>E</i><sub>p,减</sub> 计算结果为负，说明状态设定与“下降”不符，请核对 h₁、h₂。");
    }
    if (okEk && ekVal < 0) {
      msgs.push("Δ<i>E</i><sub>k,增</sub> 计算结果为负，说明该过程中动能在减少（减速过程），本页的“减少量 / 增加量”比较方式不适用，请重新选取状态。");
    }
    if (msgs.length) {
      warn.innerHTML = "物理边界提示：" + msgs.join("<br>");
      warn.style.display = "block";
    } else {
      warn.innerHTML = "";
      warn.style.display = "none";
    }
  }

  Array.prototype.forEach.call(calcIds, function (id) {
    document.getElementById(id).addEventListener("input", recalc);
  });

  /* ---------- 打印 / 另存为 PDF ---------- */
  document.getElementById("btnPrint").addEventListener("click", function () {
    Array.prototype.forEach.call(tas, autoGrow);
    window.print();
  });

  /* ---------- 清空：两次确认 ---------- */
  var mask = document.getElementById("mask");
  var dlgStep = document.getElementById("dlgStep");
  var dlgText = document.getElementById("dlgText");
  var dlgOk = document.getElementById("dlgOk");
  var step = 0;

  document.getElementById("btnClear").addEventListener("click", function () {
    step = 1;
    dlgStep.textContent = "第 1 / 2 步";
    dlgText.innerHTML = "此操作将清除本页所有填写、勾选与计算结果，<b>无法撤销</b>。是否已打印或另存为 PDF？";
    dlgOk.textContent = "继续";
    mask.classList.add("show");
    dlgOk.focus();
  });

  function closeMask() {
    mask.classList.remove("show");
    step = 0;
  }

  document.getElementById("dlgCancel").addEventListener("click", closeMask);
  mask.addEventListener("click", function (e) { if (e.target === mask) closeMask(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && mask.classList.contains("show")) closeMask(); });

  dlgOk.addEventListener("click", function () {
    if (step === 1) {
      step = 2;
      dlgStep.textContent = "第 2 / 2 步（最后确认）";
      dlgText.innerHTML = "再确认一次：点击“确认清空”后，本页所有内容将<b>立即清空且不可恢复</b>。";
      dlgOk.textContent = "确认清空";
      dlgOk.focus();
      return;
    }
    if (step === 2) {
      form.reset();
      recalc();
      Array.prototype.forEach.call(tas, autoGrow);
      closeMask();
    }
  });
})();
