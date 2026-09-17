# Thumbnail Input Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent files that cannot produce thumbnails from entering thumbnail generation during knowledge-base upload.

**Architecture:** Keep `FileType` as the coarse business boundary and introduce one shared filename predicate for the exact formats that `thumbnail_img` supports. The upload path applies both checks before calling the helper; the helper uses the exact predicate defensively for direct callers.

**Tech Stack:** Python 3.13+, pytest, existing `FileType` enum and file utility module.

## Global Constraints

- Keep upload, object-storage, PDF-repair, document metadata, and parser-selection behavior unchanged.
- The exact thumbnail format list has one source of truth.
- Preserve `thumbnail_img` as safe for direct callers: unsupported filenames return `None`.

---

### Task 1: Add the shared exact-format predicate

**Files:**
- Modify: `api/utils/file_utils.py:58-145`
- Test: `test/unit_test/api/utils/test_api_file_utils.py:20-126`

**Interfaces:**
- Produces: `is_thumbnailable_filename(filename: str) -> bool`, returning `True` only for PDF and the image filename extensions currently supported by `thumbnail_img`.
- Consumes: `_normalize_filename_for_type(filename)`.

- [ ] **Step 1: Write the failing test**

```python
from api.utils.file_utils import is_thumbnailable_filename

@pytest.mark.parametrize("filename", ["report.pdf", "photo.JPG", "icon.webp"])
def test_thumbnail_predicate_accepts_supported_formats(filename):
    assert is_thumbnailable_filename(filename) is True

@pytest.mark.parametrize("filename", ["sheet.xlsx", "recording.mp3", "movie.mp4", "unknown.bin"])
def test_thumbnail_predicate_rejects_unsupported_formats(filename):
    assert is_thumbnailable_filename(filename) is False
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest test/unit_test/api/utils/test_api_file_utils.py -k thumbnail_predicate -v`

Expected: FAIL because `is_thumbnailable_filename` is not importable.

- [ ] **Step 3: Write the minimal implementation**

```python
def is_thumbnailable_filename(filename: str) -> bool:
    normalized, ok = _normalize_filename_for_type(filename)
    if not ok:
        return False
    return bool(re.search(r"\.(pdf|jpg|jpeg|png|tif|gif|icon|ico|webp)$", normalized))
```

Make `thumbnail_img` return `None` immediately when this predicate returns `False`; retain its PDF and image generation branches.

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest test/unit_test/api/utils/test_api_file_utils.py -k "thumbnail_predicate or ThumbnailImg" -v`

Expected: PASS.

### Task 2: Apply coarse and exact isolation at upload

**Files:**
- Modify: `api/db/services/file_service.py:581-585`
- Test: `test/unit_test/api/utils/test_api_file_utils.py:20-126`

**Interfaces:**
- Consumes: `is_thumbnailable_filename(filename: str) -> bool`, `filetype`, and `FileType.PDF.value` / `FileType.VISUAL.value`.
- Produces: `thumbnail_location` remains empty unless a PDF or supported image produces thumbnail bytes.

- [ ] **Step 1: Write the failing test**

```python
def test_thumbnail_candidate_requires_coarse_and_exact_type():
    assert is_thumbnail_candidate(FileType.PDF.value, "report.pdf") is True
    assert is_thumbnail_candidate(FileType.VISUAL.value, "photo.png") is True
    assert is_thumbnail_candidate(FileType.VISUAL.value, "clip.mp4") is False
    assert is_thumbnail_candidate(FileType.DOC.value, "sheet.xlsx") is False
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest test/unit_test/api/utils/test_api_file_utils.py -k thumbnail_candidate -v`

Expected: FAIL because `is_thumbnail_candidate` is not importable.

- [ ] **Step 3: Write the minimal implementation**

Define a pure helper in `api.utils.file_utils`:

```python
def is_thumbnail_candidate(filetype: str, filename: str) -> bool:
    return filetype in (FileType.PDF.value, FileType.VISUAL.value) and is_thumbnailable_filename(filename)
```

Use it at the upload site:

```python
# Coarse types exclude documents and audio; visual also includes video,
# so the exact filename check excludes formats without thumbnail support.
img = thumbnail_img(filename, blob) if is_thumbnail_candidate(filetype, filename) else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest test/unit_test/api/utils/test_api_file_utils.py -v`

Expected: PASS.

### Task 3: Verify the focused change

**Files:**
- Modify: none
- Test: `test/unit_test/api/utils/test_api_file_utils.py`

**Interfaces:**
- Consumes: the predicates and upload boundary from Tasks 1 and 2.
- Produces: verification that supported images and PDFs retain eligibility while other accepted formats are excluded.

- [ ] **Step 1: Run lint on changed Python modules**

Run: `uv run ruff check api/utils/file_utils.py api/db/services/file_service.py test/unit_test/api/utils/test_api_file_utils.py`

Expected: PASS.

- [ ] **Step 2: Review the diff**

Run: `git diff --check && git diff -- api/utils/file_utils.py api/db/services/file_service.py test/unit_test/api/utils/test_api_file_utils.py`

Expected: no whitespace errors; one shared exact-format predicate and one documented coarse-plus-exact boundary check.
