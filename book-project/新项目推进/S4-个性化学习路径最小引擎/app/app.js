(function () {
  "use strict";

  const data = window.S4_DATA;
  const engine = window.PathEngine;
  const conceptIndex = Object.fromEntries(data.concepts.map((item) => [item.id, item]));
  const resourceIndex = Object.fromEntries(data.resources.map((item) => [item.id, item]));
  const checkIndex = Object.fromEntries(data.checks.map((item) => [item.id, item]));
  const profileIndex = Object.fromEntries(data.profiles.map((item) => [item.id, item]));

  const ui = {
    boundaryText: document.querySelector("#boundaryText"),
    profileSelect: document.querySelector("#profileSelect"),
    resetButton: document.querySelector("#resetButton"),
    updateNotice: document.querySelector("#updateNotice"),
    profileIntro: document.querySelector("#profileIntro"),
    evidenceList: document.querySelector("#evidenceList"),
    auditLog: document.querySelector("#auditLog"),
    conceptPath: document.querySelector("#conceptPath"),
    candidateList: document.querySelector("#candidateList"),
    reviewPanel: document.querySelector("#reviewPanel"),
    resourceLibrary: document.querySelector("#resourceLibrary"),
    checkLibrary: document.querySelector("#checkLibrary"),
    rulesVersion: document.querySelector("#rulesVersion"),
    contentVersion: document.querySelector("#contentVersion"),
  };

  const state = {
    profileId: data.profiles[0].id,
    events: [],
    rejected: [],
    audit: [],
    selectedCandidateId: null,
    editedReasons: {},
    activeAssignment: null,
    lastUpdatedConceptId: null,
    notice: "",
    sequence: 1,
  };

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function resetProfile(profileId) {
    const profile = profileIndex[profileId];
    state.profileId = profileId;
    state.events = clone(profile.initialEvents);
    state.rejected = [];
    state.audit = [];
    state.selectedCandidateId = null;
    state.editedReasons = {};
    state.activeAssignment = null;
    state.lastUpdatedConceptId = null;
    state.notice = "已复位：路径只根据该合成画像的初始证据生成。";
    state.sequence = 1;
    render();
  }

  function stateLabel(value) {
    return {
      unobserved: "证据待补",
      not_yet_shown: "本次待加强",
      mixed: "证据矛盾",
      supported_this_task: "本轮支持",
    }[value];
  }

  function resultTag(result) {
    if (result === "pass") return "good";
    if (result === "partial" || result === "not-yet") return "warn";
    return "";
  }

  function renderEvidence(profile) {
    ui.profileIntro.innerHTML = `<strong>${escapeHtml(profile.title)}</strong><p>${escapeHtml(profile.note)} 目标节点：${escapeHtml(conceptIndex[profile.targetConceptId].title)}。</p>`;
    ui.evidenceList.innerHTML = state.events
      .map((event) => {
        const check = checkIndex[event.checkId];
        const tags = Object.entries(event.conceptResults)
          .map(([conceptId, result]) => `<span class="tag ${resultTag(result)}">${escapeHtml(conceptIndex[conceptId].title)} · ${escapeHtml(engine.RESULT_LABEL[result])}</span>`)
          .join("");
        return `<article class="evidence-item"><header><strong>${escapeHtml(check ? check.title : event.checkId)}</strong><code>${escapeHtml(event.id)}</code></header><p>${escapeHtml(event.note || "未附说明")}</p><div class="evidence-tags">${tags}</div></article>`;
      })
      .join("");
  }

  function renderAudit() {
    if (!state.audit.length) {
      ui.auditLog.innerHTML = '<div class="empty">尚无教师决定。系统候选不会自动进入路径。</div>';
      return;
    }
    ui.auditLog.innerHTML = state.audit
      .map((item, index) => `<div class="audit-item"><strong>${index + 1}. ${escapeHtml(item.action)}</strong> ${escapeHtml(item.title)}<br>${escapeHtml(item.note)}</div>`)
      .join("");
  }

  function renderPath(states) {
    ui.conceptPath.innerHTML = data.concepts
      .map((concept, index) => {
        const conceptState = states[concept.id];
        const updated = state.lastUpdatedConceptId === concept.id ? " updated" : "";
        return `<li class="concept-node${updated}" style="animation-delay:${index * 55}ms"><span class="node-index">${concept.id}</span><div class="node-copy"><strong>${escapeHtml(concept.title)}</strong><span>${escapeHtml(concept.short)}</span></div><span class="node-state state-${conceptState.state}">${escapeHtml(stateLabel(conceptState.state))}</span></li>`;
      })
      .join("");
  }

  function modeLabel(mode) {
    return { "evidence-check": "先补证据", "conflict-check": "先复核矛盾", "learn-then-check": "微资源＋检查" }[mode] || mode;
  }

  function selectedCandidate(candidates) {
    return candidates.find((item) => item.id === state.selectedCandidateId) || candidates[0] || null;
  }

  function renderCandidates(candidates) {
    if (!state.selectedCandidateId || !candidates.some((item) => item.id === state.selectedCandidateId)) {
      state.selectedCandidateId = candidates[0] ? candidates[0].id : null;
    }
    ui.candidateList.innerHTML = candidates
      .map((candidate, index) => {
        const selected = candidate.id === state.selectedCandidateId ? " selected" : "";
        return `<article class="candidate${selected}"><div class="candidate-top"><div><span class="candidate-number">候选 ${index + 1} · ${escapeHtml(modeLabel(candidate.mode))}</span><h4>${escapeHtml(candidate.title)}</h4></div></div><p>${escapeHtml(candidate.possibleStuckPoint)}</p><button class="button ghost small" type="button" data-review="${escapeHtml(candidate.id)}">查看并审核</button></article>`;
      })
      .join("");

    ui.candidateList.querySelectorAll("[data-review]").forEach((button) => {
      button.addEventListener("click", () => {
        state.selectedCandidateId = button.dataset.review;
        render();
      });
    });
  }

  function renderAssignment(candidate) {
    const resources = candidate.resourceIds.map((id) => resourceIndex[id]);
    const check = checkIndex[candidate.checkId];
    const resourceSteps = resources.length
      ? resources.map((item) => `<li><strong>${escapeHtml(item.title)}</strong>（${item.minutes}分钟）：${escapeHtml(item.summary)}</li>`).join("")
      : "<li>不预设补学资源，先补一条低成本检查证据。</li>";
    ui.reviewPanel.innerHTML = `<div class="assignment"><span class="assignment-status">已由教师采用 · 尚未自动发送</span><h3>${escapeHtml(candidate.title)}</h3><div class="review-note">采用只代表教师选择了下一步。阅读资源本身不会更新知识证据；下面的结果按钮记录的是检查任务结果。</div><ol>${resourceSteps}</ol><div class="check-prompt"><strong>${escapeHtml(check.title)}</strong><br>${escapeHtml(check.prompt)}</div><p class="outcome-label">模拟完成检查后，记录本次可观察结果</p><div class="button-row"><button class="button danger" data-outcome="not-yet" type="button">本次尚未形成支持</button><button class="button ghost" data-outcome="partial" type="button">本次部分支持</button><button class="button" data-outcome="pass" type="button">本次形成支持</button></div></div>`;
    ui.reviewPanel.querySelectorAll("[data-outcome]").forEach((button) => {
      button.addEventListener("click", () => completeAssignment(button.dataset.outcome));
    });
  }

  function renderReview(candidate) {
    if (state.activeAssignment) {
      renderAssignment(state.activeAssignment);
      return;
    }
    if (!candidate) {
      ui.reviewPanel.innerHTML = '<div class="empty">暂无候选任务，请检查数据和规则。</div>';
      return;
    }
    const resources = candidate.resourceIds.map((id) => resourceIndex[id].title).join("、") || "无，先做检查";
    const check = checkIndex[candidate.checkId];
    const edited = state.editedReasons[candidate.id] || candidate.editableReason;
    ui.reviewPanel.innerHTML = `<span class="mode">${escapeHtml(modeLabel(candidate.mode))}</span><h3>${escapeHtml(candidate.title)}</h3><dl><div class="review-block"><dt>证据依据</dt><dd>${escapeHtml(candidate.evidenceSummary)}</dd></div><div class="review-block"><dt>可能卡点</dt><dd>${escapeHtml(candidate.possibleStuckPoint)}</dd></div><div class="review-block"><dt>不确定性</dt><dd>${escapeHtml(candidate.uncertainty)}</dd></div><div class="review-block"><dt>候选资源与检查</dt><dd>${escapeHtml(resources)} → ${escapeHtml(check.title)}</dd></div><div class="review-block"><dt>规则轨迹</dt><dd>${candidate.ruleTrace.map((item) => `<code>${escapeHtml(item)}</code>`).join(" · ")}</dd></div></dl><label for="reasonEditor"><strong>教师可改写的推荐理由</strong></label><textarea id="reasonEditor" class="reason-editor">${escapeHtml(edited)}</textarea><div class="review-note">这段理由不会改变规则结果；它记录教师为什么采用、改序或否决。若要改变任务，请审核其他候选或否决本项。</div><div class="button-row" style="margin-top:14px"><button id="acceptButton" class="button" type="button">采用为下一任务</button><button id="rejectButton" class="button danger" type="button">否决本建议</button></div>`;
    const editor = ui.reviewPanel.querySelector("#reasonEditor");
    editor.addEventListener("input", () => { state.editedReasons[candidate.id] = editor.value; });
    ui.reviewPanel.querySelector("#acceptButton").addEventListener("click", () => acceptCandidate(candidate, editor.value));
    ui.reviewPanel.querySelector("#rejectButton").addEventListener("click", () => rejectCandidate(candidate, editor.value));
  }

  function acceptCandidate(candidate, reason) {
    state.editedReasons[candidate.id] = reason;
    state.activeAssignment = clone(candidate);
    state.activeAssignment.teacherReason = reason;
    state.audit.push({ action: "采用", title: candidate.title, note: `教师理由：${reason}` });
    state.notice = "候选已进入教师确认路径，但没有自动发送。";
    render();
  }

  function rejectCandidate(candidate, reason) {
    state.editedReasons[candidate.id] = reason;
    state.rejected.push(candidate.bundleId);
    state.audit.push({ action: "否决", title: candidate.title, note: `教师理由：${reason}` });
    state.selectedCandidateId = null;
    state.notice = "已否决本项；规则保留原建议与教师理由，并显示其他候选。";
    render();
  }

  function completeAssignment(result) {
    const candidate = state.activeAssignment;
    state.events = engine.appendCheckEvidence(state.events, candidate, result, state.sequence++);
    state.audit.push({ action: "记录新证据", title: checkIndex[candidate.checkId].title, note: `${conceptIndex[candidate.targetConceptId].title}：${engine.RESULT_LABEL[result]}。路径已重新计算。` });
    state.lastUpdatedConceptId = candidate.targetConceptId;
    state.activeAssignment = null;
    state.selectedCandidateId = null;
    state.notice = `新证据已进入：${conceptIndex[candidate.targetConceptId].title}路径状态发生更新。`;
    render();
  }

  function renderLibrary() {
    ui.resourceLibrary.innerHTML = data.resources
      .map((item) => `<details><summary><span>${escapeHtml(item.id)} · ${escapeHtml(item.title)}</span><small>${item.minutes}分钟</small></summary><p>${escapeHtml(item.content)}<br><strong>来源：</strong>${escapeHtml(item.rightsNote)}</p></details>`)
      .join("");
    ui.checkLibrary.innerHTML = data.checks
      .map((item) => `<details><summary><span>${escapeHtml(item.id)} · ${escapeHtml(item.title)}</span><small>${item.minutes}分钟</small></summary><p>${escapeHtml(item.prompt)}<br><strong>观察边界：</strong>${escapeHtml(item.rubric)}</p></details>`)
      .join("");
  }

  function render() {
    const profile = profileIndex[state.profileId];
    const ranked = engine.rankRecommendations(data, state.events, state.rejected);
    renderEvidence(profile);
    renderAudit();
    renderPath(ranked.states);
    renderCandidates(ranked.candidates);
    renderReview(selectedCandidate(ranked.candidates));
    ui.updateNotice.textContent = state.notice;
    ui.profileSelect.value = state.profileId;
  }

  function init() {
    const errors = engine.validateData(data);
    if (errors.length) {
      document.body.innerHTML = `<main style="padding:40px"><h1>原型数据未通过校验</h1><pre>${escapeHtml(errors.join("\n"))}</pre></main>`;
      return;
    }
    ui.boundaryText.textContent = data.meta.boundary;
    ui.rulesVersion.textContent = data.meta.rulesetVersion;
    ui.contentVersion.textContent = data.meta.contentVersion;
    ui.profileSelect.innerHTML = data.profiles.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.title)}</option>`).join("");
    ui.profileSelect.addEventListener("change", () => resetProfile(ui.profileSelect.value));
    ui.resetButton.addEventListener("click", () => resetProfile(state.profileId));
    renderLibrary();
    resetProfile(state.profileId);
  }

  init();
})();
