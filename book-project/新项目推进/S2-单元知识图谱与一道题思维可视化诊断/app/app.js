(function () {
  "use strict";

  const graph = window.S2_GRAPH;
  const diagnostic = window.S2_DIAGNOSTIC;
  const svgNS = "http://www.w3.org/2000/svg";

  if (!graph || !diagnostic) {
    document.body.textContent = "数据文件未加载，请确认 data 目录与 app 目录保持原有相对位置。";
    return;
  }

  const elements = {
    questionStem: document.getElementById("questionStem"),
    givens: document.getElementById("givens"),
    studentText: document.getElementById("studentText"),
    charCount: document.getElementById("charCount"),
    sampleButtons: document.getElementById("sampleButtons"),
    analyzeButton: document.getElementById("analyzeButton"),
    clearButton: document.getElementById("clearButton"),
    coverageBadge: document.getElementById("coverageBadge"),
    emptyState: document.getElementById("emptyState"),
    contradictions: document.getElementById("contradictions"),
    checkpointResults: document.getElementById("checkpointResults"),
    categoryFilters: document.getElementById("categoryFilters"),
    resetGraphButton: document.getElementById("resetGraphButton"),
    knowledgeGraph: document.getElementById("knowledgeGraph"),
    nodeInspector: document.getElementById("nodeInspector"),
    sourceList: document.getElementById("sourceList")
  };

  const nodeMap = new Map(graph.nodes.map((node) => [node.id, node]));
  const sourceMap = new Map(graph.sources.map((source) => [source.id, source]));
  const visibleCategories = new Set(graph.categories.map((category) => category.id));
  let lastAnalysis = { observed: new Set(), gaps: new Set(), conflicts: new Set() };
  let selectedNodeId = null;

  function makeElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function makeSvgElement(tag, attributes) {
    const element = document.createElementNS(svgNS, tag);
    Object.entries(attributes || {}).forEach(([key, value]) => element.setAttribute(key, value));
    return element;
  }

  function normalizeText(text) {
    return text
      .replace(/[Ａ-Ｚａ-ｚ０-９]/g, (character) => String.fromCharCode(character.charCodeAt(0) - 0xfee0))
      .replace(/[＝]/g, "=")
      .replace(/[－—]/g, "-")
      .replace(/\u00a0/g, " ")
      .trim();
  }

  function firstPatternMatch(patterns, text) {
    for (const pattern of patterns) {
      pattern.lastIndex = 0;
      const match = pattern.exec(text);
      if (match) return match[0];
    }
    return null;
  }

  function analyzeText(rawText) {
    const text = normalizeText(rawText);
    const checkpointResults = diagnostic.checkpoints.map((checkpoint) => {
      const hits = checkpoint.groups
        .map((group) => ({ label: group.label, match: firstPatternMatch(group.patterns, text) }))
        .filter((hit) => hit.match);
      return {
        checkpoint,
        hits,
        present: hits.length >= checkpoint.minimumGroups
      };
    });

    const contradictionResults = diagnostic.contradictions
      .map((item) => ({ item, match: firstPatternMatch(item.patterns, text) }))
      .filter((result) => result.match);

    return { text, checkpointResults, contradictionResults };
  }

  function renderQuestion() {
    elements.questionStem.textContent = diagnostic.question.stem;
    diagnostic.question.givens.forEach((given) => elements.givens.append(makeElement("span", "", given)));
  }

  function renderSamples() {
    diagnostic.samples.forEach((sample) => {
      const button = makeElement("button", "sample-button", sample.label);
      button.type = "button";
      button.addEventListener("click", () => {
        elements.studentText.value = sample.text;
        updateCharCount();
        runAnalysis();
      });
      elements.sampleButtons.append(button);
    });
  }

  function updateCharCount() {
    elements.charCount.textContent = `${elements.studentText.value.length} 字`;
  }

  function renderContradictions(results) {
    elements.contradictions.replaceChildren();
    if (!results.length) {
      elements.contradictions.hidden = true;
      return;
    }
    elements.contradictions.hidden = false;
    elements.contradictions.append(makeElement("h3", "", `发现 ${results.length} 处需要优先核对的表述`));
    results.forEach(({ item, match }) => {
      const block = makeElement("div", "contradiction-item");
      block.append(makeElement("p", "", `${item.title}：文字中出现“${match}”`));
      block.append(makeElement("p", "", `建议追问：${item.reviewQuestion}`));
      elements.contradictions.append(block);
    });
  }

  function renderCheckpointResults(results) {
    elements.checkpointResults.replaceChildren();
    results.forEach((result, index) => {
      const { checkpoint, hits, present } = result;
      const article = makeElement("article", `checkpoint ${present ? "present" : "missing"}`);
      article.style.setProperty("--result-index", index);
      article.append(makeElement("div", "checkpoint-mark", present ? "✓" : "?"));

      const body = makeElement("div", "checkpoint-body");
      body.append(makeElement("h3", "", checkpoint.title));
      if (present) {
        body.append(makeElement("p", "", "已找到满足当前规则的显式表述。"));
        const chips = makeElement("div", "evidence-chips");
        hits.forEach((hit) => chips.append(makeElement("span", "", `${hit.label} · ${hit.match}`)));
        body.append(chips);
      } else {
        body.append(makeElement("p", "missing-copy", "未见足够的显式证据；这不等于学生不会。"));
        body.append(makeElement("p", "", `检查依据：${checkpoint.criterion}`));
      }
      body.append(makeElement("p", "review-question", `教师复核：${checkpoint.reviewQuestion}`));
      article.append(body);
      elements.checkpointResults.append(article);
    });
  }

  function updateGraphAnalysis(results, contradictions) {
    const observed = new Set();
    const gaps = new Set();
    const conflictNodes = new Set();

    results.forEach(({ checkpoint, present }) => {
      checkpoint.nodeIds.forEach((nodeId) => (present ? observed : gaps).add(nodeId));
    });
    contradictions.forEach(({ item }) => item.nodeIds.forEach((nodeId) => conflictNodes.add(nodeId)));
    observed.forEach((nodeId) => gaps.delete(nodeId));
    conflictNodes.forEach((nodeId) => {
      observed.delete(nodeId);
      gaps.delete(nodeId);
    });
    lastAnalysis = { observed, gaps, conflicts: conflictNodes };
    renderGraph();
  }

  function runAnalysis() {
    const rawText = elements.studentText.value;
    if (!rawText.trim()) {
      elements.studentText.focus();
      elements.coverageBadge.textContent = "请先输入文字";
      elements.coverageBadge.classList.remove("has-results");
      return;
    }

    const analysis = analyzeText(rawText);
    const visibleCount = analysis.checkpointResults.filter((result) => result.present).length;
    elements.emptyState.hidden = true;
    elements.coverageBadge.textContent = `可见证据 ${visibleCount}/${diagnostic.checkpoints.length}`;
    elements.coverageBadge.classList.add("has-results");
    renderContradictions(analysis.contradictionResults);
    renderCheckpointResults(analysis.checkpointResults);
    updateGraphAnalysis(analysis.checkpointResults, analysis.contradictionResults);
  }

  function resetAnalysis() {
    elements.studentText.value = "";
    updateCharCount();
    elements.coverageBadge.textContent = "等待输入";
    elements.coverageBadge.classList.remove("has-results");
    elements.emptyState.hidden = false;
    elements.contradictions.hidden = true;
    elements.contradictions.replaceChildren();
    elements.checkpointResults.replaceChildren();
    lastAnalysis = { observed: new Set(), gaps: new Set(), conflicts: new Set() };
    selectedNodeId = null;
    renderGraph();
    elements.studentText.focus();
  }

  function splitLabel(label) {
    if (label.length <= 11) return [label];
    const pivot = Math.ceil(label.length / 2);
    const breakChars = ["：", "—", " "];
    let breakIndex = -1;
    for (let offset = 0; offset < 5; offset += 1) {
      const candidates = [pivot - offset, pivot + offset];
      breakIndex = candidates.find((index) => breakChars.includes(label[index]));
      if (breakIndex !== undefined && breakIndex >= 0) break;
    }
    if (breakIndex === undefined || breakIndex < 0) breakIndex = pivot;
    const first = label.slice(0, breakIndex + (breakChars.includes(label[breakIndex]) ? 1 : 0)).trim();
    const second = label.slice(breakIndex + (breakChars.includes(label[breakIndex]) ? 1 : 0)).trim();
    return [first, second].filter(Boolean);
  }

  function graphNodeClass(nodeId) {
    if (lastAnalysis.conflicts.has(nodeId)) return "conflict";
    if (lastAnalysis.observed.has(nodeId)) return "observed";
    if (lastAnalysis.gaps.has(nodeId)) return "gap";
    return "";
  }

  function renderGraph() {
    const svg = elements.knowledgeGraph;
    svg.replaceChildren();
    const visibleNodeIds = new Set(
      graph.nodes.filter((node) => visibleCategories.has(node.category)).map((node) => node.id)
    );

    const defs = makeSvgElement("defs");
    const marker = makeSvgElement("marker", { id:"arrow", markerWidth:"7", markerHeight:"7", refX:"6", refY:"3.5", orient:"auto", markerUnits:"strokeWidth" });
    marker.append(makeSvgElement("path", { d:"M0,0 L7,3.5 L0,7 z", fill:"#45647c" }));
    defs.append(marker);
    svg.append(defs);

    const edgeLayer = makeSvgElement("g", { class:"edge-layer" });
    graph.edges.forEach((edge) => {
      if (!visibleNodeIds.has(edge.from) || !visibleNodeIds.has(edge.to)) return;
      const from = nodeMap.get(edge.from);
      const to = nodeMap.get(edge.to);
      const line = makeSvgElement("line", {
        x1:from.x, y1:from.y, x2:to.x, y2:to.y,
        class:"graph-edge", "data-edge-id":edge.id,
        "data-from":edge.from, "data-to":edge.to,
        "marker-end":"url(#arrow)"
      });
      edgeLayer.append(line);
    });
    svg.append(edgeLayer);

    const nodeLayer = makeSvgElement("g", { class:"node-layer" });
    graph.nodes.forEach((node) => {
      if (!visibleNodeIds.has(node.id)) return;
      const statusClass = graphNodeClass(node.id);
      const group = makeSvgElement("g", {
        class:`graph-node ${statusClass}${selectedNodeId === node.id ? " selected" : ""}`,
        transform:`translate(${node.x} ${node.y})`,
        tabindex:"0", role:"button", "aria-label":node.label,
        "data-node-id":node.id
      });
      group.append(makeSvgElement("rect", { x:"-78", y:"-28", width:"156", height:"56", rx:"11" }));
      const lines = splitLabel(node.label);
      lines.forEach((line, index) => {
        const text = makeSvgElement("text", { x:"0", y:lines.length === 1 ? "5" : index === 0 ? "-1" : "16", "text-anchor":"middle" });
        text.textContent = line;
        group.append(text);
      });
      const idText = makeSvgElement("text", { class:"node-id", x:"-68", y:"-16" });
      idText.textContent = node.id;
      group.append(idText);
      group.addEventListener("click", () => selectNode(node.id));
      group.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectNode(node.id);
        }
      });
      nodeLayer.append(group);
    });
    svg.append(nodeLayer);
    refreshGraphEmphasis();
  }

  function selectNode(nodeId) {
    selectedNodeId = selectedNodeId === nodeId ? null : nodeId;
    renderNodeInspector(selectedNodeId);
    renderGraph();
  }

  function refreshGraphEmphasis() {
    if (!selectedNodeId) return;
    const neighborIds = new Set([selectedNodeId]);
    graph.edges.forEach((edge) => {
      if (edge.from === selectedNodeId) neighborIds.add(edge.to);
      if (edge.to === selectedNodeId) neighborIds.add(edge.from);
    });
    elements.knowledgeGraph.querySelectorAll(".graph-node").forEach((nodeElement) => {
      const nodeId = nodeElement.getAttribute("data-node-id");
      nodeElement.classList.toggle("dimmed", !neighborIds.has(nodeId));
    });
    elements.knowledgeGraph.querySelectorAll(".graph-edge").forEach((edgeElement) => {
      const related = edgeElement.getAttribute("data-from") === selectedNodeId || edgeElement.getAttribute("data-to") === selectedNodeId;
      edgeElement.classList.toggle("related", related);
      const conflict = related && lastAnalysis.conflicts.has(selectedNodeId);
      edgeElement.classList.toggle("conflict", conflict);
    });
  }

  function renderNodeInspector(nodeId) {
    elements.nodeInspector.replaceChildren();
    elements.nodeInspector.append(makeElement("p", "step-label", "节点说明"));
    if (!nodeId) {
      elements.nodeInspector.append(makeElement("h3", "", "点击一个节点"));
      elements.nodeInspector.append(makeElement("p", "", "查看它的物理含义、来源与相邻关系。"));
      return;
    }

    const node = nodeMap.get(nodeId);
    elements.nodeInspector.append(makeElement("h3", "", node.label));
    elements.nodeInspector.append(makeElement("p", "", node.summary));
    const details = makeElement("dl", "");
    details.append(makeElement("dt", "", "类别"));
    const category = graph.categories.find((item) => item.id === node.category);
    details.append(makeElement("dd", "", category ? category.label : node.category));
    details.append(makeElement("dt", "", "来源"));
    details.append(makeElement("dd", "", node.sourceIds.map((sourceId) => sourceMap.get(sourceId)?.title || sourceId).join("；")));
    details.append(makeElement("dt", "", "相邻关系"));
    const relationList = makeElement("dd", "");
    const list = makeElement("ul", "relation-list");
    graph.edges
      .filter((edge) => edge.from === nodeId || edge.to === nodeId)
      .forEach((edge) => {
        const otherId = edge.from === nodeId ? edge.to : edge.from;
        const other = nodeMap.get(otherId);
        if (other) list.append(makeElement("li", "", `${edge.label} → ${other.label}`));
      });
    relationList.append(list);
    details.append(relationList);
    elements.nodeInspector.append(details);
  }

  function renderCategoryFilters() {
    graph.categories.forEach((category) => {
      const button = makeElement("button", "filter-button", category.label);
      button.type = "button";
      button.setAttribute("aria-pressed", "true");
      button.addEventListener("click", () => {
        if (visibleCategories.has(category.id)) visibleCategories.delete(category.id);
        else visibleCategories.add(category.id);
        button.setAttribute("aria-pressed", String(visibleCategories.has(category.id)));
        selectedNodeId = null;
        renderNodeInspector(null);
        renderGraph();
      });
      elements.categoryFilters.append(button);
    });
  }

  function resetGraph() {
    graph.categories.forEach((category) => visibleCategories.add(category.id));
    elements.categoryFilters.querySelectorAll("button").forEach((button) => button.setAttribute("aria-pressed", "true"));
    selectedNodeId = null;
    renderNodeInspector(null);
    renderGraph();
  }

  function renderSources() {
    graph.sources.forEach((source) => {
      const item = makeElement("article", "source-item");
      item.append(makeElement("p", "source-kind", source.kind.replaceAll("_", " ")));
      item.append(makeElement("h3", "", source.title));
      item.append(makeElement("p", "", source.anchor));
      item.append(makeElement("p", "", source.rights));
      elements.sourceList.append(item);
    });
  }

  elements.studentText.addEventListener("input", updateCharCount);
  elements.analyzeButton.addEventListener("click", runAnalysis);
  elements.clearButton.addEventListener("click", resetAnalysis);
  elements.resetGraphButton.addEventListener("click", resetGraph);

  renderQuestion();
  renderSamples();
  renderCategoryFilters();
  renderSources();
  renderGraph();
  updateCharCount();
})();
