#!/usr/bin/env python3
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "淮语词典.html"

HEAD_RE = re.compile(r"^(?:【[^】]+】)+")
WORD_RE = re.compile(r"【([^】]+)】")
PINYIN_RE = re.compile(r"`([^`]+)`")


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
    entries = []
    uniq = set()
    for md_path in sorted(ROOT.glob("*.md")):
        dialect = md_path.stem
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        for raw_line in text.splitlines():
            entry = parse_entry(raw_line, dialect)
            if entry and (entry["explanation"] or len(entry["heads"][0]) != 1):
                if str(entry) not in uniq:
                    entries.append(entry)
                uniq.add(str(entry))
    return entries


def build_html(entries):
    dialects = sorted({e["dialect"] for e in entries})
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
    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>淮语词典</title>
  <style>
    :root {{
      --bg: #eef4ff;
      --card: #fafdff;
      --ink: #162033;
      --muted: #4b6289;
      --line: #cfe0ff;
      --brand: #1d4ed8;
      --chip: #e8f0ff;
      --chip-line: #c1d6ff;
      --chip-text: #1e40af;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Noto Sans SC", "Source Han Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 10% 0%, #dbeafe 0%, transparent 36%),
        radial-gradient(circle at 95% 20%, #bfdbfe 0%, transparent 30%),
        var(--bg);
    }}
    .wrap {{ max-width: 1100px; margin: 0 auto; padding: 24px 16px 36px; }}
    h1 {{ margin: 0 0 8px; font-size: 34px; line-height: 1.2; }}
    .sub {{ color: var(--muted); margin-bottom: 16px; }}
    .panel {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      box-shadow: 0 6px 18px rgba(0, 0, 0, 0.05);
    }}
    .controls {{ display: grid; grid-template-columns: auto 1fr 220px; gap: 10px; align-items: center; }}
    input, select {{
      height: 42px;
      border-radius: 10px;
      border: 1px solid #b8cdf8;
      background: #fff;
      color: var(--ink);
      font-size: 15px;
      padding: 0 12px;
    }}
    .check {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: var(--muted);
      font-size: 14px;
      white-space: nowrap;
      user-select: none;
    }}
    .check input {{
      width: 16px;
      height: 16px;
      margin: 0;
      padding: 0;
    }}
    .stats {{ margin: 12px 2px 8px; color: var(--muted); font-size: 14px; }}
    .list {{ display: grid; gap: 10px; }}
    .item {{
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
      background: #fff;
    }}
    .heads {{ font-size: 20px; color: #1e3a8a; margin-bottom: 6px; display: flex; flex-wrap: wrap; gap: 8px; align-items: baseline; }}
    .heads-pinyin {{ font-size: 14px; color: var(--muted); }}
    .meta {{ font-size: 13px; color: var(--muted); margin-bottom: 0; line-height: 1.75; }}
    .chip {{
      display: inline-block;
      font-size: 12px;
      background: var(--chip);
      border: 1px solid var(--chip-line);
      color: var(--chip-text);
      border-radius: 4px;
      padding: 1px 4px;
      margin-right: 2px;
    }}
    .chip.c0 {{ background: #eaf7ff; border-color: #b6def7; color: #0b5e8e; }}
    .chip.c1 {{ background: #eafaf3; border-color: #b8ebd0; color: #176b45; }}
    .chip.c2 {{ background: #fff6e8; border-color: #f1d7ac; color: #8c5b15; }}
    .chip.c3 {{ background: #fff0f4; border-color: #f1c3d2; color: #8b2d4f; }}
    .chip.c4 {{ background: #f0efff; border-color: #ccc8f7; color: #3f3aa3; }}
    .chip.c5 {{ background: #e9f8f8; border-color: #b5e3e3; color: #116e72; }}
    .chip.c6 {{ background: #fff2ea; border-color: #f3cbb8; color: #8a3f1e; }}
    .chip.c7 {{ background: #f4f7ea; border-color: #d7e1b6; color: #556b1f; }}
    .exp {{ line-height: 1.75; white-space: pre-wrap; }}
    .meta-exp {{ color: var(--ink); margin-left: 8px; }}
    .hl {{
      background: #ffe8a3;
      color: #5f3d00;
      padding: 0 2px;
      border-radius: 4px;
    }}
    .empty {{
      text-align: center;
      color: var(--muted);
      padding: 28px 0;
    }}
    @media (max-width: 760px) {{
      .controls {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>淮语词典</h1>
    <div class=\"sub\">共<span id=\"allCount\">{total}</span>个词，<span id=\"updatedAt\">{updated_at}</span>更新</div>

    <div class=\"panel\">
      <div class=\"controls\">
        <label class=\"check\" for=\"headOnly\"><input id=\"headOnly\" type=\"checkbox\" checked />仅词头</label>
        <input id=\"q\" placeholder=\"正在加载，请稍候\" disabled />
        <select id=\"dialect\"></select>

      </div>
      <div class=\"stats\" id=\"stats\"></div>
      <div class=\"list\" id=\"list\"></div>
    </div>
  </div>

  <script>
    const CHUNK_SIZE = 200;
    const DEBOUNCE_MS = 120;

    const DIALECTS = {dialects_json};
    const RAW = {data_json};
    const DATA = RAW.map(r => ({{
      dialect: DIALECTS[r[0]],
      heads: r[1] || [],
      pinyin: r[2] || [],
      explanation: r[3] || ''
    }}));
    const INDEXED = DATA.map(item => (({{
      ...item,
      headText: item.heads.join(' ').toLowerCase(),
      fullText: [
        item.heads.join(' '),
        (item.pinyin || []).join(' '),
        item.explanation || ''
      ].join(' ').toLowerCase()
    }})));

    const qEl = document.getElementById('q');
    const dialectEl = document.getElementById('dialect');
    const headOnlyEl = document.getElementById('headOnly');
    const listEl = document.getElementById('list');
    const statsEl = document.getElementById('stats');
    let currentMatches = [];
    let renderedCount = 0;
    let io = null;
    let currentQuery = '';

    const dialects = DIALECTS.slice();
    dialectEl.innerHTML = ['<option value="">全部方言</option>']
      .concat(dialects.map(d => `<option value="${{d}}">${{d}}</option>`)).join('');

    function dialectClass(dialect) {{
      let acc = 0;
      for (let i = 0; i < dialect.length; i += 1) {{
        acc = (acc + dialect.charCodeAt(i) * (i + 1)) % 8;
      }}
      return `c${{acc}}`;
    }}

    function norm(s) {{
      return (s || '').toLowerCase().trim();
    }}

    function isPinyinQuery(q) {{
      // 只包含字母、数字、空格
      return /^[a-zA-Z0-9 ]+$/.test(q.trim());
    }}

    function matchPinyin(entry, q) {{
      // q 已经 trim
      if (!q) return true;
      const segs = q.split(/\\s+/).filter(Boolean);
      if (!segs.length) return true;
      // entry.pinyin 可能为空
      if (!entry.pinyin || !entry.pinyin.length) return false;
      // 支持 ['zz1 zo5'] 这种情况，先按空格拆分所有拼音片段
      const pinyinSegs = entry.pinyin.flatMap(p => p.split(/\\s+/).filter(Boolean));
      if (segs.length > pinyinSegs.length) return false;
      for (let i = 0; i < segs.length; i++) {{
        if (!pinyinSegs[i] || !pinyinSegs[i].toLowerCase().startsWith(segs[i].toLowerCase())) {{
          return false;
        }}
      }}
      return true;
    }}

    function match(entry, q, dialect, headOnly) {{
      if (dialect && entry.dialect !== dialect) return false;
      if (!q) return true;
      if (isPinyinQuery(q)) {{
        return matchPinyin(entry, q.trim());
      }}
      const pool = headOnly ? entry.headText : entry.fullText;
      const segs = q.split(/\\s+/).filter(Boolean);
      return segs.every(seg => pool.includes(seg));
    }}

    function escapeRegExp(s) {{
      return s.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\$&');
    }}

    function highlightText(text, rawQuery) {{
      const src = String(text || '');
      const keyword = (rawQuery || '').trim();
      if (!keyword) return escapeHtml(src);

      // 多分段高亮（如 zz zo）
      const segs = keyword.split(/\\s+/).filter(Boolean);
      if (segs.length <= 1) {{
        const pattern = new RegExp(escapeRegExp(keyword), 'ig');
        let result = '';
        let last = 0;
        let matched = false;
        let m;
        while ((m = pattern.exec(src)) !== null) {{
          matched = true;
          const start = m.index;
          const end = start + m[0].length;
          result += escapeHtml(src.slice(last, start));
          result += `<mark class="hl">${{escapeHtml(src.slice(start, end))}}</mark>`;
          last = end;
        }}
        if (!matched) return escapeHtml(src);
        result += escapeHtml(src.slice(last));
        return result;
      }}
      // 多分段高亮
      let result = '';
      let last = 0;
      let matched = false;
      // 构造所有分段的正则，按长度从长到短排序
      const sortedSegs = segs.sort((a, b) => b.length - a.length);
      const pattern = new RegExp(sortedSegs.map(escapeRegExp).join('|'), 'ig');
      let m;
      while ((m = pattern.exec(src)) !== null) {{
        matched = true;
        const start = m.index;
        const end = start + m[0].length;
        result += escapeHtml(src.slice(last, start));
        result += `<mark class="hl">${{escapeHtml(src.slice(start, end))}}</mark>`;
        last = end;
      }}

      if (!matched) return escapeHtml(src);
      result += escapeHtml(src.slice(last));
      return result;
    }}

    function renderChunk(items, append = false) {{
      if (!append) {{
        listEl.innerHTML = '';
      }}
      const fragments = items.map(item => {{
        const heads = highlightText(item.heads.join(' / '), currentQuery);
        const pinyin = (item.pinyin && item.pinyin.length)
          ? `<span class="heads-pinyin">${{highlightText(item.pinyin.join(' ; '), currentQuery)}}</span>`
          : '';
        const dialect = `<span class="chip ${{dialectClass(item.dialect)}}">${{escapeHtml(item.dialect)}}</span>`;
        const hasExp = !!(item.explanation && item.explanation.trim());
        const exp = hasExp ? highlightText(item.explanation, currentQuery) : '';
        const headsTail = hasExp ? pinyin : `${{pinyin}}${{dialect}}`;
        const meta = hasExp
          ? `<div class="meta">${{dialect}}<span class="meta-exp">${{exp}}</span></div>`
          : '';
        return `
          <article class="item">
            <div class="heads"><span>${{heads}}</span>${{headsTail}}</div>
            ${{meta}}
          </article>
        `;
      }});
      if (append) {{
        listEl.insertAdjacentHTML('beforeend', fragments.join(''));
      }} else {{
        listEl.innerHTML = fragments.join('');
      }}
    }}

    function updateStats() {{
      if (!currentMatches.length) {{
        statsEl.textContent = '什么都没找到';
        return;
      }}
      if (renderedCount < currentMatches.length) {{
        statsEl.textContent = `找到 ${{currentMatches.length}} 条，已显示 ${{renderedCount}} 条`;
      }} else {{
        statsEl.textContent = `找到 ${{currentMatches.length}} 条（已全部显示）`;
      }}
    }}

    function teardownObserver() {{
      if (io) {{
        io.disconnect();
        io = null;
      }}
    }}

    function setupObserver() {{
      teardownObserver();
      if (renderedCount >= currentMatches.length) return;
      const sentinel = document.createElement('div');
      sentinel.id = 'lazySentinel';
      sentinel.className = 'empty';
      sentinel.textContent = '向下滚动以加载更多...';
      listEl.appendChild(sentinel);

      io = new IntersectionObserver((entries) => {{
        if (!entries[0] || !entries[0].isIntersecting) return;
        renderNextChunk();
      }}, {{ rootMargin: '200px 0px' }});
      io.observe(sentinel);
    }}

    function renderNextChunk(reset = false) {{
      if (reset) {{
        renderedCount = 0;
      }}
      const sentinel = document.getElementById('lazySentinel');
      if (sentinel) sentinel.remove();

      if (!currentMatches.length) {{
        teardownObserver();
        listEl.innerHTML = '<div class="empty">未找到匹配词条</div>';
        updateStats();
        return;
      }}

      const next = currentMatches.slice(renderedCount, renderedCount + CHUNK_SIZE);
      if (!next.length) {{
        teardownObserver();
        updateStats();
        return;
      }}

      renderChunk(next, renderedCount > 0);
      renderedCount += next.length;
      updateStats();
      setupObserver();
    }}

    function debounce(fn, delay) {{
      let timer = null;
      return function (...args) {{
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
      }};
    }}

    function search() {{
      const qRaw = qEl.value;
      const q = norm(qRaw);
      const dialect = dialectEl.value;
      const headOnly = !!headOnlyEl.checked;
      currentQuery = qRaw;
      currentMatches = INDEXED.filter(x => match(x, q, dialect, headOnly));
      renderNextChunk(true);
    }}

    function escapeHtml(s) {{
      return s
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/{{/g, '&#123;&#123;')
        .replace(/}}/g, '&#125;&#125;');
    }}

    function finishLoading() {{
      qEl.disabled = false;
      qEl.placeholder = '输入词头、拼音、释义开始搜索';
    }}

    const searchDebounced = debounce(search, DEBOUNCE_MS);
    qEl.addEventListener('input', searchDebounced);
    dialectEl.addEventListener('change', search);
    headOnlyEl.addEventListener('change', search);

    // Initial render loads all entries
    statsEl.textContent = '正在加载...';
    listEl.innerHTML = '<div class="empty">正在加载词条...</div>';
    finishLoading();
    search();
  </script>
</body>
</html>
"""


def main():
    entries = load_entries()
    html = build_html(entries)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"生成完成: {OUTPUT}")
    print(f"词条数: {len(entries)}")


if __name__ == "__main__":
    main()
