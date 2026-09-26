#!/usr/bin/env python3
"""Generate verified puzzles (sudoku, word search, maze, crossword) with answer keys, as images plus
Markdown chapters that drop straight into book.json.

Usage:
    python build_puzzles.py puzzles.json --book path/to/book.json [--out manuscript]

puzzles.json:
{
  "seed": 42,
  "sections": [
    {"type": "sudoku", "title": "Easy Sudoku", "count": 6, "difficulty": "easy"},       # easy | medium | hard
    {"type": "wordsearch", "title": "In the Garden", "size": 13, "difficulty": "medium",   # easy | medium | hard
     "puzzles": [{"title": "Vegetables", "words": ["carrot", "potato", "..."]}]},
    {"type": "maze", "title": "Garden Paths", "count": 4, "size": [12, 16]},              # [columns, rows]
    {"type": "crossword", "title": "Garden Crosswords", "max_size": 15,
     "puzzles": [{"title": "Tools", "entries": [{"answer": "spade", "clue": "Flat-bladed digging tool"}]}]}
  ]
}
Every puzzle is verified before it's written: sudoku has exactly one solution, every word-search word
appears exactly once, every maze has a path from entrance to exit, every crossword run is a listed answer
and crossing letters agree. Crossword clues and word lists are content: they must be original and correct.

Writes <out>/<NN>-<section>.md for each section, <out>/<NN>-answers.md, images to <out>/puzzle-images/,
and <book build dir>/puzzles_report.json. Add the .md files to book.json "chapters" in order.
"""
import argparse
import json
import random
import re
import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Book, die, font_path, trim_size, write_json  # noqa: E402

DPI = 300
INTROS = {
    "sudoku": "Fill every empty square with a digit from 1 to 9 so that each row, each column and each of the "
              "nine 3×3 boxes contains every digit exactly once. Each puzzle has one solution.",
    "wordsearch": "Find each word from the list hidden in the grid. Words run in straight lines{dirs}. "
                  "Letters can be shared between words.",
    "maze": "Start at the gap in the top wall and find your way to the gap in the bottom wall.",
    "crossword": "Write one letter in each white square. Numbers show where each answer starts; the number in "
                 "brackets after a clue is the length of the answer.",
}
WS_DIRS = {
    "easy": [(0, 1), (1, 0)],
    "medium": [(0, 1), (1, 0), (1, 1), (-1, 1)],
    "hard": [(0, 1), (1, 0), (1, 1), (-1, 1), (0, -1), (-1, 0), (-1, -1), (1, -1)],
}
WS_DIR_TEXT = {"easy": " across (left to right) or down", "medium": " across, down or diagonally, never backwards",
               "hard": " in any of the eight directions, including backwards"}
ALL8 = WS_DIRS["hard"]


class F:
    cache = {}

    @classmethod
    def get(cls, style, size, family="sans"):
        k = (family, style, int(size))
        if k not in cls.cache:
            cls.cache[k] = ImageFont.truetype(font_path(family, style), int(size))
        return cls.cache[k]


# ---------------- Sudoku ----------------

def _masks(g):
    rows, cols, boxes = [0] * 9, [0] * 9, [0] * 9
    for i, v in enumerate(g):
        if v:
            b = 1 << v
            r, c = divmod(i, 9)
            rows[r] |= b; cols[c] |= b; boxes[(r // 3) * 3 + c // 3] |= b
    return rows, cols, boxes


def sudoku_search(g, limit=2, rng=None):
    """Count solutions up to `limit`. With rng, returns the first (randomised) solution instead."""
    g = g[:]
    rows, cols, boxes = _masks(g)
    found = []

    def rec():
        best, bm, bn = -1, 0, 10
        for i in range(81):
            if g[i] == 0:
                r, c = divmod(i, 9)
                m = ~(rows[r] | cols[c] | boxes[(r // 3) * 3 + c // 3]) & 0x3FE
                n = bin(m).count("1")
                if n < bn:
                    best, bm, bn = i, m, n
                    if n == 0:
                        return
        if best == -1:
            found.append(g[:])
            return
        r, c = divmod(best, 9)
        bx = (r // 3) * 3 + c // 3
        vals = [v for v in range(1, 10) if bm & (1 << v)]
        if rng:
            rng.shuffle(vals)
        for v in vals:
            b = 1 << v
            g[best] = v; rows[r] |= b; cols[c] |= b; boxes[bx] |= b
            rec()
            g[best] = 0; rows[r] ^= b; cols[c] ^= b; boxes[bx] ^= b
            if len(found) >= limit:
                return

    rec()
    return found


def singles_solvable(g):
    g = g[:]
    while True:
        rows, cols, boxes = _masks(g)
        progress = False
        for i in range(81):
            if g[i] == 0:
                r, c = divmod(i, 9)
                m = ~(rows[r] | cols[c] | boxes[(r // 3) * 3 + c // 3]) & 0x3FE
                if bin(m).count("1") == 1:
                    g[i] = m.bit_length() - 1
                    progress = True
                    break
        if not progress:
            return all(g)


def valid_solution(s):
    full = set(range(1, 10))
    for k in range(9):
        if set(s[k * 9:(k + 1) * 9]) != full or set(s[k::9]) != full:
            return False
        br, bc = divmod(k, 3)
        if {s[(br * 3 + dr) * 9 + bc * 3 + dc] for dr in range(3) for dc in range(3)} != full:
            return False
    return True


def make_sudoku(rng, difficulty):
    target = {"easy": (36, 40), "medium": (30, 34), "hard": (25, 29)}[difficulty]
    for _ in range(40):
        solution = sudoku_search([0] * 81, limit=1, rng=rng)[0]
        g = solution[:]
        goal = rng.randint(*target)
        cells = list(range(41))
        rng.shuffle(cells)
        for i in cells:
            pair = {i, 80 - i}
            if sum(1 for v in g if v) - len(pair) < goal:
                continue
            saved = {j: g[j] for j in pair}
            for j in pair:
                g[j] = 0
            if len(sudoku_search(g, 2)) != 1:
                for j, v in saved.items():
                    g[j] = v
        givens = sum(1 for v in g if v)
        easy = singles_solvable(g)
        if difficulty == "easy" and not easy:
            continue
        if difficulty == "hard" and easy:
            continue
        if givens > target[1] + 2:
            continue
        sols = sudoku_search(g, 2)
        assert len(sols) == 1 and sols[0] == solution and valid_solution(solution)
        return {"puzzle": g, "solution": solution, "givens": givens, "singles_only": easy}
    die(f"Couldn't generate a {difficulty} sudoku; try another seed.")


def render_sudoku(p, width_px, solution=False):
    S = width_px
    pad = S // 40
    cell = (S - 2 * pad) / 9
    img = Image.new("L", (S, S), 255)
    d = ImageDraw.Draw(img)
    f_given = F.get("bold", cell * 0.6)
    f_fill = F.get("regular", cell * 0.6)
    for k in range(10):
        w = max(2, S // 150) if k % 3 == 0 else max(1, S // 500)
        x = pad + k * cell
        d.line([(x, pad), (x, S - pad)], fill=0, width=w)
        d.line([(pad, x), (S - pad, x)], fill=0, width=w)
    for i in range(81):
        r, c = divmod(i, 9)
        v = p["puzzle"][i] or (p["solution"][i] if solution else 0)
        if v:
            given = bool(p["puzzle"][i])
            d.text((pad + (c + 0.5) * cell, pad + (r + 0.5) * cell), str(v), font=f_given if given else f_fill,
                   fill=0 if given else 110, anchor="mm")
    return img


# ---------------- Word search ----------------

def norm_word(w):
    return re.sub(r"[^A-Z]", "", w.upper())


def find_all(grid, word):
    n = len(grid)
    hits = set()
    for r in range(n):
        for c in range(n):
            for dr, dc in ALL8:
                cells = []
                for k, ch in enumerate(word):
                    rr, cc = r + dr * k, c + dc * k
                    if not (0 <= rr < n and 0 <= cc < n) or grid[rr][cc] != ch:
                        break
                    cells.append((rr, cc))
                else:
                    hits.add(frozenset(cells))
    return hits


def make_wordsearch(rng, words, size, difficulty):
    items = [(w, norm_word(w)) for w in words]
    for disp, w in items:
        if len(w) < 3:
            die(f"Word search word too short: {disp}")
        if len(w) > size:
            die(f"'{disp}' is longer than the {size}x{size} grid")
    norms = [w for _, w in items]
    if len(set(norms)) != len(norms):
        die("Duplicate words in word search list")
    for a in norms:
        for b in norms:
            if a != b and (a in b or a[::-1] in b):
                die(f"'{a}' is contained in '{b}', so it would appear twice. Drop one of them.")
    dirs = WS_DIRS[difficulty]
    alphabet = sorted(set("".join(norms)) | set("AEIOULNRST"))
    for _ in range(200):
        grid = [[None] * size for _ in range(size)]
        placed = []
        ok = True
        for disp, w in sorted(items, key=lambda x: -len(x[1])):
            for _ in range(400):
                dr, dc = rng.choice(dirs)
                r, c = rng.randrange(size), rng.randrange(size)
                cells = [(r + dr * k, c + dc * k) for k in range(len(w))]
                if all(0 <= rr < size and 0 <= cc < size and grid[rr][cc] in (None, w[k])
                       for k, (rr, cc) in enumerate(cells)):
                    for k, (rr, cc) in enumerate(cells):
                        grid[rr][cc] = w[k]
                    placed.append({"word": disp, "norm": w, "cells": cells})
                    break
            else:
                ok = False
                break
        if not ok:
            continue
        for _ in range(100):
            filled = [[ch or rng.choice(alphabet) for ch in row] for row in grid]
            if all(len(find_all(filled, p["norm"])) == 1 for p in placed):
                return {"grid": filled, "placed": placed, "size": size, "difficulty": difficulty}
    die(f"Couldn't fit the word list in a {size}x{size} grid; use a bigger size or fewer words.")


def render_wordsearch(p, width_px, solution=False):
    n = p["size"]
    pad = width_px // 30
    cell = (width_px - 2 * pad) / n
    words = sorted(x["word"].upper() for x in p["placed"])
    cols = 3
    lf = F.get("regular", cell * 0.42)
    rows_needed = -(-len(words) // cols)
    list_h = int(rows_needed * cell * 0.62 + cell)
    H = int(pad * 2 + n * cell + list_h)
    img = Image.new("L", (width_px, H), 255)
    d = ImageDraw.Draw(img)
    d.rectangle([pad - 4, pad - 4, width_px - pad + 4, pad + n * cell + 4], outline=0, width=max(2, width_px // 400))
    if solution:
        for x in p["placed"]:
            (r0, c0), (r1, c1) = x["cells"][0], x["cells"][-1]
            a = (pad + (c0 + 0.5) * cell, pad + (r0 + 0.5) * cell)
            b = (pad + (c1 + 0.5) * cell, pad + (r1 + 0.5) * cell)
            w = int(cell * 0.72)
            d.line([a, b], fill=205, width=w)
            for q in (a, b):
                d.ellipse([q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2], fill=205)
    f = F.get("bold" if not solution else "regular", cell * 0.55)
    for r in range(n):
        for c in range(n):
            d.text((pad + (c + 0.5) * cell, pad + (r + 0.5) * cell), p["grid"][r][c], font=f, fill=0, anchor="mm")
    y0 = pad + n * cell + cell * 0.7
    colw = (width_px - 2 * pad) / cols
    for i, w in enumerate(words):
        col, row = divmod(i, rows_needed)
        d.text((pad + col * colw, y0 + row * cell * 0.62), w, font=lf, fill=0, anchor="la")
    return img


# ---------------- Maze ----------------

def make_maze(rng, cols, rows):
    open_ = {(c, r): set() for c in range(cols) for r in range(rows)}
    stack, seen = [(0, 0)], {(0, 0)}
    while stack:
        c, r = stack[-1]
        nbrs = [(c + dc, r + dr, d) for dc, dr, d in ((1, 0, "E"), (-1, 0, "W"), (0, 1, "S"), (0, -1, "N"))
                if (c + dc, r + dr) in open_ and (c + dc, r + dr) not in seen]
        if not nbrs:
            stack.pop()
            continue
        nc, nr, d = rng.choice(nbrs)
        opp = {"E": "W", "W": "E", "S": "N", "N": "S"}[d]
        open_[(c, r)].add(d)
        open_[(nc, nr)].add(opp)
        seen.add((nc, nr))
        stack.append((nc, nr))
    start, end = (0, 0), (cols - 1, rows - 1)
    prev = {start: None}
    q = deque([start])
    step = {"E": (1, 0), "W": (-1, 0), "S": (0, 1), "N": (0, -1)}
    while q:
        cur = q.popleft()
        for d in open_[cur]:
            nxt = (cur[0] + step[d][0], cur[1] + step[d][1])
            if nxt not in prev:
                prev[nxt] = cur
                q.append(nxt)
    assert end in prev and len(prev) == cols * rows, "maze not fully connected"
    path, cur = [], end
    while cur:
        path.append(cur)
        cur = prev[cur]
    passages = sum(len(v) for v in open_.values()) // 2
    assert passages == cols * rows - 1, "maze is not a perfect maze"
    return {"cols": cols, "rows": rows, "open": {f"{c},{r}": sorted(v) for (c, r), v in open_.items()},
            "path": path[::-1], "_open": open_}


def render_maze(p, width_px, solution=False):
    cols, rows = p["cols"], p["rows"]
    pad = width_px // 30
    cell = (width_px - 2 * pad) / cols
    H = int(2 * pad + rows * cell)
    img = Image.new("L", (width_px, H), 255)
    d = ImageDraw.Draw(img)
    w = max(2, int(cell / 9))
    if solution:
        pts = [(pad + (c + 0.5) * cell, pad + (r + 0.5) * cell) for c, r in p["path"]]
        pts = [(pts[0][0], pad - cell * 0.4)] + pts + [(pts[-1][0], pad + rows * cell + cell * 0.4)]
        d.line(pts, fill=150, width=max(3, int(cell * 0.28)), joint="curve")
    op = p["_open"]
    for c in range(cols):
        for r in range(rows):
            x0, y0 = pad + c * cell, pad + r * cell
            x1, y1 = x0 + cell, y0 + cell
            o = op[(c, r)]
            if "N" not in o and not (c, r) == (0, 0):
                d.line([(x0, y0), (x1, y0)], fill=0, width=w)
            if "W" not in o:
                d.line([(x0, y0), (x0, y1)], fill=0, width=w)
            if c == cols - 1 and "E" not in o:
                d.line([(x1, y0), (x1, y1)], fill=0, width=w)
            if r == rows - 1 and "S" not in o and (c, r) != (cols - 1, rows - 1):
                d.line([(x0, y1), (x1, y1)], fill=0, width=w)
    return img


# ---------------- Crossword ----------------

def make_crossword(rng, entries, max_size, attempts=300):
    items = [(norm_word(e["answer"]), e["clue"].strip()) for e in entries]
    for w, clue in items:
        if len(w) < 2 or not clue:
            die(f"Crossword entry needs an answer of 2+ letters and a clue: {w!r}")
    if len({w for w, _ in items}) != len(items):
        die("Duplicate crossword answers")
    best = None
    for _ in range(attempts):
        order = sorted(items, key=lambda x: -len(x[0]) + rng.random() * 3)
        grid, used, placed = {}, {}, []

        def ok(word, r, c, dr, dc):
            inter = 0
            if grid.get((r - dr, c - dc)) or grid.get((r + dr * len(word), c + dc * len(word))):
                return -1
            for k, ch in enumerate(word):
                cell = (r + dr * k, c + dc * k)
                ex = grid.get(cell)
                if ex:
                    if ex != ch or (dr, dc) in used.get(cell, set()):
                        return -1
                    inter += 1
                else:
                    pr, pc = dc, dr
                    if grid.get((cell[0] + pr, cell[1] + pc)) or grid.get((cell[0] - pr, cell[1] - pc)):
                        return -1
            rs = [r0 for r0, _ in grid] + [r, r + dr * (len(word) - 1)]
            cs = [c0 for _, c0 in grid] + [c, c + dc * (len(word) - 1)]
            if max(rs) - min(rs) + 1 > max_size or max(cs) - min(cs) + 1 > max_size:
                return -1
            return inter

        def put(word, clue, r, c, dr, dc):
            for k, ch in enumerate(word):
                cell = (r + dr * k, c + dc * k)
                grid[cell] = ch
                used.setdefault(cell, set()).add((dr, dc))
            placed.append({"answer": word, "clue": clue, "row": r, "col": c, "dir": "across" if dc else "down"})

        w0, c0 = order[0]
        put(w0, c0, 0, 0, 0, 1)
        skipped = []
        for w, clue in order[1:]:
            cands = []
            for (r, c), ch in list(grid.items()):
                for i, wch in enumerate(w):
                    if wch != ch:
                        continue
                    for dr, dc in ((0, 1), (1, 0)):
                        sr, sc = r - dr * i, c - dc * i
                        s = ok(w, sr, sc, dr, dc)
                        if s > 0:
                            cands.append((s + rng.random() * 0.5, sr, sc, dr, dc))
            if cands:
                _, sr, sc, dr, dc = max(cands)
                put(w, clue, sr, sc, dr, dc)
            else:
                skipped.append(w)
        rs = [r for r, _ in grid]
        cs = [c for _, c in grid]
        area = (max(rs) - min(rs) + 1) * (max(cs) - min(cs) + 1)
        inter = sum(1 for v in used.values() if len(v) == 2)
        score = (len(placed), inter, -area)
        if not best or score > best[0]:
            best = (score, dict(grid), list(placed), skipped)
    _, grid, placed, skipped = best
    r0 = min(r for r, _ in grid)
    c0 = min(c for _, c in grid)
    grid = {(r - r0, c - c0): ch for (r, c), ch in grid.items()}
    for p in placed:
        p["row"] -= r0
        p["col"] -= c0
    rows = max(r for r, _ in grid) + 1
    cols = max(c for _, c in grid) + 1
    # Verify: every maximal run of 2+ letters is exactly one placed answer, and nothing else.
    runs = set()
    for r in range(rows):
        c = 0
        while c < cols:
            if (r, c) in grid:
                s = c
                while (r, c) in grid:
                    c += 1
                if c - s >= 2:
                    runs.add((r, s, "across", "".join(grid[(r, k)] for k in range(s, c))))
            c += 1
    for c in range(cols):
        r = 0
        while r < rows:
            if (r, c) in grid:
                s = r
                while (r, c) in grid:
                    r += 1
                if r - s >= 2:
                    runs.add((s, c, "down", "".join(grid[(k, c)] for k in range(s, r))))
            r += 1
    expected = {(p["row"], p["col"], p["dir"], p["answer"]) for p in placed}
    assert runs == expected, f"crossword verification failed: {runs ^ expected}"
    starts = sorted({(p["row"], p["col"]) for p in placed})
    num = {rc: i + 1 for i, rc in enumerate(starts)}
    for p in placed:
        p["number"] = num[(p["row"], p["col"])]
    return {"grid": {f"{r},{c}": ch for (r, c), ch in grid.items()}, "_grid": grid, "rows": rows, "cols": cols,
            "placed": sorted(placed, key=lambda p: (p["dir"], p["number"])), "skipped": skipped, "numbers": num}


def render_crossword(p, width_px, solution=False, max_h_ratio=1.0):
    rows, cols = p["rows"], p["cols"]
    pad = width_px // 40
    cell = min((width_px - 2 * pad) / cols, (width_px * max_h_ratio - 2 * pad) / rows)
    W = int(2 * pad + cols * cell)
    H = int(2 * pad + rows * cell)
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    nf = F.get("regular", cell * 0.28)
    lf = F.get("regular", cell * 0.58)
    lw = max(2, int(cell / 22))
    for (r, c), ch in p["_grid"].items():
        x0, y0 = pad + c * cell, pad + r * cell
        d.rectangle([x0, y0, x0 + cell, y0 + cell], outline=0, width=lw)
        if (r, c) in p["numbers"]:
            d.text((x0 + cell * 0.08, y0 + cell * 0.05), str(p["numbers"][(r, c)]), font=nf, fill=0, anchor="la")
        if solution:
            d.text((x0 + cell / 2, y0 + cell * 0.58), ch, font=lf, fill=0, anchor="mm")
    return img


# ---------------- answer sheets & output ----------------

def answer_sheet(entries, width_px):
    """2x2 grid of labelled solution images."""
    gap = width_px // 25
    slot = (width_px - gap) // 2
    label_h = int(slot * 0.09)
    heights = []
    thumbs = []
    for label, img in entries:
        scale = slot / img.width
        im = img.resize((slot, int(img.height * scale)), Image.LANCZOS)
        if im.height > slot * 1.25:
            s2 = slot * 1.25 / im.height
            im = im.resize((int(im.width * s2), int(im.height * s2)), Image.LANCZOS)
        thumbs.append((label, im))
        heights.append(im.height)
    row_h = [max(heights[i:i + 2]) + label_h for i in range(0, len(thumbs), 2)]
    H = sum(row_h) + gap * (len(row_h) - 1)
    sheet = Image.new("L", (width_px, H), 255)
    d = ImageDraw.Draw(sheet)
    y = 0
    for i, (label, im) in enumerate(thumbs):
        col = i % 2
        if i and col == 0:
            y += row_h[i // 2 - 1] + gap
        x = col * (slot + gap)
        size = label_h * 0.6
        while F.get("bold", size).getlength(label) > slot and size > 10:
            size *= 0.93
        d.text((x, y), label, font=F.get("bold", size), fill=0, anchor="la")
        sheet.paste(im, (x + (slot - im.width) // 2, y + label_h))
    return sheet


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="puzzles.json")
    ap.add_argument("--book", required=True, help="book.json (for trim size and build folder)")
    ap.add_argument("--out", help="folder for the Markdown chapters (default: <book>/manuscript)")
    ap.add_argument("--first-number", type=int, default=50, help="file-number prefix for generated chapters")
    args = ap.parse_args()

    book = Book(args.book)
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    rng = random.Random(spec.get("seed", 1))
    out = Path(args.out) if args.out else book.root / "manuscript"
    img_dir = out / "puzzle-images"
    img_dir.mkdir(parents=True, exist_ok=True)
    tw, th = book.trim()
    width_px = int((tw - 0.9) * DPI)  # a little wider than the text block, so it prints at 300+ DPI
    number = 0
    answers = []
    report = []
    files = []
    fnum = args.first_number

    for sec in spec["sections"]:
        t = sec["type"]
        slug = re.sub(r"[^a-z0-9]+", "-", sec["title"].lower()).strip("-")
        md = [f"# {sec['title']}", ""]
        intro = sec.get("intro") or INTROS[t].format(dirs=WS_DIR_TEXT.get(sec.get("difficulty", "medium"), ""))
        md += [intro, ""]
        pieces = []
        if t == "sudoku":
            for _ in range(sec.get("count", 1)):
                p = make_sudoku(rng, sec.get("difficulty", "medium"))
                pieces.append((None, p, render_sudoku, {"givens": p["givens"], "unique_solution": True,
                                                        "singles_only": p["singles_only"]}))
        elif t == "wordsearch":
            for pz in sec["puzzles"]:
                p = make_wordsearch(rng, pz["words"], sec.get("size", 13), sec.get("difficulty", "medium"))
                pieces.append((pz.get("title"), p, render_wordsearch,
                               {"words": len(p["placed"]), "each_found_exactly_once": True}))
        elif t == "maze":
            cols, rows = sec.get("size", [12, 16])
            for _ in range(sec.get("count", 1)):
                p = make_maze(rng, cols, rows)
                pieces.append((None, p, render_maze, {"path_length": len(p["path"]), "solvable": True}))
        elif t == "crossword":
            for pz in sec["puzzles"]:
                p = make_crossword(rng, pz["entries"], sec.get("max_size", 15))
                if p["skipped"]:
                    print(f"  NOTE: crossword '{pz.get('title')}' couldn't fit: {', '.join(p['skipped'])}")
                pieces.append((pz.get("title"), p, render_crossword,
                               {"placed": len(p["placed"]), "skipped": p["skipped"], "runs_verified": True}))
        else:
            die(f"Unknown puzzle type {t}")

        for i, (ptitle, p, render, checks) in enumerate(pieces):
            number += 1
            name = f"puzzle-{number:03d}"
            kw = {"max_h_ratio": 0.9} if t == "crossword" else {}
            render(p, width_px, **kw).save(img_dir / f"{name}.png", dpi=(DPI, DPI))
            sol = render(p, width_px, solution=True, **kw)
            label = f"Puzzle {number}" + (f": {ptitle}" if ptitle else "")
            answers.append((label, sol))
            heading = f"## Puzzle {number}" + (f": {ptitle}" if ptitle else "")
            if i:
                md += ['<div class="page-break"></div>', ""]
            width_attr = "{ width=85% }" if t == "crossword" else ""
            md += [heading, "", f"![{label}](puzzle-images/{name}.png){width_attr}", ""]
            if t == "crossword":
                for direction in ("across", "down"):
                    items = [x for x in p["placed"] if x["dir"] == direction]
                    if items:
                        # One paragraph per clue with the number in bold, never a Markdown numbered list:
                        # list renderers renumber 1, 2, 3... and the clues would stop matching the grid.
                        md += [f"### {direction.title()}", ""]
                        for x in items:
                            md += [f"**{x['number']}** {x['clue']} ({len(x['answer'])})", ""]
            report.append({"number": number, "type": t, "title": ptitle, **checks})
        path = out / f"{fnum:02d}-{slug}.md"
        path.write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")
        files.append(path)
        fnum += 1

    md = ["# Answers", ""]
    for k in range(0, len(answers), 4):
        sheet = answer_sheet(answers[k:k + 4], width_px)
        name = f"answers-{k // 4 + 1:02d}.png"
        sheet.save(img_dir / name, dpi=(DPI, DPI))
        width = ""
        if k:
            md += ['<div class="page-break"></div>', ""]
        else:
            # The first sheet shares a page with the chapter heading (~2.7 in), so size it to fit there.
            block_w, room = tw - 1.1, th - 1.45 - 2.7
            natural_h = block_w * sheet.height / sheet.width
            if natural_h > room:
                width = f"{{ width={int(100 * room / natural_h)}% }}"
        md += [f"![Answers {k + 1}–{min(k + 4, len(answers))}](puzzle-images/{name}){width}", ""]
    ans_path = out / f"{fnum:02d}-answers.md"
    ans_path.write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")
    files.append(ans_path)
    write_json(book.build_dir / "puzzles_report.json", {"puzzles": report, "files": [str(f) for f in files]})
    print(f"{number} puzzles generated and verified; {len(files)} Markdown files in {out}:")
    for f in files:
        print("  ", f.relative_to(book.root).as_posix())
    print("Add them to book.json \"chapters\" in this order.")


if __name__ == "__main__":
    main()
