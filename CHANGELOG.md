# Changelog

## 2026-11-09

- Refine lockdown-test briefings to show the problem sequence, bidding route, and instructions without revealing scenario names.
- Match the table's top strip to the central-panel background; enlarge test cards and center the larger play-information label above the play area.
- Lower the side-seat labels slightly while keeping them above their hands.

## 2026-11-07

- Move language selection from **Tool** to **Preference** and add a direct **Explorer → Label.md** action, localized as **标签.md** in Chinese.
- Show label definitions in a phase-by-color matrix ordered to match each phase's effective color-check sequence; identify each color as **Override DDS** or **Follow DDS**, with Chinese translations.

## 2026-10-28

- In Hidden-view demonstrations, keep dummy concealed from a human defender until they play their first card in the opening trick.
- Fix auction undo so the removed call is cleared from the visible auction.
- Reuse card widgets during hand redraws to reduce rendering overhead and slowdown during long demonstrations.
- Add a short pause between robot plays and a **Tool → Robot card sound** toggle.
- Commit active score-matrix edits when saving a problem, and add administrator controls to change student passwords or delete student accounts with their assignments and result history.
- Give each scenario its own test scoring rule, keep the asset tree expandable during test construction, and center the played-card group.
- Reduce long-session UI growth by reusing played-card widgets and disposing of closed modal dialogs; slow demonstration and test robot play.

## 2026-10-29

- Export selected administrator content to a separate account, allow importing while signed out, and exclude student accounts, assignments, and results.
- Add self-service administrator account expiration; expired accounts cannot sign in and active sessions are signed out.
- Arrange played cards at the four compass points around the trick center, preserve suit colors when reusing card widgets, and show DDS results in compact corner badges.
- Increase DDS badge height so computed card values are fully visible.
- Hide rule labels during student test playback while retaining them for robot decisions.
- Shorten the demonstration control to **Demonstrate**/**Stop** and place **Record target** in the table's top bar.
- Add independent asset-tree expand/collapse controls and Ctrl/Cmd keyboard shortcuts to resize or reset tree text; provide enough room for the **Duplicate** button label.
- Score each test scenario independently, even when scenarios share a contract.

## 2026-11-04

- Consolidate bidding, description, view, DDS, rule, labeling, and target-recording options under **Settings**; remove the mode, demonstration, view, DDS, rule, rotation, and human-seat controls from the table panel.
- Simplify the table panel to **Settings** and **Record target** at the top, move navigation controls to the lower left, and make the DDS matrix a settings-controlled lower-right panel that does not shift the cards.
- Center and soften the transparency of the play information bar, remove suit decorations from empty side-hand rows, and enlarge compass-seat labels.

## 2026-11-05

- Replace the central Settings control with **Bidding** for auction and scenario information; move DDS, styles, robot, sound, and view options into top-level **Preference** menus, and move label tools under **Explorer → Labels**.
- Center and compact the bidding route and matrix, order bids as NT, S, H, D, C and levels 1–7, and color calls by strain. Derive doubling status from the auction instead of accepting it as a separate input.
- Add persistent per-administrator application font size and color preferences.
- Apply application font size across the interface except card faces, and keep the Record target button clear of the DDS matrix.
- Keep Bidding available during demonstrations and tests; disable **Next move** for label-rule demonstrations while allowing it for recorded-sequence demonstrations.
- Apply font-size preferences directly to the main interface and add persistent background-color, panel-color, and panel-size preferences.
- Show only the read-only bidding route in test previews while keeping scenario information available; use 43 px cards, enlarge the play-information controls, and hide move navigation and human-seat controls.
- List robot label jobs in their actual per-phase color-priority order, with sequence selection explained.
- Show label definitions as a 3×6 phase/color matrix in Explorer and remove the color-job editor from the Labels menu.
- Omit the redundant **NONE** risk status from play information.
- Keep **Record target** visible but disabled until a scenario's analysis play is complete, and position it independently of ancestor clipping.
- Keep the completed deal on the table after recording its 52-card target sequence.
- Add a persistent **Preference → Styles** slider for card suit-symbol size (10–35 px), independently adjustable from the DDS badge size.
- Migrate existing administrator preferences to the updated suit-symbol size constraint without losing saved preference values.
- Use gray for NT and dark blue for spades in the bidding matrix and auction route; enlarge DDS result numbers on cards.
