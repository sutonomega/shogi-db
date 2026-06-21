"""
悪手理由解説プロンプトを組み立てる。
"""

from __future__ import annotations


def build_blunder_explanation_materials(
    game: dict,
    previous_position: dict,
    current_position: dict,
) -> dict:
    eval_before = previous_position.get("eval")
    eval_after = current_position.get("eval")
    eval_delta = _eval_delta(
        current_position["move_number"],
        eval_before,
        eval_after,
    )
    materials = {
        "game": game,
        "move_number": current_position["move_number"],
        "move": current_position.get("move"),
        "sfen_before": previous_position["sfen"],
        "sfen_after": current_position["sfen"],
        "eval_before": eval_before,
        "eval_after": eval_after,
        "eval_delta": eval_delta,
        "loss": abs(eval_delta) if eval_delta is not None and eval_delta < 0 else None,
        "best_move": current_position.get("best_move"),
        "pv": current_position.get("pv"),
        "candidates": current_position.get("candidates", []),
    }
    materials["missing"] = _missing_fields(materials)
    return materials


def build_blunder_explanation_prompt(materials: dict) -> str:
    missing = materials.get("missing", [])
    missing_text = "なし" if not missing else "、".join(missing)
    candidates_text = _format_candidates(materials.get("candidates", []))

    return "\n".join(
        [
            "あなたは将棋の悪手理由を検討するアシスタントです。",
            "次の悪手候補について、与えられた前後局面・評価値・候補手・読み筋だけを根拠に日本語で解説してください。",
            "評価値が下がった理由は、根拠と推測を分けて説明してください。",
            "",
            "条件:",
            "- 確定情報と推測を混ぜない",
            "- 根拠に使った入力項目を明示する",
            "- 与えられていない読みや評価を創作しない",
            "- 候補手や読み筋が不足している場合は、不足している前提を明記する",
            "- 次に同じミスを避けるための改善案を含める",
            "",
            "確定情報:",
            f"- 対局: {materials['game'].get('black')} vs {materials['game'].get('white')}",
            f"- 手数: {materials['move_number']}",
            f"- 実戦手: {_format_nullable(materials.get('move'))}",
            f"- 着手前SFEN: {materials['sfen_before']}",
            f"- 着手後SFEN: {materials['sfen_after']}",
            f"- 着手前評価値: {_format_eval(materials.get('eval_before'))}",
            f"- 着手後評価値: {_format_eval(materials.get('eval_after'))}",
            f"- 評価値変化: {_format_eval(materials.get('eval_delta'))}",
            f"- 損失: {_format_loss(materials.get('loss'))}",
            f"- 最善手: {_format_nullable(materials.get('best_move'))}",
            f"- 読み筋: {_format_nullable(materials.get('pv'))}",
            f"- 候補手: {candidates_text}",
            f"- 不足項目: {missing_text}",
            "",
            "出力:",
            "1. 確定情報の要約",
            "2. 実戦手で評価値が下がった根拠",
            "3. 推測として考えられる悪手理由",
            "4. 候補手・読み筋から見える改善案",
            "5. 不足情報と注意点",
        ]
    )


def _eval_delta(move_number: int, eval_before: int | None, eval_after: int | None) -> int | None:
    if eval_before is None or eval_after is None:
        return None
    if move_number % 2 == 1:
        return eval_after - eval_before
    return eval_before - eval_after


def _missing_fields(materials: dict) -> list[str]:
    missing = []
    for key, label in (
        ("eval_before", "着手前評価値"),
        ("eval_after", "着手後評価値"),
        ("best_move", "最善手"),
        ("pv", "読み筋"),
    ):
        if materials.get(key) is None:
            missing.append(label)
    if not materials.get("candidates"):
        missing.append("候補手")
    return missing


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


def _format_candidates(candidates: list[dict]) -> str:
    if not candidates:
        return "なし"
    return "、".join(
        f"{candidate.get('move', '不明')}({_format_eval(candidate.get('eval'))})"
        for candidate in candidates
    )
