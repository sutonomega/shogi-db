"""
定跡比較プロンプトを組み立てる。
"""

from __future__ import annotations


def build_opening_comparison_materials(
    position: dict,
    move_frequencies: list[dict],
    openings_by_source: dict[str, list[dict]],
) -> dict:
    materials = {
        "position_id": position["id"],
        "move_number": position["move_number"],
        "sfen": position["sfen"],
        "best_move": position.get("best_move"),
        "pv": position.get("pv"),
        "engine_candidates": position.get("candidates", []),
        "move_frequencies": move_frequencies,
        "openings_by_source": openings_by_source,
    }
    materials["missing"] = _missing_fields(materials)
    return materials


def build_opening_comparison_prompt(materials: dict) -> str:
    missing = materials.get("missing", [])
    missing_text = "なし" if not missing else "、".join(missing)
    frequencies_text = _format_moves(materials.get("move_frequencies", []))
    engine_candidates_text = _format_moves(materials.get("engine_candidates", []))
    openings_text = _format_openings_by_source(materials.get("openings_by_source", {}))

    return "\n".join(
        [
            "あなたは将棋の定跡比較を行うアシスタントです。",
            "次の局面について、自分の実戦頻度手、source別の定跡候補、エンジン候補手を比較してください。",
            "与えられた材料だけを根拠にし、source ごとの違いを日本語で説明してください。",
            "",
            "条件:",
            "- 確定情報と推測を混ぜない",
            "- 根拠に使った入力項目を明示する",
            "- 与えられていない定跡や評価を創作しない",
            "- source に候補手がない場合は不足として扱う",
            "",
            "確定情報:",
            f"- SFEN: {materials['sfen']}",
            f"- 手数: {materials['move_number']}",
            f"- エンジン最善手: {_format_nullable(materials.get('best_move'))}",
            f"- エンジン読み筋: {_format_nullable(materials.get('pv'))}",
            f"- 自分の実戦頻度手: {frequencies_text}",
            f"- source別定跡候補: {openings_text}",
            f"- エンジン候補手: {engine_candidates_text}",
            f"- 不足項目: {missing_text}",
            "",
            "出力:",
            "1. 自分の実戦頻度手の要約",
            "2. source別定跡候補との違い",
            "3. エンジン候補手との違い",
            "4. 研究時に優先して確認する手",
            "5. 不足情報と注意点",
        ]
    )


def _missing_fields(materials: dict) -> list[str]:
    missing = []
    if not materials.get("move_frequencies"):
        missing.append("自分の実戦頻度手")
    if not materials.get("engine_candidates"):
        missing.append("エンジン候補手")
    if materials.get("best_move") is None:
        missing.append("エンジン最善手")
    for source, openings in materials.get("openings_by_source", {}).items():
        if not openings:
            missing.append(f"定跡候補:{source}")
    return missing


def _format_nullable(value: str | None) -> str:
    return value if value else "なし"


def _format_eval(value: int | None) -> str:
    if value is None:
        return "なし"
    return f"{value:+d}"


def _format_moves(moves: list[dict]) -> str:
    if not moves:
        return "なし"
    parts = []
    for move in moves:
        details = []
        if "count" in move:
            details.append(f"出現{move.get('count', 0)}回")
        if "ratio" in move and move.get("ratio") is not None:
            details.append(f"割合{move['ratio']:.1%}")
        eval_value = move.get("avg_eval", move.get("eval"))
        details.append(f"評価値{_format_eval(eval_value)}")
        parts.append(f"{move.get('move', '不明')}({'、'.join(details)})")
    return "、".join(parts)


def _format_openings_by_source(openings_by_source: dict[str, list[dict]]) -> str:
    if not openings_by_source:
        return "なし"
    return " / ".join(
        f"{source}: {_format_moves(openings)}"
        for source, openings in openings_by_source.items()
    )
