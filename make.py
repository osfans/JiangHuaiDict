#!/usr/bin/env python3
import json
import re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from opencc import OpenCC
cc = OpenCC('t2s')

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "docs" / "index.html"
TEMPLATE = ROOT / "huai_dict_template.html"

HEAD_RE = re.compile(r"^(?:【[^】]+】)+")
WORD_RE = re.compile(r"【([^】]+)】")
PINYIN_RE = re.compile(r"^([a-z\[][a-z0-9 ,;/\-\[\]]*)")


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
    line = line.replace(r"\\u3000", " ").replace("（", "(").replace("）", ")").replace("～", "~").replace("：", ":").replace("；", ";").replace("，", ",").replace("！", "!").replace("？", "?").strip()
    line = cc.convert(line)
    return line


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

    cursor = 0
    heads = []
    pinyins = []

    # 兼容“【词】拼音【词】拼音释义”这类连续多段格式。
    while cursor < len(line):
        m_head = HEAD_RE.match(line[cursor:])
        if not m_head:
            break

        head_block = m_head.group(0)
        heads.extend([w.strip().strip("。") for w in WORD_RE.findall(head_block) if w.strip()])
        cursor += m_head.end()

        while cursor < len(line) and line[cursor].isspace():
            cursor += 1

        m_py = PINYIN_RE.match(line[cursor:])
        if m_py and m_py.group(1).strip():
            p = re.sub("(\\d) ([a-z])", "\\1\\2", m_py.group(1).strip())
            pinyins.append(p)
            cursor += m_py.end()

        while cursor < len(line) and line[cursor].isspace():
            cursor += 1

        if cursor >= len(line) or line[cursor] != "【":
            break

    if not heads:
        return None

    rest = line[cursor:].strip()
    explanation = rest
    explanation = re.sub(r"\s+", " ", explanation).strip(" -:\u3000")
    explanation = re.sub(r"^([名动形代副量叹连介助语拟])[容气声]?词[ ,]?", "〈\\1〉", explanation)

    return {
        "dialect": dialect,
        "heads": heads,
        "pinyin": pinyins,
        "explanation": explanation,
    }

def parse_tsv(line: str, dialect: str):
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
    seen_dialects = set()
    entries = []
    references = {}
    dialect_entry_counts = {}
    uniq = set()

    def add_dialect(name: str):
        n = (name or '').strip()
        if not n or n in seen_dialects:
            return
        seen_dialects.add(n)
        dialects.append(n)
        dialect_entry_counts.setdefault(n, 0)

    for md_path in sorted(ROOT.glob("[0-9]*.*")):
        is_tsv = md_path.suffix == ".tsv"
        dialect = md_path.stem.lstrip("0123456789")
        add_dialect(dialect)
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()

        first_line = lines[0].strip() if lines else ""
        book = strip_reference_prefix(first_line)
        second_line = lines[1].strip() if len(lines) > 1 else ""
        for tag in re.findall(r"〔([^〕]+)〕", second_line):
            add_dialect(tag)
        author = second_line if second_line else ""
        if book or author:
            references[dialect] = {"book": book, "author": author}

        for raw_line in lines:
            raw_line = norm_line(raw_line)
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
                        dialect_entry_counts[dialect] = dialect_entry_counts.get(dialect, 0) + 1
                    uniq.add(str(entry))

    for dialect in dialects:
        count = dialect_entry_counts.get(dialect, 0)
        if dialect in references or count > 0:
            meta = references.setdefault(dialect, {})
            meta["count"] = count
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
    if len(sys.argv) == 1:
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
