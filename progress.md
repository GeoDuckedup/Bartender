Original prompt: Debug the web Firebase leaderboard integration so the browser build fetches from and submits to the shared Realtime Database correctly, while desktop behavior keeps working.

- Investigating E3 regression: desktop Firebase path works, browser path does not fetch or submit.
- Strong suspect: browser transport used `pyodide.http.pyfetch`, but the addendum explicitly specifies `platform.window.fetch()` in the Pygbag runtime.
- Updated `network.py` browser path to use `platform.window.fetch()` with JS options conversion, while keeping the desktop threaded HTTP path unchanged.
- Next check: rebuild web export and verify browser fetch/submit against live Firebase.
- Based on user repro, browser was likely showing stale bundled `high_scores.json` while runtime fetch failed silently.
- Fix pass: browser no longer loads/saves `high_scores.json`, `high_scores.json` is excluded from pygbag packaging, and `network.py` now logs browser fetch/submit failures to the console.
- Added a richer pre-start splash control card in the web shell: visual `WASD`, visual arrow-key cluster, and a spacebar-style `POUR BEER` key so the browser start experience explains controls immediately.
- Replaced raw arrow glyphs in the splash control card with HTML entities plus dedicated arrow styling, since the previous literal characters were rendering incorrectly in browsers.
- Investigated Safari arrow-key regressions again and found the key clue: source files had the stronger Safari directional bridge, but generated `docs/index.html` / `web/index.html` and the packaged `tapper.tar.gz` were behind the latest source.
- Rebuilt the pygbag export and re-ran `scripts/prepare_web_build.py`, so the generated web shell now includes `forceDirectional`, `heldLeft`, `heldRight`, and the broader Safari arrow-key token detection.
- `py_compile` passed when run with a workspace-local pycache prefix; the earlier failure was only macOS Python trying to write bytecode into a protected global cache folder.
- Could not run the Playwright validation loop yet because the `playwright` npm package is not installed in this repo environment; browser-side follow-up should be manual unless/until that dependency is added.
