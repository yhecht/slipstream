#!/usr/bin/env python3
"""Generate a printable cardiology report (PDF) from Slipstream / Garmin data.

The report summarises the cardiological signal that the Slipstream integration
actually captures - the **average heart rate of every recorded activity** -
together with training-load context, broken down by intensity, by sport, and
over time. It is meant to be printed and handed to a cardiologist.

IMPORTANT - data provenance & honesty
-------------------------------------
The Slipstream MCP connector serves *activity summaries* only. It does NOT
expose Garmin's daily wellness metrics, so the following are deliberately marked
as "not available in this dataset" rather than guessed:
    VO2max, HRV (e.g. RMSSD), resting heart rate, maximum heart rate per
    activity, SpO2, respiration, stress score, blood pressure.
The only per-activity cardiac field the connector returns is the average HR.

The records below were extracted from the live Slipstream MCP connector
(tool: list_activities) on 2026-06-19 and cover the connector's full available
window, 2026-05-21 to 2026-06-18.

Run:  python3 scripts/cardiology_report.py
Out:  reports/Kardiologie_Report_Garmin.pdf
"""
from __future__ import annotations

import datetime as dt
import os
import statistics
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm, mm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# --------------------------------------------------------------------------- #
# Patient / report metadata (edit freely before printing).
# --------------------------------------------------------------------------- #
PATIENT_NAME = "Yannique Hecht"
DEVICE = "Garmin (Slipstream Connect)"
DATA_SOURCE = "Slipstream MCP-Connector (Garmin Connect)"
GENERATED = dt.date(2026, 6, 19)
WINDOW_START = dt.date(2026, 5, 21)
WINDOW_END = dt.date(2026, 6, 18)

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
PDF_PATH = os.path.join(OUT_DIR, "Kardiologie_Report_Garmin.pdf")

# Clinical-ish palette.
NAVY = colors.HexColor("#1f3a5f")
ACCENT = colors.HexColor("#b0152b")  # cardiology red
SOFT = colors.HexColor("#f2f5f9")
GREY = colors.HexColor("#5a6573")
LINE = colors.HexColor("#c9d2dd")


# --------------------------------------------------------------------------- #
# Raw data - extracted from the Slipstream MCP (list_activities) on 2026-06-19.
# Fields available from the connector: date, name, sport type, distance (km),
# moving time, pace, average HR, elevation gain. Average HR is the only cardiac
# field exposed.
# --------------------------------------------------------------------------- #
@dataclass
class Act:
    date: str
    name: str
    sport: str
    dist_km: float | None
    moving: str
    pace: str | None
    avg_hr: int | None
    elev_m: int | None


RAW: list[Act] = [
    Act("2026-05-21", "HIIT", "Workout", None, "18:57", None, 131, None),
    Act("2026-05-22", "Munich Gravel Cycling", "Ride", 39.167, "1:33:01", "2:22/km", 148, 116),
    Act("2026-05-22", "Yoga", "Yoga", None, "27:43", None, 92, None),
    Act("2026-05-23", "Munich Running", "Run", 5.421, "36:11", "6:40/km", 156, 9),
    Act("2026-05-23", "Yoga", "Yoga", None, "22:01", None, 88, None),
    Act("2026-05-25", "Yoga", "Yoga", None, "30:52", None, 85, None),
    Act("2026-05-26", "Munich Walking", "Walk", 0.164, "2:07", "12:54/km", 103, 2),
    Act("2026-05-26", "Munich Walking", "Walk", 6.595, "1:16:23", "11:35/km", 112, 20),
    Act("2026-05-26", "Yoga", "Yoga", None, "23:36", None, 87, None),
    Act("2026-05-27", "HIIT", "Workout", None, "19:08", None, 116, None),
    Act("2026-05-27", "Yoga", "Yoga", None, "23:36", None, 75, None),
    Act("2026-05-29", "Munich Running", "Run", 5.285, "32:14", "6:06/km", 162, 8),
    Act("2026-05-30", "Strength", "Strength", None, "32:01", None, 129, None),
    Act("2026-05-30", "Yoga", "Yoga", None, "20:52", None, 90, None),
    Act("2026-05-31", "Yoga", "Yoga", None, "18:49", None, 91, None),
    Act("2026-06-01", "Munich Running", "Run", 5.103, "28:59", "5:41/km", 166, 9),
    Act("2026-06-01", "Yoga", "Yoga", None, "30:06", None, 86, None),
    Act("2026-06-02", "Yoga", "Yoga", None, "41:44", None, 78, None),
    Act("2026-06-03", "HIIT", "Workout", None, "43:04", None, 136, None),
    Act("2026-06-04", "Munich Running", "Run", 6.289, "39:00", "6:12/km", 160, 10),
    Act("2026-06-04", "Yoga", "Yoga", None, "37:15", None, 97, None),
    Act("2026-06-06", "HIIT", "Workout", None, "31:58", None, 125, None),
    Act("2026-06-07", "Munich Running", "Run", 8.262, "49:07", "5:57/km", 162, 15),
    Act("2026-06-08", "Strength", "Strength", None, "11:39", None, 112, None),
    Act("2026-06-10", "Yoga", "Yoga", None, "19:37", None, 87, None),
    Act("2026-06-12", "Munich Walking", "Walk", 2.442, "27:58", "11:27/km", 109, 3),
    Act("2026-06-13", "Munich Running", "Run", 5.748, "38:19", "6:40/km", 158, 54),
    Act("2026-06-14", "Strength", "Strength", None, "55:58", None, 102, None),
    Act("2026-06-15", "Munich Cycling", "Ride", 46.933, "2:00:05", "2:34/km", 141, 229),
    Act("2026-06-15", "Yoga", "Yoga", None, "29:09", None, 91, None),
    Act("2026-06-16", "Strength", "Strength", None, "42:51", None, 126, None),
    Act("2026-06-17", "Yoga", "Yoga", None, "16:01", None, 83, None),
    Act("2026-06-18", "HIIT", "Workout", None, "23:16", None, 106, None),
]

# Clinical load grouping: from recovery (Yoga) up to high-intensity (Run).
LOAD_GROUP = {
    "Yoga": ("Ruhe / Regeneration", 0),
    "Walk": ("Leicht", 1),
    "Strength": ("Moderat (Kraft)", 2),
    "Workout": ("Submaximal (HIIT)", 3),
    "Ride": ("Submaximal (Ausdauer)", 4),
    "Run": ("Hoch (Ausdauer)", 5),
}


def _moving_to_min(s: str) -> float:
    parts = [int(p) for p in s.split(":")]
    if len(parts) == 3:
        h, m, sec = parts
    else:
        h, m, sec = 0, parts[0], parts[1]
    return h * 60 + m + sec / 60.0


# --------------------------------------------------------------------------- #
# Chart builders (saved as PNG, embedded into the PDF).
# --------------------------------------------------------------------------- #
def _style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#c9d2dd")
    ax.spines["bottom"].set_color("#c9d2dd")
    ax.tick_params(colors="#5a6573", labelsize=8)
    ax.yaxis.label.set_color("#5a6573")
    ax.xaxis.label.set_color("#5a6573")
    ax.grid(axis="y", color="#e6ebf1", linewidth=0.8)
    ax.set_axisbelow(True)


SPORT_COLORS = {
    "Yoga": "#4c9f70", "Walk": "#88b04b", "Strength": "#f0a202",
    "Workout": "#e36414", "Ride": "#3a86c8", "Run": "#b0152b",
}


def chart_timeline(path: str):
    dates = [dt.date.fromisoformat(a.date) for a in RAW]
    hrs = [a.avg_hr for a in RAW]
    cols = [SPORT_COLORS.get(a.sport, "#888") for a in RAW]
    fig, ax = plt.subplots(figsize=(7.2, 2.9), dpi=150)
    ax.plot(dates, hrs, color="#1f3a5f", linewidth=1.0, alpha=0.5, zorder=1)
    ax.scatter(dates, hrs, c=cols, s=42, zorder=3, edgecolors="white", linewidths=0.6)
    _style_axes(ax)
    ax.set_ylabel("Durchschn. HF (bpm)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    fig.autofmt_xdate(rotation=0, ha="center")
    handles = [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=c,
                          markersize=7, label=s) for s, c in SPORT_COLORS.items()]
    ax.legend(handles=handles, ncol=6, fontsize=7, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, 1.18))
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def chart_by_sport(path: str):
    order = sorted(SPORT_COLORS, key=lambda s: LOAD_GROUP[s][1])
    means, cols, labels = [], [], []
    for s in order:
        vals = [a.avg_hr for a in RAW if a.sport == s and a.avg_hr]
        means.append(statistics.mean(vals))
        cols.append(SPORT_COLORS[s])
        labels.append(f"{s}\n(n={len(vals)})")
    fig, ax = plt.subplots(figsize=(7.2, 2.7), dpi=150)
    bars = ax.bar(labels, means, color=cols, width=0.62)
    _style_axes(ax)
    ax.set_ylabel("Durchschn. HF (bpm)")
    ax.set_ylim(0, max(means) * 1.18)
    for b, m in zip(bars, means):
        ax.text(b.get_x() + b.get_width() / 2, m + 2, f"{m:.0f}",
                ha="center", va="bottom", fontsize=8, color="#1f3a5f", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def chart_distribution(path: str):
    hrs = [a.avg_hr for a in RAW if a.avg_hr]
    fig, ax = plt.subplots(figsize=(7.2, 2.5), dpi=150)
    bins = list(range(70, 180, 10))
    ax.hist(hrs, bins=bins, color="#3a86c8", edgecolor="white", alpha=0.9)
    _style_axes(ax)
    ax.set_xlabel("Durchschn. HF je Aktivität (bpm)")
    ax.set_ylabel("Anzahl Aktivitäten")
    mean = statistics.mean(hrs)
    ax.axvline(mean, color="#b0152b", linewidth=1.4, linestyle="--")
    ax.text(mean + 1.5, ax.get_ylim()[1] * 0.86, f"Mittel {mean:.0f}",
            color="#b0152b", fontsize=8, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------- #
# PDF assembly.
# --------------------------------------------------------------------------- #
def _styles():
    ss = getSampleStyleSheet()
    out = {}
    out["title"] = ParagraphStyle("title", parent=ss["Title"], fontSize=20,
                                  textColor=NAVY, spaceAfter=2, leading=23)
    out["subtitle"] = ParagraphStyle("subtitle", fontSize=10.5, textColor=GREY, spaceAfter=2)
    out["h2"] = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=13,
                               textColor=NAVY, spaceBefore=12, spaceAfter=5, leading=15)
    out["h3"] = ParagraphStyle("h3", parent=ss["Heading3"], fontSize=10.5,
                               textColor=ACCENT, spaceBefore=8, spaceAfter=3)
    out["body"] = ParagraphStyle("body", parent=ss["BodyText"], fontSize=9.5,
                                 leading=14, textColor=colors.HexColor("#22272e"))
    out["small"] = ParagraphStyle("small", fontSize=8, leading=11, textColor=GREY)
    out["note"] = ParagraphStyle("note", fontSize=8.7, leading=12.5,
                                 textColor=colors.HexColor("#22272e"))
    out["cellL"] = ParagraphStyle("cellL", fontSize=8.4, leading=10.5, alignment=TA_LEFT)
    out["cellC"] = ParagraphStyle("cellC", fontSize=8.4, leading=10.5, alignment=TA_CENTER)
    out["kpibig"] = ParagraphStyle("kpibig", fontSize=21, leading=22, alignment=TA_CENTER,
                                   textColor=NAVY, fontName="Helvetica-Bold")
    out["kpilbl"] = ParagraphStyle("kpilbl", fontSize=7.6, leading=9, alignment=TA_CENTER,
                                   textColor=GREY)
    return out


def kpi_card(value, label, st, accent=False):
    col = "#b0152b" if accent else "#1f3a5f"
    v = Paragraph(f'<font color="{col}">{value}</font>', st["kpibig"])
    l = Paragraph(label, st["kpilbl"])
    t = Table([[v], [l]], colWidths=[3.55 * cm], rowHeights=[0.95 * cm, 0.85 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
    ]))
    return t


def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    img_dir = os.path.join(OUT_DIR, "_img")
    os.makedirs(img_dir, exist_ok=True)
    p_timeline = os.path.join(img_dir, "timeline.png")
    p_sport = os.path.join(img_dir, "by_sport.png")
    p_dist = os.path.join(img_dir, "dist.png")
    chart_timeline(p_timeline)
    chart_by_sport(p_sport)
    chart_distribution(p_dist)

    st = _styles()
    hrs = [a.avg_hr for a in RAW if a.avg_hr]
    n = len(RAW)
    total_min = sum(_moving_to_min(a.moving) for a in RAW)
    total_dist = sum(a.dist_km or 0 for a in RAW)
    mean_hr = statistics.mean(hrs)
    median_hr = statistics.median(hrs)
    sd_hr = statistics.pstdev(hrs)
    min_hr = min(hrs)
    max_hr = max(hrs)
    min_act = next(a for a in RAW if a.avg_hr == min_hr)
    max_act = next(a for a in RAW if a.avg_hr == max_hr)
    n_days = (WINDOW_END - WINDOW_START).days + 1

    doc = SimpleDocTemplate(
        PDF_PATH, pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
        topMargin=1.4 * cm, bottomMargin=1.4 * cm,
        title="Kardiologischer Aktivitaets- und Herzfrequenz-Report",
        author="Slipstream / Garmin",
    )
    E = []

    # ---- Header -------------------------------------------------------- #
    E.append(Paragraph("Kardiologischer Aktivitäts- &amp; Herzfrequenz-Report", st["title"]))
    E.append(Paragraph("Auswertung der Garmin-Trainingsdaten für die kardiologische Sprechstunde",
                       st["subtitle"]))
    E.append(Spacer(1, 4))
    E.append(HRFlowable(width="100%", thickness=1.4, color=ACCENT, spaceBefore=2, spaceAfter=8))

    meta = Table([
        [Paragraph("<b>Patient</b>", st["small"]), Paragraph(PATIENT_NAME, st["small"]),
         Paragraph("<b>Auswertungszeitraum</b>", st["small"]),
         Paragraph(f"{WINDOW_START.strftime('%d.%m.%Y')} – {WINDOW_END.strftime('%d.%m.%Y')} ({n_days} Tage)", st["small"])],
        [Paragraph("<b>Gerät / Quelle</b>", st["small"]), Paragraph(DEVICE, st["small"]),
         Paragraph("<b>Aufgezeichnete Einheiten</b>", st["small"]),
         Paragraph(f"{n} Aktivitäten", st["small"])],
        [Paragraph("<b>Report erstellt</b>", st["small"]), Paragraph(GENERATED.strftime("%d.%m.%Y"), st["small"]),
         Paragraph("<b>Datenquelle</b>", st["small"]), Paragraph(DATA_SOURCE, st["small"])],
    ], colWidths=[3.0 * cm, 5.0 * cm, 4.0 * cm, 4.8 * cm])
    meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    E.append(meta)
    E.append(Spacer(1, 9))

    # ---- Data-provenance note (honesty box) ---------------------------- #
    E.append(Paragraph("Wichtiger Hinweis zur Datengrundlage", st["h3"]))
    note = (
        "Diese Auswertung basiert ausschließlich auf den <b>Aktivitäts-Zusammenfassungen</b>, "
        "die der Garmin-/Slipstream-Connector bereitstellt. Der pro Einheit verfügbare "
        "kardiologische Messwert ist die <b>durchschnittliche Herzfrequenz</b>. "
        "Folgende, häufig erfragte Werte sind in diesem Datensatz <b>nicht enthalten</b> und "
        "wurden bewusst nicht geschätzt: <b>VO₂max, HRV (z. B. RMSSD), Ruhepuls, maximale "
        "Herzfrequenz pro Einheit, SpO₂, Atemfrequenz, Stress-Score, Blutdruck.</b> "
        "Diese Tagesmetriken werden von der aktuellen Integration nicht abgerufen. "
        "Außerdem reicht der verfügbare Datenzeitraum nur bis zum <b>21.05.2026</b> zurück – "
        "Daten ab Dezember liegen in der Integration derzeit nicht vor."
    )
    nbox = Table([[Paragraph(note, st["note"])]], colWidths=[16.8 * cm])
    nbox.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff6f1")),
        ("BOX", (0, 0), (-1, -1), 0.6, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    E.append(nbox)
    E.append(Spacer(1, 11))

    # ---- KPI row ------------------------------------------------------- #
    E.append(Paragraph("Kardiologische Kennzahlen im Überblick", st["h2"]))
    kpis = [
        kpi_card(f"{mean_hr:.0f}", "Ø HF über alle<br/>Einheiten (bpm)", st, accent=True),
        kpi_card(f"{min_hr}", "Niedrigste Ø-HF<br/>(Ruhe/Yoga, bpm)", st),
        kpi_card(f"{max_hr}", "Höchste Ø-HF<br/>(Belastung/Lauf, bpm)", st, accent=True),
        kpi_card(f"{median_hr:.0f}", "Median Ø-HF<br/>(bpm)", st),
        kpi_card(f"{n}", "Aufgezeichnete<br/>Einheiten", st),
    ]
    krow = Table([kpis], colWidths=[3.62 * cm] * 5)
    krow.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("LEFTPADDING", (0, 0), (-1, -1), 2),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 2)]))
    E.append(krow)
    E.append(Spacer(1, 6))
    E.append(Paragraph(
        f"Spannweite der durchschnittlichen Herzfrequenzen: <b>{min_hr}–{max_hr} bpm</b> "
        f"(Standardabweichung {sd_hr:.0f} bpm). Niedrigster Wert bei „{min_act.name}“ "
        f"({min_act.date}), höchster Wert bei „{max_act.name}“ ({max_act.date}). "
        "Die Werte verhalten sich physiologisch erwartbar: niedrige Frequenzen in Ruhe-/"
        "Regenerationseinheiten (Yoga), hohe Frequenzen unter Ausdauerbelastung (Laufen).",
        st["body"]))
    E.append(Spacer(1, 6))

    # ---- Executive summary --------------------------------------------- #
    E.append(Paragraph("Zusammenfassung für die Sprechstunde", st["h2"]))
    summary = (
        f"Im Zeitraum vom {WINDOW_START.strftime('%d.%m.')} bis {WINDOW_END.strftime('%d.%m.%Y')} "
        f"({n_days} Tage) wurden <b>{n} Trainingseinheiten</b> mit einer Gesamt-Bewegungszeit von "
        f"<b>{total_min/60:.1f} Stunden</b> und einer Ausdauer-Distanz von <b>{total_dist:.0f} km</b> "
        "(Laufen + Radfahren + Gehen) aufgezeichnet. Das Aktivitätsprofil ist breit angelegt und "
        "kombiniert regenerative Einheiten (Yoga, 13×), moderate Kraft- und Intervalleinheiten sowie "
        "intensive Ausdauerbelastungen (Laufen, Radfahren).<br/><br/>"
        f"Die durchschnittliche Herzfrequenz über alle Einheiten liegt bei <b>{mean_hr:.0f} bpm</b>. "
        "Unter intensiver Ausdauerbelastung (Laufen) werden im Mittel rund <b>161 bpm</b> erreicht, "
        f"mit einem Spitzenwert der Durchschnitts-HF von <b>{max_hr} bpm</b>. In Regenerationseinheiten "
        "fällt die mittlere Herzfrequenz auf <b>75–97 bpm</b> ab. Die saubere Differenzierung der "
        "Herzfrequenz zwischen Belastung und Ruhe sowie der erkennbare Abfall in Erholungsphasen sind "
        "Hinweise auf eine angemessene kardiale Belastungs- und Erholungsregulation. "
        "Auffällige Ausreißer (z. B. unerwartet hohe HF bei geringer Belastung) finden sich in den "
        "Rohdaten nicht. <i>Hinweis: Diese Auswertung ersetzt keine ärztliche Diagnostik; sie dient "
        "ausschließlich als strukturierte Übersicht der getragenen Trainingsdaten.</i>"
    )
    E.append(Paragraph(summary, st["body"]))

    E.append(PageBreak())

    # ---- Charts -------------------------------------------------------- #
    E.append(Paragraph("Trendanalyse", st["h2"]))
    E.append(Paragraph("Durchschnittliche Herzfrequenz je Einheit im Zeitverlauf", st["h3"]))
    E.append(Image(p_timeline, width=16.8 * cm, height=6.8 * cm))
    E.append(Spacer(1, 4))
    E.append(Paragraph(
        "Jeder Punkt ist eine Trainingseinheit (Farbe = Sportart). Die klar getrennten Bänder zeigen "
        "die belastungsabhängige Herzfrequenz: Yoga/Gehen im unteren, Laufen im oberen Bereich. "
        "Über den Zeitraum ist kein auffälliger Anstieg oder Drift der belastungsbezogenen "
        "Herzfrequenz erkennbar.", st["small"]))
    E.append(Spacer(1, 10))

    E.append(Paragraph("Mittlere Herzfrequenz nach Belastungsart (aufsteigend)", st["h3"]))
    E.append(Image(p_sport, width=16.8 * cm, height=6.3 * cm))
    E.append(Spacer(1, 10))

    E.append(Paragraph("Verteilung der durchschnittlichen Herzfrequenzen", st["h3"]))
    E.append(Image(p_dist, width=16.8 * cm, height=5.8 * cm))

    E.append(PageBreak())

    # ---- Breakdown by load / sport ------------------------------------- #
    E.append(Paragraph("Aufschlüsselung nach Belastung &amp; Sportart", st["h2"]))
    head = ["Belastungsstufe", "Sportart", "Einheiten", "Ø HF", "Min HF", "Max HF", "Σ Zeit", "Σ Distanz"]
    rows = [[Paragraph(f"<b>{h}</b>", st["cellC"]) for h in head]]
    for s in sorted(SPORT_COLORS, key=lambda x: LOAD_GROUP[x][1]):
        acts = [a for a in RAW if a.sport == s]
        vals = [a.avg_hr for a in acts if a.avg_hr]
        mins = sum(_moving_to_min(a.moving) for a in acts)
        dist = sum(a.dist_km or 0 for a in acts)
        rows.append([
            Paragraph(LOAD_GROUP[s][0], st["cellL"]),
            Paragraph(s, st["cellL"]),
            Paragraph(str(len(acts)), st["cellC"]),
            Paragraph(f"{statistics.mean(vals):.0f}", st["cellC"]),
            Paragraph(str(min(vals)), st["cellC"]),
            Paragraph(str(max(vals)), st["cellC"]),
            Paragraph(f"{mins/60:.1f} h" if mins >= 60 else f"{mins:.0f} min", st["cellC"]),
            Paragraph(f"{dist:.1f} km" if dist else "–", st["cellC"]),
        ])
    # Overall row
    rows.append([
        Paragraph("<b>Gesamt</b>", st["cellL"]), Paragraph("<b>alle</b>", st["cellL"]),
        Paragraph(f"<b>{n}</b>", st["cellC"]), Paragraph(f"<b>{mean_hr:.0f}</b>", st["cellC"]),
        Paragraph(f"<b>{min_hr}</b>", st["cellC"]), Paragraph(f"<b>{max_hr}</b>", st["cellC"]),
        Paragraph(f"<b>{total_min/60:.1f} h</b>", st["cellC"]),
        Paragraph(f"<b>{total_dist:.0f} km</b>", st["cellC"]),
    ])
    tbl = Table(rows, colWidths=[3.7 * cm, 2.5 * cm, 1.7 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm, 2.0 * cm, 2.4 * cm],
                repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, SOFT]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e7edf4")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, NAVY),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, NAVY),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    E.append(tbl)
    E.append(Spacer(1, 5))
    E.append(Paragraph(
        "„Min HF“ und „Max HF“ bezeichnen hier die niedrigste bzw. höchste <i>durchschnittliche</i> "
        "Herzfrequenz einer Einheit innerhalb der Gruppe (Momentan-Maxima werden vom Connector nicht "
        "übermittelt).", st["small"]))
    E.append(Spacer(1, 10))

    # ---- Belastung vs. Ruhe summary ------------------------------------ #
    E.append(Paragraph("Belastung vs. Ruhe – kardiale Antwort", st["h3"]))
    rest = [a.avg_hr for a in RAW if a.sport in ("Yoga",)]
    light = [a.avg_hr for a in RAW if a.sport in ("Walk", "Strength")]
    submax = [a.avg_hr for a in RAW if a.sport in ("Workout", "Ride")]
    high = [a.avg_hr for a in RAW if a.sport in ("Run",)]
    comp = [
        ["Kategorie", "Einheiten (Beispiele)", "Ø HF (bpm)", "Bereich (bpm)"],
        ["Ruhe / Regeneration", "Yoga", f"{statistics.mean(rest):.0f}", f"{min(rest)}–{max(rest)}"],
        ["Leicht–moderat", "Gehen, Kraft", f"{statistics.mean(light):.0f}", f"{min(light)}–{max(light)}"],
        ["Submaximal", "HIIT, Radfahren", f"{statistics.mean(submax):.0f}", f"{min(submax)}–{max(submax)}"],
        ["Hohe Belastung", "Laufen", f"{statistics.mean(high):.0f}", f"{min(high)}–{max(high)}"],
    ]
    comp_rows = [[Paragraph(f"<b>{c}</b>" if i == 0 else c, st["cellL"] if j < 2 else st["cellC"])
                  for j, c in enumerate(r)] for i, r in enumerate(comp)]
    ctbl = Table(comp_rows, colWidths=[4.2 * cm, 5.6 * cm, 3.0 * cm, 4.0 * cm])
    ctbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34506f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    E.append(ctbl)

    E.append(PageBreak())

    # ---- Raw data table ------------------------------------------------- #
    E.append(Paragraph("Rohdaten – alle aufgezeichneten Einheiten", st["h2"]))
    E.append(Paragraph(
        "Vollständige, ungefilterte Liste der vom Connector gelieferten Einheiten "
        "(chronologisch). Dies sind die Quelldaten aller obigen Auswertungen.", st["small"]))
    E.append(Spacer(1, 5))
    rhead = ["Datum", "Aktivität", "Sportart", "Distanz", "Bewegungszeit", "Pace", "Ø HF (bpm)", "Höhenm."]
    rrows = [[Paragraph(f"<b>{h}</b>", st["cellC"]) for h in rhead]]
    for a in RAW:
        rrows.append([
            Paragraph(dt.date.fromisoformat(a.date).strftime("%d.%m.%Y"), st["cellC"]),
            Paragraph(a.name, st["cellL"]),
            Paragraph(a.sport, st["cellL"]),
            Paragraph(f"{a.dist_km:.2f} km" if a.dist_km else "–", st["cellC"]),
            Paragraph(a.moving, st["cellC"]),
            Paragraph(a.pace or "–", st["cellC"]),
            Paragraph(str(a.avg_hr) if a.avg_hr else "–", st["cellC"]),
            Paragraph(f"{a.elev_m} m" if a.elev_m else "–", st["cellC"]),
        ])
    rtbl = Table(rrows, repeatRows=1,
                 colWidths=[2.0 * cm, 3.5 * cm, 2.0 * cm, 1.9 * cm, 2.4 * cm, 1.9 * cm, 1.7 * cm, 1.4 * cm])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
    ]
    # Highlight HR cell by intensity.
    for i, a in enumerate(RAW, start=1):
        if a.avg_hr and a.avg_hr >= 155:
            style.append(("TEXTCOLOR", (6, i), (6, i), ACCENT))
            style.append(("FONTNAME", (6, i), (6, i), "Helvetica-Bold"))
    rtbl.setStyle(TableStyle(style))
    E.append(rtbl)
    E.append(Spacer(1, 8))

    # ---- Footer / disclaimer ------------------------------------------- #
    E.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=4, spaceAfter=6))
    E.append(Paragraph(
        "<b>Methodik &amp; Hinweise.</b> Datenquelle: Garmin Connect über den Slipstream-MCP-Connector, "
        f"extrahiert am {GENERATED.strftime('%d.%m.%Y')}. Pro Einheit ist als kardiologischer Messwert "
        "ausschließlich die durchschnittliche Herzfrequenz verfügbar; Momentan-Maxima, Ruhepuls, HRV, "
        "VO₂max und SpO₂ sind in diesem Datensatz nicht enthalten. Alle aggregierten Werte (Mittel, "
        "Median, Min/Max, Standardabweichung) wurden direkt aus den Rohdaten dieser Tabelle berechnet. "
        "Dieser Report ist eine strukturierte Datenübersicht und stellt keine medizinische Diagnose dar.",
        st["small"]))
    E.append(Spacer(1, 4))
    E.append(Paragraph(
        f"Erstellt mit Slipstream · Patient: {PATIENT_NAME} · "
        f"Zeitraum {WINDOW_START.strftime('%d.%m.%Y')}–{WINDOW_END.strftime('%d.%m.%Y')} · "
        f"Seite generiert am {GENERATED.strftime('%d.%m.%Y')}", st["small"]))

    def _page_footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(GREY)
        canvas.drawRightString(A4[0] - 1.6 * cm, 0.8 * cm, f"Seite {doc_.page}")
        canvas.drawString(1.6 * cm, 0.8 * cm,
                          "Kardiologie-Report · Garmin/Slipstream · vertraulich")
        canvas.setStrokeColor(LINE)
        canvas.line(1.6 * cm, 1.1 * cm, A4[0] - 1.6 * cm, 1.1 * cm)
        canvas.restoreState()

    doc.build(E, onFirstPage=_page_footer, onLaterPages=_page_footer)
    print(f"Wrote {PDF_PATH}")


if __name__ == "__main__":
    build()
