"""single_question_cli.py — 单问脚本共享 CLI 辅助器。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from eight_questions_domain import (
    EightQuestionAnswer,
    SOURCE_LABEL,
    default_db_path,
    now_iso,
    sanitize_excerpt,
)


def _default_output_dir(question_key: str, ts_code: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M")
    return Path("logs") / question_key / ts_code / ts


def _sanitize_answer(answer: EightQuestionAnswer) -> EightQuestionAnswer:
    answer.finalize_status()
    try:
        answer.validate()
    except ValueError as exc:
        answer.status = "insufficient-evidence"
        answer.rating = None
        answer.notes.append(f"validate 失败: {exc}")
    return answer


def build_single_question_payload(
    ts_code: str,
    as_of_date: str,
    answer: EightQuestionAnswer,
) -> dict[str, object]:
    return {
        "ts_code": ts_code,
        "as_of_date": as_of_date,
        "generated_at": now_iso(),
        "question_id": answer.question_id,
        "question_title": answer.question_title,
        "answer": answer.to_payload(),
    }


def render_single_question_markdown(
    ts_code: str,
    as_of_date: str,
    answer: EightQuestionAnswer,
) -> str:
    lines: list[str] = []
    lines.append(f"# 八问单问调研 · Q{answer.question_id} {answer.question_title}")
    lines.append("")
    lines.append(f"- 股票代码: {ts_code}")
    lines.append(f"- 分析日期: {as_of_date}")
    lines.append(f"- 生成时间: {now_iso()}")
    lines.append(
        f"- 状态: `{answer.status}` · 评级: `{answer.rating}` · 加权: `{answer.weighted_rating()}`"
    )
    lines.append("")

    if answer.answer:
        lines.append("## 回答")
        lines.append("")
        lines.append(answer.answer)
        lines.append("")

    if answer.human_in_loop_requests:
        lines.append("## 需要人工介入")
        lines.append("")
        for request in answer.human_in_loop_requests:
            lines.append(f"- {request}")
        lines.append("")

    if answer.critical_gaps:
        lines.append("## 关键证据缺口")
        lines.append("")
        for gap in answer.critical_gaps:
            lines.append(f"- {gap}")
        lines.append("")

    if answer.rating_signals:
        lines.append("## 评级依据")
        lines.append("")
        for signal in answer.rating_signals:
            lines.append(f"- {signal}")
        lines.append("")

    if answer.missing_inputs:
        lines.append("## 待补输入")
        lines.append("")
        for missing in answer.missing_inputs:
            lines.append(f"- {missing}")
        lines.append("")

    if answer.notes:
        lines.append("## 备注")
        lines.append("")
        for note in answer.notes:
            lines.append(f"- {note}")
        lines.append("")

    lines.append("## 证据")
    lines.append("")
    if answer.evidence:
        lines.append("| # | 来源类型 | 标题 / 摘录 | URL |")
        lines.append("| - | --- | --- | --- |")
        for index, evidence in enumerate(answer.evidence, 1):
            label = SOURCE_LABEL[evidence.source_type]
            title = sanitize_excerpt(evidence.title or "", limit=200)
            excerpt = sanitize_excerpt(evidence.excerpt)
            lines.append(
                f"| {index} | {label} | {title} — {excerpt} | <{evidence.source_url}> |"
            )
    else:
        lines.append("_无证据。_")
    lines.append("")
    return "\n".join(lines)


def run_single_question_cli(
    *,
    question_key: str,
    answer_fn: Callable[..., EightQuestionAnswer],
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=f"八问单问运行器 ({question_key})")
    parser.add_argument("--ts-code", required=True)
    parser.add_argument("--duckdb-path", type=Path, default=default_db_path())
    parser.add_argument("--as-of-date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--format", choices=["json", "markdown", "both"], default="both")
    args = parser.parse_args(argv)

    output_dir = args.output_dir or _default_output_dir(question_key, args.ts_code)
    output_dir.mkdir(parents=True, exist_ok=True)

    answer = _sanitize_answer(answer_fn(ts_code=args.ts_code, db_path=args.duckdb_path))
    payload = build_single_question_payload(args.ts_code, args.as_of_date, answer)

    if args.format in ("json", "both"):
        (output_dir / f"{question_key}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if args.format in ("markdown", "both"):
        (output_dir / f"{question_key}.md").write_text(
            render_single_question_markdown(args.ts_code, args.as_of_date, answer),
            encoding="utf-8",
        )

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0