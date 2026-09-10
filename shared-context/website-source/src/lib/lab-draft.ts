/** 只持久化明确登记的原始表格字段，不保存 DOM、计算结果或设备权限。 */
type Fields = Record<string, HTMLInputElement | null>;
type Draft = { version: 1; experiment: string; savedAt: number; fields: Record<string, string> };

export function bindLabDraft(options: { experiment: string; fields: Fields; onRestore: () => void }) {
  const root = document.querySelector<HTMLElement>('[data-lab-draft]');
  const workbench = document.querySelector<HTMLElement>('#lab-workbench');
  if (!root || !workbench) return;
  const fields = Object.entries(options.fields).filter((entry): entry is [string, HTMLInputElement] => entry[1] instanceof HTMLInputElement);
  const controls = root.querySelector<HTMLElement>('[data-draft-actions]')!;
  const status = root.querySelector<HTMLElement>('[data-draft-status]')!;
  const saveButton = root.querySelector<HTMLButtonElement>('[data-draft-save]')!;
  const restoreButton = root.querySelector<HTMLButtonElement>('[data-draft-restore]')!;
  const conflict = root.querySelector<HTMLElement>('[data-draft-conflict]')!;
  const storageKey = `yucai:lab-draft:${options.experiment}:v1`;
  let lastSeen: string | null = null;
  let dirty = false;
  let blocked = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  const say = (message: string) => { status.textContent = message; };
  const time = (date: number) => new Date(date).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  const read = (raw: string): Draft => {
    if (raw.length > 32000) throw new Error('草稿过大');
    const draft = JSON.parse(raw) as Draft;
    if (!draft || draft.version !== 1 || draft.experiment !== options.experiment || !Number.isFinite(draft.savedAt) || draft.savedAt <= 0 || !draft.fields || typeof draft.fields !== 'object' || Array.isArray(draft.fields)) throw new Error('草稿格式不兼容');
    // 必须整份可用后才写入表格，避免半恢复；字段使用固定清单。
    if (Object.keys(draft.fields).length !== fields.length) throw new Error('字段不匹配');
    for (const [key, input] of fields) {
      const value = draft.fields[key];
      if (typeof value !== 'string' || value.length > 300 || (input.type === 'number' && value !== '' && !Number.isFinite(Number(value)))) throw new Error('字段损坏');
    }
    return draft;
  };
  const stop = () => { if (timer !== undefined) clearTimeout(timer); timer = undefined; };
  const showConflict = () => {
    blocked = true; conflict.hidden = false; stop();
    say('草稿已在其他标签页更改，尚未覆盖。');
  };
  const save = () => {
    stop();
    if (blocked) return;
    try {
      if (localStorage.getItem(storageKey) !== lastSeen) { showConflict(); return; }
      const draft: Draft = { version: 1, experiment: options.experiment, savedAt: Date.now(), fields: Object.fromEntries(fields.map(([key, input]) => [key, input.value])) };
      const raw = JSON.stringify(draft);
      read(raw);
      localStorage.setItem(storageKey, raw);
      lastSeen = raw; dirty = false; restoreButton.disabled = false;
      say(`已保存本机草稿 · ${time(draft.savedAt)}`);
    } catch { say('无法保存到浏览器。请导出 CSV 保留本次数据。'); }
  };
  const restore = () => {
    stop();
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw === null) {
        lastSeen = null; dirty = false; blocked = false; conflict.hidden = true; restoreButton.disabled = true; saveButton.disabled = false;
        say('没有已保存草稿；当前表格保持不变。下次修改后自动保存。');
        return;
      }
      const draft = read(raw);
      fields.forEach(([key, input]) => { input.value = draft.fields[key]; });
      options.onRestore();
      lastSeen = raw; dirty = false; blocked = false; conflict.hidden = true; restoreButton.disabled = false; saveButton.disabled = false;
      say(`已恢复本机草稿 · ${time(draft.savedAt)}`);
    } catch {
      blocked = true; saveButton.disabled = true; restoreButton.disabled = true;
      say('旧草稿无法读取，尚未覆盖。可先导出当前表格，再删除旧草稿后继续保存。');
    }
  };
  const changed = () => {
    dirty = true;
    if (blocked) return;
    stop(); say('正在保存本机草稿…'); timer = setTimeout(save, 180);
  };
  controls.hidden = false;
  try {
    lastSeen = localStorage.getItem(storageKey);
    if (lastSeen !== null) restore();
  } catch { say('浏览器未开放本机存储。请导出 CSV 保留本次数据。'); }
  const inputs = new Set(fields.map(([, input]) => input));
  workbench.addEventListener('input', event => { if (event.target instanceof HTMLInputElement && inputs.has(event.target)) changed(); });
  // 采集值填表和清空由原实验代码写入 input.value，等原处理结束后再保存。
  workbench.addEventListener('click', event => {
    if ((event.target as HTMLElement).closest('#clear-data, #ai-simulate, [data-fill-point], [data-fill-trial]')) queueMicrotask(changed);
  });
  saveButton.addEventListener('click', save);
  restoreButton.addEventListener('click', restore);
  root.querySelector('[data-draft-forget]')?.addEventListener('click', () => {
    stop();
    try {
      localStorage.removeItem(storageKey);
      lastSeen = null; dirty = false; blocked = false; conflict.hidden = true; saveButton.disabled = false; restoreButton.disabled = true;
      say('已删除本机草稿，当前表格保持不变。下次修改后自动保存。');
    } catch { say('浏览器未允许删除草稿，当前表格保持不变。'); }
  });
  root.querySelector('[data-draft-load-other]')?.addEventListener('click', restore);
  root.querySelector('[data-draft-keep-current]')?.addEventListener('click', () => {
    try { lastSeen = localStorage.getItem(storageKey); blocked = false; saveButton.disabled = false; conflict.hidden = true; save(); }
    catch { say('无法保存到浏览器。请导出 CSV 保留本次数据。'); }
  });
  window.addEventListener('pagehide', () => { if (dirty) save(); });
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden' && dirty) save(); });
  window.addEventListener('storage', event => {
    if ((event.key === storageKey || event.key === null) && event.newValue !== lastSeen) showConflict();
  });
}
