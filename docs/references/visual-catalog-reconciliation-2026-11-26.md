# Visual catalog reconciliation

The legacy Excalidraw, shadcn and Storybook manifests contain fourteen asset occurrences already represented in the canonical visual-evidence library. Do not import these as new unique visual discoveries. The reconciliation verifies actual legacy/canonical bytes, Git blob SHA-1, byte counts, pinned upstream source repo/commit/path/URL, and license text. Existing canonical validation checks derivative bytes and timestamp bounds. Tests cover removing a canonical reference. This does not establish screenshot semantics, verified UI state, playback or live upstream availability.

Run `python -m pytest tests/test_visual_reference_index.py -q`. Results must be measured by CI; no visual content inspection is implied.
