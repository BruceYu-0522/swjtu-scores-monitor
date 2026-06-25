# Headless Browser Session Design

## Goal

Allow the Tencent Cloud server to monitor SWJTU scores without a graphical
desktop after the user completes enterprise-WeChat authentication once.

## Root Cause

The current bootstrap script saves browser cookies, but `ScoreFetcher` later
copies those cookies into a `requests.Session`. The current SWJTU login flow
does not accept that reduced session: the same IP and cookies still produce
the "not logged in" page. The authenticated browser state must therefore be
reused by a real browser.

## Design

1. Add Playwright as a project dependency so local bootstrap and server
   monitoring use the same browser API.
2. During interactive bootstrap, save Playwright `storage_state` rather than
   cookies alone. This includes cookies and origin storage, with IndexedDB
   included when supported.
3. Store the state inside the existing encrypted Gist payload. Keep reading
   the old cookie-only format so failures produce a clear reauthorization
   path instead of a decoding error.
4. When a saved browser state exists, `ScoreFetcher` starts headless Chromium,
   loads the state, and validates the score page in the browser.
5. Fetch the total-score and normal-score HTML through that browser, then pass
   the HTML to the existing BeautifulSoup parsing logic.
6. Always close the page, context, browser, and Playwright runtime after the
   score fetch or on error.
7. Keep the legacy password login only for installations with no saved browser
   state. An invalid saved browser state requires interactive reauthorization.

## Operational Flow

1. The user runs bootstrap on Windows through the SSH SOCKS proxy, so browser
   traffic exits from the Tencent Cloud server IP.
2. Bootstrap encrypts and saves the complete browser state to Gist.
3. A timer on Tencent Cloud runs `actions/index.py monitor`.
4. Headless Chromium restores the state, opens score pages, and returns HTML.
5. Existing comparison, persistence, and email notification code continues
   unchanged.

## Error Handling

- Missing Playwright or Chromium reports an actionable installation command.
- Invalid or expired authentication returns the existing login-required result
  and notification.
- Browser resources are closed even when navigation or parsing fails.
- Logs do not print cookie values, tokens, passwords, or encrypted state.

## Tests

- Bootstrap saves full storage state and browser metadata.
- Browser state is preferred over cookie-only `requests` restoration.
- A score table validates the restored browser session.
- A logged-out page rejects the restored browser session.
- Browser page HTML is handed to the existing score parsers.
- Browser resources close on success and failure.

