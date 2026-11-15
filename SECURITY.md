# Security Policy

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Report them privately through GitHub:
**Security → Report a vulnerability** on this repository
(GitHub private vulnerability reporting).

Include a description, steps to reproduce and the affected version.
You will get a response as soon as possible; please allow reasonable time for a fix
before any public disclosure.

## Scope

Examples of relevant issues:

- Credentials being written to logs, exports or the screen
- The Windows system proxy not being restored correctly
- The local proxy being reachable from other machines (it must listen on `127.0.0.1` only)

Note that the security of third-party proxies themselves is outside the project's
control — see [DISCLAIMER.md](app/DISCLAIMER.md).
