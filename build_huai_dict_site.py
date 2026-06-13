#!/usr/bin/env python3
import json
import re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "dist" / "index.html"
TEMPLATE = ROOT / "huai_dict_template.html"

HEAD_RE = re.compile(r"^(?:【[^】]+】)+")
WORD_RE = re.compile(r"【([^】]+)】")
PINYIN_RE = re.compile(r"^([a-z][a-z0-9 ,;/\-]*)")


def render_template(template_path: Path, replacements: dict[str, str]) -> str:
    tpl = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        tpl = tpl.replace(key, value)
    return tpl

def strip_reference_prefix(line: str) -> str:
    s = (line or "").strip()
    s = re.sub(r"^\s*#+\s*", "", s)
    s = re.sub(r"^\s*[-*+]\s*", "", s)
    s = re.sub(r"^\s*\d+[.)、]\s*", "", s)
    s = re.sub(r"^\s*(?:参考资料|书目|资料来源)\s*[:：]\s*", "", s)
    return s.strip()

def norm_line(line):
    return line.replace(r"\\u3000", " ").replace("（", "(").replace("）", ")").replace("～", "~").replace("：", ":").replace("；", ";").replace("，", ",").replace("！", "!").replace("？", "?").strip()


def clean_line(line: str) -> str:
    line = norm_line(line)
    if line.startswith("- ") or line.startswith("1. "):
        line = line[2:].strip()
        if "【" not in line: line = f"【{line}】"
    return line.strip()


def parse_md(line: str, dialect: str):
    line = clean_line(line)
    if not line:
        return None

    m = HEAD_RE.match(line)
    if not m:
        return None

    head_block = m.group(0)
    heads = [w.strip().strip("。") for w in WORD_RE.findall(head_block) if w.strip()]
    if not heads:
        return None

    rest = line[m.end():].strip()
    pinyins = [p.strip() for p in PINYIN_RE.findall(rest) if p.strip()]

    # 释义里去掉拼音片段，保留其他信息
    explanation = PINYIN_RE.sub("", rest)
    explanation = re.sub(r"\s+", " ", explanation).strip(" -:\u3000")

    return {
        "dialect": dialect,
        "heads": heads,
        "pinyin": pinyins,
        "explanation": explanation,
    }

def parse_tsv(line: str, dialect: str):
    line = norm_line(line)
    count = line.count("\t")
    if count == 0: return None
    if count == 1:
        heads, pinyins = line.split("\t")
        explanation = ""
    else:
        heads, pinyins, explanation = line.split("\t")[:3]
    return {
        "dialect": dialect,
        "heads": [heads],
        "pinyin": [pinyins],
        "explanation": explanation,
    }

def load_entries():
    dialects = []
    entries = []
    references = {}
    uniq = set()
    for md_path in sorted(ROOT.glob("[0-9]*.*")):
        is_tsv = md_path.suffix == ".tsv"
        dialect = md_path.stem.lstrip("0123456789")
        dialects.append(dialect)
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()

        first_line = lines[0].strip() if lines else ""
        book = strip_reference_prefix(first_line)
        second_line = lines[1].strip() if len(lines) > 1 else ""
        author = second_line if second_line else ""
        if book or author:
            references[dialect] = {"book": book, "author": author}

        for raw_line in lines:
            groups = re.findall(r"`([^`]+)`", raw_line)
            inline_groups = len(groups) >= 1
            if not inline_groups:
                groups = [raw_line]
            for group in groups:
                if inline_groups and not HEAD_RE.match(group):
                    group = f"【{group}】"
                if is_tsv:
                    entry = parse_tsv(group, dialect)
                else:
                    entry = parse_md(group, dialect)
                if entry and (entry["explanation"] or len(entry["heads"][0]) != 1):
                    if str(entry) not in uniq:
                        entries.append(entry)
                    uniq.add(str(entry))
    return dialects, entries, references


def build_html(dialects, entries, references):
    dialect_idx = {d: i for i, d in enumerate(dialects)}
    # 紧凑编码: [方言索引, 词头数组, 拼音数组, 释义]
    records = [
        [dialect_idx[e["dialect"]], e["heads"], e["pinyin"], e["explanation"]]
        for e in entries
    ]
    refs_json = json.dumps(references, ensure_ascii=False, separators=(",", ":"))
    dialects_json = json.dumps(dialects, ensure_ascii=False, separators=(",", ":"))
    data_json = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    if len(sys.argv) > 1:
        json.dump(records, open("dump.json", "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
    total = len(entries)
    tz_utc8 = timezone(timedelta(hours=8))
    updated_at = datetime.now(tz_utc8).strftime("%Y年%m月%d号")
    return render_template(
        TEMPLATE,
        {
            "__TOTAL__": str(total),
            "__UPDATED_AT__": updated_at,
            "__REFS_JSON__": refs_json,
            "__DIALECTS_JSON__": dialects_json,
            "__DATA_JSON__": data_json,
        },
    )


def main():
    dialects, entries, references = load_entries()
    html = build_html(dialects, entries, references)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8", newline="\n")
    size_bytes = OUTPUT.stat().st_size
    print(f"生成完成: {OUTPUT}")
    print(f"词条数: {len(entries)}")
    print(f"HTML大小: {size_bytes} bytes ({size_bytes / (1024 * 1024):.2f} MB)")

if __name__ == "__main__":
    main()
