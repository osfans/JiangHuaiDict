#!/usr/bin/env python3
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parent
SOURCE_XLSX = ROOT / "淮語詞典230301initial.xlsx"
OUTPUT_MD = ROOT / "900词表.md"


def as_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def build_wordlist() -> list[str]:
    wb = load_workbook(SOURCE_XLSX, data_only=True)
    ws = wb.worksheets[1]

    max_col = ws.max_column
    max_row = ws.max_row

    # 从第1行读取地名表头，C列及以后为各地解释列
    place_headers = {
        col: as_text(ws.cell(row=1, column=col).value) for col in range(3, max_col + 1)
    }

    lines: list[str] = [f"# {SOURCE_XLSX.name}", ""]

    for row in range(2, max_row + 1):
        head = as_text(ws.cell(row=row, column=2).value)
        if not head:
            continue

        merged_parts: list[tuple[list[str], str]] = []
        for col in range(3, max_col + 1):
            explanation = as_text(ws.cell(row=row, column=col).value)
            if not explanation or explanation == "/":
                continue
            place = place_headers.get(col, "").strip("（府城）") or f"第{col}列"

            # 若当前列解释与前一列一致，则合并地名标签
            if merged_parts and merged_parts[-1][1] == explanation:
                merged_parts[-1][0].append(place)
            else:
                merged_parts.append(([place], explanation))

        if not merged_parts:
            # 无任何解释则跳过
            continue

        parts = [f"{''.join(f'〔{p}〕' for p in places)}{exp}" for places, exp in merged_parts]
        lines.append(f"【{head}】{''.join(parts)}")

    return lines


def main() -> None:
    lines = build_wordlist()
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已生成: {OUTPUT_MD}")
    print(f"词条数: {max(len(lines) - 1, 0)}")


if __name__ == "__main__":
    main()
