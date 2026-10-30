"""Markdown (+ LaTeX math) -> PDF, via KaTeX and a headless Edge/Chrome.

Usage: python md2pdf.py <file.md> [more.md ...]
If the .md lives in a `_source/` or `_fuente/` folder, the PDF is written to the parent folder (inside `Study notes (Claude)` / `Apuntes explicativos (Claude)`: its `Wn/` / `Tn/` subfolder, from the first W/T number in the name);
otherwise it is written next to the .md. After printing, the page is rendered again and checked:
  WARNING (exit code 1): formula errors (with the LaTeX), Markdown/LaTeX/HTML left unrendered,
      missing images, anything wider than the text column (Edge then shrinks the whole PDF).
  CHECK (worth a look, exit code unaffected): paragraphs run together, tall inline formulas, big blank space at the
      bottom of a page (esqCLI > 4 cm, notesCLI/apuntesCLI > 9 cm; see doc_layout).
Before printing, titles are kept with their first block and short inline formulas are made unbreakable (glued to
the brackets/punctuation around them); a title still left at the bottom of a page is a WARNING.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from markdown_it import MarkdownIt

# Tried in order; the next one is used if a browser writes no PDF.
BROWSERS = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")),  # per-user Chrome install
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    Path("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
] + [Path(p) for p in map(shutil.which, ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                                         "microsoft-edge", "microsoft-edge-stable", "brave", "brave-browser")) if p]
# Brave last: on Arch/Wayland its headless print hung forever (2026-10-10).
# Claude Code's shell has __COMPAT_LAYER=RunAsInvoker. Edge 153 sees it, relaunches itself detached and
# returns at once, so the PDF appeared seconds later in a deleted temp folder and --dump-dom came back empty
# (found 2026-09-26). Launching the browsers without it makes them run in the foreground again.
BROWSER_ENV = {k: v for k, v in os.environ.items() if k.upper() != "__COMPAT_LAYER"}
KATEX = "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9"
SOURCE_DIRS = {"_source", "_fuente"}

CSS = """
@page { size: A4; margin: 16mm 15mm 16mm 15mm; }
@media screen { body { width: calc(180mm - 16px); } }  /* same text column as the printed page (180 mm minus the default 8px body margins), for the layout checks */
body { font-family: "Segoe UI", Calibri, Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1a1a1a; }
h1 { font-size: 19pt; color: #7a2a00; border-bottom: 2px solid #7a2a00; padding-bottom: 4px; margin-top: 0; }
h2 { font-size: 14.5pt; color: #1f3a68; border-bottom: 1px solid #c8d1e0; padding-bottom: 2px; margin-top: 22px; break-after: avoid; }
h3 { font-size: 12pt; color: #1f3a68; margin-top: 16px; break-after: avoid; }
p, li { orphans: 3; widows: 3; }
table { border-collapse: collapse; margin: 8px 0; width: 100%; break-inside: avoid; font-size: 9.8pt; }
th, td { border: 1px solid #b9c2d0; padding: 4px 7px; vertical-align: top; text-align: left; }
th { background: #e8edf5; }
blockquote { margin: 10px 0; padding: 6px 12px; background: #f6f3ea; border-left: 4px solid #d9a441; break-inside: avoid; }
code { font-family: Consolas, monospace; font-size: 9.5pt; background: #f1f1f1; padding: 0 3px; border-radius: 3px; }
pre { background: #f1f1f1; padding: 6px 9px; border-radius: 4px; white-space: pre-wrap; break-inside: avoid; }
pre code { padding: 0; }
img { max-width: 100%; }
hr { border: none; border-top: 1px solid #ddd; margin: 18px 0; }
.math-display { margin: 8px 0; overflow-x: visible; break-inside: avoid; }
/* "$$…$$<span class="cond">…</span>": the purple condition sits on the formula's line, right next to it (before, the
   display div pushed it to the next line, left margin). Wraps below only if there is no room. */
.math-cond { display: flex; flex-wrap: wrap; justify-content: center; align-items: center; column-gap: 14px; break-inside: avoid; }
.math-cond > .math-display { margin: 8px 0; }
.math-cond .katex-display { margin: 0.5em 0; }
.katex { font-size: 1.08em; }
.katex-error-box { color: #b00020; border: 2px solid #b00020; padding: 4px; }
/* Optional colour code for study notes (classes used in the .md as <span class="def">…) */
.def { color: #1b8a3a; }                                   /* green text: definition */
.hl-def { background: #c9f2c9; }                           /* green highlight: definition */
.ul-def { text-decoration-line: underline; text-decoration-color: #1b8a3a; text-decoration-thickness: 2px; text-underline-offset: 3px; }  /* green underline: important definition */
.asm { color: #7b2fb5; }                                   /* purple text: assumption */
.hl-asm { background: #e6d4f7; }                           /* purple highlight: assumption */
.cond { color: #7b2fb5; font-size: 0.92em; }               /* purple text next to an equation: iff conditions for it */
.box-law { display: inline-block; background: #e6d4f7; border: 2px solid #7b2fb5; padding: 3px 8px; }  /* purple box: always-true law / theorem */
div.box-law { display: table; margin: 10px auto; padding: 0 18px; break-inside: avoid; }
.box-def { display: inline-block; background: #c9f2c9; border: 2px solid #1b8a3a; padding: 3px 8px; }  /* green box: pure definition formula (text stays black) */
div.box-def { display: table; margin: 10px auto; padding: 0 18px; break-inside: avoid; }
.hl-f { background: #ffc9c9; padding: 1px 3px; }           /* red highlight: important formula */
.box-f { display: inline-block; background: #ffc9c9; border: 2px solid #d01818; padding: 3px 8px; }  /* key formula / conclusion */
div.box-f { display: table; margin: 10px auto; padding: 0 18px; break-inside: avoid; }
.case { color: #1e9bd7; }                                  /* light blue text: case-dependent */
.corr { color: #d01818; }                                  /* red text: exercise / correction */
.hl { background: #fff27a; }                               /* yellow highlight: other important info */
.cmp { color: #1a2f9e; }                                   /* dark blue text: the 2nd of two things compared */
.minor { color: #808080; }                                 /* grey text: minor / can be skipped */
.minor-li { color: #808080; }                              /* whole list item grey: its bullet goes light grey too */
li:has(> .minor-li, > p > .minor-li)::marker { color: #b8b8b8; }
.hl-case { background: #cdeafa; padding: 1px 3px; }        /* light blue highlight: 2nd group of cases on the page */
/* Inline highlight around tall maths (dfrac, sub/superscripts): an inline background only covers the text line, so
   numerators/denominators stuck out of it. KaTeX's .base pieces are inline-blocks as tall as the formula: paint them too. */
span.hl .katex-html > .base { background: #fff27a; }
span.hl-f .katex-html > .base { background: #ffc9c9; }
span.hl-def .katex-html > .base { background: #c9f2c9; }
span.hl-asm .katex-html > .base { background: #e6d4f7; }
span.hl-case .katex-html > .base { background: #cdeafa; }
span.hl-math { display: inline-block; }
.box-case { display: inline-block; border: 2px solid #1e9bd7; padding: 1px 6px; }  /* light blue box: 3rd group of cases */
div.box-case { display: table; margin: 8px auto; padding: 0 14px; break-inside: avoid; }
.ul-case { text-decoration-line: underline; text-decoration-color: #1e9bd7; text-decoration-thickness: 2px; text-underline-offset: 3px; }  /* light blue underline: 3rd group (alternative to box-case) */
.box-g { display: inline-block; border: 1px solid #aaa; padding: 1px 6px; color: #888; }  /* formula on the exam formula sheet: grey + thin grey box */
div.box-g { display: table; margin: 8px auto; padding: 0 14px; break-inside: avoid; }
.grey-f { color: #888; }                                   /* formula on the formula sheet that had no box: grey only */
.box { display: inline-block; border: 1.6px solid #222; padding: 3px 8px; }  /* plain box: final result to keep at hand, below red */
div.box { display: table; margin: 10px auto; padding: 0 18px; break-inside: avoid; }
/* Highlight width = importance: a highlighted display formula is highlighted only around the formula;
   add "wide" (<div class="hl-f wide">) for margin-to-margin, only for the most important ones. */
div.hl, div.hl-f, div.hl-def, div.hl-asm, div.hl-case { display: table; margin: 8px auto; padding: 0 14px; break-inside: avoid; }
div.wide { display: block; margin: 8px 0; }
.skipped { color: #808080; font-weight: 700; }             /* grey bold: skipped on purpose / still to check */
.imp1::after, .imp2::after, .imp3::after { font-weight: 900; font-size: 1.05em; vertical-align: 0.55em; margin-left: 3px; color: #222; }
.imp1::after { content: "!"; } .imp2::after { content: "!!"; } .imp3::after { content: "!!!"; }  /* floating bold ! marks: importance 1-3 */
/* Whole-passage brackets: one big ( ) or [ ] spanning everything the mark applies to, not just its title */
div.minor, div.aside { position: relative; margin: 10px 2px; padding: 2px 18px; break-inside: avoid; }
div.minor::before, div.minor::after, div.aside::before, div.aside::after { content: ""; position: absolute; top: 0; bottom: 0; width: 9px; }
div.minor::before { left: 0; border-left: 2.2px solid #7a7a7a; border-radius: 100% 0 0 100% / 50% 0 0 50%; }     /* ( ... ): minor / skippable */
div.minor::after { right: 0; border-right: 2.2px solid #7a7a7a; border-radius: 0 100% 100% 0 / 0 50% 50% 0; }
div.aside::before { left: 0; border: 1.8px solid #444; border-right: none; }                                     /* [ ... ]: extra info, outside the main thread */
div.aside::after { right: 0; border: 1.8px solid #444; border-left: none; }
/* Translation of a hard English word, right after it: "word (palabra)", parentheses included, all grey and smaller */
.tr { color: #808080; font-size: 0.82em; }
/* Small [ ... ] on the right edge of the column, next to what it refers to. Inside a heading = about the whole
   section (the title stays in place). With .tr: a grey translation note [word = palabra] that didn't fit in the text.
   Absolutely positioned: it takes no room, so the text is laid out as if it weren't there (nothing wraps around it)
   and it sits at the height where it is written. Put it only where there is empty space (after a short line, on a
   heading's line, beside a centred display formula); the layout check warns if it lands on text. */
body { position: relative; }
.aside-r { position: absolute; right: 0; max-width: 34%; margin-top: 1px; padding: 1px 9px;
           font-size: 8.3pt; font-weight: normal; font-style: normal; line-height: 1.3; color: #444; text-align: left; }
.aside-r::before, .aside-r::after { content: ""; position: absolute; top: 0; bottom: 0; width: 5px; border: 1.2px solid #444; }
.aside-r::before { left: 0; border-right: none; }
.aside-r::after { right: 0; border-left: none; }
.aside-r.tr { color: #808080; }
.aside-r.tr::before, .aside-r.tr::after { border-color: #909090; }
/* Version line (experimental, 2026-09-27): "created · editedN · updatedN", tiny and light grey.
   notesCLI/ejsCLI: right after the rules-checked stamp, above the title. esqCLI: .end, the last line of the file. */
.docdates { text-align: right; font-size: 6.5pt; line-height: 1.2; color: #a8a8a8; margin: 0 0 3px; }
.docdates.end { margin: 16px 0 0; }
/* Added by the script before printing (see glueInline / keepWithNext): a short inline formula glued to the "(" before
   it and the ")" "." "," after it, so "(>0)" never breaks; a title kept on the same page as its first block. */
.nobr { white-space: nowrap; }
.keep { break-inside: avoid; }
"""

SCRIPT = r"""
<script>
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("[data-tex]").forEach(function (el) {
    var tex = el.textContent, display = el.dataset.tex === "display";
    try { katex.render(tex, el, {displayMode: display, throwOnError: true, strict: false}); }
    catch (e) {
      var msg = String(e.message) + "  in: " + tex.replace(/\s+/g, " ").trim().slice(0, 160);
      el.innerHTML = '<span class="katex-error-box">ERROR KaTeX: ' + msg.replace(/&/g, "&amp;").replace(/</g, "&lt;") + '</span>';
    }
  });
});
// Layout fixes, done on "load" (images in place, so heights are real) and before printing:
window.addEventListener("load", function () { boxMathHighlights(); glueInline(); keepWithNext(); });
// 0) A highlight that holds only maths becomes one inline-block, so the colour is a clean rectangle as tall as the
//    formula (fractions included). Highlights mixing text and maths keep the per-piece painting (see CSS).
function boxMathHighlights() {
  document.querySelectorAll("span.hl, span.hl-f, span.hl-def, span.hl-asm, span.hl-case").forEach(function (el) {
    if (!el.querySelector(".katex")) return;
    var c = el.cloneNode(true);
    c.querySelectorAll(".katex").forEach(function (k) { k.remove(); });
    if (!c.textContent.trim()) el.classList.add("hl-math");
  });
}
// 1) Short inline formulas never break across lines (KaTeX allows a break after "<", ">", "=") and stay glued to an
//    opening "(" / "[" before them and to ")" "." "," ";" ":" after them. Long ones (> 45% of the line) may still break.
function glueInline() {
  var col = document.body.getBoundingClientRect().width;
  document.querySelectorAll('[data-tex="inline"]').forEach(function (el) {
    var w = 0;
    Array.prototype.forEach.call(el.getClientRects(), function (r) { w += r.width; });
    if (w > 0.45 * col) return;
    var box = document.createElement("span"); box.className = "nobr";
    var prev = el.previousSibling, next = el.nextSibling;
    el.parentNode.insertBefore(box, el);
    if (prev && prev.nodeType === 3) {
      var m = prev.data.match(/[(\[{¿¡"“‘]+$/);
      if (m) { prev.data = prev.data.slice(0, -m[0].length); box.appendChild(document.createTextNode(m[0])); }
    }
    box.appendChild(el);
    if (next && next.nodeType === 3) {
      var m2 = next.data.match(/^[)\]}.,;:!?%"”’]+/);
      if (m2) { next.data = next.data.slice(m2[0].length); box.appendChild(document.createTextNode(m2[0])); }
    }
  });
}
// 2) A title never sits alone at the bottom of a page: every heading, and every "pseudo-title" (a paragraph that is
//    only bold text, like "**Choosing v_c:**"), goes in a div.keep (break-inside: avoid) with the block after it
//    (following titles are chained in). A block taller than KEEP_MAX is not moved whole: a long list keeps only its
//    first item with the title; anything else gets break-after: avoid on the title + orphans (the PDF check still
//    warns). KEEP_MAX depends on the document (see doc_layout): small in esqCLI, which must stay compact.
function isTitle(el) {
  if (/^H[1-6]$/.test(el.tagName)) return true;
  if (el.tagName !== "P" || el.children.length !== 1 || el.children[0].tagName !== "STRONG") return false;
  var t = el.textContent.trim();
  return t.length > 0 && t.length <= 160 && el.children[0].textContent.trim() === t;
}
function keepWithNext() {
  Array.prototype.slice.call(document.querySelectorAll("h1, h2, h3, h4, h5, h6, p")).forEach(function (el) {
    if (!isTitle(el) || el.parentElement.classList.contains("keep")) return;
    var group = [el], nx = el.nextElementSibling;
    while (nx && isTitle(nx)) { group.push(nx); nx = nx.nextElementSibling; }
    if (!nx || nx.id === "qa-report") return;
    if (nx.getBoundingClientRect().height > KEEP_MAX) {
      if (!/^(UL|OL)$/.test(nx.tagName) || nx.children.length < 2) {
        // too tall to move whole: only the title and the first lines (orphans: 3) go to the next page
        group.forEach(function (g) { g.style.breakAfter = "avoid"; });
        return;
      }
      var first = document.createElement(nx.tagName);
      first.appendChild(nx.firstElementChild);
      if (nx.tagName === "OL") { var st = nx.start || 1; first.start = st; nx.start = st + 1; }
      first.style.marginBottom = "0"; nx.style.marginTop = "0";
      nx.parentNode.insertBefore(first, nx); nx = first;
    }
    var keep = document.createElement("div"); keep.className = "keep";
    el.parentNode.insertBefore(keep, el);
    group.concat([nx]).forEach(function (g) { keep.appendChild(g); });
  });
}
// Layout checks on the rendered page (read back by check_render through --dump-dom; hidden, so never printed)
window.addEventListener("load", function () { document.fonts.ready.then(qa); });  // measure with KaTeX's own fonts
function qa() {
  var out = [], fs = parseFloat(getComputedStyle(document.body).fontSize), right = document.body.getBoundingClientRect().right;
  function around(t, i, n) { return t.slice(Math.max(0, i - 40), i + n + 40).replace(/\s+/g, " ").trim(); }
  function tex(el) { var a = el.querySelector("annotation"); return (a ? a.textContent : el.textContent).replace(/\s+/g, " ").trim().slice(0, 120); }
  var clone = document.body.cloneNode(true);
  clone.querySelectorAll(".katex, .katex-error-box, code, pre, script, style").forEach(function (e) { e.remove(); });
  var text = clone.textContent;
  var leftovers = [/\*\*[^*\n]{1,80}\*\*/g, /\\(frac|begin|end|vec|hat|left|right|sum|int|mathrm|text|langle|rangle)\b/g, /<\/?(span|div|strong|em|br|sup|sub)\b[^>]*>/g];
  if (CHECK_DOLLARS) leftovers.push(/\$[^$\n]{1,80}\$/g);  // skipped when the .md writes literal dollars as \$
  leftovers.forEach(function (re) { var m; while ((m = re.exec(text))) out.push(["WARNING", "unrendered Markdown/LaTeX/HTML in the text: ..." + around(text, m.index, m[0].length) + "..."]); });
  document.querySelectorAll("img").forEach(function (im) { if (!im.complete || !im.naturalWidth) out.push(["WARNING", "image not found: " + im.getAttribute("src")]); });
  // Anything wider than the text column makes Edge shrink the WHOLE PDF to fit (smaller text on every page).
  // Report only the outermost element that sticks out, described by its formula / image / text.
  // A formula is measured by its visible pieces (.base, .tag): its box is always as wide as the column even when
  // the formula sticks out, and KaTeX's hidden MathML copy must be ignored.
  function rightOf(el) {
    if (!el.classList.contains("katex")) return el.getBoundingClientRect().right;
    var m = -Infinity;
    el.querySelectorAll(".katex-html > .base, .katex-html > .tag").forEach(function (b) { m = Math.max(m, b.getBoundingClientRect().right); });
    return m > -Infinity ? m : el.getBoundingClientRect().right;
  }
  document.querySelectorAll("body *").forEach(function (el) {
    if (el.closest("#qa-report") || (el.parentElement && el.parentElement.closest(".katex"))) return;
    if (rightOf(el) <= right + 1) return;
    for (var a = el.parentElement; a && a !== document.body; a = a.parentElement) if (rightOf(a) > right + 1) return;
    var k = el.classList.contains("katex") ? el : el.querySelector(".katex");
    var what = el.tagName === "IMG" ? "image " + el.getAttribute("src")
      : k ? "formula " + tex(k)
      : el.tagName.toLowerCase() + (el.className ? "." + el.className : "") + " '" + el.textContent.replace(/\s+/g, " ").trim().slice(0, 80) + "'";
    out.push(["WARNING", "wider than the page by " + Math.round(rightOf(el) - right) + " px, so the whole PDF gets shrunk: " + what]);
  });
  // Right-margin notes (.aside-r) take no room, so they must sit in empty space: warn when one covers text,
  // a formula, an image, a box or another note.
  var notes = Array.prototype.slice.call(document.querySelectorAll(".aside-r"));
  if (notes.length) {
    var solid = [];  // rects of everything a note must not cover
    var walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (var n = walk.nextNode(); n; n = walk.nextNode()) {
      if (!n.textContent.trim() || n.parentElement.closest(".aside-r, #qa-report, .katex-mathml, script, style")) continue;
      var r = document.createRange(); r.selectNodeContents(n);
      Array.prototype.forEach.call(r.getClientRects(), function (c) { solid.push(c); });
    }
    document.querySelectorAll("img, table, .box, .box-f, .box-law, .box-def, .box-case, .katex-html > .base").forEach(function (el) { if (!el.closest(".aside-r")) solid.push(el.getBoundingClientRect()); });
    function hit(a, b) { return a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1; }
    notes.forEach(function (nt, i) {
      var a = nt.getBoundingClientRect(), g = {left: a.left - 6, right: a.right, top: a.top, bottom: a.bottom};
      var clash = solid.some(function (s) { return hit(g, s); }) || notes.some(function (o, j) { return j !== i && hit(a, o.getBoundingClientRect()); });
      if (clash) out.push(["WARNING", "right-margin note lands on text/formula/box/another note (move it next to a short line, a heading or a display formula, or shorten it): '" + nt.textContent.replace(/\s+/g, " ").trim().slice(0, 80) + "'"]);
    });
  }
  var tall = [];
  document.querySelectorAll('[data-tex="inline"]').forEach(function (el) {
    // measure each unbreakable piece (.base), so a formula that wraps onto two lines doesn't count as tall
    var h = 0;
    el.querySelectorAll(".katex-html .base").forEach(function (b) { h = Math.max(h, b.getBoundingClientRect().height / fs); });
    if (h > TALL_INLINE_EM) tall.push(tex(el).slice(0, 50));
  });
  if (tall.length) out.push(["CHECK", tall.length + " tall inline formula(s) (matrices, dfrac...) push their lines apart; fine if intended, otherwise smallmatrix / frac / display math: " + tall.join("  |  ")]);
  var pre = document.createElement("pre"); pre.id = "qa-report"; pre.style.display = "none";
  pre.textContent = JSON.stringify(out); document.body.appendChild(pre);
}
</script>
"""
TALL_INLINE_EM = 2.4  # inline formulas taller than this many em spread the text lines apart
KEEP_MAX = 420  # px (~11 cm): a block after a title up to this tall moves to the next page with its title
PAGE_BOTTOM_PT = 16 / 25.4 * 72  # bottom margin of @page
PT_PER_CM = 72 / 2.54


def doc_layout(stem):
    """Per document type (from the file name, set up 2026-09-28): (KEEP_MAX in px, blank space in cm at the bottom
    of a page that gives a CHECK, or None = no check). esqCLI must be compact: small blocks only move whole with
    their title and a gap > 4 cm is flagged; notesCLI/apuntesCLI may have gaps, only > 9 cm is flagged; ejsCLI and
    anything else: no gap check."""
    s = stem.lower()
    if s.startswith("esqcli"):
        return 150, 4.0  # 150 px ~ 4 cm
    if s.startswith(("notescli", "apuntescli")):
        return KEEP_MAX, 9.0
    return KEEP_MAX, None


def bottom_gaps(pdf, min_cm):
    """CHECK for every page (not the last) whose content ends more than min_cm above the bottom margin, i.e. a
    block too tall for the rest of the page jumped to the next one. Needs PyMuPDF; skipped without it."""
    try:
        import pymupdf
    except ImportError:
        return []
    out = []
    doc = pymupdf.open(pdf)
    for i in range(len(doc) - 1):
        page, low = doc[i], -1.0
        for b in page.get_text("dict")["blocks"]:
            if b["type"] == 1:
                low = max(low, b["bbox"][3])
            else:
                for ln in b["lines"]:
                    if any(s["text"].strip() for s in ln["spans"]):
                        low = max(low, ln["bbox"][3])
        for d in page.get_drawings():
            low = max(low, d["rect"].y1)
        if low < 0:
            continue
        gap = (page.rect.height - PAGE_BOTTOM_PT - low) / PT_PER_CM
        if gap > min_cm:
            nxt = " ".join(doc[i + 1].get_text().split())[:60]
            out.append(("CHECK", f"{gap:.1f} cm blank at the bottom of page {i + 1} (limit {min_cm:g} cm for this "
                                 f"document); page {i + 2} starts with '{nxt}'"))
    doc.close()
    return out


def orphan_titles(pdf):
    """Safety net for keepWithNext: WARNING when the last line of a page (not the last page) is a title, i.e. a bold
    line that is a heading (>= 11.5 pt) or ends in ':'. Needs PyMuPDF; skipped without it."""
    try:
        import pymupdf
    except ImportError:
        return []
    out = []
    doc = pymupdf.open(pdf)
    for i, page in enumerate(doc):
        if i == len(doc) - 1:
            break
        lines, img_low = [], -1
        for b in page.get_text("dict")["blocks"]:
            if b["type"] == 1:
                img_low = max(img_low, b["bbox"][3])
                continue
            for ln in b["lines"]:
                spans = [s for s in ln["spans"] if s["text"].strip() and s["size"] >= 2]
                if spans:
                    lines.append((ln["bbox"], spans))
        if not lines:
            continue
        y0, y1 = max(lines, key=lambda l: l[0][3])[0][1::2]
        if img_low > y1:  # the page ends with an image, not with text
            continue
        # one visual line can come out as several PDF lines (text and each formula piece): gather them all
        row = [l for l in lines if l[0][3] > y0 + 1 and l[0][1] < y1 - 1]
        last = [s for _, spans in sorted(row, key=lambda l: l[0][0]) for s in spans]
        words = [s for s in last if not s["font"].startswith("KaTeX") and s["size"] >= 9]  # skip maths, margin notes
        if not words:
            continue
        bold = all(s["flags"] & 16 or "Bold" in s["font"] or "Semibold" in s["font"] for s in words)
        text = "".join(s["text"] for s in last).strip()
        if bold and (max(s["size"] for s in words) >= 11.5 or text.endswith(":")):
            out.append(("WARNING", f"title alone at the bottom of page {i + 1}: '{text[:70]}' (keep it with its first block)"))
    doc.close()
    return out


def find_browsers():
    found = [b for b in BROWSERS if b.exists()]
    if not found:
        sys.exit("No Edge or Chrome found (looked in: " + ", ".join(map(str, BROWSERS)) + ")")
    return found


def protect_math(text):
    store = []

    def keep(kind):
        def repl(m):
            store.append((kind, m.group(1)))
            return f"MATHPH{len(store) - 1}X"
        return repl

    text = re.sub(r"\$\$(.+?)\$\$", keep("display"), text, flags=re.S)
    text = re.sub(r"(?<![\\$])\$(?!\$)(.+?)(?<![\\$])\$", keep("inline"), text)
    return text, store


def restore_math(body, store):
    def span(i):
        kind, tex = store[i]
        tag = "div" if kind == "display" else "span"
        cls = ' class="math-display"' if kind == "display" else ""
        return f'<{tag}{cls} data-tex="{kind}">{html.escape(tex.strip())}</{tag}>'

    # display formula + its purple cond (in a paragraph or inside a box div) -> one flex line, cond beside the formula
    cond = lambda m: f'<div class="math-cond">{span(int(m.group(1)))}{m.group(2)}</div>'
    body = re.sub(r'<p>\s*MATHPH(\d+)X\s*(<span class="cond">.*?</span>)\s*</p>', cond, body, flags=re.S)
    body = re.sub(r'MATHPH(\d+)X\s*(<span class="cond">.*?</span>)', lambda m: cond(m) if store[int(m.group(1))][0] == "display" else m.group(0), body, flags=re.S)
    body = re.sub(r"<p>\s*MATHPH(\d+)X\s*</p>", lambda m: span(int(m.group(1))), body)
    return re.sub(r"MATHPH(\d+)X", lambda m: span(int(m.group(1))), body)


def build_html(md_path, keep_max=KEEP_MAX, text=None, stem=None):
    """text/stem: build from an already filtered text (e.g. a copy of the note) instead of the file itself."""
    text = md_path.read_text(encoding="utf-8") if text is None else text
    protected, store = protect_math(text)
    md = MarkdownIt("commonmark", {"html": True}).enable("table")
    body = restore_math(md.render(protected), store)
    title = html.escape(stem or md_path.stem)
    # <base> makes relative image paths in the .md resolve from the .md's folder
    base = md_path.parent.as_uri() + "/"
    script = (SCRIPT.replace("TALL_INLINE_EM", str(TALL_INLINE_EM)).replace("KEEP_MAX", str(keep_max))
              .replace("CHECK_DOLLARS", "false" if "\\$" in text else "true"))
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>
<base href="{base}">
<link rel="stylesheet" href="{KATEX}/katex.min.css">
<script src="{KATEX}/katex.min.js"></script>
<style>{CSS}</style>{script}</head><body>{body}</body></html>""", len(store), text, body


def run_browser(cmd, done, timeout=180):
    """Run a headless browser and return its stdout. Windows: wait for it to exit. macOS/Linux: Chrome (154 on macOS,
    2026-10-09) writes the PDF / dumps the DOM and then never exits, so poll until done(stdout_so_far) and
    stop it ourselves (4 s instead of a 180 s hang)."""
    if os.name == "nt":
        try:
            return subprocess.run(cmd, capture_output=True, timeout=timeout, env=BROWSER_ENV,
                                  encoding="utf-8", errors="replace").stdout or ""
        except subprocess.TimeoutExpired:
            print(f"  note: {Path(cmd[0]).name} hung for {timeout} s")
            return ""
    with tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace") as out:
        p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.DEVNULL, env=BROWSER_ENV)
        end = time.time() + timeout
        while p.poll() is None and time.time() < end:
            time.sleep(0.5)
            out.seek(0)
            if done(out.read()):
                break
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
        out.seek(0)
        return out.read()


def pdf_ready(pdf):
    """done() for run_browser: the PDF exists, is not empty and its size didn't change in the last 0.5 s."""
    sizes = []

    def done(_):
        sizes.append(pdf.stat().st_size if pdf.exists() else 0)
        return len(sizes) >= 2 and sizes[-1] > 0 and sizes[-1] == sizes[-2]
    return done


def check_render(browser, page, tmp, n_math, text, body):
    """Render the page again, dump the final DOM and report problems as (level, message).
    WARNING = definitely broken (exit code 1); CHECK = probably wrong, worth a look."""
    problems = []
    if "<details" in text:
        problems.append(("WARNING", "contains <details> blocks, which don't work on paper (move answers to a final section)"))
    # A line break inside a paragraph followed by a bold lead-in is almost always two paragraphs run together
    for m in re.finditer(r"(?:[^>\s]|</(?:strong|em|span|a|code)>)\n<strong>(.{1,60}?)</strong>", body):
        problems.append(("CHECK", f"paragraphs run together before **{html.unescape(m.group(1))}** (add a blank line, or a '>' line inside a blockquote)"))
    dom = run_browser(
        [str(browser), "--headless=new", "--disable-gpu", f"--user-data-dir={tmp / 'profile2'}",
         "--virtual-time-budget=20000", "--dump-dom", page.as_uri()],
        lambda s: "</html>" in s)
    dom = re.sub(r"<script.*?</script>", "", dom, flags=re.S)
    errors = [html.unescape(e) for e in re.findall(r'katex-error-box">(.*?)</span>', dom)]
    if n_math and ('class="katex"' not in dom or any("katex is not defined" in e for e in errors)):
        return problems + [("WARNING", "KaTeX did not load (no internet?): formulas are printed as raw LaTeX")]
    problems += [("WARNING", e) for e in errors]
    qa = re.search(r'<pre id="qa-report"[^>]*>(.*?)</pre>', dom, flags=re.S)
    if qa:
        problems += [tuple(x) for x in json.loads(html.unescape(qa.group(1)))]
    else:
        problems.append(("CHECK", "the layout checks did not run (page took too long to load?)"))
    return problems


def convert(md_path):
    md_path = md_path.resolve()
    if not md_path.is_file():
        print(f"FAIL: {md_path} does not exist")
        return False
    browsers = find_browsers()
    out_dir = md_path.parent.parent if md_path.parent.name in SOURCE_DIRS else md_path.parent
    # Study-notes folders: PDF goes in the folder of its first week/tema (W1-2 -> W1/), sources stay flat
    week = re.search(r"\b([WT]\d+)", md_path.stem)
    if week and out_dir.name in ("Study notes (Claude)", "Apuntes explicativos (Claude)"):
        out_dir = out_dir / week.group(1)
        out_dir.mkdir(exist_ok=True)
    out_pdf = out_dir / (md_path.stem + ".pdf")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        page = tmp / "page.html"
        keep_max, gap_cm = doc_layout(md_path.stem)
        page_html, n_math, text, body = build_html(md_path, keep_max)
        page.write_text(page_html, encoding="utf-8")
        tmp_pdf = tmp / "out.pdf"
        for browser in browsers:
            cmd = [str(browser), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                   f"--user-data-dir={tmp / ('profile-' + browser.stem)}", "--virtual-time-budget=20000",
                   f"--print-to-pdf={tmp_pdf}", page.as_uri()]
            run_browser(cmd, pdf_ready(tmp_pdf))
            for _ in range(20):  # safety net in case a browser still detaches: wait up to 10 s for the PDF
                if tmp_pdf.exists() and tmp_pdf.stat().st_size:
                    break
                time.sleep(0.5)
            if tmp_pdf.exists() and tmp_pdf.stat().st_size:
                break
            print(f"  note: {browser.name} wrote no PDF, trying the next browser")
        else:
            print(f"FAIL: PDF generation failed for {md_path} (tried: {', '.join(b.name for b in browsers)})")
            return False
        problems = check_render(browser, page, tmp, n_math, text, body)
        shutil.move(str(tmp_pdf), out_pdf)
    problems += orphan_titles(out_pdf)
    if gap_cm:
        problems += bottom_gaps(out_pdf, gap_cm)
    print(f"OK -> {out_pdf}  ({n_math} formulas)")
    for level, msg in problems:
        print(f"  {level}: {msg}")
    return not any(level == "WARNING" for level, _ in problems)


if __name__ == "__main__":
    # Windows consoles default to cp1252; KaTeX error messages contain characters it can't print
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    results = [convert(Path(arg)) for arg in sys.argv[1:]]
    sys.exit(0 if all(results) else 1)
