# Changelog

All notable changes to PHANTOM are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.5] - 2026-11-16

### Added
- First-time setup shows a live download bar (percent, size, speed) and an animated
  indicator while Python installs
- The window opens maximized on start (classic console: the text area is grown to fill the
  screen first). Can be turned off in Settings -> [W] Start maximized

## [1.0.4] - 2026-11-16

### Added
- First-time setup: if no working Python is found, `PHANTOM.bat` offers to download the official
  Python installer from python.org, verifies its signature and installs it for the current user
- The launcher now ignores the Microsoft Store placeholder `python` command
- Modified-copy check: PHANTOM compares its program files with the released list on start
  and, if they were changed, reminds the user what the license allows (shown once per change,
  never blocks)
- "Made by KØRVEX" in the About screen and README

### Changed
- License: from now on **PolyForm Internal Use License 1.0.0** with an extra permission
  for personal use - you may use and change the software for yourself, but not publish,
  share or redistribute it. Versions up to v1.0.3 remain under the MIT License

### Fixed
- Desktop shortcut pointed to a wrong path when the folder name contained characters
  outside the Windows ANSI code page (for example `Ø`); shortcuts are now written with
  the Unicode shell-link API and verified after saving

## [1.0.3] - 2026-11-15

### Added
- PHANTOM icon (hooded phantom on a dark purple folder): applied to the PHANTOM folder on start (Windows drops folder icons when
  extracting ZIPs), plus an optional desktop shortcut with the icon - offered once on first
  start and available in Rotation Settings -> [D]

### Fixed
- Layout was off-center after leaving full screen: PHANTOM now waits until the window
  size settles before redrawing, and also catches resizes that happen while drawing

## [1.0.2] - 2026-11-15

### Added
- "Welcome back" screen for users who declined the terms before: asks honestly why they
  returned and explains that accepting is a real promise, not just a way in

### Changed
- Declined-terms message is now shown fully in PHANTOM green

## [1.0.1] - 2026-11-15

### Added
- Terms of use screen on first start (asked again only when the terms change)
- Friendly explanation screen when the terms are declined
- Acceptable use and no-liability-for-misuse section in DISCLAIMER.md and README

## [1.0.0] - 2026-11-15

### Added
- Local rotating proxy on `127.0.0.1` with HTTP, HTTPS, SOCKS4 and SOCKS5 upstream support
- Proxy list loading (`IP:PORT`, `IP:PORT:USER:PASS`, `USER:PASS@IP:PORT`, protocol prefixes)
- Availability checks with HTTPS tunnel test, latency, exit IP, country and region
- Timed and manual rotation, random / sequential mode, reuse avoidance
- Automatic failover, latency filter and parallel backup attempts
- Fastest rotation mode with background health checks
- Sticky sites: same proxy per website for a configurable time
- Connection status screen, live monitor and timestamped activity logs
- Optional Windows system proxy mode with automatic restore
- Centered, resize-aware terminal interface with full and compact headers
- Auto-saved configuration
- Project layout: `PHANTOM.bat`, `README.md`, `LICENSE` at the root, program in `app/`, lists in `proxies/`
- Automatic installation of `requirements.txt` on first start
- Automated tests (pytest) and GitHub Actions CI on Windows
- Issue / pull request templates, SECURITY.md, example proxy list
- Open source documentation: MIT License, README, BRANDING, DISCLAIMER, CONTRIBUTING
