# Security Policy

## Scope
CHAD is intended to read and modify local repositories and execute developer tools. Vulnerabilities may affect source code, credentials, local files, processes, or network access.

## Reporting
Do not disclose exploitable vulnerabilities in public issues. Report them privately to the repository owner through an available private GitHub security reporting channel. Include affected versions/commits, reproduction steps, impact, and suggested mitigations. Do not include real secrets or personal data in the report.

## Security design requirements
- Treat model output, repository content, tool output, and external content as untrusted.
- Enforce workspace boundaries after canonical path resolution.
- Redact credentials from logs and model-visible context.
- Require explicit approval for destructive actions and policy-sensitive commands.
- Bound process runtime, output size, concurrency, and agent iterations.
- Record security-relevant decisions without recording secret values.
- Do not claim OS-level sandboxing unless it is implemented and tested.
- Make network access an explicit capability controlled by policy.

## Supported versions
Until the first release exists, security fixes target the default development branch. A formal support window will be defined before stable releases.
