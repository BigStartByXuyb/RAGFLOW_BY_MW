# Thumbnail input isolation

## Goal

Avoid invoking thumbnail generation for file types that cannot produce a thumbnail, while keeping the current upload, storage, PDF repair, and parser-selection behavior unchanged.

## Design

Thumbnail generation uses two checks at the upload boundary:

1. A coarse `FileType` check permits only PDF and visual files as possible candidates.  This documents the business-level eligibility and excludes document and audio files before the helper is called.
2. A shared filename-based predicate permits only the exact formats currently supported by `thumbnail_img`: PDF and the supported image formats.  It excludes visual formats such as video that do not currently have thumbnail support.

`thumbnail_img` also uses the shared exact-format predicate as a defensive guard so direct callers receive `None` for unsupported names without duplicating the extension list.

## Behavior

- PDF and supported image files retain their existing thumbnail behavior.
- Documents, spreadsheets, text files, code files, audio files, videos, and unsupported extensions do not call `thumbnail_img` from the knowledge-base upload path.
- No parser, storage, document metadata, or PDF-repair behavior changes.

## Tests

Add focused tests for the exact-format predicate and the upload boundary, proving that an eligible file invokes thumbnail generation and an ineligible accepted file does not.
