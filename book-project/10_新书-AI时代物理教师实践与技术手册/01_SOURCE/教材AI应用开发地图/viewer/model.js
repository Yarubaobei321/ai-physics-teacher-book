(function exposeTopicRadar(root) {
  const PRIORITY_ORDER = Object.freeze({ P0: 0, P1: 1, P2: 2, P3: 3 });

  function normalizeText(value) {
    return String(value ?? "")
      .normalize("NFKC")
      .toLocaleLowerCase("zh-CN")
      .replace(/\s+/gu, " ")
      .trim();
  }

  function includesAny(values, selected) {
    if (!selected || selected.length === 0) return true;
    return selected.some((value) => values.includes(value));
  }

  function topicCarriers(topic) {
    return topic.carriers ?? [topic.primary_carrier, ...(topic.supporting_carriers ?? [])];
  }

  function topicSearchText(topic) {
    return normalizeText(
      [
        topic.topic,
        topic.textbook_anchor,
        topic.learning_object,
        topic.mvp_ai,
        topic.reality_requirement,
        topic.section_title,
      ].join(" "),
    );
  }

  function filterTopics(topics, filters = {}) {
    const search = normalizeText(filters.search);
    const domains = filters.domains ?? [];
    const primaryCarriers = filters.primaryCarriers ?? [];
    const carriers = filters.carriers ?? [];
    const aiCapabilities = filters.aiCapabilities ?? [];
    const priorities = filters.priorities ?? [];

    return topics
      .filter((topic) => !search || topicSearchText(topic).includes(search))
      .filter((topic) => domains.length === 0 || domains.includes(topic.domain))
      .filter(
        (topic) =>
          primaryCarriers.length === 0 || primaryCarriers.includes(topic.primary_carrier),
      )
      .filter((topic) => includesAny(topicCarriers(topic), carriers))
      .filter((topic) => includesAny(topic.ai_capabilities, aiCapabilities))
      .filter(
        (topic) => priorities.length === 0 || priorities.includes(topic.priority),
      )
      .sort(
        (first, second) =>
          PRIORITY_ORDER[first.priority] - PRIORITY_ORDER[second.priority] ||
          first.domain.localeCompare(second.domain) ||
          first.ordinal - second.ordinal,
      );
  }

  function countBy(topics, getter) {
    const counts = {};
    topics.forEach((topic) => {
      const values = getter(topic);
      (Array.isArray(values) ? values : [values]).forEach((value) => {
        counts[value] = (counts[value] ?? 0) + 1;
      });
    });
    return counts;
  }

  function summarize(topics) {
    return {
      total: topics.length,
      domains: countBy(topics, (topic) => topic.domain),
      primaryCarriers: countBy(topics, (topic) => topic.primary_carrier),
      carriers: countBy(topics, topicCarriers),
      aiCapabilities: countBy(topics, (topic) => topic.ai_capabilities),
      priorities: countBy(topics, (topic) => topic.priority),
    };
  }

  root.TopicRadar = Object.freeze({ filterTopics, normalizeText, summarize, topicCarriers });
})(globalThis);
