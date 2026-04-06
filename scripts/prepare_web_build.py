from __future__ import annotations

import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_WEB_DIR = REPO_ROOT / "build" / "web"
TARGET_DIRS = (REPO_ROOT / "docs", REPO_ROOT / "web")
BOX_ART_SOURCE = REPO_ROOT / "web_assets" / "box-art.png"

PROMPT_HTML = """<div class="infobox-title">BARTENDER</div>
<div class="infobox-subtitle">SPACEBAR TO START</div>"""

LOADING_HTML = """<div class="infobox-title">BARTENDER</div>
<div class="infobox-subtitle">LOADING</div>
<div class="infobox-note">INSTALLING {pkg.upper()}</div>"""

STATUS_BLOCK = """        #status {
            display: inline-block;
            vertical-align: top;
            margin-top: 20px;
            margin-left: 0;
            font-weight: bold;
            color: #f6ddb0;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            text-shadow: 0 2px 0 #5a2e14;
        }
"""

PROGRESS_BLOCK = """        #progress {
            height: 12px;
            width: 260px;
            accent-color: #d07c2f;
        }

        #transfer {
            position: fixed;
            left: 50%;
            bottom: 28px;
            transform: translateX(-50%);
            z-index: 30;
            text-align: center;
        }

        #splash-art {
            position: fixed;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -52%);
            z-index: 8;
            display: flex;
            align-items: center;
            justify-content: center;
            pointer-events: none;
            transition: opacity 180ms ease;
        }

        #splash-art img {
            display: block;
            width: min(34vw, 420px);
            max-height: 78vh;
            height: auto;
            border: 4px solid #d66b2c;
            border-radius: 14px;
            box-shadow:
                0 0 0 8px rgba(22, 11, 6, 0.92),
                0 20px 60px rgba(0, 0, 0, 0.48);
        }
"""

INFOBOX_BLOCK = """        #infobox {
            position: fixed; /* center relative to viewport */
            background: rgba(154, 85, 30, 0.74);
            color: #ffe9bf;
            font-weight: bold;
            padding: 8px 18px 10px;
            border: 4px solid #d66b2c;
            border-radius: 14px;
            box-shadow: 0 0 0 6px rgba(30, 15, 9, 0.92);
            z-index: 999999;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            text-align: center;
            min-width: 280px;
            max-width: 340px;
            height: auto;
        }

        .infobox-title {
            font-size: 22px;
            line-height: 1;
            letter-spacing: 0.08em;
            color: #ffe9bf;
            text-shadow: 0 3px 0 #7d2219;
            margin-bottom: 4px;
        }

        .infobox-subtitle {
            font-size: 12px;
            line-height: 1.2;
            color: #f6ddb0;
            margin-bottom: 0;
        }
"""

BODY_BLOCK = """        body {
            font-family: "Courier New", monospace;
            margin: 0;
            padding: 0;
            background-color: #160b06;
            color: #f6ddb0;
            overflow: hidden;
        }

        body.started #splash-art {
            opacity: 0;
            visibility: hidden;
        }

        body.started #transfer {
            display: none;
        }
"""

FOCUS_JS = """        const focusCanvas = () => {
            canvas.focus()
        }

        ;["click", "mousedown", "touchstart"].forEach((eventName) => {
            canvas.addEventListener(eventName, focusCanvas, { passive: true })
            document.addEventListener(eventName, focusCanvas, { passive: true })
        })

        window.addEventListener(
            "keydown",
            (event) => {
                const blockedKeys = new Set([
                    "ArrowUp",
                    "ArrowDown",
                    "ArrowLeft",
                    "ArrowRight",
                    " ",
                    "Spacebar",
                    "w",
                    "W",
                    "a",
                    "A",
                    "s",
                    "S",
                    "d",
                    "D",
                    "f",
                    "F",
                ])
                if (blockedKeys.has(event.key)) {
                    event.preventDefault()
                    focusCanvas()
                    if ((event.key === " " || event.key === "Spacebar") && window.MM && !window.MM.UME) {
                        window.MM.UME = true
                    }
                }
            },
            { capture: true }
        )
"""

SPLASH_HTML = """<body>

    <div id="splash-art">
        <img src="box-art.png" alt="Bartender box art">
    </div>
"""


def replace_once(text: str, old: str, new: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Expected snippet not found while patching:\n{old[:120]}")
    return text.replace(old, new, 1)


def patch_index_html(html: str) -> str:
    html = replace_once(
        html,
        """function show_infobox() {
    infobox.style.display = "block";

    // Measure box
    const w = infobox.offsetWidth;
    const h = infobox.offsetHeight;

    // Center in viewport
    const left = (window.innerWidth - w) / 2;
    const top = (window.innerHeight - h) / 2;

    infobox.style.left = left + "px";
    infobox.style.top = top + "px";
}
""",
        """function show_infobox() {
    infobox.style.display = "block";

    // Measure box
    const w = infobox.offsetWidth;
    const h = infobox.offsetHeight;

    // Center horizontally and anchor lower over the poster without stretching.
    const left = (window.innerWidth - w) / 2;
    const top = Math.min(
        window.innerHeight - h - 32,
        Math.max(24, (window.innerHeight * 0.62) - (h / 2))
    );

    infobox.style.left = left + "px";
    infobox.style.top = top + "px";
}
""",
    )
    html = replace_once(
        html,
        '    platform.document.body.style.background = "#7f7f7f"\n',
        '    platform.document.body.style.background = "#160b06"\n',
    )
    html = replace_once(
        html,
        '        msg  = "Ready to start ! Please click/touch page"\n        platform.window.infobox.innerText = msg\n',
        f'        msg  = """\n{PROMPT_HTML}\n"""\n        platform.window.infobox.innerHTML = msg\n',
    )
    html = replace_once(
        html,
        "        while not platform.window.MM.UME:\n            await asyncio.sleep(.1)\n",
        "        while not platform.window.MM.UME:\n            await asyncio.sleep(.1)\n\n        platform.window.document.body.classList.add(\"started\")\n",
    )
    html = replace_once(
        html,
        '        platform.window.infobox.innerText = f"installing {pkg}"\n',
        f'        platform.window.infobox.innerHTML = f"""\n{LOADING_HTML}\n"""\n',
    )
    html = replace_once(
        html,
        """        #status {
            display: inline-block;
            vertical-align: top;
            margin-top: 20px;
            margin-left: 30px;
            font-weight: bold;
            color: rgb(120, 120, 120);
        }
""",
        STATUS_BLOCK,
    )
    html = replace_once(
        html,
        """        #progress {
            height: 20px;
            width: 300px;
        }
""",
        PROGRESS_BLOCK,
    )
    html = replace_once(
        html,
        """        #infobox {
            position: fixed; /* center relative to viewport */
            background: green;
            color: blue;
            font-weight: bold;
            padding: 12px 24px;
 /*           display: none; */
            z-index: 999999;
        }
""",
        INFOBOX_BLOCK,
    )
    html = replace_once(
        html,
        """        canvas.emscripten {
            border: 0px none;
            background-color: transparent;
            width: 100%;
            height: 100%;
            z-index: 5;
""",
        """        canvas.emscripten {
            border: 0px none;
            background-color: transparent;
            width: 100%;
            height: 100%;
            image-rendering: pixelated;
            image-rendering: crisp-edges;
            z-index: 5;
""",
    )
    html = replace_once(
        html,
        """        body {
            font-family: arial;
            margin: 0;
            padding: none;
            background-color:powderblue;
        }
""",
        BODY_BLOCK,
    )
    html = replace_once(
        html,
        "<body>\n",
        SPLASH_HTML,
    )
    html = replace_once(
        html,
        "        show_infobox()\n",
        f"        show_infobox()\n\n{FOCUS_JS}",
    )
    return html


def prepare_target(target_dir: Path) -> None:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(BUILD_WEB_DIR, target_dir)
    shutil.copy2(BOX_ART_SOURCE, target_dir / "box-art.png")
    index_path = target_dir / "index.html"
    index_path.write_text(patch_index_html(index_path.read_text()))


def main() -> None:
    if not BUILD_WEB_DIR.exists():
        raise SystemExit(f"Missing build output: {BUILD_WEB_DIR}")
    if not BOX_ART_SOURCE.exists():
        raise SystemExit(f"Missing box art source: {BOX_ART_SOURCE}")

    for target_dir in TARGET_DIRS:
        prepare_target(target_dir)

    print("Prepared web build in docs/ and web/")


if __name__ == "__main__":
    main()
