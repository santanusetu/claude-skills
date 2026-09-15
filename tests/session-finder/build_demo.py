#!/usr/bin/env python3
"""Record the README demo GIF of the session-finder page from the fictional fixtures.

Run from the repo root:  python3 tests/session-finder/build_demo.py
Needs Playwright for Python (with Chromium) and ffmpeg. Writes .github/media/session-finder-demo.gif.
"""
import glob, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_example  # noqa: E402  (also pins TZ so the times match the screenshots)
from playwright.sync_api import sync_playwright  # noqa: E402

W, H = 1200, 640
OUT = os.path.join(build_example.OUT, "session-finder-demo.gif")

# A visible pointer, since headless recordings do not draw the system cursor.
CURSOR = """
const c = document.createElement('div');
c.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24"><path d="M3 2l7 19 2.6-7.9L20.5 10z" fill="#fff" stroke="#000" stroke-width="1.4" stroke-linejoin="round"/></svg>';
Object.assign(c.style, {position:'fixed', left:'0', top:'0', zIndex:99999, pointerEvents:'none', transition:'none'});
document.body.appendChild(c);
document.addEventListener('mousemove', e => { c.style.transform = `translate(${e.clientX}px, ${e.clientY}px)`; }, true);
"""


def center(page, selector):
    box = page.locator(selector).bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def main():
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is required")
    work = tempfile.mkdtemp()
    html = os.path.join(work, "page.html")
    with open(html, "w") as fh:
        fh.write(build_example.example_html("dark"))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": W, "height": H}, record_video_dir=work,
                                  record_video_size={"width": W, "height": H})
        ctx.grant_permissions(["clipboard-read", "clipboard-write"])
        page = ctx.new_page()
        page.goto("file://" + html)
        page.evaluate(CURSOR)
        page.mouse.move(W - 120, 60)
        page.wait_for_timeout(1200)

        rows = page.locator("tr.row")
        for i in (2, 3, 0):  # point at a few rows: the prompt types out each command
            x, y = center(page, f"tr.row >> nth={i} >> td.about")
            page.mouse.move(x, y, steps=18)
            page.wait_for_timeout(1300)

        x, y = center(page, "tr.row >> nth=0 >> button")  # copy a safe session
        page.mouse.move(x, y, steps=18)
        page.wait_for_timeout(400)
        page.mouse.click(x, y)
        page.wait_for_timeout(1600)

        x, y = center(page, "tr.row >> nth=1 >> button")  # the one open elsewhere
        page.mouse.move(x, y, steps=18)
        page.wait_for_timeout(500)
        page.mouse.click(x, y)
        page.wait_for_timeout(2600)
        assert rows.nth(1).locator(".warnline").is_visible(), "warning line did not appear"

        video = page.video.path()
        ctx.close()
        browser.close()

    palette = os.path.join(work, "palette.png")
    trim = ["-ss", "0.4"]  # skip the blank first frames before the page paints
    vf = "fps=10,scale=860:-1:flags=lanczos"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *trim, "-i", video, "-vf", f"{vf},palettegen=max_colors=64", palette], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *trim, "-i", video, "-i", palette, "-lavfi",
                    f"{vf}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4", "-loop", "0", OUT], check=True)
    shutil.rmtree(work, ignore_errors=True)
    print("wrote", OUT, f"{os.path.getsize(OUT) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
