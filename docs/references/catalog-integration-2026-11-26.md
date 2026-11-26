# Public catalog integration — 2026-11-26

Nine existing public catalogs are now explicitly projected into the same public research index, preserving source namespace, record ID, source URL references, original-record SHA-256 and catalog SHA-256. They include async UX, behavioral UX, component behavior, microinteractions, agent-ready design systems, AI-native families, ChatGPT Space views, AI product artifacts and design activities. Derived records are cataloged syntheses, not newly researched unique concepts or verified product behavior. The source documents are not modified. Activities without per-record source IDs remain explicitly unlinked; do not infer citation authority.

The full public corpus, including this expansion, goes through the existing retrieval regression gate. If rankings regress, investigate actual returned evidence and incomplete labels; never lower thresholds or add expected-answer metadata to the retriever merely to obtain green CI.

Coverage distinguishes domains with linked knowledge records from domains with only linked source records. Source-only architecture/history links do not constitute semantic extraction. Other source-only or visual catalogs not explicitly approved here remain out of scope. No private archive path is scanned.

First expanded run 45828333992: recall .80, precision .40 vs .48 floor, MRR .75, one negative abstained, p95 4.428s. Gate correctly failed. Source URL deduplication and consistent representative provenance are follow-up changes; preserve failure artifacts and public-only ranking IDs for review. No gate threshold changed.
