# Security Policy

## Supported versions

NewbieGram tracks the current stable line only.

| Version | Supported |
|---------|-----------|
| 0.3.x   | Yes       |
| < 0.3   | No        |

## Reporting a vulnerability

**Do not open a public issue for a security problem.**

Open a confidential report through GitHub's
[private vulnerability reporting](https://github.com/putzxdevs/newbiegram/security/advisories/new)
instead. If that is unavailable, contact the maintainers directly.

Please include:

- a description of the issue and its impact
- the version of NewbieGram and Python you are using
- steps to reproduce, ideally with a minimal script
- any proof-of-concept code or logs (with credentials redacted)

You can expect an acknowledgement within a few days. Once the report is
confirmed, we will agree on a disclosure timeline with you before publishing a
fix or advisory.

## Scope

In scope:

- anything that lets an attacker read, modify, or intercept data intended for
  another user or session
- authentication bypass, or leaking session strings and API credentials
- flaws in the MTProto framing, encryption, or key derivation
- remote code execution or arbitrary file writes through the library's own APIs
- unsafe parsing of untrusted message text or entities

Out of scope:

- issues that require you to already control the client process or its config
- denial of service purely from sending a very large amount of data through the
  normal API, at a rate your own credentials allow
- reports against the Telegram servers themselves

## Handling secrets

Session strings and API credentials are as sensitive as a password:

- never commit them, or paste them into an issue or pull request
- treat a session string as compromised if it is ever logged in public
- you can revoke a session at any time from the active-sessions list in the
  Telegram app