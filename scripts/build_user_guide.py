from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SOURCE = DOCS / "USER_GUIDE.md"

# HTML temporaneo in build/; solo il PDF pubblicabile in dist/.
BUILD_DIR = ROOT / "build" / "user-guide"
DIST_DIR = ROOT / "dist"
OUTPUT = DIST_DIR / "LudoX-Guida-rapida.pdf"


CSS = r"""
@page {
    size: A4;
    margin: 16mm 16mm 20mm 16mm;
}

html {
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
}

body {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10.5pt;
    line-height: 1.45;
    color: #222;
    max-width: 178mm;
    margin: 0 auto;
}

h1 {
    font-size: 24pt;
    line-height: 1.15;
    margin: 0 0 8mm;
}

h2 {
    font-size: 17pt;
    line-height: 1.2;
    margin-top: 10mm;
    margin-bottom: 4mm;
    break-after: avoid-page;
    page-break-after: avoid;
}

h3 {
    font-size: 13pt;
    margin-top: 7mm;
    margin-bottom: 3mm;
    break-after: avoid-page;
    page-break-after: avoid;
}

p {
    orphans: 3;
    widows: 3;
}

img {
    display: block;
    max-width: 100%;
    max-height: 185mm;
    width: auto;
    height: auto;
    margin: 5mm auto 2mm;
    object-fit: contain;
    break-inside: avoid;
    page-break-inside: avoid;
}

pre {
    background: #f3f3f3;
    padding: 4mm;
    border-radius: 2mm;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    break-inside: avoid;
    page-break-inside: avoid;
}

code {
    font-family: Consolas, "Courier New", monospace;
}

blockquote {
    border-left: 3px solid #888;
    padding: 2mm 0 2mm 5mm;
    margin: 5mm 0;
    color: #444;
    break-inside: avoid;
    page-break-inside: avoid;
}

li {
    margin-bottom: 1.4mm;
}

hr {
    border: 0;
    border-top: 1px solid #ccc;
    margin: 8mm 0;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 5mm 0;
    break-inside: avoid;
}

th, td {
    border: 1px solid #bbb;
    padding: 2.5mm;
    vertical-align: top;
}

em {
    color: #555;
}
"""


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(
            f"File non trovato: {SOURCE}\n"
            "Metti questo script nel repository LudoX e verifica che esista docs/USER_GUIDE.md."
        )

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    source = SOURCE.read_text(encoding="utf-8")

    body = markdown.markdown(
        source,
        extensions=[
            "extra",
            "fenced_code",
            "tables",
            "sane_lists",
        ],
    )

    # I link relativi alle immagini nel Markdown sono relativi a docs/.
    docs_base = DOCS.resolve().as_uri()
    if not docs_base.endswith("/"):
        docs_base += "/"

    html = f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<base href="{docs_base}">
<title>LudoX - Guida rapida</title>
<style>
{CSS}
</style>
</head>
<body>
{body}
</body>
</html>
"""

    html_path = BUILD_DIR / "USER_GUIDE.html"
    html_path.write_text(html, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")

        page.pdf(
            path=str(OUTPUT),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<span></span>",
            footer_template="""
            <div style="
                width:100%;
                text-align:center;
                font-family:Arial, sans-serif;
                font-size:8px;
                color:#777;
            ">
                LudoX - Guida rapida ·
                <span class="pageNumber"></span> /
                <span class="totalPages"></span>
            </div>
            """,
            margin={
                "top": "16mm",
                "right": "16mm",
                "bottom": "20mm",
                "left": "16mm",
            },
        )
        browser.close()

    print(f"PDF creato: {OUTPUT}")


if __name__ == "__main__":
    main()
