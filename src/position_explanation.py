"""
局面解説プロンプトを組み立てる。
"""

from __future__ import annotations

import shlex
import subprocess


class PositionExplanationError(RuntimeError):
    pass


def build_position_explanation_prompt(materials: dict) -> str:
    missing = materials.get("missing", [])
    missing_text = "なし" if not missing else "、".join(missing)
    candidates_text = _format_candidates(materials.get("candidates", []))
    openings_text = _format_openings(materials.get("openings", []))

    return "\n".join(
        [
            "あなたは将棋の局面を検討するアシスタントです。",
            "次の局面について、与えられた評価値・実戦手・候補手・読み筋だけを根拠に日本語で解説してください。",
            "特に評価値が悪化している場合は、なぜ悪化した可能性が高いかを、根拠と推測を分けて説明してください。",
            "",
            "条件:",
            "- 確定情報と推測を混ぜない",
            "- 根拠に使った入力項目を明示する",
            "- 与えられていない読みや評価を創作しない",
            "- 断定しすぎず、与えられた材料から分かる範囲で説明する",
            "- USI形式の手はそのまま使ってよい",
            "- 候補手や読み筋が不足している場合は、不足している前提を明記する",
            "",
            "確定情報:",
            f"- SFEN: {materials['sfen']}",
            f"- 手数: {materials['move_number']}",
            f"- 実戦手: {_format_nullable(materials.get('move'))}",
            f"- 評価値: {_format_eval(materials.get('eval'))}",
            f"- 最善手: {_format_nullable(materials.get('best_move'))}",
            f"- 読み筋: {_format_nullable(materials.get('pv'))}",
            f"- 候補手: {candidates_text}",
            f"- 自分専用定跡候補: {openings_text}",
            f"- 不足項目: {missing_text}",
            "",
            "出力:",
            "1. 確定情報の要約",
            "2. 根拠に基づく実戦手の評価",
            "3. 推測として考えられる悪化理由",
            "4. 候補手・読み筋から見える改善案",
            "5. 不足情報と注意点",
        ]
    )


def build_position_explanation_materials(
    position: dict,
    openings: list[dict],
) -> dict:
    materials = {
        "position_id": position["id"],
        "move_number": position["move_number"],
        "sfen": position["sfen"],
        "move": position["move"],
        "eval": position["eval"],
        "best_move": position["best_move"],
        "pv": position["pv"],
        "candidates": position["candidates"],
        "analyzed_at": position["analyzed_at"],
        "engine_name": position["engine_name"],
        "engine_depth": position["engine_depth"],
        "openings": openings,
    }
    materials["missing"] = _missing_fields(materials)
    return materials


def generate_position_explanation(
    prompt: str,
    *,
    llm_command: str,
    timeout: float = 60.0,
) -> str:
    if not prompt.strip():
        raise PositionExplanationError("Explanation prompt is empty")
    if not llm_command.strip():
        raise PositionExplanationError("LLM command is empty")

    try:
        process = subprocess.run(
            shlex.split(llm_command),
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except ValueError as exc:
        raise PositionExplanationError(str(exc)) from exc
    except subprocess.TimeoutExpired as exc:
        raise PositionExplanationError("LLM command timed out") from exc

    if process.returncode != 0:
        stderr = process.stderr.strip()
        message = stderr or f"LLM command failed with exit code {process.returncode}"
        raise PositionExplanationError(message)

    explanation = process.stdout.strip()
    if not explanation:
        raise PositionExplanationError("LLM command returned empty output")
    return explanation


def _missing_fields(materials: dict) -> list[str]:
    missing = []
    for key, label in (
        ("eval", "評価値"),
        ("best_move", "最善手"),
        ("pv", "読み筋"),
    ):
        if materials.get(key) is None:
            missing.append(label)
    if not materials.get("candidates"):
        missing.append("候補手")
    if not materials.get("openings"):
        missing.append("自分専用定跡候補")
    return missing


def _format_eval(value: int | None) -> str:
    if value is None:
        return "なし"
    return f"{value:+d}"


def _format_nullable(value: str | None) -> str:
    return value if value else "なし"


def _format_candidates(candidates: list[dict]) -> str:
    if not candidates:
        return "なし"
    return "、".join(
        f"{candidate.get('move', '不明')}({_format_eval(candidate.get('eval'))})"
        for candidate in candidates
    )


def _format_openings(openings: list[dict]) -> str:
    if not openings:
        return "なし"
    return "、".join(
        (
            f"{opening.get('move', '不明')}"
            f"(出現{opening.get('count', 0)}回"
            f"、平均評価値{_format_eval(opening.get('avg_eval'))})"
        )
        for opening in openings
    )
