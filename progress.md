Original prompt: Debug the web Firebase leaderboard integration so the browser build fetches from and submits to the shared Realtime Database correctly, while desktop behavior keeps working.

- Investigating E3 regression: desktop Firebase path works, browser path does not fetch or submit.
- Strong suspect: browser transport used `pyodide.http.pyfetch`, but the addendum explicitly specifies `platform.window.fetch()` in the Pygbag runtime.
- Updated `network.py` browser path to use `platform.window.fetch()` with JS options conversion, while keeping the desktop threaded HTTP path unchanged.
- Next check: rebuild web export and verify browser fetch/submit against live Firebase.
