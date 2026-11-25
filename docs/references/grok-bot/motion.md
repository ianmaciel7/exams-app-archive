# Motion contracts — original Exam App adaptation

Status: proposed and implemented in the standalone lab, not measured Grok Bot timings. Keep identity (shape and color) separate from lifecycle (pose and expression). Preserve a stable hit target. Animation must not imply backend success; drive it from real events.

| State | Meaning | Original motion | Proposed loop / transition |
|---|---|---|---|
| idle | available | subtle vertical drift | 2400 ms |
| thinking | preparing | slow eye glance, slight tilt | 1500 ms |
| working | actively executing | orbit and compact bounce | 1200 ms |
| waiting | awaiting external dependency | three pulsing dots | 1400 ms |
| blocked | needs intervention | small finite shake; explicit text | 320 ms |
| done | task succeeded | finite squash-and-stretch, then still | 440 ms |

Use a 180 ms ease-out for discrete visual changes; durations are local design choices. Distinguish dwell (hover delay) from transition. Never present simulated progress as actual completion. For asynchronous tasks, show a textual action and timestamp, and expose details by focus/hover or explicit button. On cancel or retry clear stale animations. Errors remain legible without color. Pause on hidden tabs; respect prefers-reduced-motion and allow manual pause.

## Implementation recipe
- CSS/SVG: render body, eyes and orbit in separate layers; animate transform/opacity rather than layout. State is a single data-state value. Use stable viewBox and fixed avatar dimensions.
- React: state enum plus event reducer; map status from task service, not timers. Render the original SVG component and pass state as a prop. Use aria-live="polite" on a separate status label.
- Motion/Rive: if the project needs continuous morphs, use compatible paths or radial profiles; preserve continuity when interrupted. Separate looping state animations from one-shot reactions, cancel obsolete transitions, and return to the current authoritative state. Choose a license-compatible original rig. No third-party code is vendored.
- QA: keyboard and touch state controls; reduced motion (no loops); blocked/done remain readable without motion; check 16/24/32/64 px and dark/light; test fast state switching, tab visibility, cancellation and long-running operations.

## Candidate uses
Importing exam PDFs, indexing question banks, synchronization, search, generating study reports and background tasks. Prefer a compact status icon plus details over an always-moving decoration. Use a separate badge or status line for meaningful outcomes.
