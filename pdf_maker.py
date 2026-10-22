"""Savollar va javoblar PDF fayllari: ikki ustunli A4, Test ID, xira suv belgi (watermark)."""
import random
import string
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    FrameBreak,
    KeepTogether,
    NextPageTemplate,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from config import BRAND, FONTS_DIR, LEVELS, OUTPUT_DIR

for _name, _file in [("Serif", "DejaVuSerifCondensed.ttf"),
                     ("Serif-Bold", "DejaVuSerifCondensed-Bold.ttf"),
                     ("Serif-Italic", "DejaVuSerifCondensed-Italic.ttf"),
                     ("Serif-BoldItalic", "DejaVuSerifCondensed-BoldItalic.ttf")]:
    pdfmetrics.registerFont(TTFont(_name, str(FONTS_DIR / _file)))
pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-Bold",
                              italic="Serif-Italic", boldItalic="Serif-BoldItalic")

# ---------- O'lchamlar va ranglar ----------
W, H = A4
M = 12 * mm                       # chap/o'ng chekka
GUTTER = 10 * mm                  # ustunlar orasi
COL_W = (W - 2 * M - GUTTER) / 2  # bitta ustun kengligi
NUM_W = 20                        # savol raqami uchun joy
COL_BOTTOM = 48                   # ustunlar pastki chegarasi
LATER_TOP = H - 42                # 2-sahifadan boshlab ustunlar yuqori chegarasi
FIRST_TOP = H - 100               # 1-sahifada sarlavhadan keyin

BLUE = colors.HexColor("#1428c8")
GREY = colors.HexColor("#8a8a8a")
LIGHT = colors.HexColor("#eef1fb")
FS = 9.5                          # asosiy shrift o'lchami

S_NUM = ParagraphStyle("num", fontName="Serif-Bold", fontSize=FS, leading=12.5, textColor=BLUE)
S_Q = ParagraphStyle("q", fontName="Serif", fontSize=FS, leading=12.5)
S_OPT = ParagraphStyle("opt", fontName="Serif", fontSize=FS, leading=12.5)
S_ANS = ParagraphStyle("ans", fontName="Serif", fontSize=FS, leading=12.5, spaceBefore=2)
S_SOL = ParagraphStyle("sol", fontName="Serif-Italic", fontSize=FS - 0.5, leading=12,
                       textColor=colors.HexColor("#555555"), spaceBefore=1)
S_HEAD = ParagraphStyle("head", fontName="Serif-Bold", fontSize=11, leading=15,
                        textColor=BLUE, spaceAfter=4)
S_CELL = ParagraphStyle("cell", fontName="Serif", fontSize=FS, leading=12, alignment=TA_CENTER)


def _t(text: str) -> str:
    """Matnni Paragraph uchun xavfsiz qiladi."""
    return escape(str(text)).replace("\n", "<br/>")


def new_test_id() -> str:
    """#T_D4J ko'rinishidagi qisqa Test ID."""
    return "#T_" + "".join(random.choices(string.ascii_uppercase + string.digits, k=3))


# ---------- Sahifa bezagi: suv belgi, tepa/past chiziqlar, sarlavha ----------
def _watermark(c):
    text = "©" + BRAND.lstrip("@")
    c.saveState()
    c.setFont("Serif-Italic", 30)
    c.setFillColor(colors.Color(0.55, 0.55, 0.55))
    c.setFillAlpha(0.15)
    step_x, step_y = 170, 140
    row, y = 0, -30
    while y < H + 120:
        x = -60 + (step_x / 2 if row % 2 else 0)
        while x < W + 120:
            c.saveState()
            c.translate(x, y)
            c.rotate(45)
            c.drawCentredString(0, 0, text)
            c.restoreState()
            x += step_x
        y += step_y
        row += 1
    c.restoreState()


def _decor(first: bool, col_top: float, title: str, test_id: str, subtitle: str):
    def draw(c, doc):
        _watermark(c)  # eng birinchi chiziladi, shuning uchun matn ortida qoladi
        c.saveState()
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.6)
        # tepa
        c.setFont("Serif-Bold", 9)
        c.setFillColor(colors.black)
        c.drawString(M, H - 26, test_id)
        c.setFont("Serif-Italic", 9)
        c.setFillColor(GREY)
        c.drawCentredString(W / 2, H - 26, BRAND)
        c.line(M, H - 32, W - M, H - 32)
        # past
        c.line(M, 40, W - M, 40)
        c.setFont("Serif-Italic", 8.5)
        c.drawCentredString(W / 2, 28, f"{BRAND}  •  Sahifa {doc.page}")
        # birinchi sahifa sarlavhasi
        if first:
            c.setFont("Serif-Bold", 15)
            c.setFillColor(BLUE)
            c.drawCentredString(W / 2, H - 62, title)
            c.setFont("Serif", 8.5)
            c.setFillColor(GREY)
            c.drawCentredString(W / 2, H - 76, f"Test ID: {test_id}")
            c.drawCentredString(W / 2, H - 88, subtitle)
        # ustunlar orasidagi chiziq
        c.setStrokeColor(colors.black)
        c.line(W / 2, COL_BOTTOM, W / 2, col_top)
        c.restoreState()
    return draw


def _column_frames(top: float, tag: str) -> list[Frame]:
    kw = dict(leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    h = top - COL_BOTTOM
    return [Frame(M, COL_BOTTOM, COL_W, h, id=f"{tag}L", **kw),
            Frame(W - M - COL_W, COL_BOTTOM, COL_W, h, id=f"{tag}R", **kw)]


def _build(path: Path, story: list, title: str, test_id: str, subtitle: str,
           doc_title: str, first_extra: list[Frame] | None = None,
           first_top: float = FIRST_TOP) -> None:
    doc = BaseDocTemplate(str(path), pagesize=A4, leftMargin=M, rightMargin=M,
                          topMargin=42, bottomMargin=COL_BOTTOM,
                          title=doc_title, author=BRAND)
    first = PageTemplate(
        id="first", frames=(first_extra or []) + _column_frames(first_top, "f"),
        onPage=_decor(True, first_top, title, test_id, subtitle))
    later = PageTemplate(
        id="later", frames=_column_frames(LATER_TOP, "l"),
        onPage=_decor(False, LATER_TOP, title, test_id, subtitle))
    doc.addPageTemplates([first, later])
    doc.build([NextPageTemplate("later")] + story)


# ---------- Savol bloklari ----------
def _options_table(options: dict, width: float) -> Table:
    """Variantlar sig'sa bir qatorda, bo'lmasa 2x2 yoki ustma-ust."""
    longest = max(stringWidth(f"A) {options[k]}", "Serif", FS) for k in "ABCD") + 10
    cols = 4 if longest <= width / 4 else 2 if longest <= width / 2 else 1
    cells = [Paragraph(f"<b>{k})</b> {_t(options[k])}", S_OPT) for k in "ABCD"]
    rows = [cells[i:i + cols] for i in range(0, 4, cols)]
    t = Table(rows, colWidths=[width / cols] * cols)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                           ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return t


def _numbered(i: int, parts: list) -> Table:
    """Ko'k raqam chapda, matn o'ngda (osilgan abzats)."""
    t = Table([[Paragraph(f"{i}.", S_NUM), parts]], colWidths=[NUM_W, COL_W - NUM_W])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return t


def _titles(kind: str, topic: str, level: str) -> tuple[str, str, str]:
    q_title = "Test Savollari" if kind == "test" else "Yozma Misollar"
    a_title = "Test Javoblari" if kind == "test" else "Yozma Javoblar"
    sub = f"Mavzu: {topic}  •  Daraja: {LEVELS[level]}  •  {date.today():%d.%m.%Y}"
    return q_title, a_title, sub


def make_questions_pdf(questions: list[dict], topic: str, level: str, kind: str,
                       test_id: str, path: Path) -> Path:
    title, _, sub = _titles(kind, topic, level)
    gap = 20 if kind == "test" else 64  # yozma misolda yechish uchun joy qoldiriladi
    story = []
    for i, q in enumerate(questions, 1):
        parts = [Paragraph(_t(q["question"]), S_Q)]
        if kind == "test":
            parts += [Spacer(1, 3), _options_table(q["options"], COL_W - NUM_W)]
        story.append(KeepTogether([_numbered(i, parts), Spacer(1, gap)]))
    _build(path, story, title, test_id, sub, f"{title} {test_id}")
    return path


def make_answers_pdf(questions: list[dict], topic: str, level: str, kind: str,
                     test_id: str, path: Path) -> Path:
    _, title, sub = _titles(kind, topic, level)
    full_w = W - 2 * M

    # 1) Javoblar kaliti: sahifa tepasida butun kenglikda
    per_row = 10 if kind == "test" else 5
    cells = []
    for i, q in enumerate(questions, 1):
        label = f"<b>{i}</b> – {_t(q['answer'])}" if kind == "test" \
            else f"<b>{i})</b> {_t(q['answer'])}"
        cells.append(Paragraph(label, S_CELL))
    rows = [cells[i:i + per_row] for i in range(0, len(cells), per_row)]
    rows[-1] += [""] * (per_row - len(rows[-1]))
    key = Table(rows, colWidths=[full_w / per_row] * per_row)
    key.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b8bfd8")),
                             ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("TOPPADDING", (0, 0), (-1, -1), 5),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    head = Paragraph("Javoblar kaliti", S_HEAD)
    key_h = head.wrap(full_w, 1000)[1] + key.wrap(full_w, 10000)[1] + 6
    first_top = FIRST_TOP - key_h - 12
    key_frame = Frame(M, first_top + 6, full_w, key_h, id="key", leftPadding=0,
                      rightPadding=0, topPadding=0, bottomPadding=0)

    story = [head, key, FrameBreak(), Paragraph("Yechimlar", S_HEAD)]

    # 2) Yechimlar: ikki ustunda
    for i, q in enumerate(questions, 1):
        parts = [Paragraph(_t(q["question"]), S_Q)]
        if kind == "test":
            parts.append(Paragraph(
                f"<b>Javob: {q['answer']})</b> {_t(q['options'][q['answer']])}", S_ANS))
        else:
            parts.append(Paragraph(f"<b>Javob:</b> {_t(q['answer'])}", S_ANS))
        if q.get("solution"):
            parts.append(Paragraph(f"Yechim: {_t(q['solution'])}", S_SOL))
        story.append(KeepTogether([_numbered(i, parts), Spacer(1, 9)]))

    _build(path, story, title, test_id, sub, f"{title} {test_id}",
           first_extra=[key_frame], first_top=first_top)
    return path


def make_pdfs(questions: list[dict], topic: str, level: str, kind: str,
              user_id: int) -> tuple[Path, Path, str]:
    """Savollar va javoblar PDF larini yasaydi. (savollar, javoblar, test_id) qaytaradi."""
    test_id = new_test_id()
    code = test_id.split("_", 1)[1]  # D4J
    folder = OUTPUT_DIR / f"{user_id}_{code}"
    folder.mkdir(parents=True, exist_ok=True)
    q = make_questions_pdf(questions, topic, level, kind, test_id, folder / f"Savollar_{code}.pdf")
    a = make_answers_pdf(questions, topic, level, kind, test_id, folder / f"Javoblar_{code}.pdf")
    return q, a, test_id
