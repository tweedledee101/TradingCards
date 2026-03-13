# Documentation Update Rule

## ALWAYS Update Existing Files - NEVER Create New Ones

When updating project status or documentation:

1. **Find the existing file first** - Use fileSearch to locate STATUS.md, PROJECT-STATUS.md, etc.
2. **Update the existing file** - Use fsReplace to modify content
3. **NEVER create dated files** - No STATUS-FEB16.md, PROJECT-STATUS-2026-02-16.md, etc.
4. **NEVER create duplicate files** - No NEW-STATUS.md, UPDATED-STATUS.md, etc.

## Standard Documentation Files

- `STATUS.md` - Current project status (update this daily)
- `README.md` - Project overview (update when features change)
- `PHASE1-STRATEGY.md` - Phase 1 approach (update when strategy changes)

## When to Create New Files

ONLY create new files for:
- New features that need their own guide
- New architectural decisions
- New setup instructions for new tools

## Example: Updating Status

**WRONG:**
```
Creating PROJECT-STATUS-FEB16.md...
```

**CORRECT:**
```
Updating STATUS.md with latest progress...
```
