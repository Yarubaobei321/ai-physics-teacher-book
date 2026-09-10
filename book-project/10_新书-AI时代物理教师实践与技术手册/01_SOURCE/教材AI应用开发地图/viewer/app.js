(function runRadar() {
  const topics = window.TEXTBOOK_TOPICS ?? [];
  const radar = window.TopicRadar;

  const carrierLabels = { K: "K 关系图谱", S: "S 模拟仿真", D: "D DIS实测", H: "H 虚实结合", V: "V 视频视觉", P: "P 工程项目" };
  const labels = {
    domains: { MEC: "力学、波与光", EM: "电磁与传感", THM: "热学与近代" },
    priorities: { P0: "P0 先建设", P1: "P1 第二批", P2: "P2 研究储备", P3: "P3 现成资源优先" },
    primaryCarriers: carrierLabels,
    carriers: carrierLabels,
    aiCapabilities: { A1: "A1 抽取", A2: "A2 诊断", A3: "A3 生成", A4: "A4 数据分析", A5: "A5 视觉识别", A6: "A6 科学审核", A7: "A7 推荐", A8: "A8 编排" },
  };

  const state = {
    search: "",
    domains: [],
    priorities: [],
    primaryCarriers: [],
    carriers: [],
    aiCapabilities: [],
  };

  const elements = {
    search: document.querySelector("#search"),
    clear: document.querySelector("#clear-filters"),
    visibleCount: document.querySelector("#visible-count"),
    activeFilters: document.querySelector("#active-filters"),
    topicList: document.querySelector("#topic-list"),
    emptyState: document.querySelector("#empty-state"),
    domainFilters: document.querySelector("#domain-filters"),
    priorityFilters: document.querySelector("#priority-filters"),
    primaryCarrierFilters: document.querySelector("#primary-carrier-filters"),
    carrierFilters: document.querySelector("#carrier-filters"),
    aiFilters: document.querySelector("#ai-filters"),
    quickActions: [...document.querySelectorAll("[data-quick]")],
    clearActions: [...document.querySelectorAll('[data-action="clear"]')],
  };

  const summary = radar.summarize(topics);

  function checkbox(group, code, count) {
    const label = document.createElement("label");
    label.className = "option-row";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = code;
    input.dataset.group = group;
    const text = document.createElement("span");
    text.textContent = labels[group][code];
    const number = document.createElement("small");
    number.textContent = String(count ?? 0);
    label.append(input, text, number);
    return label;
  }

  function mountFilters() {
    const groups = [
      ["domains", elements.domainFilters, summary.domains],
      ["priorities", elements.priorityFilters, summary.priorities],
      ["primaryCarriers", elements.primaryCarrierFilters, summary.primaryCarriers],
      ["carriers", elements.carrierFilters, summary.carriers],
      ["aiCapabilities", elements.aiFilters, summary.aiCapabilities],
    ];
    groups.forEach(([group, container, counts]) => {
      Object.keys(labels[group]).forEach((code) => {
        container.append(checkbox(group, code, counts[code]));
      });
    });

    document.querySelectorAll('input[type="checkbox"][data-group]').forEach((input) => {
      input.addEventListener("change", () => {
        const group = input.dataset.group;
        state[group] = [...document.querySelectorAll(`input[data-group="${group}"]:checked`)].map(
          (item) => item.value,
        );
        render();
      });
    });
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function plainText(value) {
    return String(value).replaceAll("**", "").replaceAll("`", "");
  }

  function carrierPanel(topic) {
    const panel = element("div", "carrier-panel");
    const roleLine = element("div", "carrier-role-line");
    roleLine.append(
      element("span", "carrier-role primary-role", `首选 ${topic.primary_carrier}`),
    );
    if (topic.supporting_carriers.length > 0) {
      roleLine.append(
        element("span", "carrier-role supporting-role", `支持 ${topic.supporting_carriers.join("→")}`),
      );
    }

    const rail = element("div", "carrier-rail");
    Object.keys(labels.carriers).forEach((code) => {
      const segment = element("span", "carrier-segment", code);
      segment.dataset.code = code;
      if (code === topic.primary_carrier) {
        segment.classList.add("active", "primary");
        segment.title = `首选载体 · ${labels.carriers[code]}`;
      } else if (topic.supporting_carriers.includes(code)) {
        const order = topic.supporting_carriers.indexOf(code) + 1;
        segment.classList.add("active", "supporting");
        segment.title = `第${order}支持载体 · ${labels.carriers[code]}`;
      } else {
        segment.title = labels.carriers[code];
      }
      rail.append(segment);
    });
    panel.append(roleLine, rail);
    return panel;
  }

  function cardField(label, value, extraClass = "") {
    const paragraph = element("p", `card-field ${extraClass}`.trim());
    paragraph.append(
      element("strong", "", label),
      document.createTextNode(plainText(value)),
    );
    return paragraph;
  }

  function topicCard(topic, index) {
    const article = element("article", "topic-card");
    article.dataset.domain = topic.domain;
    article.style.animationDelay = `${Math.min(index, 8) * 18}ms`;

    const head = element("div", "card-head");
    const titleBlock = element("div");
    titleBlock.append(
      element("h3", "", plainText(topic.topic)),
      element("p", "anchor", `${topic.domain_title} · ${topic.textbook_anchor}`),
    );
    const priority = element("span", `priority ${topic.priority}`, topic.priority);
    head.append(titleBlock, priority);

    const grid = element("div", "card-grid");
    grid.append(
      cardField("最值得显现的学习对象", topic.learning_object),
      cardField("最小开发单元与AI增量", topic.mvp_ai),
      cardField("真实／虚实要求", topic.reality_requirement, "reality-field"),
    );

    const foot = element("div", "card-foot");
    foot.append(
      element("span", "", topic.section_title),
      ...topic.ai_capabilities.map((code) => element("span", "", labels.aiCapabilities[code] ?? code)),
      element("span", "", `${topic.source_file}:${topic.source_line}`),
    );

    article.append(head, carrierPanel(topic), grid, foot);
    return article;
  }

  function renderActiveFilters() {
    const chips = [];
    if (state.search) chips.push(`搜索：${state.search}`);
    ["domains", "priorities", "primaryCarriers", "carriers", "aiCapabilities"].forEach((group) => {
      state[group].forEach((code) => {
        const prefix = group === "primaryCarriers" ? "首选：" : group === "carriers" ? "包含：" : "";
        chips.push(`${prefix}${labels[group][code] ?? code}`);
      });
    });
    elements.activeFilters.replaceChildren(
      ...chips.map((text) => element("span", "active-filter", text)),
    );
  }

  function render() {
    const visible = radar.filterTopics(topics, state);
    elements.visibleCount.textContent = String(visible.length);
    elements.topicList.replaceChildren(...visible.map(topicCard));
    elements.topicList.hidden = visible.length === 0;
    elements.emptyState.hidden = visible.length !== 0;
    renderActiveFilters();
  }

  function clearFilters() {
    state.search = "";
    state.domains = [];
    state.priorities = [];
    state.primaryCarriers = [];
    state.carriers = [];
    state.aiCapabilities = [];
    elements.search.value = "";
    document.querySelectorAll('input[type="checkbox"][data-group]').forEach((input) => {
      input.checked = false;
    });
    render();
  }

  function setSingleFilter(group, values) {
    clearFilters();
    state[group] = values;
    values.forEach((value) => {
      const input = document.querySelector(`input[data-group="${group}"][value="${value}"]`);
      if (input) input.checked = true;
    });
    render();
  }

  elements.search.addEventListener("input", () => {
    state.search = elements.search.value;
    render();
  });
  elements.clear.addEventListener("click", clearFilters);
  elements.clearActions.forEach((button) => button.addEventListener("click", clearFilters));
  elements.quickActions.forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.quick === "p0") setSingleFilter("priorities", ["P0"]);
      if (button.dataset.quick === "reality") setSingleFilter("carriers", ["D", "H"]);
      if (button.dataset.quick === "reason") setSingleFilter("carriers", ["K"]);
    });
  });

  mountFilters();
  render();
})();
