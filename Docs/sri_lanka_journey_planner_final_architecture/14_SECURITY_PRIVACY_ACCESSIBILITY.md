# 14 — Security, Privacy and Accessibility

## Security
- HTTPS for all network traffic.
- OAuth2/OIDC provider for accounts; short-lived access tokens and secure refresh handling.
- Role-based access control for admin/data reviewer/operator.
- Least privilege for database and background workers.
- Secrets in a secret manager, never in source control or mobile bundle.
- Parameterised queries and schema validation.
- Rate limits and abuse protection for public endpoints.
- Audit logs for data publication, rollback and report review.
- Dependency scanning, container scanning and regular patching.
- Backups with restore drills.
- Separate development, staging and production credentials/data.

## Privacy
- Guest planning should work without account creation.
- Request location permission only when needed.
- Do not retain continuous location history by default.
- Explain why photos/location are requested in issue reports.
- Define retention periods for reports, sessions, logs and account data.
- Provide account data export/deletion workflow where applicable.
- Avoid sending precise location or personally identifying information to an LLM unless essential and explicitly governed.
- Review applicable Sri Lankan data protection requirements and any other jurisdiction relevant to deployment/users with qualified counsel.

## Accessibility
- Support larger fonts, screen readers and adequate contrast.
- Provide text instructions alongside maps.
- Keep controls large and predictable.
- Avoid relying only on audio, colour or spatial map interpretation.
- Accessibility route claims require verified infrastructure attributes such as step-free access, lifts, ramps and crossing conditions.
- Mark unknown accessibility attributes as unknown.
