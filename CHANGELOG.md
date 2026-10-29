# Changelog

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
