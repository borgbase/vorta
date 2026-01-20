---
name: issue-triage
description: Triage and classify GitHub issues for the Vorta project. Use when reviewing issues, applying labels, deciding whether to close issues, or evaluating feature requests against project scope.
user-invocable: true
---

# Vorta Issue Triage Policy

Use this policy to classify, label, and manage GitHub issues for the Vorta project.

## Core Principles

1. **Bugs should be found and addressed** - prioritize by severity
2. **Feature requests adding complexity, dependencies, or affecting rare use cases** - mark as `status:idea`
3. **Issues already addressed** - close with explanation
4. **Borg feature requests** - mark as `status:wontfix` with comment directing to BorgBackup
5. **Issues needing testing on specific systems** - mark as `help wanted`

## Available Labels

### Type Labels
- `type:bug` - Something doesn't work as intended
- `type:enhancement` - Improvement of an existing function
- `type:feature` - New functionality
- `type:question` / `type:support` - Questions about using Vorta
- `type:docs` - Documentation issues
- `type:refactor` - Code refactoring
- `type:translations` - Translation problems

### Priority Labels
- `priority:high` - Security issues, data loss risks, crashes in core functionality
- `priority:medium` - Broken features with workarounds
- `priority:low` - Cosmetic issues, minor improvements, edge cases

### Status Labels
| Label | When to Apply |
|-------|---------------|
| `status:idea` | Valid suggestion but: adds complexity, requires external dependencies, environment-specific, or rare use case. Keep open for discussion. |
| `status:wontfix` | Outside project scope OR belongs in Borg itself. Close with explanation. |
| `status:duplicate` | Already reported. Close and link to original. |
| `status:invalid` | Not actionable or not a Vorta issue. Close. |
| `status:needs details` | Missing reproduction steps, version info, or logs. |
| `status:not-reproducible` | Cannot reproduce with provided information. |
| `status:planning` | Large accepted feature needing design discussion. |
| `status:ready` | Fully specified, ready for implementation. |
| `status:stale` | No activity for 60+ days awaiting reporter response. |

### Platform Labels
- `os:linux`, `os:macos`, `os:windows`
- `package:flatpak`, `package:pip`, `package:native-linux`, `package:pyinstaller`

### Contributor Labels
- `help wanted` - Maintainers need community help (testing, implementation)
- `good first issue` - Simple change for new contributors

## Decision Tree for Feature Requests

```
Is this a Borg feature request?
├─ YES → status:wontfix, close with comment linking to BorgBackup issues
└─ NO → Continue...

Does it add significant complexity?
├─ YES → status:idea
└─ NO → Continue...

Does it require new external dependencies?
├─ YES → status:idea
└─ NO → Continue...

Does it only work in specific environments?
├─ YES → status:idea (+ help wanted if testing needed)
└─ NO → Continue...

Is it a rare/niche use case?
├─ YES → status:idea
└─ NO → Accept as type:feature or type:enhancement
```

## When to Close Issues

**Close immediately with explanation:**
- Fixed in current version (reference PR/commit)
- Duplicate (link to original issue)
- Belongs in Borg, not Vorta (`status:wontfix`)
- Outside project scope (`status:wontfix`)
- Invalid or spam (`status:invalid`)

**Close after waiting period:**
- No response to `status:needs details` for 30+ days → add `status:stale`, close after 14 more days
- Cannot reproduce and reporter unresponsive

**Keep open with `status:idea`:**
- Valid suggestion that doesn't fit current priorities
- Community may contribute implementation
- May become relevant in future

## Required Information for Bug Reports

Before marking as `status:needs details`, check for:
- Vorta version
- OS and version
- Borg version
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs (Help → Debug Log)

## Comment Templates

### For Borg Feature Requests
```
This feature would need to be implemented in BorgBackup itself rather than Vorta.
Vorta is a GUI wrapper and relies on Borg's capabilities.

Please consider opening a feature request at: https://github.com/borgbackup/borg/issues

Closing as `wontfix` since this is outside Vorta's scope.
```

### For Ideas (complexity/dependencies)
```
Thank you for this suggestion! This is an interesting idea, but it would add
significant complexity / require external dependencies / only affect specific
environments.

Marking as `idea` to keep the discussion open. Community contributions are welcome
if someone wants to implement this.
```

### For Already Fixed Issues
```
This has been addressed in version X.Y.Z / commit abc123 / PR #NNN.

[Brief explanation of how it was fixed]

Closing as resolved.
```

### For Needs Testing
```
We cannot reproduce/test this on [platform]. Adding `help wanted` - if you have
access to [specific environment], please help verify this issue.
```

## Label Combinations Quick Reference

| Scenario | Labels |
|----------|--------|
| Critical bug | `type:bug`, `priority:high` |
| Minor Linux-only bug | `type:bug`, `priority:low`, `os:linux` |
| Good starter task | `help wanted`, `good first issue` |
| Needs macOS testing | `help wanted`, `os:macos` |
| Complex feature request | `status:idea`, `type:feature` |
| Flatpak packaging issue | `type:bug`, `package:flatpak` |
| Borg feature request | `status:wontfix` (then close) |
| Accepted large feature | `status:planning`, `type:feature` |

## Periodic Maintenance

- **Monthly**: Review `status:needs details` issues, apply `status:stale` if no response
- **Quarterly**: Review `status:idea` issues for relevance, close if obsolete
- **Per release**: Close issues fixed in release, update milestones
