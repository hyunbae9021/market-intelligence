"""
PDF 렌더러 - Markdown 리포트를 인쇄용 HTML로 변환
브라우저의 print() 또는 wkhtmltopdf를 통해 PDF 생성
"""
from __future__ import annotations

import re
from datetime import datetime


_TABLE_ROW_RE = re.compile(r'^\|(.+)\|$')
_TABLE_SEP_RE = re.compile(r'^\|[\|\s\-:]+\|$')


def markdown_to_print_html(
    markdown_text: str,
    title: str,
    subtitle: str = "",
    generated_at: str = "",
    doc_class: str = "대외비",
) -> str:
    """Markdown → 인쇄 최적화 HTML 변환"""
    body_html = _convert_md(markdown_text or "")

    now = generated_at or datetime.now().strftime("%Y년 %m월 %d일")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{_esc(title)} — MI Report</title>
  <style>
    /* ── 기본 ── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --accent: #1a56db;
      --accent-light: #e8f0fe;
      --text: #1a202c;
      --text-muted: #4a5568;
      --border: #e2e8f0;
      --surface: #f7fafc;
      --danger: #c53030;
    }}

    body {{
      font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
      font-size: 10pt;
      line-height: 1.7;
      color: var(--text);
      background: #fff;
      padding: 0;
      margin: 0;
    }}

    /* ── 커버 페이지 ── */
    .cover {{
      width: 100%;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 60px 72px;
      border-bottom: 4px solid var(--accent);
      page-break-after: always;
    }}
    .cover-badge {{
      font-size: 9pt;
      font-weight: 700;
      letter-spacing: 0.15em;
      color: var(--danger);
      border: 1px solid var(--danger);
      display: inline-block;
      padding: 3px 10px;
      margin-bottom: 48px;
    }}
    .cover-title {{
      font-size: 28pt;
      font-weight: 800;
      line-height: 1.2;
      color: var(--text);
      margin-bottom: 16px;
    }}
    .cover-subtitle {{
      font-size: 14pt;
      color: var(--text-muted);
      font-weight: 400;
      margin-bottom: 40px;
    }}
    .cover-divider {{
      width: 80px;
      height: 4px;
      background: var(--accent);
      margin-bottom: 40px;
    }}
    .cover-meta {{
      font-size: 9.5pt;
      color: var(--text-muted);
      line-height: 2;
    }}
    .cover-meta strong {{ color: var(--text); }}
    .cover-footer {{
      font-size: 8.5pt;
      color: var(--text-muted);
      border-top: 1px solid var(--border);
      padding-top: 16px;
    }}

    /* ── 본문 레이아웃 ── */
    .report-body {{
      max-width: 800px;
      margin: 0 auto;
      padding: 48px 64px;
    }}

    /* ── 헤딩 ── */
    h1 {{
      font-size: 18pt;
      font-weight: 800;
      color: var(--accent);
      margin: 36px 0 12px;
      padding-bottom: 8px;
      border-bottom: 2px solid var(--accent);
      page-break-after: avoid;
    }}
    h2 {{
      font-size: 13pt;
      font-weight: 700;
      color: var(--text);
      margin: 28px 0 10px;
      padding-left: 10px;
      border-left: 4px solid var(--accent);
      page-break-after: avoid;
    }}
    h3 {{
      font-size: 11pt;
      font-weight: 700;
      color: var(--text);
      margin: 20px 0 8px;
      page-break-after: avoid;
    }}
    h4 {{
      font-size: 10pt;
      font-weight: 700;
      color: var(--text-muted);
      margin: 14px 0 6px;
    }}

    /* ── 단락 ── */
    p {{ margin: 0 0 10px; }}

    /* ── 리스트 ── */
    ul, ol {{
      margin: 8px 0 12px 20px;
    }}
    li {{ margin: 4px 0; }}

    /* ── 테이블 ── */
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0 20px;
      font-size: 9pt;
      page-break-inside: avoid;
    }}
    th {{
      background: var(--accent);
      color: #fff;
      font-weight: 700;
      padding: 7px 10px;
      text-align: left;
      font-size: 8.5pt;
    }}
    td {{
      padding: 6px 10px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }}
    tr:nth-child(even) td {{ background: var(--surface); }}
    tr:hover td {{ background: var(--accent-light); }}

    /* ── 인용구 ── */
    blockquote {{
      border-left: 4px solid var(--accent);
      background: var(--accent-light);
      padding: 12px 16px;
      margin: 12px 0;
      border-radius: 0 6px 6px 0;
      font-style: italic;
      color: #2d3748;
      page-break-inside: avoid;
    }}
    blockquote p {{ margin: 0; }}

    /* ── 수평선 ── */
    hr {{
      border: none;
      border-top: 1px solid var(--border);
      margin: 24px 0;
    }}

    /* ── 강조 ── */
    strong {{ font-weight: 700; }}
    em {{ font-style: italic; color: var(--text-muted); }}
    code {{
      font-family: 'Courier New', monospace;
      font-size: 8.5pt;
      background: #f1f5f9;
      padding: 1px 5px;
      border-radius: 3px;
      border: 1px solid var(--border);
    }}

    /* ── 섹션 구분 ── */
    .section-break {{ page-break-before: always; }}

    /* ── 페이지 번호 ── */
    @page {{
      size: A4;
      margin: 20mm 18mm 20mm 18mm;
      @bottom-right {{
        content: counter(page) " / " counter(pages);
        font-size: 8pt;
        color: #718096;
      }}
    }}

    /* ── 인쇄 최적화 ── */
    @media print {{
      body {{ font-size: 9.5pt; }}
      .cover {{ min-height: auto; padding: 40px; }}
      .no-print {{ display: none !important; }}
      a {{ text-decoration: none; color: inherit; }}
      h1, h2, h3 {{ page-break-after: avoid; }}
      table {{ page-break-inside: avoid; }}
      blockquote {{ page-break-inside: avoid; }}
    }}

    /* ── 인쇄 버튼 (화면 전용) ── */
    .print-toolbar {{
      position: fixed;
      top: 16px;
      right: 16px;
      display: flex;
      gap: 8px;
      z-index: 999;
      background: #fff;
      padding: 10px 14px;
      border-radius: 10px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }}
    .print-btn {{
      background: #1a56db;
      color: #fff;
      border: none;
      padding: 10px 20px;
      border-radius: 7px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      font-family: inherit;
    }}
    .print-btn:hover {{ background: #1341b5; }}
    .close-btn {{
      background: #f1f5f9;
      color: #4a5568;
      border: 1px solid #e2e8f0;
    }}
    .close-btn:hover {{ background: #e2e8f0; }}
  </style>
</head>
<body>

<!-- 인쇄 툴바 (화면 전용) -->
<div class="print-toolbar no-print">
  <button class="print-btn" onclick="window.print()">🖨️ PDF로 저장</button>
  <button class="print-btn close-btn" onclick="window.close()">✕ 닫기</button>
</div>

<!-- 커버 페이지 -->
<div class="cover">
  <div>
    <div class="cover-badge">{_esc(doc_class)}</div>
    <div class="cover-title">{_esc(title)}</div>
    {f'<div class="cover-subtitle">{_esc(subtitle)}</div>' if subtitle else ''}
    <div class="cover-divider"></div>
    <div class="cover-meta">
      <strong>작성일</strong> {_esc(now)}<br>
      <strong>분석 방법론</strong> 14개 전문 AI 에이전트 멀티스테이지 분석<br>
      <strong>플랫폼</strong> Market Intelligence Multi-Agent System
    </div>
  </div>
  <div class="cover-footer">
    본 리포트는 AI 에이전트가 자동 수집·분석한 데이터를 기반으로 작성되었습니다.
    최종 의사결정 시 전문가 검토를 권장합니다.
  </div>
</div>

<!-- 본문 -->
<div class="report-body">
{body_html}
</div>

<script>
  // 열리자마자 인쇄 대화상자 (옵션)
  // window.onload = () => window.print();
</script>
</body>
</html>"""


def agent_to_print_html(agent_data: dict, session_topic: str) -> str:
    """단일 에이전트 결과 → 인쇄용 HTML"""
    agent_name = agent_data.get("agent_name", "에이전트")
    phase = agent_data.get("phase", 0)
    summary = agent_data.get("summary", "")
    analysis = agent_data.get("analysis", "") or ""
    quality = agent_data.get("quality", {}) or {}
    duration = agent_data.get("duration_seconds") or 0
    data_points = agent_data.get("data_points_collected", 0)
    sources = agent_data.get("sources_used", [])

    quality_level = quality.get("overall", "unknown")
    quality_badge_color = {"pass": "#16a34a", "warning": "#d97706", "fail": "#dc2626"}.get(quality_level, "#718096")
    quality_label = {"pass": "PASS ✓", "warning": "WARNING ⚠", "fail": "FAIL ✗"}.get(quality_level, quality_level)

    checks_html = ""
    if quality.get("checks"):
        rows = "".join([
            f"<tr><td>{_esc(c.get('criterion',''))}</td>"
            f"<td>{_esc(c.get('target',''))}</td>"
            f"<td>{_esc(c.get('actual',''))}</td>"
            f"<td style='color:{'#16a34a' if c.get('level')=='pass' else '#dc2626'};font-weight:700'>"
            f"{'✓' if c.get('level')=='pass' else '✗'}</td></tr>"
            for c in quality.get("checks", [])
        ])
        checks_html = f"""
<h2>품질 검증 결과</h2>
<table>
  <thead><tr><th>검증 항목</th><th>목표</th><th>실제</th><th>판정</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<p><strong>종합:</strong> {_esc(quality.get('summary', ''))}</p>
"""

    sources_html = ""
    if sources:
        src_items = "".join(f"<li>{_esc(s)}</li>" for s in sources[:20])
        sources_html = f"<h2>데이터 출처</h2><ul>{src_items}</ul>"

    body_html = _convert_md(analysis)

    now = datetime.now().strftime("%Y년 %m월 %d일")
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <title>{_esc(agent_name)} — {_esc(session_topic)}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
      font-size: 10pt; line-height: 1.7; color: #1a202c; background: #fff;
      padding: 0; max-width: 820px; margin: 0 auto;
    }}
    .agent-header {{
      background: #1a56db; color: #fff; padding: 32px 48px;
      page-break-after: avoid;
    }}
    .agent-phase {{ font-size: 9pt; opacity: 0.8; margin-bottom: 6px; }}
    .agent-name {{ font-size: 20pt; font-weight: 800; margin-bottom: 10px; }}
    .agent-topic {{ font-size: 10pt; opacity: 0.85; }}
    .agent-meta {{
      display: flex; gap: 24px;
      padding: 16px 48px;
      background: #f7fafc;
      border-bottom: 1px solid #e2e8f0;
      font-size: 9pt; color: #4a5568;
      flex-wrap: wrap;
    }}
    .meta-item strong {{ color: #1a202c; }}
    .quality-badge {{
      display: inline-block; padding: 3px 10px; border-radius: 4px;
      font-weight: 700; font-size: 8.5pt; color: #fff;
      background: {quality_badge_color};
    }}
    .summary-box {{
      margin: 24px 48px;
      padding: 14px 18px;
      background: #e8f0fe;
      border-left: 4px solid #1a56db;
      border-radius: 0 6px 6px 0;
      font-style: italic;
      color: #2d3748;
      page-break-inside: avoid;
    }}
    .body-content {{ padding: 8px 48px 48px; }}
    h1 {{ font-size: 16pt; font-weight: 800; color: #1a56db; margin: 32px 0 10px; padding-bottom: 6px; border-bottom: 2px solid #1a56db; }}
    h2 {{ font-size: 12pt; font-weight: 700; margin: 22px 0 8px; padding-left: 8px; border-left: 4px solid #1a56db; }}
    h3 {{ font-size: 10.5pt; font-weight: 700; margin: 16px 0 6px; }}
    h4 {{ font-size: 10pt; font-weight: 700; color: #4a5568; margin: 12px 0 4px; }}
    p {{ margin: 0 0 9px; }}
    ul, ol {{ margin: 6px 0 10px 20px; }}
    li {{ margin: 3px 0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 10px 0 18px; font-size: 9pt; page-break-inside: avoid; }}
    th {{ background: #1a56db; color: #fff; padding: 6px 9px; text-align: left; font-size: 8.5pt; }}
    td {{ padding: 5px 9px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
    tr:nth-child(even) td {{ background: #f7fafc; }}
    blockquote {{ border-left: 4px solid #1a56db; background: #e8f0fe; padding: 10px 14px; margin: 10px 0; border-radius: 0 5px 5px 0; font-style: italic; }}
    blockquote p {{ margin: 0; }}
    hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 20px 0; }}
    strong {{ font-weight: 700; }}
    code {{ font-family: monospace; font-size: 8.5pt; background: #f1f5f9; padding: 1px 4px; border-radius: 3px; border: 1px solid #e2e8f0; }}
    .print-toolbar {{
      position: fixed; top: 14px; right: 14px;
      display: flex; gap: 8px; z-index: 999;
      background: #fff; padding: 8px 12px; border-radius: 8px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    }}
    .print-btn {{
      background: #1a56db; color: #fff; border: none;
      padding: 8px 16px; border-radius: 6px; font-size: 12px;
      font-weight: 700; cursor: pointer; font-family: inherit;
    }}
    .print-btn:hover {{ background: #1341b5; }}
    .close-btn {{ background: #f1f5f9; color: #4a5568; border: 1px solid #e2e8f0; }}
    @media print {{
      body {{ font-size: 9.5pt; }}
      .print-toolbar {{ display: none !important; }}
    }}
    @page {{ size: A4; margin: 18mm 16mm; }}
  </style>
</head>
<body>
<div class="print-toolbar">
  <button class="print-btn" onclick="window.print()">🖨️ PDF 저장</button>
  <button class="print-btn close-btn" onclick="window.close()">✕</button>
</div>

<div class="agent-header">
  <div class="agent-phase">Phase {phase} 에이전트</div>
  <div class="agent-name">{_esc(agent_name)}</div>
  <div class="agent-topic">{_esc(session_topic)}</div>
</div>

<div class="agent-meta">
  <div class="meta-item"><strong>작성일</strong> {now}</div>
  <div class="meta-item"><strong>소요 시간</strong> {duration:.1f}초</div>
  <div class="meta-item"><strong>수집 데이터</strong> {data_points}건</div>
  <div class="meta-item"><strong>품질</strong> <span class="quality-badge">{quality_label}</span></div>
</div>

<div class="summary-box">{_esc(summary)}</div>

<div class="body-content">
{body_html}
{checks_html}
{sources_html}
</div>
</body>
</html>"""


def _esc(text: str) -> str:
    """HTML 이스케이프"""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _convert_md(md: str) -> str:
    """Markdown → HTML (테이블 포함 전처리)"""
    lines = md.split("\n")
    output: list[str] = []
    in_table = False
    in_ul = False
    in_ol = False
    in_blockquote = False

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            output.append("</ul>")
            in_ul = False
        if in_ol:
            output.append("</ol>")
            in_ol = False

    for line in lines:
        # 테이블 감지
        if _TABLE_ROW_RE.match(line):
            if _TABLE_SEP_RE.match(line):
                # 구분선 → 헤더 행을 thead로 변환
                if output and output[-1].startswith("<tr>"):
                    header_row = output.pop()
                    header_row = header_row.replace("<td>", "<th>").replace("</td>", "</th>")
                    if not in_table:
                        output.append("<table><thead>")
                        in_table = True
                    output.append(header_row)
                    output.append("</thead><tbody>")
                continue
            else:
                close_lists()
                cells = line[1:-1].split("|")
                row = "<tr>" + "".join(f"<td>{_inline(c.strip())}</td>" for c in cells) + "</tr>"
                if not in_table:
                    output.append("<table><tbody>")
                    in_table = True
                output.append(row)
                continue
        else:
            if in_table:
                output.append("</tbody></table>")
                in_table = False

        # 수평선
        if re.match(r'^---+$', line.strip()):
            close_lists()
            output.append("<hr>")
            continue

        # 헤딩
        h_match = re.match(r'^(#{1,4})\s+(.+)$', line)
        if h_match:
            close_lists()
            level = len(h_match.group(1))
            text = _inline(h_match.group(2))
            output.append(f"<h{level}>{text}</h{level}>")
            continue

        # 인용구
        bq_match = re.match(r'^>\s*(.*)$', line)
        if bq_match:
            close_lists()
            content = _inline(bq_match.group(1))
            if not in_blockquote:
                output.append("<blockquote>")
                in_blockquote = True
            output.append(f"<p>{content}</p>")
            continue
        else:
            if in_blockquote:
                output.append("</blockquote>")
                in_blockquote = False

        # 비순서 리스트
        ul_match = re.match(r'^[-*]\s+(.+)$', line)
        if ul_match:
            if not in_ul:
                close_lists()
                output.append("<ul>")
                in_ul = True
            output.append(f"<li>{_inline(ul_match.group(1))}</li>")
            continue

        # 순서 리스트
        ol_match = re.match(r'^\d+\.\s+(.+)$', line)
        if ol_match:
            if not in_ol:
                close_lists()
                output.append("<ol>")
                in_ol = True
            output.append(f"<li>{_inline(ol_match.group(1))}</li>")
            continue

        # 일반 단락
        close_lists()
        stripped = line.strip()
        if stripped:
            output.append(f"<p>{_inline(stripped)}</p>")
        else:
            output.append("")

    # 열린 태그 닫기
    close_lists()
    if in_table:
        output.append("</tbody></table>")
    if in_blockquote:
        output.append("</blockquote>")

    return "\n".join(output)


def _inline(text: str) -> str:
    """인라인 Markdown 처리 (굵게, 기울임, 코드, 링크)"""
    text = _esc(text)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text
