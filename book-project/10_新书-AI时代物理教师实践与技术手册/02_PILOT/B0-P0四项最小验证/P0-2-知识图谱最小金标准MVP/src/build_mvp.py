#!/usr/bin/env python3
"""构建“动量与碰撞”知识系统最小金标准审阅产物。

只使用本地 CSV 与 Python 标准库；不调用外部模型或服务。
"""

from __future__ import annotations

import csv
import html
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
GENERATED = ROOT / "generated"


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def unique_values(rows: list[dict[str, str]], key: str, label: str) -> set[str]:
    values = [row[key] for row in rows]
    if len(values) != len(set(values)):
        raise ValueError(f"{label}存在重复ID：{key}")
    return set(values)


def validate_sources(bundle: dict[str, list[dict[str, str]]]) -> None:
    components = bundle["components"]
    edges = bundle["edges"]
    rejected = bundle["rejected"]
    questions = bundle["questions"]
    mappings = bundle["mappings"]
    responses = bundle["responses"]

    kc_ids = unique_values(components, "kc_id", "知识组件")
    edge_ids = unique_values(edges, "edge_id", "图谱边")
    rejected_ids = unique_values(rejected, "candidate_id", "否决边")
    question_ids = unique_values(questions, "question_id", "题目")
    if edge_ids & rejected_ids:
        raise ValueError("已采用边与否决边ID不能重复")

    sequence = sorted(int(row["sequence"]) for row in questions)
    if sequence != list(range(1, len(questions) + 1)):
        raise ValueError("题目顺序必须从1连续编号")
    if len(questions) != 20:
        raise ValueError("当前最小验证固定为20道自编题")

    for row in edges:
        if row["from_kc"] not in kc_ids or row["to_kc"] not in kc_ids:
            raise ValueError(f"图谱边引用未知组件：{row}")
        if row["from_kc"] == row["to_kc"]:
            raise ValueError(f"图谱不允许自环：{row}")
    for row in rejected:
        if row["from_kc"] not in kc_ids or row["to_kc"] not in kc_ids:
            raise ValueError(f"否决边引用未知组件：{row}")

    # 对当前所有候选依赖边执行无环检查；supports边也不应形成回路。
    adjacency: dict[str, list[str]] = defaultdict(list)
    indegree = {kc_id: 0 for kc_id in kc_ids}
    for row in edges:
        adjacency[row["from_kc"]].append(row["to_kc"])
        indegree[row["to_kc"]] += 1
    queue = [kc_id for kc_id, degree in indegree.items() if degree == 0]
    visited = 0
    while queue:
        current = queue.pop()
        visited += 1
        for target in adjacency[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited != len(kc_ids):
        raise ValueError("内容图谱存在环，需教师复核边的方向")

    mapped_questions: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in mappings:
        if row["question_id"] not in question_ids or row["kc_id"] not in kc_ids:
            raise ValueError(f"Q-matrix引用未知ID：{row}")
        if row["role"] not in {"primary", "supporting"}:
            raise ValueError(f"Q-matrix角色无效：{row}")
        mapped_questions[row["question_id"]].append(row)
    for question_id in question_ids:
        if not mapped_questions[question_id]:
            raise ValueError(f"题目未映射知识组件：{question_id}")
        if not any(row["role"] == "primary" for row in mapped_questions[question_id]):
            raise ValueError(f"题目缺少primary组件：{question_id}")

    by_student: dict[str, set[str]] = defaultdict(set)
    for row in responses:
        if row["question_id"] not in question_ids:
            raise ValueError(f"合成作答引用未知题目：{row}")
        if row["correct"] not in {"0", "1"}:
            raise ValueError(f"correct字段只能为0或1：{row}")
        if row["data_identity"] != "合成轨迹":
            raise ValueError("所有作答必须显式标识为合成轨迹")
        if row["question_id"] in by_student[row["student_id"]]:
            raise ValueError(f"同一合成学生重复作答：{row}")
        by_student[row["student_id"]].add(row["question_id"])
    if len(by_student) < 3:
        raise ValueError("至少需要3组合成学生状态")
    for student_id, answered in by_student.items():
        if answered != question_ids:
            raise ValueError(f"{student_id}没有覆盖全部20题")


def load_bundle() -> dict[str, list[dict[str, str]]]:
    bundle = {
        "components": read_csv("knowledge_components.csv"),
        "edges": read_csv("graph_edges.csv"),
        "rejected": read_csv("rejected_edges.csv"),
        "questions": read_csv("questions.csv"),
        "mappings": read_csv("q_matrix.csv"),
        "responses": read_csv("synthetic_responses.csv"),
        "parameters": read_csv("model_parameters.csv"),
    }
    validate_sources(bundle)
    return bundle


def bkt_update(prior: float, correct: bool, guess: float, slip: float, learn: float) -> tuple[float, float]:
    if correct:
        numerator = prior * (1 - slip)
        denominator = numerator + (1 - prior) * guess
    else:
        numerator = prior * slip
        denominator = numerator + (1 - prior) * (1 - guess)
    posterior = numerator / denominator
    after_learning = posterior + (1 - posterior) * learn
    return posterior, after_learning


def build_states(bundle: dict[str, list[dict[str, str]]]) -> tuple[list[dict[str, object]], dict[str, dict[str, float]]]:
    params = {row["parameter"]: float(row["value"]) for row in bundle["parameters"]}
    initial = params["initial_mastery"]
    learn = params["learn_transition"]
    guess = params["guess"]
    slip = params["slip"]

    q_sequence = {row["question_id"]: int(row["sequence"]) for row in bundle["questions"]}
    q_mappings: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in bundle["mappings"]:
        q_mappings[row["question_id"]].append(row)

    responses: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in bundle["responses"]:
        responses[row["student_id"]].append(row)

    output: list[dict[str, object]] = []
    final_states: dict[str, dict[str, float]] = {}
    for student_id, rows in sorted(responses.items()):
        state = {row["kc_id"]: initial for row in bundle["components"]}
        for response in sorted(rows, key=lambda item: q_sequence[item["question_id"]]):
            correct = response["correct"] == "1"
            for mapping in q_mappings[response["question_id"]]:
                kc_id = mapping["kc_id"]
                prior = state[kc_id]
                posterior, after = bkt_update(prior, correct, guess, slip, learn)
                state[kc_id] = after
                output.append(
                    {
                        "student_id": student_id,
                        "student_label": response["student_label"],
                        "sequence": q_sequence[response["question_id"]],
                        "question_id": response["question_id"],
                        "kc_id": kc_id,
                        "role": mapping["role"],
                        "correct": int(correct),
                        "prior": f"{prior:.4f}",
                        "posterior_before_learning": f"{posterior:.4f}",
                        "state_after_learning": f"{after:.4f}",
                        "data_identity": "合成轨迹／演示参数",
                    }
                )
        final_states[student_id] = state
    return output, final_states


def component_evidence(bundle: dict[str, list[dict[str, str]]]) -> dict[str, dict[str, tuple[int, int]]]:
    mapping_by_question: dict[str, list[str]] = defaultdict(list)
    for row in bundle["mappings"]:
        mapping_by_question[row["question_id"]].append(row["kc_id"])
    evidence: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for row in bundle["responses"]:
        for kc_id in mapping_by_question[row["question_id"]]:
            evidence[row["student_id"]][kc_id][1] += 1
            evidence[row["student_id"]][kc_id][0] += int(row["correct"])
    return {
        student_id: {kc_id: (values[0], values[1]) for kc_id, values in components.items()}
        for student_id, components in evidence.items()
    }


def build_comparison(bundle: dict[str, list[dict[str, str]]], final_states: dict[str, dict[str, float]]) -> str:
    names = {row["kc_id"]: row["name"] for row in bundle["components"]}
    labels: dict[str, str] = {}
    scores: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))
    for row in bundle["responses"]:
        labels[row["student_id"]] = row["student_label"]
        correct, total = scores[row["student_id"]]
        scores[row["student_id"]] = (correct + int(row["correct"]), total + 1)
    evidence = component_evidence(bundle)

    lines = [
        "# 四层信息比较与三组合成诊断",
        "",
        "> 全部学生轨迹为合成数据；状态参数人为设定。以下结果只验证信息结构，不代表真实学生诊断。",
        "",
        "## 四层逐步增加了什么",
        "",
        "| 层次 | 本地可见信息 | 新增教师动作 | 仍然看不见什么 |",
        "| --- | --- | --- | --- |",
        "| 章节标签 | 单元总分、题目属于动量与碰撞 | 判断是否回看本单元 | 具体错误对象与前置关系 |",
        "| 内容图谱 | 10个组件、13条候选依赖、3条否决边 | 沿前置关系回查定义和任务 | 没有作答证据，不能定位学生 |",
        "| Q-matrix | 20题与组件的36条映射 | 按组件聚合原始作答并发现证据稀疏处 | 多组件题的一次错误由谁造成 |",
        "| 动态状态 | 作答顺序下的透明概率更新 | 选择优先回看的组件和区分性追问 | 真实掌握、稳定迁移与教学效果 |",
        "",
        "## 章节标签只给出总分",
        "",
        "| 合成学生 | 总分 | 单凭总分容易漏掉的差异 |",
        "| --- | ---: | --- |",
    ]
    summary_notes = {
        "SYN-A": "错误集中在方向与反弹符号，后段整体表现较好。",
        "SYN-B": "基础计算较好，但系统边界、外冲量和实验守恒结论反复混淆。",
        "SYN-C": "前段多个基础任务失败，后段出现改善；顺序信息不可由总分恢复。",
    }
    for student_id in sorted(scores):
        correct, total = scores[student_id]
        lines.append(f"| {student_id}　{labels[student_id]} | {correct}/{total} | {summary_notes[student_id]} |")

    for student_id in sorted(final_states):
        lines.extend(
            [
                "",
                f"## {student_id}　{labels[student_id]}",
                "",
                "| 组件 | Q-matrix证据 | 演示状态终值 |",
                "| --- | ---: | ---: |",
            ]
        )
        ordered = sorted(final_states[student_id].items(), key=lambda item: item[1])
        for kc_id, state in ordered:
            correct, total = evidence[student_id].get(kc_id, (0, 0))
            lines.append(f"| {kc_id} {names[kc_id]} | {correct}/{total} | {state:.3f} |")
        lowest = ordered[:3]
        candidate_text = "、".join(f"{kc_id}{names[kc_id]}" for kc_id, _ in lowest)
        lines.extend(
            [
                "",
                f"**优先人工回看候选**：{candidate_text}。这是按演示状态排序生成的复核入口，不是自动教学路径，也不是掌握／未掌握分类。",
            ]
        )

    lines.extend(
        [
            "",
            "## 一个主动暴露出来的归因反例",
            "",
            "SYN-A在Q07的合成错误被人为注明为“反弹时速度符号错误”。但Q07同时映射K04动量定理和K02动量的矢量性，简单更新会让两个组件一起下降；由于K04只有两次观察且后一次答错，它最终反而成为最低状态。这里已经知道合成错误的设计原因，模型仍给出偏移的优先级，直接说明Q-matrix加动态状态也不能自动解决多组件归因。教师需要回看原答、询问符号约定，或补一道只改变方向而不改变动量定理结构的区分性题。",
            "",
            "## 共同裁决",
            "",
            "1. 若只看总分，SYN-A与SYN-B的错误性质会被压平；Q-matrix才让两者分开。",
            "2. SYN-C展示了动态层保存顺序的价值，但后段答对究竟来自学习、题型变化还是猜测，本数据无法区分。",
            "3. 多组件题会同时更新多个状态，可能把一个符号错误扩散成多个组件下降；必须回看原始作答或补区分性追问。",
            "4. 本轮最有价值的不是某个概率，而是所有节点、边、映射、参数和更新都可以被教师追溯与否决。",
            "",
            "## 不得外推",
            "",
            "- 不得用三组合成轨迹评价任何模型准确率；",
            "- 不得把终值设为学生成绩或永久标签；",
            "- 不得宣称知识图谱、Q-matrix或BKT提高了学习效果；",
            "- 未完成双教师独立标注前，不称当前图谱或Q-matrix为正式金标准。",
            "",
        ]
    )
    return "\n".join(lines)


def table_html(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(value)}</th>" for value in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f"<div class='table-wrap'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def build_html(bundle: dict[str, list[dict[str, str]]], final_states: dict[str, dict[str, float]]) -> str:
    names = {row["kc_id"]: row["name"] for row in bundle["components"]}
    labels = {row["student_id"]: row["student_label"] for row in bundle["responses"]}
    evidence = component_evidence(bundle)
    score_by_student: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in bundle["responses"]:
        score_by_student[row["student_id"]][0] += int(row["correct"])
        score_by_student[row["student_id"]][1] += 1

    state_cards = []
    for student_id in sorted(final_states):
        ordered = sorted(final_states[student_id].items(), key=lambda item: item[1])
        state_rows = []
        for kc_id, state in ordered:
            correct, total = evidence[student_id].get(kc_id, (0, 0))
            state_rows.append([f"{kc_id} {names[kc_id]}", f"{correct}/{total}", f"{state:.3f}"])
        score = score_by_student[student_id]
        state_cards.append(
            f"<section class='student'><h3>{html.escape(student_id)}　{html.escape(labels[student_id])}</h3>"
            f"<p class='score'>章节总分：{score[0]}/{score[1]}</p>"
            + table_html(["组件", "Q-matrix证据", "演示状态终值"], state_rows)
            + "<p class='boundary'>表中概率是演示参数下的诊断假设，只用于决定先回看哪些原始作答。</p></section>"
        )

    edge_rows = [
        [row["edge_id"], f"{row['from_kc']} {names[row['from_kc']]}", f"{row['to_kc']} {names[row['to_kc']]}", row["relation"], row["rationale"]]
        for row in bundle["edges"]
    ]
    rejected_rows = [
        [row["candidate_id"], f"{row['from_kc']} → {row['to_kc']}", row["rejection_reason"]]
        for row in bundle["rejected"]
    ]

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>动量与碰撞知识系统最小金标准 MVP</title>
<style>
:root{{--ink:#172033;--muted:#657089;--paper:#f4f7fb;--card:#fff;--blue:#3156d3;--cyan:#0e8a93;--amber:#b05b06;--red:#a52b2b;--line:#dce3ee}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}}
main{{max-width:1180px;margin:auto;padding:36px 22px 72px}} h1{{font-size:clamp(28px,5vw,48px);line-height:1.15;margin:.2em 0}} h2{{margin-top:2.3em}} h3{{margin-bottom:.3em}} .eyebrow{{color:var(--blue);font-weight:700;letter-spacing:.08em}} .lead{{font-size:1.15rem;max-width:850px;color:#38445c}} .warning{{background:#fff2de;border-left:5px solid var(--amber);padding:14px 18px;border-radius:8px;margin:24px 0}} .layers{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:25px 0}} .layer,.student,.panel{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:0 8px 22px #3344660d}} .layer strong{{display:block;color:var(--blue);font-size:1.08rem}} .layer span{{color:var(--muted)}} .students{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}} .score{{color:var(--blue);font-weight:700}} .boundary{{font-size:.9rem;color:var(--muted)}} .table-wrap{{overflow:auto}} table{{width:100%;border-collapse:collapse;font-size:.92rem}} th,td{{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;vertical-align:top}} th{{background:#eef2ff;color:#283e85;position:sticky;top:0}} .two{{display:grid;grid-template-columns:1.4fr 1fr;gap:16px}} .bad{{color:var(--red)}} .good{{color:var(--cyan)}} code{{background:#e9eef7;padding:.12em .35em;border-radius:4px}} a{{color:var(--blue)}}
@media(max-width:900px){{.layers,.students,.two{{grid-template-columns:1fr}}}}
</style>
</head>
<body><main>
<p class="eyebrow">B0 · P0-2 · 离线最小验证</p>
<h1>一张“知识图谱”不能同时充当地图、测量仪和导航员</h1>
<p class="lead">这个自建样机把章节标签、内容图谱、Q-matrix和简单动态状态拆开，让教师看见每一层新增了什么，也能追溯它在哪里可能误导判断。</p>
<div class="warning"><strong>证据边界：</strong>20道题全部自编，3组学生轨迹全部合成，参数人为设定，图谱尚未经第二位教师审定。页面不呈现真实学生结论。</div>
<section class="layers">
  <div class="layer"><strong>1 章节标签</strong><span>只给出单元归属与总分。</span></div>
  <div class="layer"><strong>2 内容图谱</strong><span>给出候选前置关系，但没有学生证据。</span></div>
  <div class="layer"><strong>3 Q-matrix</strong><span>声明每道题测什么，同时暴露多组件归因。</span></div>
  <div class="layer"><strong>4 动态状态</strong><span>保存作答顺序，生成可更新的诊断假设。</span></div>
</section>
<h2>三组合成轨迹：相近分数，缺口并不相同</h2>
<div class="students">{''.join(state_cards)}</div>
<section class="warning"><strong>归因反例：</strong>SYN-A的Q07被设计为“反弹符号错误”，但多组件映射使K04动量定理也同步下降，并被状态排序放在最前。即使已知合成错误原因，简单模型仍会误导优先级；必须回看原始作答或补区分性追问。</section>
<h2>内容图谱：采用的边和否决的边都要留下</h2>
<div class="two"><section class="panel"><h3 class="good">13条候选依赖边</h3>{table_html(['ID','前置','目标','关系','理由'],edge_rows)}</section><section class="panel"><h3 class="bad">3条明确否决边</h3>{table_html(['ID','候选边','否决理由'],rejected_rows)}</section></div>
<h2>教师仍需做的六次裁决</h2>
<ol class="panel"><li>节点粒度是否适合真实课程；</li><li>边是物理必要关系还是教学顺序偏好；</li><li>题目映射是否遗漏替代解法；</li><li>一次错误应该归因到哪里；</li><li>下一步应追问、复测、讲解还是观察；</li><li>何时停止相信聚合结果并回到原始作答。</li></ol>
<h2>本地文件</h2>
<p><a href="../README.md">README</a> · <a href="../教师裁决与证据边界.md">教师裁决与证据边界</a> · <a href="comparison.md">四层比较Markdown</a> · <a href="student_state_updates.csv">逐次状态更新CSV</a></p>
<p class="boundary">本页由<code>python3 src/build_mvp.py</code>从CSV事实源生成；不调用网络或外部模型。</p>
</main></body></html>"""


def main() -> None:
    GENERATED.mkdir(exist_ok=True)
    bundle = load_bundle()
    updates, final_states = build_states(bundle)
    update_fields = [
        "student_id", "student_label", "sequence", "question_id", "kc_id", "role", "correct",
        "prior", "posterior_before_learning", "state_after_learning", "data_identity",
    ]
    write_csv(GENERATED / "student_state_updates.csv", updates, update_fields)
    (GENERATED / "comparison.md").write_text(build_comparison(bundle, final_states), encoding="utf-8")
    (GENERATED / "index.html").write_text(build_html(bundle, final_states), encoding="utf-8")
    print(
        f"已生成：{len(bundle['components'])}个组件，{len(bundle['questions'])}道自编题，"
        f"{len(bundle['mappings'])}条Q-matrix映射，{len(bundle['responses'])}条合成作答，"
        f"{len(updates)}条状态更新。"
    )


if __name__ == "__main__":
    main()
