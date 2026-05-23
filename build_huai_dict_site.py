#!/usr/bin/env python3
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "dist" / "index.html"
TEMPLATE = ROOT / "huai_dict_template.html"

HEAD_RE = re.compile(r"^(?:【[^】]+】)+")
WORD_RE = re.compile(r"【([^】]+)】")
PINYIN_RE = re.compile(r"`([^`]+)`")


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
  s = re.sub(r"^\s*(?:参考书目|书目|资料来源)\s*[:：]\s*", "", s)
  return s.strip()

def dialect_chip_escape(dialect: str) -> str:
    return re.sub(r"(\d+)$", "<small>\\1</small>", dialect)

def dialect_chip_class(dialect: str) -> str:
    name = re.sub(r"\d+$", "", dialect)
    acc = 0
    for i, ch in enumerate(name):
        acc = (acc + ord(ch) * (i + 1)) % 8
    return f"c{acc}"

def clean_line(line: str) -> str:
    # 按要求忽略所有〓符号
    line = line.replace("〓", "")
    line = line.replace(r"\\u3000", " ")
    return line.strip()


def parse_entry(line: str, dialect: str):
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

    # 释义里去掉反引号拼音片段，保留其他信息
    explanation = PINYIN_RE.sub("", rest)
    explanation = re.sub(r"\s+", " ", explanation).strip(" -:\u3000")

    return {
        "dialect": dialect,
        "heads": heads,
        "pinyin": pinyins,
        "explanation": explanation,
    }


def load_entries():
    dialects = []
    entries = []
    references = {}
    uniq = set()
    for md_path in sorted(ROOT.glob("*.md")):
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
            entry = parse_entry(raw_line, dialect)
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
    dialects_json = json.dumps(dialects, ensure_ascii=False, separators=(",", ":"))
    data_json = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    total = len(entries)
    tz_utc8 = timezone(timedelta(hours=8))
    updated_at = datetime.now(tz_utc8).strftime("%Y年%m月%d号")
    ref_rows = []
    for d in list(references):
      book = references[d].get("book", "")
      author = references[d].get("author", "")
      chip_class = dialect_chip_class(d)
      author_html = (
        f'<span class="ref-author">（{html.escape(author)}）</span>' if author else ""
      )
      ref_rows.append(
        f'<li><span class="chip {chip_class}">{dialect_chip_escape(html.escape(d))}</span><span class="ref-sep"> </span><span class="ref-book">{html.escape(book)}</span>{author_html}</li>'
      )
    refs_html = "\n".join(ref_rows) if ref_rows else '<li>暂无参考资料信息</li>'
    return render_template(
            TEMPLATE,
            {
                    "__TOTAL__": str(total),
                    "__UPDATED_AT__": updated_at,
                    "__REFS_HTML__": refs_html,
                    "__DIALECTS_JSON__": dialects_json,
                    "__DATA_JSON__": data_json,
            },
    )


def main():
    dialects, entries, references = load_entries()
    html = build_html(dialects, entries, references)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    size_bytes = OUTPUT.stat().st_size
    print(f"生成完成: {OUTPUT}")
    print(f"词条数: {len(entries)}")
    print(f"HTML大小: {size_bytes} bytes ({size_bytes / (1024 * 1024):.2f} MB)")


if __name__ == "__main__":
    main()
