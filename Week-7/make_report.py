"""Build REPORT.md and the one-page REPORT.pdf from the metrics/ files.

Usage: python make_report.py
"""

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = Path(__file__).resolve().parent
DATASETS = {"fashion": ("Fashion-MNIST", HERE / "fashion-mnist"),
            "cifar": ("CIFAR-10", HERE / "cifar10")}
INK, MUTED, RULE, HEAD_BG = "#1f2430", "#5b6170", "#d9dce3", "#eef1f6"


def load(folder, name):
    return json.loads((folder / "metrics" / name).read_text(encoding="utf-8"))


def collect():
    data = {}
    for key, (title, folder) in DATASETS.items():
        data[key] = {"title": title, "folder": folder.name,
                     "base": load(folder, "baseline.json"), "opt": load(folder, "optimized.json"),
                     "hpo": load(folder, "best_params.json"),
                     "imp": load(folder, "param_importances.json")}
    return data


def fmt_time(sec):
    return f"{sec / 60:.1f} min" if sec >= 60 else f"{sec:.0f} s"


def fmt_value(v):
    if isinstance(v, bool):
        return "on" if v else "off"
    if isinstance(v, float):
        return f"{v:.2e}" if v < 0.01 else f"{v:.3f}"
    return str(v)


def epochs_text(m):
    if "best_epoch" in m:
        return f"{m['epochs']} (best {m['best_epoch']})"
    return str(m["epochs"])


def results_rows(d):
    header = ["", "Fashion baseline", "Fashion optimized", "CIFAR baseline", "CIFAR optimized"]
    runs = [d["fashion"]["base"], d["fashion"]["opt"], d["cifar"]["base"], d["cifar"]["opt"]]
    rows = [
        ["Test accuracy"] + [f"{100 * m['test_accuracy']:.2f}%" for m in runs],
        ["Test loss"] + [f"{m['test_loss']:.3f}" for m in runs],
        ["Epochs"] + [epochs_text(m) for m in runs],
        ["Training time"] + [fmt_time(m["train_time_sec"]) for m in runs],
        ["Parameters"] + [f"{m['num_parameters']:,}" for m in runs],
    ]
    hpo = ["HPO (trials, time)", "–", f"{d['fashion']['hpo']['n_trials']} x "
           f"{d['fashion']['hpo']['epochs_per_trial']} ep, {fmt_time(d['fashion']['hpo']['hpo_time_sec'])}",
           "–", f"{d['cifar']['hpo']['n_trials']} x {d['cifar']['hpo']['epochs_per_trial']} ep, "
           f"{fmt_time(d['cifar']['hpo']['hpo_time_sec'])}"]
    return header, rows + [hpo]


def params_text(p):
    return ", ".join(f"{k}={fmt_value(v)}" for k, v in p.items())


def insights(d):
    """Commentary sentences with the measured numbers."""
    lines = []
    for key in ("fashion", "cifar"):
        x = d[key]
        b, o = x["base"]["test_accuracy"], x["opt"]["test_accuracy"]
        top, share = next(iter(x["imp"].items()))
        lines.append(
            f"<b>{x['title']}:</b> test accuracy {100 * b:.2f}% &rarr; {100 * o:.2f}% "
            f"(<b>{100 * (o - b):+.2f} pp</b>, error rate {100 * (1 - b):.1f}% &rarr; "
            f"{100 * (1 - o):.1f}%), test loss {x['base']['test_loss']:.3f} &rarr; "
            f"{x['opt']['test_loss']:.3f}. Most important hyperparameter (fANOVA): "
            f"<b>{top}</b> ({100 * share:.0f}% of the explained variance).")
    return lines


LIMITATIONS = [
    "<b>Compute:</b> everything ran on one laptop GPU (RTX 3050 Ti, 4 GB); the Docker/Cog "
    "containers serve the models on CPU. This limited the budget to short trials.",
    "<b>Few, short trials:</b> {f_trials} trials (Fashion) and {c_trials} trials (CIFAR) of 3 "
    "epochs each, with median pruning; no trial was too slow, so the planned budget was kept. "
    "Short trials favour settings that learn fast: on CIFAR-10 the search turned augmentation "
    "off, and the final model overfit (train loss {c_train_loss:.2f} vs. validation loss "
    "{c_val_loss:.2f} at the best epoch) and stopped early at epoch {c_epochs}, so longer trials "
    "would likely pick augmentation. The importance values come from only "
    "{f_complete}/{c_complete} complete trials and are rough.",
    "<b>Test set kept out of the search:</b> HPO and best-epoch selection used only a fixed 10% "
    "validation split of the training set, so the test accuracy is an honest estimate. The "
    "optimized models therefore trained on 90% of the training data, the baselines on 100%.",
    "<b>One seed, one split:</b> no repeated runs, so differences below ~0.5 pp should not be "
    "over-interpreted.",
]


def limitations(d):
    values = {"f_trials": d["fashion"]["hpo"]["n_trials"], "c_trials": d["cifar"]["hpo"]["n_trials"],
              "f_complete": d["fashion"]["hpo"]["n_complete"],
              "c_complete": d["cifar"]["hpo"]["n_complete"]}
    opt = d["cifar"]["opt"]
    best = opt["history"][opt["best_epoch"] - 1]
    values.update(c_train_loss=best["train_loss"], c_val_loss=best["val_loss"],
                  c_epochs=opt["epochs"])
    return [line.format(**values) for line in LIMITATIONS]


INTRO = ("Baselines follow the PyTorch tutorials exactly (Quickstart MLP for Fashion-MNIST; the "
         "\"Training a Classifier\" CNN for CIFAR-10). The optimized models come from an Optuna "
         "search (TPE sampler, seed 42, MedianPruner) on a 10% validation split, then a longer "
         "final training run that keeps the best validation epoch.")

WHY = ("Same data and framework; only the training settings and the model size (and, for "
       "CIFAR-10, a configurable CNN instead of the tiny tutorial net) were chosen by the search. "
       "The error rate fell by a factor of about 2.4-3.4 on the two datasets. The tutorial settings "
       "demonstrate the API rather than aim for accuracy, so a systematic search pays off quickly "
       "even with a small budget, and the right learning rate matters more than the optimizer name.")


# ---------------------------------------------------------------- Markdown

def write_markdown(d):
    header, rows = results_rows(d)
    md = ["# Week 7 — Baseline vs. HPO-Optimized Models", "", INTRO, "",
          "## Results (test set)", "",
          "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    md += ["| " + " | ".join(r) + " |" for r in rows]
    md += ["", "## Best hyperparameters", ""]
    for key in ("fashion", "cifar"):
        x = d[key]
        md.append(f"- **{x['title']}** (val acc {100 * x['hpo']['best_val_accuracy']:.2f}%, trial "
                  f"{x['hpo']['best_trial']}): {params_text(x['hpo']['params'])}")
    md += ["", "## Optimization history", "",
           "| Fashion-MNIST | CIFAR-10 |", "|---|---|",
           "| ![Fashion-MNIST](fashion-mnist/metrics/optimization_history.png) | "
           "![CIFAR-10](cifar10/metrics/optimization_history.png) |", "",
           "## Why hyperparameter optimization matters", "", WHY, ""]
    md += ["- " + strip_tags(s) for s in insights(d)]
    md += ["", "## Limitations", ""]
    md += ["- " + strip_tags(s) for s in limitations(d)]
    (HERE / "REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def strip_tags(text):
    return (text.replace("<b>", "**").replace("</b>", "**")
            .replace("&rarr;", "→"))


# ---------------------------------------------------------------- PDF

def write_pdf(d):
    page_count = {"n": 0}

    def on_page(canvas, doc):
        page_count["n"] += 1

    doc = SimpleDocTemplate(str(HERE / "REPORT.pdf"), pagesize=A4, title="Week 7 performance report",
                            leftMargin=1.4 * cm, rightMargin=1.4 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.0 * cm)
    width = A4[0] - doc.leftMargin - doc.rightMargin
    title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=14, leading=17,
                           textColor=INK, spaceAfter=2)
    h = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=9.5, leading=12,
                       textColor=INK, spaceBefore=5, spaceAfter=2)
    body = ParagraphStyle("b", fontName="Helvetica", fontSize=8, leading=10.2,
                          textColor=INK, alignment=TA_LEFT)
    small = ParagraphStyle("s", parent=body, fontSize=7.5, leading=9.4)
    cell = ParagraphStyle("c", parent=body, fontSize=7.8, leading=9.6)

    story = [Paragraph("Week 7 — Baseline vs. HPO-Optimized Models (Fashion-MNIST &amp; CIFAR-10)", title),
             Paragraph(INTRO, small)]

    header, rows = results_rows(d)
    story.append(Paragraph("Results on the test set", h))
    table = Table([header] + rows, colWidths=[3.2 * cm] + [(width - 3.2 * cm) / 4] * 4)
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 7.8),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.8),
        ("FONT", (0, 1), (0, -1), "Helvetica-Bold", 7.8),
        ("FONT", (2, 1), (2, 1), "Helvetica-Bold", 7.8),
        ("FONT", (4, 1), (4, 1), "Helvetica-Bold", 7.8),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(INK)),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(HEAD_BG)),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor(RULE)),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(table)

    story.append(Paragraph("Best hyperparameters (from the validation split)", h))
    prow = []
    for key in ("fashion", "cifar"):
        x = d[key]
        prow.append(Paragraph(f"<b>{x['title']}</b> — val acc {100 * x['hpo']['best_val_accuracy']:.2f}% "
                              f"(trial {x['hpo']['best_trial']}): {params_text(x['hpo']['params'])}", cell))
    ptable = Table([prow], colWidths=[width / 2] * 2)
    ptable.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor(RULE)),
                                ("LINEAFTER", (0, 0), (0, 0), 0.4, colors.HexColor(RULE))]))
    story.append(ptable)

    story.append(Paragraph("Optuna optimization history (validation accuracy per trial)", h))
    img_w = width / 2 - 0.15 * cm
    img_h = img_w * 3.2 / 6
    images = [Image(str(HERE / x["folder"] / "metrics" / "optimization_history.png"), img_w, img_h)
              for x in (d["fashion"], d["cifar"])]
    story.append(Table([images], colWidths=[width / 2] * 2,
                       style=[("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))

    story.append(Paragraph("Why hyperparameter optimization matters", h))
    story.append(Paragraph(WHY, body))
    for line in insights(d):
        story.append(Paragraph("&bull; " + line, body))
    story.append(Paragraph("Limitations", h))
    for line in limitations(d):
        story.append(Paragraph("&bull; " + line, body))
    story.append(Spacer(1, 3))
    story.append(Paragraph("Full numbers: */metrics/*.json and hpo_trials.csv. "
                           "Code and instructions: Week-7/README.md.", small))
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return page_count["n"]


def main():
    d = collect()
    write_markdown(d)
    pages = write_pdf(d)
    print(f"Wrote REPORT.md and REPORT.pdf ({pages} page{'s' if pages != 1 else ''})")
    if pages != 1:
        raise SystemExit("REPORT.pdf must be exactly one page")


if __name__ == "__main__":
    main()
