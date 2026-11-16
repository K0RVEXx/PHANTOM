# Contributing to PHANTOM

Thank you for your interest in improving PHANTOM!

## Reporting bugs

Open an issue and include:

- Windows version, Python version (`python --version`) and terminal (cmd / Windows Terminal)
- Steps to reproduce, what you expected and what happened
- Relevant lines from `app/logs/phantom.log`

**Remove proxy credentials, IP lists and any personal data before posting.**
PHANTOM never writes passwords to the log, but check pasted config or list files.

## Suggesting features

Open an issue describing the problem the feature solves, how it would work from the
user's point of view (which menu, which setting), and any alternatives you considered.

## Pull requests

1. Fork the repository and create a branch from `main` (e.g. `fix/socks5-auth`).
2. Keep each pull request focused on one change.
3. Update `README.md` and `app/CHANGELOG.md` when behavior or settings change.
4. Describe what you changed and how you tested it.

## Code quality

- Python 3.8+ compatible, standard library first; new dependencies need a good reason
  and must be added to `app/requirements.txt`.
- Keep the modular structure: UI in `ui.py` / `app.py`, networking in `engine.py` /
  `tunnel.py`, proxy handling in `proxy.py`.
- All user-facing text (menus, statuses, errors, logs) is in **English**.
- Never log or display passwords, tokens or other credentials — use `Proxy.label()`.
- No fake or simulated results: every status shown must come from a real check.
- The Windows system proxy must only change on explicit user action and must always
  be restorable.
- No administrator rights may be required.

## Testing before submitting

Run the automated tests first:

```bash
python -m pytest tests
```

Then check these manually on Windows before opening a pull request:

1. `PHANTOM.bat` starts without errors and every main menu item opens and returns.
2. Load a proxy list and run the availability check.
3. Start rotation and verify the exit IP changes:
   `curl -x http://127.0.0.1:8888 https://api.ipify.org` (run it several times).
4. Verify failover: with a dead proxy in the pool, requests still succeed.
5. Enable and disable the Windows system proxy and confirm the original settings are
   restored (Settings → Network & internet → Proxy).
6. Exit with `[0]`, with Ctrl+C and by closing the window — the local port must be
   released and Windows proxy settings restored.
7. Resize the window / toggle full screen and confirm the layout redraws correctly.

## License of contributions

By submitting a contribution, you agree that KØRVEX may use, change and release it as
part of PHANTOM under the project's license (see [LICENSE](../LICENSE)). Forking this
repository on GitHub to prepare a pull request is fine; publishing a fork as a separate
project is not allowed.
