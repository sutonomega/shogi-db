"""
局面解説プロンプトを組み立てる。
"""

from __future__ import annotations
from .japanese_move import (
    format_usi_move_with_japanese,
    format_usi_pv_with_japanese,
    usi_to_japanese_move,
)

import shlex
import subprocess
import re


class PositionExplanationError(RuntimeError):
    pass

ANSI_ESCAPE_PATTERN = re.compile(
    r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
)

def _format_move(materials: dict, move: str | None) -> str:
    return _format_move_from_sfen(
        materials.get("sfen"),
        move,
    )

def strip_ansi_escape(text: str) -> str:
    return ANSI_ESCAPE_PATTERN.sub("", text)

def _format_move_from_sfen(sfen: str | None, move: str | None) -> str:
    if not move:
        return "なし"

    if not sfen:
        return move

    try:
        japanese = usi_to_japanese_move(
            sfen,
            move,
        )
    except Exception:
        return move

    if japanese.endswith("?"):
        return move

    return f"{move}（{japanese}）"

def _format_pv(materials: dict) -> str:
    pv = materials.get("pv")
    if not pv:
        return "なし"

    try:
        formatted = format_usi_pv_with_japanese(
            materials["sfen"],
            pv,
        )
    except Exception:
        return pv

    return formatted or pv

def build_position_explanation_prompt(materials: dict) -> str:
    missing = materials.get("missing", [])
    missing_text = "なし" if not missing else "、".join(missing)
    candidates_text = _format_candidates(materials.get("candidates", []),materials,)
    openings_text = _format_openings(materials.get("openings", []),materials,)
    previous = materials.get("previous_position")
    previous_sfen = previous.get("sfen") if previous else None

    return "\n".join(
        [
            "あなたは将棋の局面を検討するアシスタントです。",
            "次の局面について、与えられた前後局面・評価値・実戦手・候補手・読み筋だけを根拠に日本語で解説してください。",
            "特に評価値が悪化している場合は、なぜ悪化した可能性が高いかを、根拠と推測を分けて説明してください。",
            "",
            "条件:",
            "- 確定情報と推測を混ぜない",
            "- 根拠に使った入力項目を明示する",
            "- 与えられていない読みや評価を創作しない",
            "- 断定しすぎず、与えられた材料から分かる範囲で説明する",
            "- 評価値低下が小さい場合は、悪化理由を無理に作らない",
            "- 候補手上位との差は同一解析結果内の参考値として扱い、単独で理由を断定しない",
            "- USI形式の手はそのまま使ってよい",
            "- 候補手や読み筋が不足している場合は、不足している前提を明記する",
            f"- 解説方針: {materials['explanation_policy']}",
            "",
            "確定情報:",
            f"- SFEN: {materials['sfen']}",
            f"- 直前SFEN: {_format_nullable(previous_sfen)}",
            f"- 手数: {materials['move_number']}",
            f"- 実戦手: {_format_nullable(materials.get('move'))}",
            f"- 着手前評価値: {_format_eval(materials.get('eval_before'))}",
            f"- 評価値: {_format_eval(materials.get('eval'))}",
            f"- 評価値変化: {_format_eval(materials.get('eval_delta'))}",
            f"- 損失: {_format_loss(materials.get('loss'))}",
            f"- 解説粒度: {materials['severity']}",
            f"- 最善手: {_format_move_from_sfen(materials.get('sfen'), materials.get('best_move'))}",
            f"- 候補手上位評価値: {_format_eval(materials.get('top_candidate_eval'))}",
            f"- 候補手上位との差: {_format_eval(materials.get('top_candidate_eval_gap'))}",
            f"- 読み筋: {_format_pv(materials)}",
            f"- 候補手: {candidates_text}",
            f"- 定跡候補: {openings_text}",
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
    previous_position: dict | None = None,
) -> dict:
    eval_before = previous_position.get("eval") if previous_position else None
    eval_after = position.get("eval")
    eval_delta = _eval_delta(position["move_number"], eval_before, eval_after)
    top_candidate = _top_candidate(position.get("candidates", []))
    top_candidate_eval = top_candidate.get("eval") if top_candidate else None
    top_candidate_eval_gap = _eval_gap(top_candidate_eval, eval_after)
    loss = abs(eval_delta) if eval_delta is not None and eval_delta < 0 else None
    materials = {
        "position_id": position["id"],
        "move_number": position["move_number"],
        "sfen": position["sfen"],
        "previous_position": previous_position,
        "move": position["move"],
        "eval_before": eval_before,
        "eval": position["eval"],
        "eval_delta": eval_delta,
        "loss": loss,
        "best_move": position["best_move"],
        "top_candidate_eval": top_candidate_eval,
        "top_candidate_eval_gap": top_candidate_eval_gap,
        "pv": position["pv"],
        "candidates": position["candidates"],
        "analyzed_at": position["analyzed_at"],
        "engine_name": position["engine_name"],
        "engine_depth": position["engine_depth"],
        "openings": openings,
    }
    materials["severity"] = _severity(materials["loss"])
    materials["explanation_policy"] = _explanation_policy(materials["severity"])
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
        stderr = strip_ansi_escape(process.stderr).strip()
        message = stderr or f"LLM command failed with exit code {process.returncode}"
        raise PositionExplanationError(message)

    explanation = strip_ansi_escape(process.stdout).strip()
    if not explanation:
        raise PositionExplanationError("LLM command returned empty output")
    return explanation


def _missing_fields(materials: dict) -> list[str]:
    missing = []
    for key, label in (
        ("previous_position", "直前局面"),
        ("eval_before", "着手前評価値"),
        ("eval", "評価値"),
        ("best_move", "最善手"),
        ("pv", "読み筋"),
    ):
        if materials.get(key) is None:
            missing.append(label)
    if not materials.get("candidates"):
        missing.append("候補手")
    if not materials.get("openings"):
        missing.append("定跡候補")
    return missing


def _eval_delta(move_number: int, eval_before: int | None, eval_after: int | None) -> int | None:
    if eval_before is None or eval_after is None:
        return None
    if move_number % 2 == 1:
        return eval_after - eval_before
    return eval_before - eval_after


def _eval_gap(best_eval: int | None, eval_after: int | None) -> int | None:
    if best_eval is None or eval_after is None:
        return None
    return best_eval - eval_after


def _top_candidate(candidates: list[dict]) -> dict | None:
    if not candidates:
        return None
    return candidates[0]


def _severity(loss: int | None) -> str:
    if loss is None:
        return "unknown"
    if loss < 200:
        return "none"
    if loss < 500:
        return "brief"
    return "detailed"


def _explanation_policy(severity: str) -> str:
    if severity == "none":
        return "200点未満の軽微な変化のため、悪化理由を無理に作らない"
    if severity == "brief":
        return "200点以上500点未満の低下として、根拠に限定した簡易解説にする"
    if severity == "detailed":
        return "500点以上の低下として、候補手・読み筋を使って詳細に解説する"
    return "評価値変化が不明なため、不足情報を明示して断定を避ける"


def _format_eval(value: int | None) -> str:
    if value is None:
        return "なし"
    return f"{value:+d}"


def _format_loss(value: int | None) -> str:
    if value is None:
        return "なし"
    return str(value)


def _format_nullable(value: str | None) -> str:
    return value if value else "なし"


def _format_candidates(
    candidates: list[dict],
    materials: dict,
) -> str:
    if not candidates:
        return "なし"

    return "、".join(
        (
            f"{_format_move(materials, candidate.get('move'))}"
            f"({_format_eval(candidate.get('eval'))})"
        )
        for candidate in candidates
    )


def _format_openings(openings: list[dict],materials: dict,) -> str:
    if not openings:
        return "なし"

    return "、".join(
        (
            f"{_format_move(materials, opening.get('move'))}"
            f"(出現{opening.get('count', 0)}回"
            f"、平均評価値{_format_eval(opening.get('avg_eval'))})"
        )
        for opening in openings
    )
