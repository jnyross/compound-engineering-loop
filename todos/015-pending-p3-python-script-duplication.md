---
status: pending
priority: p3
issue_id: "015"
tags: [code-review, duplication, simplicity]
dependencies: []
---

# Deduplicate Gemini Image Generation Python Scripts

## Problem Statement

Three standalone scripts (generate_image.py, edit_image.py, compose_images.py) duplicate the exact same logic that gemini_images.py already encapsulates as a library class. Each script independently reads API keys, creates clients, builds configs, and iterates response parts — all of which the GeminiImageGenerator class already handles.

## Findings

- gemini_images.py (263 lines): complete library with generate(), edit(), compose() methods
- generate_image.py (133 lines): duplicates generate() logic
- edit_image.py (144 lines): duplicates edit() logic
- compose_images.py (157 lines): duplicates compose() logic
- ~300 lines of duplicated code
- Scripts also accept arbitrary file paths without path traversal protection
- Found by: performance-oracle, security-sentinel (Finding F4)

## Proposed Solutions

### Option 1: Replace with thin CLI wrappers (Recommended)

**Approach:** Rewrite the 3 scripts as thin argparse wrappers that import from gemini_images.py.

**Effort:** 1 hour
**Risk:** Low

## Acceptance Criteria

- [ ] No duplicated Gemini API logic across scripts
- [ ] All 3 scripts import from gemini_images.py
- [ ] Output path validation added to prevent path traversal
