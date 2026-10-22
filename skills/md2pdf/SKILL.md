---
name: md2pdf
description: Convert Markdown (.md) files, including LaTeX math ($...$ and $$...$$), into nicely formatted A4 PDFs with properly rendered formulas. Use whenever the user says "md to pdf", "go from .md to .pdf", "make it a PDF", "convert to PDF", "regenerate the PDF", "export this as PDF", or asks for any document/notes/summary/formula sheet delivered as a PDF.
---

# Markdown → PDF

The converter is `~/.claude/skills/md2pdf/md2pdf.py` (Markdown + KaTeX, printed with headless Chrome, falling back to Edge if Chrome writes no PDF (Chrome first because it is ~2× faster; both work. Edge "wrote no PDF" on 2026-09-26 because of the `__COMPAT_LAYER` variable in Claude Code's shell, which the script now strips before launching the browsers); needs internet for KaTeX and the `markdown-it-py` package (`python -m pip install markdown-it-py`); `pymupdf` for rendering pages to check them).

Note (migrated kit): the blank-space checks and some layout rules only switch on for file names starting with `esqCLI` / `notesCLI` / `apuntesCLI` / `ejsCLI` (the original owner's study-document naming). Other names get every other check. The CSS classes (`def`, `hl-f`, `box-f`, `minor`, `aside`…) come from the owner's colour code for notes; use them only if the user adopts a colour code.

## What to do

1. **Work out which .md file(s).**
   - If the user named or attached a file, use it.
   - Otherwise use the .md we just wrote or edited in this conversation.
   - If it's still unclear, look for .md files in the current folder (and in `_source/` / `_fuente/` subfolders), pick the obvious one, or ask with a short list if there are several candidates.
   - If the user wants a PDF of content that isn't in a .md yet, first write the Markdown source (see "Where files go"), then convert it.

2. **Convert** (quote paths; they often contain spaces and accents):
   ```
   <PY> "<HOME>/.claude/skills/md2pdf/md2pdf.py" "<file.md>" ["<more.md>" ...]
   ```

3. **Read the output.** Each file prints `OK -> <pdf path> (N formulas)`, then `WARNING:` and `CHECK:` lines. The script re-renders the page and checks **every page** for the problems below, so you don't need to render pages to find them.

   **`WARNING` = broken (exit code 1).** Fix it in the .md and convert again, until none are left:
   - `ERROR KaTeX: … in: <LaTeX>` → fix that formula; the message shows its LaTeX, so search the .md for it.
   - `wider than the page by N px, so the whole PDF gets shrunk: formula …` → the browser shrinks the **whole PDF** to fit anything wider than the text column, so every page ends up with smaller text. Split the formula over lines (`\begin{gathered} … \\ … \end{gathered}`, or `aligned` with `&`), or move its words out into the text. A wide image or table: make it narrower.
   - `unrendered Markdown/LaTeX/HTML in the text` → usually Markdown inside an HTML block written on one line (`<div class="hl">**x**</div>` prints the `**`): use `<strong>`/`<em>` there, or leave a blank line after the opening tag and before the closing one. Otherwise an unmatched `$` or a typo in a tag.
   - `image not found: …` → fix the path (it's relative to the .md's folder).
   - `KaTeX did not load` → no internet; tell the user, formulas would be raw LaTeX.
   - `right-margin note lands on text/formula/box/another note` → an `aside-r` note (absolutely positioned, the text doesn't wrap around it) covers something. Move it to empty space nearby: after a short line, just before a centred `$$` display formula as `<div class="aside-r">…</div>`, or on a heading's line; or shorten it.
   - `title alone at the bottom of page N: '…'` → a heading or bold "…:" lead-in ended a page with its content on the next one. The script already prevents this on its own (see *Automatic layout fixes* below), so this only fires when the block after the title is too tall to move whole (> ~11 cm, ~4 cm in `esqCLI`; not a list) and the title's `break-after: avoid` wasn't honoured: wrap the title and the start of that block in `<div style="break-inside:avoid">` (blank line after the opening tag and before `</div>`), or split the block.
   - `contains <details> blocks` → replace them (they don't work on paper): put the answers/solutions in a final section instead.

   **`CHECK` = probably wrong, have a look** (doesn't change the exit code):
   - `paragraphs run together before **X**` → a line starting with bold comes straight after a text line with no blank line between them, so both print as one paragraph. Almost always a missing blank line (inside a blockquote, a `>` line): add it, unless the join is intended.
   - `N tall inline formula(s) …` → inline matrices or `\dfrac` push their lines apart. Often deliberate, so leave existing ones alone. For ones you just wrote, use `\left(\begin{smallmatrix}…\end{smallmatrix}\right)`, `\frac` or a display formula when that reads better.
   - `X cm blank at the bottom of page N (limit …); page N+1 starts with '…'` → a block that can't be split (box, blockquote, figure, `div.minor`/`div.aside`, table) didn't fit and jumped to the next page. Only checked in `esqCLI` (> 4 cm, they must be compact) and `notesCLI`/`apuntesCLI` (> 9 cm); `ejsCLI` and other files never. Fix it only in a file you are writing or editing now: shrink the figure, split the block in two, or move a small block into the gap. A deliberate page break, or a gap nothing can fill, is fine: leave it and mention it in one line.

   Other failures: `FAIL: PDF generation failed … (tried: …)` = no browser wrote the PDF, even on a one-line test file → tell the user, don't work around it. `No Edge or Chrome found` / `ModuleNotFoundError: markdown_it` → tell the user; the fix for the latter is `python -m pip install markdown-it-py`.

4. **Look at the pages only for what the script can't judge:** new or changed figures, and new or changed boxes, brackets (`div.minor` / `div.aside`), right-margin notes (`aside-r`: they take no room, so check they read as belonging to the right line) and tables. Render just those pages to PNG in the scratchpad (`pymupdf.open(pdf)[i].get_pixmap(dpi=100).save(png)`) and look at them. Pages with only text and formulas are already covered by the checks.

5. **Report** the PDF path to the user in one or two lines. Don't paste the content back.

## Automatic layout fixes (added 2026-09-28, nothing to write in the .md)

Before printing, the page script:
- **Keeps every title with its first block:** each heading `h1–h6`, and each *pseudo-title* (a paragraph that is only bold text, like `**Choosing $\mathbf v_c$:**`), goes in a `div.keep` (`break-inside: avoid`) together with the block after it; consecutive titles are chained. A long list keeps only its first item with the title. A block too tall to move whole (> ~11 cm; **~4 cm in `esqCLI`**, so esqs stay compact) is not moved: the title gets `break-after: avoid`, so only it and the block's first lines go to the next page. Manual `break-inside:avoid` wrappers are no longer needed (old ones are harmless). The PDF is then scanned and any page that still ends with a title gives a `WARNING` (see above).
- **Never breaks short inline maths:** an inline formula narrower than 45 % of the line can't be split (KaTeX would break after `<`, `>`, `=`), and it is glued to the `(` / `[` right before it and to `)` `.` `,` `;` `:` right after it, so `($>0$)` never prints as `(>` | `0)` or `(>0` | `)`.

## Where files go

- If the .md is inside a `_source/` or `_fuente/` folder, the PDF is written to the **parent** folder (source stays tucked away, PDF sits next to the other material).
- Otherwise the PDF is written **next to the .md**, with the same name.
- An existing PDF with that name is overwritten. That's intended when regenerating from its own source; if it looks like an unrelated PDF (e.g. a teacher's file), check with the user first.
- When creating a new document from scratch, put the Markdown in a `_source/` subfolder next to where the PDF should end up (`_fuente/` for Spanish-language material), unless the project's CLAUDE.md says otherwise.

## Writing Markdown that converts well

- Math: `$...$` inline, `$$...$$` display (can span lines). Standard KaTeX LaTeX: `\frac`, `\vec`, `\hat`, `\langle \rangle`, `\begin{aligned}`, `\begin{pmatrix}`, `\boxed{}`, `\text{}`… No custom `\newcommand`. No Unicode maths symbols inside `\text{}` (a `·` there gives `Undefined control sequence: \cdotp`): write `\text{J}\cdot\text{s}`.
- A literal dollar sign must be written `\$`.
- The text column is about 17.5 cm wide: split long display formulas over lines (`gathered` / `aligned`) instead of chaining several results with `\qquad`.
- Separate paragraphs with a blank line (inside a blockquote, a line with just `>`). A line that starts with `**Bold:**` right under another line joins that paragraph.
- Markdown isn't processed inside an HTML block written on one line: use `<strong>`/`<em>` there, or put the Markdown on its own lines with blank lines around it.
- Tables (GitHub pipe tables), blockquotes (render as highlighted boxes — good for key results/warnings), code blocks, `---` rules and relative image paths all work.
- No `<details>`/collapsible content; nothing interactive.
- After **any** later edit to the .md, regenerate the PDF so both stay in sync.
