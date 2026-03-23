# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest  | yes |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report vulnerabilities by emailing the maintainer directly or by opening a
[GitHub Security Advisory](https://github.com/tsayles/branded-pdf-service/security/advisories/new).

Include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested remediation

You will receive an acknowledgement within 72 hours. We aim to release a fix
within 14 days of a confirmed report.

## Security Considerations for Operators

- **API keys:** Set \PDF_API_KEYS\ via environment variable or a mounted
  \secrets/api-keys.txt\ file. Never commit API keys to version control.
- **Network exposure:** Do not expose this service directly to the public
  internet without a reverse proxy (nginx, Caddy, Traefik) handling TLS.
- **Brand configs:** Brand volumes should be mounted read-only (\:ro\) in
  production. The write API (Phase 5) uses a separate named volume.
- **Non-root:** The container runs as the \pdfservice\ user (UID 1001).
  Do not override with \--user root\.
- **Markdown input:** Markdown is processed by Pandoc. Typst does not execute
  arbitrary code from document content. The attack surface for malicious
  Markdown is low, but operators should consider input length limits for
  public-facing deployments.
