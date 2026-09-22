## Summary

Describe the behavior change and why it is needed.

## Scope

- [ ] Product/UI
- [ ] Conversation/application core
- [ ] Model gateway/provider
- [ ] Tooling
- [ ] Agents
- [ ] Memory
- [ ] Persistence
- [ ] Security
- [ ] Documentation
- [ ] CI/deployment

## Verification

- [ ] Targeted tests run
- [ ] Relevant regression tests run
- [ ] Lint/type/static checks run where configured
- [ ] Manual verification performed where relevant
- [ ] Security-sensitive paths reviewed

## Architecture

- [ ] CHAD -> LapisLLM boundary preserved
- [ ] Provider-specific code remains behind an adapter
- [ ] No consumer-product responsibility was moved into LapisLLM
- [ ] No secrets or generated artifacts added

## Documentation

- [ ] Documentation updated
- [ ] Roadmap item linked
- [ ] ADR added/updated when architecture changed

## Remaining uncertainty

State anything that was not verified.
