# Patterns worth knowing about, not worth copying yet

Architectures seen on other projects that are too tightly coupled to their original context to
drop in as generic skills here, but are worth remembering before building something similar from
scratch.

## Tiered plan-and-verify loop with idea briefs

A heavier variant of this repo's own `feature_analyst`/`ralph-implement` pair: work is triaged
into three tiers by risk (skip planning entirely / lightweight plan / full idea-brief-then-plan),
and every plan ends with a black-box verification round — a separate subagent that never saw the
code, given only user-facing scenarios and acceptance criteria, talking to the running bot the way
a real user would. Tracking failures over time found that every criterion that failed black-box
testing was an invariant left to prose ("the bot must never X") rather than enforced in code —
worth remembering generally: if a requirement reads like "must always/never," write the code
guard, not just the instruction. Adopt the tiering if this project's plans start either over- or
under-investing relative to the actual risk of the change (right now, a single `feature_analyst`
pass covers everything — fine at this size).

## Deploy-safety protocol

Ask consent → backup current state → deploy → restart → health-check with retry → rollback on
failure. The shape generalizes to any single-server deploy. This project's `deploy.yml` already
does push → test gate → sync → systemd restart → active-status poll; a rollback step (revert to
the previous commit's files and restart) is the one piece not yet automated here.

## Agent-loop design notes

Useful ideas for a long-running agent loop (as opposed to a per-invocation skill): a running
findings memory carried across turns, a rate-limit fallback chain across providers/models, and
per-session logging for post-hoc debugging.
