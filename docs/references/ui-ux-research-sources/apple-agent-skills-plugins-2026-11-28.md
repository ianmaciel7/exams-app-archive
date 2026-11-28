# Apple agent skills and plugin ecosystem — 2026-11-28

External public research, original synthesis. Consulted 2026-11-28. No installation, native export, execution, or full source-code audit performed. Companion to [HIG craft](apple-hig-design-craft-2026-11-27.md); not a replacement.

## Apple-authored resources
- [Xcode coding intelligence](https://developer.apple.com/documentation/xcode/coding-intelligence), [WWDC26 state of the union](https://developer.apple.com/videos/play/wwdc2026/102/), [release notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes): official Apple specialists, skills, MCP and ACP plugins; Figma and GitHub partner integrations.
- [WWDC SwiftUI](https://developer.apple.com/videos/play/wwdc2026/269/) documents xcrun agent skills export. [SwiftLee June 2026](https://www.avanderlee.com/ai-development/using-xcode-27s-agent-skills-in-claude-codex-and-cursor/) documents early seven-skill export. [Independent newer mirror](https://github.com/mariusfanu/xcode-skills) reports 15 Apple-authored skills exported from Xcode 27.3 beta 2: swiftui-specialist, swiftui-whats-new-27, building-document-based-swiftui-applications, app-intents-specialist, app-intents-whats-new-27, siri-app-integration, siri-evaluations, foundation-models-specialist, app-resizability, macos-touch-gestures, audit-xcode-security-settings, adopt-c-bounds-safety, modernize-tests, device-interaction, xctrace. Earlier names test-modernizer, c-bounds-safety and uikit-app-modernization are historical. Prefer direct Xcode export; mirror is not Apple-published, inventory not independently exported here. Device interaction and profiling depend on tool access. [Earlier mirror](https://github.com/superagents-lab/xcode27-skills) explicitly does not grant rights to underlying Apple content.
- [Apple Foundation Models Utilities](https://github.com/apple/foundation-models-utilities) contains [foundation-models-language-model-protocol](https://github.com/apple/foundation-models-utilities/blob/main/skills/foundation-models-language-model-protocol/SKILL.md); complete directory inventory not verified.
- [Apple Core AI Models](https://github.com/apple/coreai-models) officially publishes coreai-skills plugin for Claude Code, Codex and Gemini CLI: working-with-coreai, model-authoring, model-compression-exploration, auditing-helper-reuse. BSD-3-Clause repository; native runtime requires Apple toolchain.

## Independent UI/UX references
- [dickwu/apple-design-skill](https://github.com/dickwu/apple-design-skill): cross-platform review.
- [efey1ldirim/apple-skill](https://github.com/efey1ldirim/apple-skill): HIG adaptation to web design and component recipes.
- [justinwetch/HIGAgentSkills](https://github.com/justinwetch/HIGAgentSkills): HIG discovery.
- [davidcafor/apple-hig-skill](https://github.com/davidcafor/apple-hig-skill), [ykswang/apple-hig-skill](https://github.com/ykswang/apple-hig-skill), [al1h3n/apple-skills](https://github.com/al1h3n/apple-skills): native design, updating guidance, materials.
- [Zinoo00/apple-human-interface-guideline-skills](https://github.com/Zinoo00/apple-human-interface-guideline-skills), [ebuntario/apple-hig](https://github.com/ebuntario/apple-hig), [Neel-Sh/Apple-HIG](https://github.com/Neel-Sh/Apple-HIG): accessible and native interface patterns.
- [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills): apple-hig-expert plugin.

## Other agent plugins and catalogs
- [OpenAI Build iOS Apps](https://github.com/openai/plugins/tree/main/plugins/build-ios-apps), [Build macOS Apps](https://github.com/openai/plugins/tree/main/plugins/build-macos-apps): native UI patterns, performance and testing; desktop window management and inspectors are useful conceptual references for web workspaces.
- [Prisma Labs Apple Skills](https://github.com/Prisma-Labs-Dev/apple-skills), [Swift Skills](https://github.com/swift-library/skills), [Apple Engineering Skills](https://github.com/coryparrry/apple-engineering-skills), [iOS Skills Collection](https://github.com/JordanCoin/ios-skills-collection), [Swift Agent Skills catalog](https://github.com/twostraws/Swift-Agent-Skills), [SwiftSkills](https://swiftskills.dev/).

## Transfer rule
For web UI research, prioritize primary HIG sources and portable layout, hierarchy, navigation, interaction and accessibility principles; evaluate actual browser states independently. Do not apply native API, colors, fonts or material rules mechanically to web apps. No third-party scripts executed; license and provenance must be verified before redistribution. No application or plugin changes made.
