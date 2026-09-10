(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.PathEngine = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const RESULT_SCORE = { "not-yet": 0, partial: 0.5, pass: 1 };
  const RESULT_LABEL = { "not-yet": "本次尚未形成支持", partial: "本次证据部分支持", pass: "本次证据支持" };

  function byId(items) {
    return Object.fromEntries(items.map((item) => [item.id, item]));
  }

  function evidenceForConcept(events, conceptId) {
    return events
      .filter((event) => Object.prototype.hasOwnProperty.call(event.conceptResults || {}, conceptId))
      .map((event) => ({ event, result: event.conceptResults[conceptId] }));
  }

  function computeConceptStates(data, events) {
    const checkIndex = byId(data.checks);
    const states = {};

    data.concepts.forEach((concept) => {
      const evidence = evidenceForConcept(events, concept.id);
      const results = evidence.map((item) => item.result);
      let state = "unobserved";
      let score = null;

      if (results.length) {
        score = results.reduce((sum, result) => sum + RESULT_SCORE[result], 0) / results.length;
        const hasPass = results.includes("pass");
        const hasNotYet = results.includes("not-yet");
        if (hasPass && hasNotYet) state = "mixed";
        else state = score >= 0.6 ? "supported_this_task" : "not_yet_shown";
      }

      states[concept.id] = {
        conceptId: concept.id,
        state,
        score,
        evidenceIds: evidence.map((item) => item.event.id),
        evidence: evidence.map((item) => ({
          id: item.event.id,
          checkId: item.event.checkId,
          checkTitle: checkIndex[item.event.checkId] ? checkIndex[item.event.checkId].title : item.event.checkId,
          result: item.result,
          resultLabel: RESULT_LABEL[item.result],
          note: item.event.note || "",
        })),
      };
    });

    return states;
  }

  function concernPriority(state) {
    if (state.state === "mixed") return 0;
    if (state.state === "unobserved") return 1;
    if (state.state === "not_yet_shown") return 2;
    return 9;
  }

  function describeEvidence(concept, state) {
    if (state.state === "unobserved") {
      return `当前没有直接观察“${concept.title}”的检查事件。`;
    }
    return state.evidence
      .map((item) => `${item.checkTitle}：${item.resultLabel}${item.note ? `（${item.note}）` : ""}`)
      .join("；");
  }

  function uncertaintyFor(state) {
    if (state.state === "unobserved") return "缺少直接证据不能写成薄弱，先用低成本检查补线索。";
    if (state.state === "mixed") return "不同检查给出的线索冲突，可能受情境、表述或偶然因素影响。";
    if (state.state === "not_yet_shown") return "一次或少量任务只说明本次表现，不能解释真实认知原因。";
    return "本轮有支持证据，但仍不代表稳定迁移到其他情境。";
  }

  function makeVerificationCandidate(data, concept, state) {
    const checkIndex = byId(data.checks);
    const checkId = data.verificationCheckByConcept[concept.id];
    const check = checkIndex[checkId];
    const action = `先做${check.title}中针对“${concept.title}”的片段，不预设补学资源。`;
    const reason = `${describeEvidence(concept, state)} ${uncertaintyFor(state)} ${action} 教师可以改写、换序或否决。`;
    return {
      id: `VERIFY-${concept.id}`,
      bundleId: `VERIFY-${concept.id}`,
      targetConceptId: concept.id,
      title: `先补证据｜${check.title}`,
      resourceIds: [],
      checkId,
      mode: state.state === "mixed" ? "conflict-check" : "evidence-check",
      ruleTrace: [state.state === "mixed" ? "R-MIXED-VERIFY" : "R-UNKNOWN-CHECK", "R-UPSTREAM-FIRST"],
      evidenceIds: state.evidenceIds,
      evidenceSummary: describeEvidence(concept, state),
      possibleStuckPoint: `“${concept.title}”是后续路径的一处可能复核点，不是对学习者的定性。`,
      uncertainty: uncertaintyFor(state),
      action,
      editableReason: reason,
    };
  }

  function makeBundleCandidate(data, bundle, concept, state) {
    const resourceIndex = byId(data.resources);
    const checkIndex = byId(data.checks);
    const resourceNames = bundle.resourceIds.map((id) => resourceIndex[id].title).join("、");
    const check = checkIndex[bundle.checkId];
    const action = `先看${resourceNames}，再用${check.title}留下新的可观察证据。`;
    const reason = `${describeEvidence(concept, state)} “${concept.title}”可能值得优先复核，但也可能只是当前任务情境造成。${action} 教师可以改写、换序或否决。`;
    return {
      id: bundle.id,
      bundleId: bundle.id,
      targetConceptId: concept.id,
      title: bundle.title,
      resourceIds: bundle.resourceIds.slice(),
      checkId: bundle.checkId,
      mode: "learn-then-check",
      ruleTrace: ["R-EVIDENCE-GAP", "R-UPSTREAM-FIRST", "R-RESOURCE-THEN-CHECK"],
      evidenceIds: state.evidenceIds,
      evidenceSummary: describeEvidence(concept, state),
      possibleStuckPoint: `“${concept.title}”是当前证据指向的一种可能复核点。`,
      uncertainty: uncertaintyFor(state),
      action,
      editableReason: reason,
    };
  }

  function rankRecommendations(data, events, rejectedBundleIds) {
    const rejected = new Set(rejectedBundleIds || []);
    const conceptIndex = byId(data.concepts);
    const states = computeConceptStates(data, events);
    const concerns = data.concepts
      .map((concept) => ({ concept, state: states[concept.id] }))
      .filter((item) => item.state.state !== "supported_this_task")
      .sort((a, b) => a.concept.order - b.concept.order || concernPriority(a.state) - concernPriority(b.state));

    const candidates = [];
    for (const concern of concerns) {
      const { concept, state } = concern;
      if ((state.state === "unobserved" || state.state === "mixed") && !rejected.has(`VERIFY-${concept.id}`)) {
        candidates.push(makeVerificationCandidate(data, concept, state));
      }
      const bundles = data.bundles.filter((bundle) => bundle.targetConceptId === concept.id && !rejected.has(bundle.id));
      bundles.forEach((bundle) => candidates.push(makeBundleCandidate(data, bundle, conceptIndex[bundle.targetConceptId], state)));
      if (candidates.length >= 3) break;
    }

    if (!candidates.length) {
      const concept = conceptIndex.K6;
      const state = states.K6;
      const bundle = data.bundles.find((item) => item.id === "B-K6-B");
      candidates.push(makeBundleCandidate(data, bundle, concept, state));
    }

    return { states, candidates: candidates.slice(0, 3) };
  }

  function appendCheckEvidence(events, candidate, result, sequence) {
    if (!Object.prototype.hasOwnProperty.call(RESULT_SCORE, result)) {
      throw new Error(`Unknown result: ${result}`);
    }
    return events.concat({
      id: `RUN-${String(sequence).padStart(2, "0")}`,
      checkId: candidate.checkId,
      conceptResults: { [candidate.targetConceptId]: result },
      note: `教师采用“${candidate.title}”后记录：${RESULT_LABEL[result]}。`,
    });
  }

  function validateData(data) {
    const errors = [];
    const conceptIds = new Set(data.concepts.map((item) => item.id));
    const resourceIds = new Set(data.resources.map((item) => item.id));
    const checkIds = new Set(data.checks.map((item) => item.id));

    if (conceptIds.size !== data.concepts.length) errors.push("知识节点ID存在重复。");
    if (resourceIds.size !== data.resources.length) errors.push("微资源ID存在重复。");
    if (checkIds.size !== data.checks.length) errors.push("检查任务ID存在重复。");

    if (data.resources.length < 8 || data.resources.length > 12) errors.push("微资源数量必须在8—12项之间。");
    if (data.checks.length < 3 || data.checks.length > 5) errors.push("检查任务数量必须在3—5项之间。");
    if (!data.meta.declaredSyntheticOnly) errors.push("必须声明只使用合成画像。");
    if (data.meta.networkRequired) errors.push("原型不得依赖网络。");

    data.concepts.forEach((concept) => {
      concept.prerequisiteIds.forEach((id) => {
        if (!conceptIds.has(id)) errors.push(`${concept.id}存在悬空前置节点${id}。`);
      });
    });

    const visiting = new Set();
    const visited = new Set();
    const conceptIndex = byId(data.concepts);
    function visit(conceptId) {
      if (visiting.has(conceptId)) {
        errors.push(`知识结构存在循环：${conceptId}。`);
        return;
      }
      if (visited.has(conceptId) || !conceptIndex[conceptId]) return;
      visiting.add(conceptId);
      conceptIndex[conceptId].prerequisiteIds.forEach(visit);
      visiting.delete(conceptId);
      visited.add(conceptId);
    }
    data.concepts.forEach((concept) => visit(concept.id));
    data.resources.forEach((resource) => {
      if (resource.sourceType !== "self-authored") errors.push(`${resource.id}不是自编资源。`);
      if (!resource.rightsNote) errors.push(`${resource.id}缺少授权说明。`);
      resource.conceptIds.forEach((id) => {
        if (!conceptIds.has(id)) errors.push(`${resource.id}引用未知节点${id}。`);
      });
    });
    data.checks.forEach((check) => {
      if (check.sourceType !== "self-authored") errors.push(`${check.id}不是自编任务。`);
      if (!check.rightsNote) errors.push(`${check.id}缺少授权说明。`);
      check.targetConceptIds.forEach((id) => {
        if (!conceptIds.has(id)) errors.push(`${check.id}引用未知节点${id}。`);
      });
    });
    data.bundles.forEach((bundle) => {
      if (!conceptIds.has(bundle.targetConceptId)) errors.push(`${bundle.id}引用未知目标节点。`);
      if (!checkIds.has(bundle.checkId)) errors.push(`${bundle.id}引用未知检查任务。`);
      bundle.resourceIds.forEach((id) => {
        if (!resourceIds.has(id)) errors.push(`${bundle.id}引用未知资源${id}。`);
      });
    });
    data.profiles.forEach((profile) => {
      if (!profile.declaredSynthetic) errors.push(`${profile.id}未声明为合成画像。`);
    });
    return errors;
  }

  return {
    RESULT_LABEL,
    computeConceptStates,
    rankRecommendations,
    appendCheckEvidence,
    validateData,
  };
});
