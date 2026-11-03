# -*- coding: utf-8 -*-
"""Fill the institute thesis template (a copy) with the report content through Word automation."""
import io
import re
import sys
from pathlib import Path

import win32com.client as w

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import thesis_content as C  # noqa: E402

SRC = r'C:\Users\gauth\Downloads\Phase-2 UG_Thesis_Minor Specialization Project work Template.doc'
WORK = HERE / 'template_copy.docx'
OUT = HERE / 'Thesis_Report.docx'
FIGS = HERE / 'thesis_figs'
FONT = 'Times New Roman'
AUTO = -16777216


def parse(s):
    out, spans, i, ital = [], [], 0, None
    while i < len(s):
        c = s[i]
        if c in '^_' and i + 1 < len(s) and s[i + 1] == '{':
            j = s.index('}', i)
            inner = s[i + 2:j]
            spans.append(('sup' if c == '^' else 'sub', len(out), len(out) + len(inner)))
            out.extend(inner)
            i = j + 1
        elif c == '*':
            if ital is None:
                ital = len(out)
            else:
                spans.append(('it', ital, len(out)))
                ital = None
            i += 1
        else:
            out.append(c)
            i += 1
    return ''.join(out), spans


app = w.Dispatch('Word.Application')
app.Visible = False
app.DisplayAlerts = 0
d = app.Documents.Open(str(WORK), False, False)
print('opened copy, read-only =', d.ReadOnly, flush=True)

bm_pages = {}  # bookmark -> label


def apply_spans(base, spans):
    for kind, s, e in spans:
        r = d.Range(base + s, base + e)
        if kind == 'sup':
            r.Font.Superscript = True
        elif kind == 'sub':
            r.Font.Subscript = True
        else:
            r.Font.Italic = True


def fmt_body(p, size=12, align=3, after=6, before=0, space_mult=1.25):
    f = p.Format
    p.Range.ListFormat.RemoveNumbers()
    p.Range.Font.Name = FONT
    p.Range.Font.Size = size
    p.Range.Font.Bold = False
    p.Range.Font.Italic = False
    p.Range.Font.Superscript = False
    p.Range.Font.Subscript = False
    p.Range.Font.Color = AUTO
    f.Alignment = align
    f.LeftIndent = 0
    f.RightIndent = 0
    f.FirstLineIndent = 0
    f.SpaceBefore = before
    f.SpaceAfter = after
    f.LineSpacingRule = 5
    f.LineSpacing = 12 * space_mult
    f.KeepWithNext = False
    f.PageBreakBefore = False


def add_par(pos, text, kind='p', bm=None):
    plain, spans = parse(text)
    d.Range(pos, pos).InsertBefore(plain + '\r')
    p = d.Range(pos, pos).Paragraphs(1)
    if kind == 'h':
        fmt_body(p, align=0, before=10, after=4)
        p.Range.Font.Bold = True
        p.Range.Font.Italic = True
        p.Format.KeepWithNext = True
    elif kind == 'eq':
        fmt_body(p, align=1, before=2, after=6)
        p.Range.Font.Italic = True
    elif kind == 'cap':
        fmt_body(p, size=11, align=1, before=2, after=8, space_mult=1.0)
        p.Range.Font.Bold = True
    elif kind == 'tcap':
        fmt_body(p, size=11, align=1, before=6, after=4, space_mult=1.0)
        p.Range.Font.Bold = True
        p.Format.KeepWithNext = True
    elif kind == 'b':
        fmt_body(p, after=3)
        p.Range.ListFormat.ApplyBulletDefault()
        p.Format.Alignment = 3
    else:
        fmt_body(p)
    apply_spans(pos, spans)
    if kind in ('h',):
        p.Range.Font.Italic = True
    if bm:
        d.Bookmarks.Add(bm, d.Range(pos, pos + len(plain)))
    return pos + len(plain) + 1


def add_table(pos, label, caption, rows, widths):
    pos = add_par(pos, f'{label}: {caption}', 'tcap', bm='cap_' + re.sub(r'\W', '_', label))
    nr, nc = len(rows), len(rows[0])
    t = d.Tables.Add(d.Range(pos, pos), nr, nc)
    try:
        t.Style = 'Table Grid'
    except Exception:
        t.Borders.Enable = True
    t.Range.Font.Name = FONT
    t.Range.Font.Size = 10
    t.Range.ParagraphFormat.SpaceAfter = 0
    t.Range.ParagraphFormat.SpaceBefore = 0
    t.Range.ParagraphFormat.LineSpacingRule = 0
    t.Range.ParagraphFormat.LeftIndent = 0
    t.Range.ParagraphFormat.FirstLineIndent = 0
    t.AllowAutoFit = False
    t.PreferredWidthType = 2
    t.PreferredWidth = 100
    for c in range(nc):
        t.Columns(c + 1).PreferredWidthType = 2
        t.Columns(c + 1).PreferredWidth = widths[c] * 100
    for r, row in enumerate(rows, 1):
        for c, text in enumerate(row, 1):
            plain, spans = parse(text)
            cell = t.Cell(r, c)
            cell.Range.Text = plain
            base = cell.Range.Start
            apply_spans(base, spans)
            cell.Range.ParagraphFormat.Alignment = 0 if (c == 1 and nc > 2 and False) else 1
            cell.Range.Font.Bold = (r == 1)
            cell.VerticalAlignment = 1
            if r == 1:
                cell.Shading.BackgroundPatternColor = 14277081  # light grey
    t.Rows(1).HeadingFormat = True
    if nr <= 12:
        for r in range(1, nr):
            t.Rows(r).Range.ParagraphFormat.KeepWithNext = True
    t.Rows.AllowBreakAcrossPages = False
    t.TopPadding = 2
    t.BottomPadding = 2
    pos = t.Range.End
    # small spacer paragraph after the table
    d.Range(pos, pos).InsertBefore('\r')
    sp = d.Range(pos, pos).Paragraphs(1)
    fmt_body(sp, size=6, after=0, space_mult=1.0)
    return pos + 1


def add_figure(pos, fname, label, caption, width_in):
    d.Range(pos, pos).InsertBefore('\r')
    p = d.Range(pos, pos).Paragraphs(1)
    fmt_body(p, align=1, before=6, after=2, space_mult=1.0)
    p.Format.KeepWithNext = True
    ils = d.InlineShapes.AddPicture(str(FIGS / fname), False, True, d.Range(pos, pos))
    ils.LockAspectRatio = True
    ils.Width = width_in * 72
    pos = d.Range(pos, pos).Paragraphs(1).Range.End
    return add_par(pos, f'{label}: {caption}', 'cap', bm='cap_' + re.sub(r'\W', '_', label))


def build_chapter(pos, items):
    for it in items:
        k = it[0]
        if k == 'h':
            pos = add_par(pos, f'{it[1]}\u2003{it[2]}', 'h', bm='sec_' + it[1].replace('.', '_'))
        elif k == 'p':
            pos = add_par(pos, it[1], 'p')
        elif k == 'eq':
            pos = add_par(pos, it[1], 'eq')
        elif k == 'b':
            for txt in it[1]:
                pos = add_par(pos, txt, 'b')
        elif k == 't':
            pos = add_table(pos, it[1], it[2], it[3], it[4])
        elif k == 'f':
            pos = add_figure(pos, it[1], it[2], it[3], it[4])
    return pos


# ------------------------------------------------------------------ locate paragraphs (original indices)
paras = [p.Range.Text for p in d.Paragraphs]
print('paragraphs', len(paras))


def idx(startswith, start=0):
    for i in range(start, len(paras)):
        if paras[i].lstrip('\x0c').startswith(startswith):
            return i + 1
    raise KeyError(startswith)


starts = [i + 1 for i, t in enumerate(paras) if t.startswith('This chapter should include')]
assert len(starts) == 5, starts
ff = [i + 1 for i, t in enumerate(paras) if t.startswith('\x0c') and 'CHAPTER' in t or t.startswith('\x0cREFERENCES')]
ends = []
for s in starts:
    nxt = min(f for f in ff if f > s)
    ends.append(nxt - 1)
print('chapter ranges', list(zip(starts, ends)))

# ------------------------------------------------------------------ tail: delete the guidelines page first
gi = idx('General Guidelines')
prev = gi - 1
start_del = d.Paragraphs(prev).Range.Start if paras[prev - 1].strip('\x0c\r\n ') == '' else d.Paragraphs(gi).Range.Start
d.Range(start_del, d.Content.End - 1).Delete()
print('guidelines page removed')

# ------------------------------------------------------------------ references (original indices, before chapter edits)
def set_para_text(i, lines):
    p = d.Paragraphs(i)
    r = p.Range
    r.MoveEnd(1, -1)
    r.Text = '\r'.join(lines)


ref_book_i = idx('[1] Name 1, “Book Title”')
ref_web_i = idx('[1] Topic 1')
ref_j2 = idx('[2] Name 1 and Name 2')
ref_j1 = idx('[1] Name 1 and Name 2')
n = 1
j_lines = [f'[{n + k}] {t}' for k, t in enumerate(C.REFS_JOURNAL)]
n += len(C.REFS_JOURNAL)
b_lines = [f'[{n + k}] {t}' for k, t in enumerate(C.REFS_BOOK)]
n += len(C.REFS_BOOK)
w_lines = [f'[{n + k}] {t}' for k, t in enumerate(C.REFS_WEB)]
set_para_text(ref_web_i, w_lines)
set_para_text(ref_book_i, b_lines)
d.Range(d.Paragraphs(ref_j1).Range.Start, d.Paragraphs(ref_j2).Range.End - 1).Text = '\r'.join(j_lines)
for i in (ref_j1, ref_book_i, ref_web_i):
    pass  # formatting is inherited from the template paragraphs

# ------------------------------------------------------------------ chapters, last to first
chapters = [C.CH1, C.CH2, C.CH3, C.CH4, C.CH5]
for (s, e), items in reversed(list(zip(zip(starts, ends), chapters))):
    a = d.Paragraphs(s).Range.Start
    b = d.Paragraphs(e).Range.End - 1
    d.Range(a, b).Delete()
    anchor = d.Range(a, a).Paragraphs(1)
    anchor.Range.ListFormat.RemoveNumbers()
    anchor.Format.Reset()
    anchor.Range.Font.Reset()
    build_chapter(a, items)
    print('chapter built at', a)

# ------------------------------------------------------------------ cover, certificate, acknowledgement, abstract
for find, rep in (('<PROJECT TITLE>', C.TITLE_CASE), ('PROJECT TITLE', C.TITLE)):
    rg = d.Content
    ok = rg.Find.Execute(find, True, False, False, False, False, True, 0, False, rep, 2)
    print('replace', find, ok, flush=True)


def find_para(startswith):
    for p in d.Paragraphs:
        if p.Range.Text.startswith(startswith):
            return p
    raise KeyError(startswith)


def fill_block(p, texts):
    r = p.Range
    r.MoveEnd(1, -1)
    start = r.Start
    plains = [parse(t) for t in texts]
    r.Text = '\r'.join(pl for pl, _ in plains)
    pos = start
    for k, (pl, spans) in enumerate(plains):
        para = d.Range(pos, pos).Paragraphs(1)
        fmt_body(para, after=8)
        apply_spans(pos, spans)
        pos += len(pl) + 1


find_para(C.TITLE[:25]).Range.Font.Size = 15
fill_block(find_para('This section should contain the acknowledgements'), C.ACK)
fill_block(find_para('The abstract is brief synopsis'), C.ABSTRACT)

# project details table: Project Title
for t in d.Tables:
    if 'Student Details' in t.Range.Text:
        cells = list(t.Range.Cells)
        for k, c in enumerate(cells):
            if c.Range.Text.strip('\r\x07 ') == 'Project Title':
                cells[k + 1].Range.Text = C.TITLE_CASE
        break

# remove empty paragraphs after the last reference (they cause a blank page)
plist = d.Paragraphs
for i in range(1, plist.Count + 1):
    if plist(i).Range.Text.startswith('[16]'):
        j = i + 1
        while j <= plist.Count and plist(j).Range.Text in ('\r', ' \r'):
            plist(j).Range.Delete()
            plist = d.Paragraphs
        break
for head in ('LIST OF TABLES', 'LIST OF FIGURES'):
    for p in d.Paragraphs:
        if p.Range.Text.strip('\r ') == head:
            p.Format.PageBreakBefore = True
            break

# ------------------------------------------------------------------ section breaks and page numbers
def break_at_para(prefix):
    for p in d.Paragraphs:
        tx = p.Range.Text
        if tx.startswith('' + prefix):
            st = p.Range.Start
            d.Range(st, st + 1).Delete()
            d.Range(st, st).InsertBreak(2)  # next-page section break
            return
    raise KeyError(prefix)


break_at_para('CHAPTER 1')
break_at_para('ACKNOWLEDGMENTS')
print('sections now', d.Sections.Count, flush=True)


def number_footer(sec, style, label):
    ft = sec.Footers(1)
    ft.LinkToPrevious = False
    ft.Range.Text = ''
    ft.PageNumbers.Add(2, True)
    ft.PageNumbers.NumberStyle = style
    ft.PageNumbers.RestartNumberingAtSection = True
    ft.PageNumbers.StartingNumber = 1
    ft.Range.Font.Name = FONT
    ft.Range.Font.Size = 11
    print('footer set', label, flush=True)


# sections: 1-2 cover/certificate (no number), 3 front matter (roman), 4 chapters onward (arabic from 1)
for k in (1, 2):
    d.Sections(k).Footers(1).LinkToPrevious = False
number_footer(d.Sections(3), 2, 'roman')
number_footer(d.Sections(4), 0, 'arabic')

# ------------------------------------------------------------------ contents and lists
d.Repaginate()


def roman(n):
    vals = [(10, 'x'), (9, 'ix'), (5, 'v'), (4, 'iv'), (1, 'i')]
    out = ''
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


def page_of_range(r):
    return int(r.Information(1))


def page_of_bm(name):
    return page_of_range(d.Bookmarks(name).Range)


def para_page_last(startswith):
    found = None
    for p in d.Paragraphs:
        if p.Range.Text.lstrip('').startswith(startswith):
            found = p
    return page_of_range(found.Range) if found is not None else None


def para_page(startswith):
    for p in d.Paragraphs:
        if p.Range.Text.lstrip('\x0c').startswith(startswith):
            return page_of_range(p.Range)
    return None


# list-of-tables / list-of-figures tables
def fill_list(table_pos, entries):
    t = d.Tables(table_pos)
    need = len(entries) + 1 - t.Rows.Count
    for _ in range(max(0, need)):
        t.Rows.Add()
    for k, (num, title, bm) in enumerate(entries, 2):
        t.Cell(k, 1).Range.Text = num
        t.Cell(k, 2).Range.Text = title
        t.Cell(k, 3).Range.Text = str(page_of_bm(bm))
        for c in (1, 2, 3):
            t.Cell(k, c).Range.Font.Name = FONT
            t.Cell(k, c).Range.Font.Size = 11
        t.Cell(k, 2).Range.ParagraphFormat.Alignment = 0


tab_entries, fig_entries = [], []
for ch in (C.CH1, C.CH2, C.CH3, C.CH4, C.CH5):
    for it in ch:
        if it[0] == 't':
            tab_entries.append((it[1].replace('Table ', ''), it[2], 'cap_' + re.sub(r'\W', '_', it[1])))
        if it[0] == 'f':
            fig_entries.append((it[2].replace('Fig. ', ''), it[3], 'cap_' + re.sub(r'\W', '_', it[2])))

tbl_list_idx = fig_list_idx = None
for i, t in enumerate(d.Tables, 1):
    head = t.Range.Text[:12]
    if head.startswith('Table No'):
        tbl_list_idx = i
    if head.startswith('Figure No'):
        fig_list_idx = i
fill_list(fig_list_idx, fig_entries)
fill_list(tbl_list_idx, tab_entries)

# table of contents (table with 'Acknowledgement')
toc = None
for t in d.Tables:
    if 'Acknowledgement' in t.Range.Text and 'INTRODUCTION' in t.Range.Text:
        toc = t
        break


def row_texts(t, r):
    return [t.Cell(r, c).Range.Text.strip('\r\x07 ') for c in range(1, t.Rows(r).Cells.Count + 1)]


def find_row(t, text):
    for r in range(1, t.Rows.Count + 1):
        try:
            if row_texts(t, r)[0].startswith(text):
                return r
        except Exception:
            pass
    raise KeyError(text)


ref_row = find_row(toc, 'Chapter 1') + 1
SUB_SIZE = toc.Cell(ref_row, 3).Range.Font.Size
print('toc sub size', SUB_SIZE, flush=True)
chap_heads = [[x for x in ch if x[0] == 'h'] for ch in (C.CH1, C.CH2, C.CH3, C.CH4, C.CH5)]
for n in range(5, 0, -1):
    r0 = find_row(toc, f'Chapter {n}')
    last = r0
    while True:
        nxt = last + 1
        try:
            if toc.Rows(nxt).Cells.Count == 4:
                last = nxt
                continue
        except Exception:
            pass
        break
    have = last - r0
    heads = chap_heads[n - 1]
    if len(heads) > have:
        toc.Rows(last).Select()
        app.Selection.InsertRowsBelow(len(heads) - have)
    for k, h in enumerate(heads, 1):
        r = r0 + k
        toc.Cell(r, 2).Range.Text = h[1]
        toc.Cell(r, 3).Range.Text = h[2]
        toc.Cell(r, 4).Range.Text = str(page_of_bm('sec_' + h[1].replace('.', '_')))
        toc.Cell(r, 2).Range.Font.Bold = True
        toc.Cell(r, 3).Range.Font.Bold = False
        toc.Cell(r, 3).Range.Font.Color = AUTO
        toc.Cell(r, 4).Range.Font.Bold = False
        toc.Cell(r, 4).Range.Font.Color = AUTO
        for cc in (2, 3, 4):
            toc.Cell(r, cc).Range.Font.Size = SUB_SIZE
            toc.Cell(r, cc).Range.Font.Name = FONT
    # chapter page
    toc.Cell(r0, 3).Range.Text = str(para_page(f'CHAPTER {n}'))
    for k in range(have + 1, 0, -1):
        pass

front = {'Acknowledgement': 'ACKNOWLEDGMENTS', 'Abstract': 'ABSTRACT', 'List Of Tables': 'LIST OF TABLES', 'List Of Figures': 'LIST OF FIGURES'}
for label, head in front.items():
    r = find_row(toc, label)
    pg = para_page(head)
    toc.Cell(r, 3).Range.Text = roman(pg) if pg else ''
for label, head in (('REFERENCES', 'REFERENCES'), ('ANNEXURES', 'ANNEXURES'), ('PROJECT DETAILS', 'PROJECT DETAILS')):
    r = find_row(toc, label)
    pg = para_page_last(head)
    if pg:
        toc.Cell(r, 2).Range.Text = str(pg)

d.Repaginate()
print('pages', d.ComputeStatistics(2))
import time
t0 = time.time()
d.ExportAsFixedFormat(str(HERE / 'Thesis_Report.pdf'), 17)
print('pdf exported', round(time.time() - t0, 1), flush=True)
xml = d.Content.WordOpenXML
io.open(str(HERE / 'Thesis_Report_flat.xml'), 'w', encoding='utf-8').write(xml)
print('flat OPC exported', len(xml), flush=True)
d.Close(False)
app.Quit()
print('done')
