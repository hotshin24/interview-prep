#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""신호진_면접_답변집.md -> iOS 스타일 단일 HTML (고정 목차)"""
import re, html, json, sys, io

import os, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_md = [f for f in glob.glob(os.path.join(ROOT, "*.md")) if os.path.basename(f) != "README.md"]
SRC = _md[0] if _md else os.path.join(ROOT, "원고.md")
OUT = os.path.join(ROOT, "index.html")

# ---------- inline ----------
def inline(text):
    """코드 스팬을 자리표시자로 보호한 뒤 강조 문법을 처리한다."""
    spans = []

    def stash(m):
        spans.append('<code>' + html.escape(m.group(1)) + '</code>')
        return '\x00%d\x00' % (len(spans) - 1)

    t = re.sub(r'`([^`]+)`', stash, text)
    t = html.escape(t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t, flags=re.S)
    t = re.sub(r'(?<![\*\w])\*([^*\n]+)\*(?!\*)', r'<em>\1</em>', t)
    t = re.sub(r'\x00(\d+)\x00', lambda m: spans[int(m.group(1))], t)
    return t


def plain(text):
    """TOC 라벨용 — 마크업 기호 제거."""
    t = text.replace('`', '')
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    return html.escape(t.strip())

BADGE_RE = re.compile(r'[🔥⚠️]+')

def split_badges(title):
    fires = title.count('🔥')
    warns = title.count('⚠')
    clean = title.replace('🔥', '').replace('⚠️', '').replace('⚠', '').replace('️', '').strip()
    clean = re.sub(r'\s+', ' ', clean)
    badges = ''
    if warns:
        badges += '<span class="badge badge-warn" title="보완 필요 항목">⚠️</span>'
    if fires:
        badges += '<span class="badge badge-hot" title="빈출·핵심 질문">🔥%s</span>' % ('<span class="x2">×2</span>' if fires > 1 else '')
    return clean, badges, fires, warns

NUM_RE = re.compile(r'^\s*([0-9]+(?:[~–\-][0-9]+)?(?:-[a-z])?)\.\s+(.*)$')
CH_RE = re.compile(r'^\s*([0-9]{2})\.\s+(.*)$')
SUB_RE = re.compile(r'^\s*([0-9]+-[0-9]+)\.\s+(.*)$')

# ---------- block parser ----------
class Doc:
    def __init__(self):
        self.body = []
        self.toc = []          # list of chapters {label,num,id,items:[{...}]}
        self.card_open = False
        self.chapter_open = False
        self.stats = {'q': 0, 'hot': 0, 'warn': 0}

    def w(self, s):
        self.body.append(s)

    def close_card(self):
        if self.card_open:
            self.w('</article>')
            self.card_open = False

    def close_chapter(self):
        self.close_card()
        if self.chapter_open:
            self.w('</section>')
            self.chapter_open = False


# 원본 md에서 누락된 구조 헤더 — 빌드 단계에서만 복원한다.
# (문서 자체가 "4-5 다음에 5-2"로 이어지므로 번호 체계상 명백한 누락)
INJECT = [
    ('### 86.', ['## 4-6. 마크업 · 구조']),
    ('### 93.', ['# 05. HOOT UP — AI 파이프라인 디렉팅 🔥', '## 5-1. 근본 질문']),
]


def restore_headers(lines):
    out = []
    todo = dict(INJECT)
    body = '\n'.join(lines)
    for key, headers in list(todo.items()):
        if all(h.split('.')[0] + '.' in body and h[:12] in body for h in headers):
            todo.pop(key)          # 원고에 이미 있으면 삽입하지 않음
    for ln in lines:
        for key in list(todo):
            if ln.startswith(key):
                for h in todo.pop(key):
                    out.extend([h, ''])
                break
        out.append(ln)
    if todo:
        sys.stderr.write('알림: 헤더 삽입 지점 없음 %s\n' % list(todo))
    return out


def parse(md):
    lines = restore_headers(md.split('\n'))
    doc = Doc()
    i = 0
    n = len(lines)
    para = []
    doc_title = None
    lead = []
    lead_mode = [False]

    def flush_para():
        nonlocal para
        if not para:
            return
        raw = '\n'.join(para).strip()
        para = []
        if not raw:
            return
        if lead_mode[0]:
            lead.append(raw)
            return
        cls = 'p'
        first = raw.lstrip()
        if first.startswith('▸'):
            cls = 'p tip'
            raw = raw
        elif first.startswith('**A.**'):
            cls = 'p answer'
        body = '<br>'.join(inline(l) for l in raw.split('\n'))
        if cls == 'p tip':
            body = re.sub(r'^▸\s*', '', body)
            body = re.sub(r'<br>▸\s*', '<br>', body)
            doc.w('<div class="tip"><span class="tip-mark" aria-hidden="true">▸</span><div>%s</div></div>' % body)
        elif cls == 'p answer':
            body = re.sub(r'^<strong>A\.</strong>\s*', '', body)
            doc.w('<div class="answer"><span class="a-chip">A</span><div class="a-body">%s</div></div>' % body)
        else:
            doc.w('<p>%s</p>' % body)

    while i < n:
        line = lines[i]
        s = line.rstrip()

        # code fence
        if s.startswith('```'):
            flush_para()
            lang = s[3:].strip() or 'text'
            i += 1
            buf = []
            while i < n and not lines[i].rstrip().startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1
            code = html.escape('\n'.join(buf))
            doc.w('<figure class="code"><figcaption>%s</figcaption><pre><code>%s</code></pre></figure>'
                  % (html.escape(lang), code))
            continue

        # table
        if s.startswith('|'):
            flush_para()
            rows = []
            while i < n and lines[i].lstrip().startswith('|'):
                rows.append(lines[i].strip())
                i += 1
            def cells(r):
                r = r.strip()
                if r.startswith('|'): r = r[1:]
                if r.endswith('|'): r = r[:-1]
                return [c.strip() for c in r.split('|')]
            head = cells(rows[0])
            body_rows = rows[2:] if len(rows) > 1 and set(rows[1].replace('|', '').replace(' ', '')) <= set('-:') else rows[1:]
            th = ''.join('<th>%s</th>' % inline(c) for c in head)
            trs = []
            for r in body_rows:
                cs = cells(r)
                trs.append('<tr>' + ''.join('<td>%s</td>' % inline(c) for c in cs) + '</tr>')
            doc.w('<div class="table-wrap"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
                  % (th, ''.join(trs)))
            continue

        # blockquote
        if s.startswith('>'):
            flush_para()
            buf = []
            while i < n and lines[i].lstrip().startswith('>'):
                buf.append(re.sub(r'^\s*>\s?', '', lines[i]))
                i += 1
            content = '<br>'.join(inline(l) for l in buf if l.strip() != '')
            doc.w('<blockquote class="note">%s</blockquote>' % content)
            continue

        # unordered list
        if re.match(r'^\s*[-*]\s+', s):
            flush_para()
            items = []
            while i < n and re.match(r'^\s*[-*]\s+', lines[i]):
                items.append(re.sub(r'^\s*[-*]\s+', '', lines[i].rstrip()))
                i += 1
            doc.w('<ul>' + ''.join('<li>%s</li>' % inline(t) for t in items) + '</ul>')
            continue

        # ordered list
        if re.match(r'^\s*\d+\.\s+', s) and not s.startswith('#'):
            flush_para()
            items = []
            while i < n and re.match(r'^\s*\d+\.\s+', lines[i]):
                items.append(re.sub(r'^\s*\d+\.\s+', '', lines[i].rstrip()))
                i += 1
            doc.w('<ol>' + ''.join('<li>%s</li>' % inline(t) for t in items) + '</ol>')
            continue

        # hr
        if re.match(r'^-{3,}$', s.strip()):
            flush_para()
            i += 1
            continue

        # headings
        m = re.match(r'^(#{1,4})\s+(.*)$', s)
        if m:
            flush_para()
            level = len(m.group(1))
            title = m.group(2).strip()
            if level == 1 and doc_title is None:
                doc_title = title
                lead_mode[0] = True
                i += 1
                continue
            lead_mode[0] = False
            if level == 1:
                doc.close_chapter()
                clean, badges, fires, warns = split_badges(title)
                cm = CH_RE.match(clean)
                num = cm.group(1) if cm else ''
                label = cm.group(2) if cm else clean
                cid = 's%d' % (len(doc.toc) + 1)
                doc.toc.append({'id': cid, 'num': num, 'label': label, 'badges': badges, 'items': []})
                doc.w('<section class="chapter" id="%s">' % cid)
                doc.chapter_open = True
                if num:
                    doc.w('<header class="chapter-head"><div class="chapter-num">%s</div>'
                          '<h2 class="chapter-title">%s%s</h2></header>'
                          % (html.escape(num), inline(label), badges))
                else:
                    doc.w('<header class="chapter-head no-num"><h2 class="chapter-title">%s%s</h2></header>'
                          % (inline(label), badges))
                i += 1
                continue
            if level == 2:
                doc.close_card()
                clean, badges, fires, warns = split_badges(title)
                if not doc.chapter_open:
                    # 상위 챕터가 없는 ## 는 챕터로 승격
                    cid = 's%d' % (len(doc.toc) + 1)
                    doc.toc.append({'id': cid, 'num': '', 'label': clean, 'badges': badges, 'items': []})
                    doc.w('<section class="chapter" id="%s">' % cid)
                    doc.chapter_open = True
                    doc.w('<header class="chapter-head no-num"><h2 class="chapter-title">%s%s</h2></header>'
                          % (inline(clean), badges))
                    i += 1
                    continue
                sm = SUB_RE.match(clean)
                num = sm.group(1) if sm else ''
                label = sm.group(2) if sm else clean
                gid = '%s-g%d' % (doc.toc[-1]['id'], len([x for x in doc.toc[-1]['items'] if x['type'] == 'group']) + 1)
                doc.toc[-1]['items'].append({'type': 'group', 'id': gid, 'num': num, 'label': label, 'badges': badges})
                doc.w('<h3 class="group-title" id="%s">%s%s%s</h3>'
                      % (gid, ('<span class="group-num">%s</span>' % html.escape(num)) if num else '',
                         inline(label), badges))
                i += 1
                continue
            # level 3+ -> question card
            doc.close_card()
            if not doc.chapter_open:
                cid = 's%d' % (len(doc.toc) + 1)
                doc.toc.append({'id': cid, 'num': '', 'label': '기타', 'badges': '', 'items': []})
                doc.w('<section class="chapter" id="%s">' % cid)
                doc.chapter_open = True
            clean, badges, fires, warns = split_badges(title)
            qm = NUM_RE.match(clean)
            qnum = qm.group(1) if qm else ''
            label = qm.group(2) if qm else clean
            doc.stats['q'] += 1
            if fires: doc.stats['hot'] += 1
            if warns: doc.stats['warn'] += 1
            qid = 'q%d' % doc.stats['q']
            doc.toc[-1]['items'].append({'type': 'q', 'id': qid, 'num': qnum, 'label': label,
                                         'badges': badges, 'hot': fires, 'warn': warns})
            doc.w('<article class="qa%s%s" id="%s">' % (' is-hot' if fires else '', ' is-warn' if warns else '', qid))
            doc.w('<h4 class="qa-title">%s<span class="qa-text">%s</span>%s</h4>'
                  % (('<span class="qa-num">%s</span>' % html.escape(qnum)) if qnum else '',
                     inline(label), badges))
            doc.w('<div class="qa-body">')
            doc.card_open = 'body'
            # patch: close both div and article later
            i += 1
            continue

        # blank
        if not s.strip():
            flush_para()
            i += 1
            continue

        para.append(s)
        i += 1

    flush_para()
    doc.close_chapter()
    doc.lead = lead
    return doc, doc_title


# fix card closing (needs </div></article>)
def _close_card(self):
    if self.card_open:
        self.w('</div></article>')
        self.card_open = False
Doc.close_card = _close_card


def build_toc(toc):
    out = []
    for ch in toc:
        qs = [x for x in ch['items'] if x['type'] == 'q']
        out.append('<li class="toc-chapter" data-target="%s">' % ch['id'])
        out.append('<button class="toc-ch-btn" type="button" data-goto="%s" aria-expanded="false">'
                   '<span class="toc-ch-num">%s</span>'
                   '<span class="toc-ch-label">%s</span>'
                   '<span class="toc-count">%d</span>'
                   '<svg class="chev" viewBox="0 0 12 20" aria-hidden="true"><path d="M2 2l8 8-8 8" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>'
                   '</button>' % (ch['id'], html.escape(ch['num'] or '·'), plain(ch['label']), len(qs)))
        if ch['items']:
            out.append('<ul class="toc-sub">')
            for it in ch['items']:
                if it['type'] == 'group':
                    out.append('<li class="toc-group"><a href="#%s" data-id="%s">%s%s</a></li>'
                               % (it['id'], it['id'],
                                  ('<span class="g-num">%s</span>' % html.escape(it['num'])) if it['num'] else '',
                                  plain(it['label'])))
                else:
                    marks = ''
                    if it['warn']: marks += '<span class="m warn">⚠️</span>'
                    if it['hot']: marks += '<span class="m hot">🔥</span>'
                    out.append('<li class="toc-q"><a href="#%s" data-id="%s"><span class="q-num">%s</span>'
                               '<span class="q-label">%s</span>%s</a></li>'
                               % (it['id'], it['id'], html.escape(it['num'] or '·'),
                                  plain(it['label']), marks))
            out.append('</ul>')
        out.append('</li>')
    return '\n'.join(out)


def main():
    md = io.open(SRC, encoding='utf-8').read()
    doc, title = parse(md)
    body = '\n'.join(doc.body)
    lead_html = '<br>'.join(inline(l) for blk in getattr(doc, 'lead', []) for l in blk.split('\n'))
    toc_html = build_toc(doc.toc)
    tpl = io.open(TPL, encoding='utf-8').read()
    out = (tpl.replace('{{TITLE}}', html.escape(title or '면접 답변집'))
              .replace('{{TOC}}', toc_html)
              .replace('{{BODY}}', body)
              .replace('{{LEAD}}', lead_html)
              .replace('{{STAT_Q}}', str(doc.stats['q']))
              .replace('{{STAT_HOT}}', str(doc.stats['hot']))
              .replace('{{STAT_WARN}}', str(doc.stats['warn']))
              .replace('{{STAT_CH}}', str(len(doc.toc))))
    io.open(OUT, 'w', encoding='utf-8').write(out)
    print('chapters=%d questions=%d hot=%d warn=%d' % (len(doc.toc), doc.stats['q'], doc.stats['hot'], doc.stats['warn']))
    print('wrote', OUT, len(out), 'bytes')

TPL = os.path.join(ROOT, "tools", "template.html")

if __name__ == '__main__':
    main()
