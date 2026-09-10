import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const reports = [];

function readJson(relativePath) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, relativePath), 'utf8'));
}

function sha256File(absolutePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(absolutePath)).digest('hex');
}

function nonEmpty(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function objectValue(value) {
  return value && typeof value === 'object' && !Array.isArray(value);
}

function requiredFields(value, fields, prefix, errors) {
  if (!objectValue(value)) {
    errors.push(`${prefix}必须是对象`);
    return;
  }
  for (const field of fields) {
    if (!(field in value)) errors.push(`${prefix}.${field}缺失`);
  }
}

function record(name, passed, details = '') {
  reports.push({ name, passed, details });
  assert.equal(passed, true, `${name}: ${details}`);
}

const modelSchema = readJson('schemas/physics-model-card.schema.json');
const dataSchema = readJson('schemas/measurement-dataset.schema.json');

function validateSchemas() {
  const errors = [];
  const modelRequired = [
    'research_object', 'system_boundary', 'interval', 'assumptions', 'variables',
    'core_relations', 'applicability_boundaries', 'independent_truths', 'test_suites',
    'gate_status', 'stop_conditions',
  ];
  const dataRequired = [
    'data_identity', 'device', 'calibration', 'raw_file', 'channels', 'transformations',
    'manual_handling', 'anomalies', 'conclusion_limit',
  ];
  if (modelSchema.$schema !== 'https://json-schema.org/draft/2020-12/schema') errors.push('模型卡Schema draft错误');
  if (dataSchema.$schema !== 'https://json-schema.org/draft/2020-12/schema') errors.push('数据集Schema draft错误');
  for (const field of modelRequired) {
    if (!modelSchema.required.includes(field)) errors.push(`模型卡Schema缺必填${field}`);
  }
  for (const field of dataRequired) {
    if (!dataSchema.required.includes(field)) errors.push(`数据集Schema缺必填${field}`);
  }
  const suites = modelSchema.properties.test_suites.required;
  for (const key of ['standard', 'boundary_zero', 'extreme', 'counter_expected', 'independent_benchmark']) {
    if (!suites.includes(key)) errors.push(`模型卡Schema缺测试类${key}`);
  }
  const gates = modelSchema.properties.gate_status.required;
  for (const key of ['runtime', 'physics', 'teaching', 'release']) {
    if (!gates.includes(key)) errors.push(`模型卡Schema缺验收门${key}`);
  }
  if (modelSchema.additionalProperties !== false || dataSchema.additionalProperties !== false) {
    errors.push('顶层Schema必须拒绝未登记字段');
  }
  return errors;
}

const REVIEW_STATUSES = new Set(['draft', 'teacher_review_pending', 'teacher_approved', 'stopped']);
const RELATION_STATUSES = new Set(['verified', 'teacher_review_pending', 'rejected']);
const DATA_IDENTITIES = new Set(['model_input', 'model_output', 'derived_model_output', 'measured', 'manual', 'synthetic', 'default', 'corrected']);
const TEST_KEYS = ['standard', 'boundary_zero', 'extreme', 'counter_expected', 'independent_benchmark'];
const GATE_KEYS = ['runtime', 'physics', 'teaching', 'release'];
const GATE_STATUSES = new Set(['pass', 'return', 'pause_pending_confirmation', 'stop']);

function validateModelCard(card) {
  const errors = [];
  requiredFields(card, modelSchema.required, 'card', errors);
  if (!objectValue(card)) return errors;
  if (card.schema_version !== '1.0') errors.push('schema_version必须为1.0');
  if (!REVIEW_STATUSES.has(card.review_status)) errors.push('review_status非法');
  for (const key of ['card_id', 'title', 'model_version', 'claim_ceiling']) {
    if (!nonEmpty(card[key])) errors.push(`${key}不能为空`);
  }

  requiredFields(card.research_object, ['objects', 'process', 'purpose'], 'research_object', errors);
  if (!Array.isArray(card.research_object?.objects) || card.research_object.objects.length === 0) errors.push('research_object.objects不能为空');
  if (!nonEmpty(card.research_object?.process) || !nonEmpty(card.research_object?.purpose)) errors.push('研究过程和用途不能为空');
  requiredFields(card.system_boundary, ['included', 'external', 'exchange_handling'], 'system_boundary', errors);
  if (!Array.isArray(card.system_boundary?.included) || card.system_boundary.included.length === 0) errors.push('system_boundary.included不能为空');
  if (!nonEmpty(card.system_boundary?.exchange_handling)) errors.push('system_boundary.exchange_handling不能为空');
  requiredFields(card.interval, ['time', 'space', 'states'], 'interval', errors);
  if (!Array.isArray(card.interval?.states) || card.interval.states.length < 2) errors.push('interval.states至少两个');

  for (const [field, minimum] of [['assumptions', 1], ['variables', 1], ['core_relations', 1], ['applicability_boundaries', 1], ['independent_truths', 1], ['stop_conditions', 1], ['sources', 1]]) {
    if (!Array.isArray(card[field]) || card[field].length < minimum) errors.push(`${field}不能为空数组`);
  }
  for (const variable of card.variables ?? []) {
    for (const key of ['symbol', 'meaning', 'object_binding', 'input_unit', 'internal_unit', 'display_unit']) {
      if (!nonEmpty(variable[key])) errors.push(`variable.${key}不能为空`);
    }
    if (!DATA_IDENTITIES.has(variable.data_identity)) errors.push(`变量${variable.symbol ?? '?'}的数据身份非法`);
    if (variable.allowed_range && !(Number.isFinite(variable.allowed_range.minimum) && Number.isFinite(variable.allowed_range.maximum) && variable.allowed_range.minimum <= variable.allowed_range.maximum)) {
      errors.push(`变量${variable.symbol ?? '?'}允许范围非法`);
    }
  }
  for (const relation of card.core_relations ?? []) {
    if (!RELATION_STATUSES.has(relation.status)) errors.push(`关系${relation.relation_id ?? '?'}状态非法`);
    if (!nonEmpty(relation.expression) || !Array.isArray(relation.conditions) || relation.conditions.length === 0) errors.push(`关系${relation.relation_id ?? '?'}缺表达式或条件`);
  }
  for (const truth of card.independent_truths ?? []) {
    if (!nonEmpty(truth.description) || !nonEmpty(truth.source) || !nonEmpty(truth.independence)) errors.push(`独立真值${truth.truth_id ?? '?'}字段不完整`);
  }

  requiredFields(card.test_suites, TEST_KEYS, 'test_suites', errors);
  for (const key of TEST_KEYS) {
    const tests = card.test_suites?.[key];
    if (!Array.isArray(tests) || tests.length === 0) {
      errors.push(`五类测试${key}不能为空`);
      continue;
    }
    for (const test of tests) {
      if (!nonEmpty(test.test_id) || !nonEmpty(test.description)) errors.push(`${key}测试缺ID或说明`);
      if (!['pass', 'fail', 'pending'].includes(test.status)) errors.push(`${test.test_id ?? key}测试状态非法`);
      if (!['automatic_precheck', 'human_manual_check', 'teacher_review', 'measurement'].includes(test.evidence_identity)) errors.push(`${test.test_id ?? key}证据身份非法`);
    }
  }

  requiredFields(card.gate_status, GATE_KEYS, 'gate_status', errors);
  for (const key of GATE_KEYS) {
    const gate = card.gate_status?.[key];
    requiredFields(gate, ['status', 'scope', 'reviewer_role', 'evidence', 'pending_or_return_items'], `gate_status.${key}`, errors);
    if (!GATE_STATUSES.has(gate?.status)) errors.push(`${key}门状态非法`);
    if (!nonEmpty(gate?.scope) || !nonEmpty(gate?.reviewer_role)) errors.push(`${key}门范围或签字角色为空`);
    if (!Array.isArray(gate?.evidence) || gate.evidence.length === 0) errors.push(`${key}门证据不能为空`);
  }
  requiredFields(card.teacher_review, ['status', 'required_role', 'pending_items'], 'teacher_review', errors);
  if (!['pending', 'approved', 'rejected'].includes(card.teacher_review?.status)) errors.push('teacher_review.status非法');
  if (card.review_status === 'teacher_approved') {
    if (card.teacher_review?.status !== 'approved') errors.push('teacher_approved必须有teacher_review.approved');
    if (card.gate_status?.physics?.status !== 'pass') errors.push('teacher_approved必须有物理门pass');
    if (!nonEmpty(card.teacher_review?.reviewer) || !nonEmpty(card.teacher_review?.reviewed_at)) errors.push('教师批准必须记录reviewer和reviewed_at');
  }
  if (card.review_status === 'teacher_review_pending' && card.gate_status?.physics?.status === 'pass') {
    errors.push('教师终审待定时物理门不得标pass');
  }
  return errors;
}

const DATASET_IDENTITIES = new Set(['measured', 'synthetic', 'model_output']);
const CHANNEL_ROLES = new Set(['direct', 'proxy', 'derived']);

function validateDataset(dataset) {
  const errors = [];
  requiredFields(dataset, dataSchema.required, 'dataset', errors);
  if (!objectValue(dataset)) return errors;
  if (dataset.schema_version !== '1.0') errors.push('schema_version必须为1.0');
  for (const key of ['dataset_id', 'title', 'description', 'claim_ceiling', 'conclusion_limit']) {
    if (!nonEmpty(dataset[key])) errors.push(`${key}不能为空`);
  }
  if (!DATASET_IDENTITIES.has(dataset.data_identity)) errors.push('data_identity非法');
  requiredFields(dataset.device, ['kind', 'device_id', 'name', 'model', 'version', 'settings'], 'device', errors);
  requiredFields(dataset.calibration, ['status', 'method', 'references'], 'calibration', errors);
  requiredFields(dataset.raw_file, ['path', 'media_type', 'sha256', 'rows', 'immutable', 'identity_label'], 'raw_file', errors);

  const expectedDevice = { measured: 'physical_device', synthetic: 'software_generator', model_output: 'software_model' }[dataset.data_identity];
  const expectedCalibration = dataset.data_identity === 'measured' ? 'performed' : 'not_applicable';
  if (dataset.device?.kind !== expectedDevice) errors.push(`${dataset.data_identity}身份要求device.kind=${expectedDevice}`);
  if (dataset.calibration?.status !== expectedCalibration) errors.push(`${dataset.data_identity}身份要求calibration.status=${expectedCalibration}`);
  if (dataset.raw_file?.identity_label !== dataset.data_identity) errors.push('raw_file.identity_label必须等于顶层data_identity');
  if (!/^[a-f0-9]{64}$/.test(dataset.raw_file?.sha256 ?? '')) errors.push('raw_file.sha256必须是64位小写十六进制');
  if (dataset.raw_file?.immutable !== true) errors.push('raw_file.immutable必须为true');

  if (nonEmpty(dataset.raw_file?.path)) {
    const rawPath = path.join(ROOT, dataset.raw_file.path);
    if (!fs.existsSync(rawPath)) {
      errors.push(`原始文件不存在:${dataset.raw_file.path}`);
    } else {
      if (sha256File(rawPath) !== dataset.raw_file.sha256) errors.push('原始文件SHA-256不匹配');
      if (dataset.raw_file.media_type === 'text/csv') {
        const lines = fs.readFileSync(rawPath, 'utf8').trim().split(/\r?\n/);
        if (lines.length - 1 !== dataset.raw_file.rows) errors.push('CSV数据行数与raw_file.rows不一致');
        const identityIndex = lines[0].split(',').indexOf('data_identity');
        if (identityIndex < 0) errors.push('CSV缺data_identity列');
        else {
          for (const line of lines.slice(1)) {
            if (line.split(',')[identityIndex] !== dataset.data_identity) errors.push('CSV行身份与顶层data_identity不一致');
          }
        }
      }
    }
  }

  if (!Array.isArray(dataset.channels) || dataset.channels.length === 0) errors.push('channels不能为空');
  const channelIds = new Set();
  for (const channel of dataset.channels ?? []) {
    if (!nonEmpty(channel.channel_id) || channelIds.has(channel.channel_id)) errors.push(`通道ID为空或重复:${channel.channel_id ?? '?'}`);
    channelIds.add(channel.channel_id);
    if (channel.data_identity !== dataset.data_identity) errors.push(`通道${channel.channel_id}身份与顶层不一致`);
    if (!CHANNEL_ROLES.has(channel.quantity_role)) errors.push(`通道${channel.channel_id}角色非法`);
    for (const key of ['label', 'quantity', 'unit', 'source_field_or_transformation']) {
      if (!nonEmpty(channel[key])) errors.push(`通道${channel.channel_id}.${key}为空`);
    }
  }
  if (!(dataset.channels ?? []).some((channel) => channel.quantity_role === 'direct')) errors.push('至少需要一个direct通道');

  if (!Array.isArray(dataset.transformations)) errors.push('transformations必须是数组');
  for (const transformation of dataset.transformations ?? []) {
    if (!channelIds.has(transformation.output_channel)) errors.push(`变换${transformation.transformation_id}输出通道不存在`);
    for (const input of transformation.input_channels ?? []) {
      if (!channelIds.has(input)) errors.push(`变换${transformation.transformation_id}输入通道${input}不存在`);
    }
    if (!nonEmpty(transformation.method) || !nonEmpty(transformation.expression_or_procedure) || !nonEmpty(transformation.software_identity)) errors.push(`变换${transformation.transformation_id}说明不完整`);
  }

  requiredFields(dataset.manual_handling, ['original_preserved', 'actions'], 'manual_handling', errors);
  if (dataset.manual_handling?.original_preserved !== true) errors.push('人工处置必须保留原始数据');
  for (const action of dataset.manual_handling?.actions ?? []) {
    if (action.raw_data_retained !== true) errors.push(`人工处置${action.action_id}必须保留原始数据`);
    if (!nonEmpty(action.reason) || !Array.isArray(action.sample_ids) || action.sample_ids.length === 0) errors.push(`人工处置${action.action_id}缺样本或理由`);
  }
  if (!Array.isArray(dataset.anomalies)) errors.push('anomalies必须是数组');
  if (!Array.isArray(dataset.sources) || dataset.sources.length === 0) errors.push('sources不能为空');
  return errors;
}

const schemaErrors = validateSchemas();
record('两份Schema包含R0关键字段、五类测试和四道门', schemaErrors.length === 0, schemaErrors.join('；'));

const modelCard = readJson('examples/s1-collision-model-card.json');
const modelErrors = validateModelCard(modelCard);
record('S1模型卡通过关键约束', modelErrors.length === 0, modelErrors.join('；'));
record(
  'S1保持教师终审待定且物理门未冒充通过',
  modelCard.review_status === 'teacher_review_pending' &&
    modelCard.teacher_review.status === 'pending' &&
    modelCard.gate_status.physics.status === 'pause_pending_confirmation',
  JSON.stringify({ review_status: modelCard.review_status, teacher_review: modelCard.teacher_review.status, physics_gate: modelCard.gate_status.physics.status }),
);

const dataset = readJson('examples/synthetic-collision-measurement-dataset.json');
const datasetErrors = validateDataset(dataset);
record('合成测量链示例通过关键约束与原始哈希检查', datasetErrors.length === 0, datasetErrors.join('；'));
record(
  '合成示例未冒充DIS实测且删点保留原始值',
  dataset.data_identity === 'synthetic' &&
    dataset.device.kind === 'software_generator' &&
    dataset.calibration.status === 'not_applicable' &&
    dataset.manual_handling.original_preserved === true &&
    dataset.manual_handling.actions.every((action) => action.raw_data_retained === true),
  JSON.stringify({ identity: dataset.data_identity, device: dataset.device.kind, calibration: dataset.calibration.status }),
);

const invalidModel = readJson('tests/fixtures/invalid-model-card.json');
const invalidModelErrors = validateModelCard(invalidModel);
record(
  '故意非法模型卡被拒绝',
  invalidModelErrors.length > 0 &&
    invalidModelErrors.some((error) => error.includes('system_boundary')) &&
    invalidModelErrors.some((error) => error.includes('teacher_approved')),
  `${invalidModelErrors.length}项错误：${invalidModelErrors.slice(0, 5).join('；')}`,
);

const invalidDataset = readJson('tests/fixtures/invalid-measurement-dataset.json');
const invalidDatasetErrors = validateDataset(invalidDataset);
record(
  '故意非法实测身份数据集被拒绝',
  invalidDatasetErrors.length > 0 &&
    invalidDatasetErrors.some((error) => error.includes('physical_device')) &&
    invalidDatasetErrors.some((error) => error.toLowerCase().includes('sha256')),
  `${invalidDatasetErrors.length}项错误：${invalidDatasetErrors.slice(0, 5).join('；')}`,
);

for (const report of reports) {
  console.log(`${report.passed ? 'PASS' : 'FAIL'} ${report.name}`);
  if (report.details) console.log(`  ${report.details}`);
}
console.log(`SUMMARY ${reports.filter((report) => report.passed).length}/${reports.length} checks passed`);
