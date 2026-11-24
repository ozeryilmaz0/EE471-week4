"""Recording helper: run the 10 Task 1 and the 5 Task 4 demos one after another.

All models are loaded (and warmed up) first, then every step works like this:

    1. the screen is cleared and a big title such as "Task 1 · 3/10 · TEXT GENERATION"
       is shown together with the input; a timer in the top-right corner counts the
       seconds since the title appeared and turns red after 12 seconds;
    2. Enter -> the task runs and the result is shown in a coloured panel;
    3. Enter -> next step.

The local time (with milliseconds) at which every title appears is written to
demo_timestamps.json, so the recording can later be cut into one clip per task.

Usage (from Week-9, with the repo venv):
    ..\\venv\\Scripts\\python.exe run_task1_task4.py              # all 15 steps
    ..\\venv\\Scripts\\python.exe run_task1_task4.py --start 11   # continue from step 11
    ..\\venv\\Scripts\\python.exe run_task1_task4.py --auto       # no Enter needed (test run)

Keys: Enter = continue, q or Esc = quit (timestamps are kept).
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "task1"), str(HERE / "task4")]

from rich.console import Group  # noqa: E402
from rich.live import Live  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.rule import Rule  # noqa: E402
from rich.spinner import Spinner  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402
from shared import console, input_panel  # noqa: E402

TIMESTAMPS = HERE / "demo_timestamps.json"
RED_AFTER = 12.0  # seconds

TASK1 = ["sentiment_analysis", "zero_shot_classification", "text_generation", "fill_mask",
         "named_entity_recognition", "question_answering", "summarization", "translation",
         "image_classification", "speech_recognition"]
TASK4 = ["load_and_save", "encoding_decoding", "padding", "truncation", "special_tokens"]

# 5x5 block font for the big titles (drawn with half blocks, so one letter is 3 lines high).
FONT = {
    "A": [".###.", "#...#", "#####", "#...#", "#...#"], "B": ["####.", "#...#", "####.", "#...#", "####."],
    "C": [".####", "#....", "#....", "#....", ".####"], "D": ["####.", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "####.", "#....", "#####"], "F": ["#####", "#....", "####.", "#....", "#...."],
    "G": [".####", "#....", "#..##", "#...#", ".####"], "H": ["#...#", "#...#", "#####", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "#####"], "J": ["#####", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "###..", "#..#.", "#...#"], "L": ["#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#...#", "#...#"], "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", ".###."], "P": ["####.", "#...#", "####.", "#....", "#...."],
    "Q": [".###.", "#...#", "#.#.#", "#..#.", ".##.#"], "R": ["####.", "#...#", "####.", "#..#.", "#...#"],
    "S": [".####", "#....", ".###.", "....#", "####."], "T": ["#####", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", ".###."], "V": ["#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#.#.#", "##.##", "#...#"], "X": ["#...#", ".#.#.", "..#..", ".#.#.", "#...#"],
    "Y": ["#...#", ".#.#.", "..#..", "..#..", "..#.."], "Z": ["#####", "...#.", "..#..", ".#...", "#####"],
    "0": [".###.", "#..##", "#.#.#", "##..#", ".###."], "1": ["..#..", ".##..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "..##.", ".#...", "#####"], "3": ["####.", "....#", ".###.", "....#", "####."],
    "4": ["#...#", "#...#", "#####", "....#", "....#"], "5": ["#####", "#....", "####.", "....#", "####."],
    "6": [".###.", "#....", "####.", "#...#", ".###."], "7": ["#####", "....#", "...#.", "..#..", "..#.."],
    "8": [".###.", "#...#", ".###.", "#...#", ".###."], "9": [".###.", "#...#", ".####", "....#", ".###."],
    "/": ["....#", "...#.", "..#..", ".#...", "#...."], "-": [".....", ".....", "#####", ".....", "....."],
    "·": [".....", ".....", "..#..", ".....", "....."], " ": ["...", "...", "...", "...", "..."],
}
HALF = {(False, False): " ", (True, False): "▀", (False, True): "▄", (True, True): "█"}


def big_line(text: str) -> list[str]:
    """Draw one line of text with the block font; returns 3 terminal rows."""
    rows = ["", "", "", "", ""]
    for ch in text.upper():
        glyph = FONT.get(ch, FONT[" "])
        for i in range(5):
            rows[i] += glyph[i] + "."
    rows.append("." * len(rows[0]))  # 6th empty row so the rows pair up
    return ["".join(HALF[(a == "#", b == "#")] for a, b in zip(rows[r], rows[r + 1])) for r in (0, 2, 4)]


def big(text: str, width: int, style: str) -> Text:
    """Big text, word-wrapped so it fits into ``width`` columns."""
    max_chars = max(8, width // 6)
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    out = Text(style=style)
    for n, line in enumerate(lines):
        if n:
            out.append("\n")
        out.append("\n".join(big_line(line)))
    return out


@dataclass
class Step:
    index: int          # 1..15
    task: str           # "Task 1" / "Task 4"
    number: int         # position inside the task
    total: int          # steps in the task
    module: ModuleType
    folder: str
    obj: Any = None

    @property
    def title(self) -> str:
        return f"{self.task} · {self.number}/{self.total} · {self.module.TITLE}"

    @property
    def script(self) -> str:
        return f"{self.folder}/{self.module.__name__}.py"


@dataclass
class Screen:
    """The renderable that Live redraws ten times per second."""
    step: Step
    started: float = field(default_factory=time.perf_counter)
    state: str = "input"  # input -> running -> result
    result: Any = None
    seconds: float = 0.0
    error: str | None = None

    def timer(self) -> Text:
        elapsed = time.perf_counter() - self.started
        style = "bold white on red" if elapsed >= RED_AFTER else "bold black on green"
        return Text(f" ⏱ {elapsed:5.1f} s ", style=style)

    def __rich__(self) -> Group:
        step = self.step
        width = console.width
        top = Table.grid(expand=True)
        top.add_column()
        top.add_column(justify="right")
        top.add_row(Text(f" Week 9 · Hugging Face · step {step.index}/15 · {step.script}", style="dim"),
                    self.timer())
        parts: list[Any] = [
            top,
            big(f"{step.task} · {step.number}/{step.total}", width, "bold cyan"),
            big(step.module.TITLE, width, "bold yellow"),
            Rule(Text(step.title, style="bold"), style="bright_black"),
            input_panel(step.module),
        ]
        if self.state == "input":
            parts.append(Text("  Press Enter to run ▶", style="bold green"))
        elif self.state == "running":
            parts.append(Spinner("dots", text=Text(" running ...", style="bold yellow")))
        elif self.error:
            parts.append(Panel(Text(self.error, style="red"), title="[bold red]ERROR", border_style="red"))
        else:
            parts.append(Panel(step.module.render(self.result), title="[bold]OUTPUT", border_style="green",
                               subtitle=f"inference {self.seconds:.2f} s", padding=(0, 2)))
            nxt = "next step" if step.index < 15 else "finish"
            parts.append(Text(f"  Press Enter for {nxt} ▶", style="bold green"))
        return Group(*parts)


def now() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


class Keys:
    """Enter / quit detection that does not block the Live refresh."""

    def __init__(self, auto: bool):
        self.auto = auto
        self.windows = os.name == "nt"

    def drain(self) -> None:
        if self.windows and not self.auto:
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getwch()

    def wait(self) -> bool:
        """Wait for Enter. Returns False if the user pressed q / Esc."""
        if self.auto:
            time.sleep(0.8)
            return True
        self.drain()  # ignore keys pressed before the prompt appeared
        if not self.windows:
            return sys.stdin.readline().strip().lower() != "q"
        import msvcrt
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\r", "\n"):
                    return True
                if ch in ("q", "Q", "\x1b"):
                    return False
            time.sleep(0.02)


def build_steps() -> list[Step]:
    steps = []
    for task, folder, names in (("Task 1", "task1", TASK1), ("Task 4", "task4", TASK4)):
        for n, name in enumerate(names, 1):
            steps.append(Step(len(steps) + 1, task, n, len(names), importlib.import_module(name), folder))
    return steps


def load_all(steps: list[Step]) -> None:
    console.clear()
    console.rule("[bold cyan]Week 9 · loading all models")
    t0 = time.perf_counter()
    for step in steps:
        start = time.perf_counter()
        with console.status(f"[yellow]Loading {step.module.MODEL} ({step.module.TITLE.lower()}) ..."):
            step.obj = step.module.load()
            loaded = time.perf_counter() - start
            start = time.perf_counter()
            step.module.run(step.obj)  # warm-up, so the first real run is fast
            warm = time.perf_counter() - start
        console.print(f"  [green]✓[/] {step.index:2}. {step.module.TITLE:26} {step.module.MODEL:50} "
                      f"[dim]load {loaded:5.1f} s · warm-up {warm:5.2f} s[/]")
    console.rule(f"[dim]ready in {time.perf_counter() - t0:.0f} s")


def save(data: dict) -> None:
    TIMESTAMPS.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", type=int, default=1, help="first step to run (1-15)")
    parser.add_argument("--auto", action="store_true", help="do not wait for Enter (test run)")
    args = parser.parse_args()

    steps = build_steps()
    keys = Keys(args.auto)
    load_all(steps)
    if console.width < 140:
        console.print(f"[yellow]Tip: the terminal is {console.width} columns wide; "
                      "maximise it (140+ columns) so every table fits.[/]")
    console.print("\n[bold green]All models loaded. Press Enter to start.[/]")
    if not keys.wait():
        return 0

    data: dict[str, Any] = {"created": now(), "steps": []}
    if args.start > 1 and TIMESTAMPS.exists():  # keep the earlier entries when resuming
        old = json.loads(TIMESTAMPS.read_text(encoding="utf-8"))
        data["steps"] = [s for s in old.get("steps", []) if s["index"] < args.start]

    quit_early = False
    with Live(console=console, screen=True, auto_refresh=True, refresh_per_second=10,
              redirect_stdout=False, redirect_stderr=False) as live:
        for step in steps[args.start - 1:]:
            screen = Screen(step)
            live.update(screen, refresh=True)
            entry = {"index": step.index, "title": step.title, "script": step.script,
                     "clip": f"{step.task.lower().replace(' ', '')}_{step.number:02d}_{step.module.__name__}",
                     "title_shown_at": now()}
            data["steps"].append(entry)
            save(data)
            if not keys.wait():
                quit_early = True
                break

            screen.state = "running"
            start = time.perf_counter()
            try:
                screen.result = step.module.run(step.obj)
            except Exception as exc:  # show the error on screen and keep going
                screen.error = f"{type(exc).__name__}: {exc}"
            screen.seconds = time.perf_counter() - start
            screen.state = "result"
            live.refresh()
            entry.update(result_shown_at=now(), inference_seconds=round(screen.seconds, 3),
                         ok=screen.error is None)
            save(data)
            if not keys.wait():
                quit_early = True
                break
            entry["ended_at"] = now()
            save(data)

    data["ended_at"] = now()
    save(data)
    console.clear()
    console.print(big("STOPPED" if quit_early else "DONE", console.width, "bold green"))
    console.print(f"\n  Timestamps saved to [bold]{TIMESTAMPS}[/]")
    failed = [s["title"] for s in data["steps"] if s.get("ok") is False]
    if failed:
        console.print("[red]  Failed steps:[/] " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
