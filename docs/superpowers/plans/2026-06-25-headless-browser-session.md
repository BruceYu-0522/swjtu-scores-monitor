# Headless Browser Session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reuse a complete authenticated Playwright browser state on Tencent Cloud so score monitoring runs headlessly without a graphical desktop.

**Architecture:** Interactive bootstrap stores Playwright `storage_state` in the existing encrypted Gist payload. `ScoreFetcher` detects that state, opens a short-lived headless Chromium context, validates the authenticated score page, fetches both score-page HTML documents, and feeds them into the existing BeautifulSoup parsing behavior.

**Tech Stack:** Python 3.12, Playwright, requests, BeautifulSoup, pytest, uv

---

### Task 1: Persist Complete Playwright State

**Files:**
- Modify: `scripts/bootstrap_session.py`
- Modify: `test/test_bootstrap_session.py`

- [ ] **Step 1: Write the failing test**

Add a fake browser context test which asserts that bootstrap session data uses
`context.storage_state(indexed_db=True)` and stores the result under
`storage_state`, together with the captured user agent.

- [ ] **Step 2: Run the focused test**

Run:

```powershell
$env:UV_CACHE_DIR="$PWD\.uv-cache"
uv run --with pytest --with playwright pytest test/test_bootstrap_session.py -q
```

Expected: FAIL because bootstrap currently stores only `context.cookies()`.

- [ ] **Step 3: Implement the storage-state helper**

Add:

```python
def capture_storage_state(context):
    try:
        return context.storage_state(indexed_db=True)
    except TypeError:
        return context.storage_state()
```

Use it before closing the browser and save the returned dictionary as
`session_data["storage_state"]`. Keep `cookies` as a compatibility summary.

- [ ] **Step 4: Run the focused test**

Expected: all bootstrap tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/bootstrap_session.py test/test_bootstrap_session.py
git commit -m "feat: persist complete browser storage state"
```

### Task 2: Add a Headless Browser Session Adapter

**Files:**
- Create: `utils/browser_session.py`
- Create: `test/test_browser_session.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`

- [ ] **Step 1: Write failing adapter tests**

Cover these behaviors with fake Playwright objects:

```python
def test_start_restores_storage_state_and_validates_score_page(): ...
def test_start_rejects_logged_out_page_and_closes_resources(): ...
def test_get_html_returns_page_content(): ...
def test_close_releases_context_browser_and_runtime(): ...
```

The fake context must record the `storage_state` passed to
`browser.new_context`, and the fake page must return configured URL, title,
and HTML.

- [ ] **Step 2: Run the focused tests**

Run:

```powershell
uv run --with pytest --with playwright pytest test/test_browser_session.py -q
```

Expected: FAIL because `utils.browser_session` does not exist.

- [ ] **Step 3: Implement `BrowserSession`**

Create a focused adapter with:

```python
class BrowserSession:
    def __init__(self, storage_state, playwright_factory=None): ...
    def start(self, validation_url): ...
    def get_html(self, url, referer=None): ...
    def close(self): ...
```

`start` launches Chromium with `headless=True`, creates a context using the
saved state, loads the validation URL, and accepts the session only when a
`table#table3` exists. It logs a short page summary on rejection. `close`
releases page, context, browser, and Playwright runtime safely and
idempotently.

- [ ] **Step 4: Add Playwright dependency**

Add a pinned Playwright dependency through:

```powershell
uv add playwright
```

- [ ] **Step 5: Run focused tests**

Expected: all browser-session tests PASS.

- [ ] **Step 6: Commit**

```bash
git add utils/browser_session.py test/test_browser_session.py pyproject.toml uv.lock
git commit -m "feat: add headless browser session adapter"
```

### Task 3: Route Score Fetching Through Chromium

**Files:**
- Modify: `utils/fetcher.py`
- Modify: `test/test_fetcher_session.py`

- [ ] **Step 1: Write failing integration-unit tests**

Add tests that provide saved data containing:

```python
{"storage_state": {"cookies": [], "origins": []}}
```

Assert that:

1. `login()` starts the injected browser adapter and does not call the
   requests-session validator.
2. `get_all_scores()` parses HTML returned by the browser adapter.
3. `get_normal_scores()` parses HTML returned by the browser adapter.
4. `close()` is called after `get_combined_scores()`, including when parsing
   raises.

- [ ] **Step 2: Run the focused tests**

Run:

```powershell
uv run --with pytest pytest test/test_fetcher_session.py -q
```

Expected: FAIL because `ScoreFetcher` does not yet select a browser adapter.

- [ ] **Step 3: Implement browser routing**

Inject a `browser_session_factory` into `ScoreFetcher`. When saved data has a
`storage_state`, start the adapter and use its `get_html` method in both score
fetch methods. Move HTML parsing into private helpers shared by requests and
browser paths. Close the browser adapter in a `finally` block around combined
fetching.

- [ ] **Step 4: Preserve compatibility**

Cookie-only saved data continues through the existing requests-session path.
No saved state continues through legacy password login. Invalid complete
browser state stops and requests manual reauthorization.

- [ ] **Step 5: Run focused tests**

Expected: all fetcher tests PASS.

- [ ] **Step 6: Commit**

```bash
git add utils/fetcher.py test/test_fetcher_session.py
git commit -m "feat: fetch scores with restored headless browser"
```

### Task 4: Documentation and Full Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update operating instructions**

Document that:

- Bootstrap must be rerun once after this upgrade.
- `uv sync` installs Playwright, while
  `uv run playwright install chromium` installs Chromium.
- Tencent Cloud monitoring runs headlessly and does not need XFCE/xrdp.
- The SSH SOCKS tunnel is needed only while refreshing authorization.

- [ ] **Step 2: Run full verification**

Run:

```powershell
$env:UV_CACHE_DIR="$PWD\.uv-cache"
uv sync
uv run python -m pytest test -q
uv run python -m compileall actions scripts utils
git diff --check
```

Expected: all tests PASS, compilation succeeds, and no whitespace errors.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: explain headless server monitoring"
```

- [ ] **Step 4: Push**

Push `codex/headless-browser-session` to the `fork` remote, then merge or
fast-forward it into the fork's default branch after verification.

