# Bridge Demonstration Tool

A desktop application for administrators to organize bridge deals and scenarios, configure play instructions, and demonstrate card play. The application is built with Python, PyQt6, and SQLite.

## Current capabilities

- Register, log in, and log out as an administrator. Administrator passwords are stored as hashes.
- Set an optional expiration date for your own signed-in administrator account. Expired accounts are denied sign-in and active sessions are signed out.
- Organize assets in an administrator-specific tree of folders, cases, boards, and scenarios. The tree uses distinct icons and colors for each asset type, and supports search, context-menu actions, and keyboard shortcuts. Use **Expand all**/**Collapse all** and Ctrl/Cmd + +/−/0 to manage the current tree's folders and text size.
- Move folders, cases, boards, and scenarios between valid parents. The move workflow previews the source and destination and requires confirmation before changing the asset tree; descendants move with their parent.
- Add assets with wide, readable name fields and selection dialogs.
- Create and edit boards using either a graphical card picker or PBN hand entry. PBN entry shows a live card-hand preview below each hand. The visual picker shows seat colors and can randomly deal the remaining cards when each seat has either 0 or 13 cards. Deal validation checks that all 52 cards are distinct and present.
- Configure a scenario's auction, contract, declarer, labels, or target-card sequence; its doubling status is derived from the auction route.
- Display and play a scenario on the bridge table. The table supports seat-perspective rotation, analysis/hidden views, normal/demonstration modes, label/target rules, and a double-dummy result matrix.
- Show the current trick's played cards, keeping the completed trick visible until play starts on the next trick. Up to 64 recent game states are retained for undo during the session.
- Assign a color and sequence to each card label. Sequence numbers appear in the card's upper-right corner, and inserting or moving a label reorders only labels of that color. Selecting a different color updates the suggested sequence to that color's current count plus one.
- Use Last move or Reset to review analysis play. Reset restores the oldest state still retained in the undo history.
- Open Instructions for an in-app guide. The administrator-only Monitor shows aggregate resource counts for all administrators, including the current account, and local runtime/error status, without exposing saved asset contents.
- Use the top-level **Preference**, **Administrator**, **Tool**, **Test**, and **Explorer** menus. Administrators register students and assign tests from Test → Student management; students use Administrator → Student login. Test → Examine test results displays saved results for the signed-in administrator. Explorer opens `README.md`, `requirements.txt`, and `Label.md`; in Chinese, the README entry opens `README_zh.md` and `Label.md` is displayed as `标签.md`.
- Export selected administrator workspace content as a single encrypted `.bdtpack` file and import it on another computer. Each import creates a separate destination administrator account; importing does not require an active administrator. The package uses scrypt key derivation and AES-256-GCM authenticated encryption.
- Build tests from multiple problems. Each problem can include several candidate scenarios from one case; one candidate is selected for each problem every time the test runs. Each scenario has its own contract/stasis scoring rule, even when contracts are shared.
- Run tests in Lockdown mode with hidden hands. Administrators assign tests to registered students. Student login automatically enters Lockdown and lists available tests; each assignment can be completed only once. Results are linked to the student account.
- Generate an administrator-wide test report with score statistics, a contestant-by-problem matrix, scenario difficulty statistics, and the top three contestants; export it as a PDF in English or Chinese.
- Validate bridge calls, legal card play, trick winners, and duplicate scoring in the core modules.
- Use the optional `dds3` Python module through a DDS wrapper and robot agent when a compatible installation is available.

## Scenario workflow

The central table represents a **scenario**, not a board:

1. Selecting a board in the asset tree only selects it; it does not load its cards into the table.
2. Adding an asset while a board is selected creates a new, empty scenario, selects it, and loads it into the table.
3. A new scenario starts with no auction calls, labels, or target cards. Configure its auction and play instructions with the table controls before starting a demonstration.
4. Clicking a scenario in the tree only selects it. Double-clicking a scenario saves the currently loaded scenario and loads the selected one.
5. The active scenario is also saved before logout. Its auction, contract, declarer, doubling status, labels, target mode, and target-card sequence are persisted.

For a playable scenario, the auction must be complete and legal and the contract must be valid. Label mode does not require labels: when none are configured, robots use DDS recommendations only. Labels are optional overrides in label mode. Target mode requires a target-card sequence. A passed-out auction does not start a card-play demonstration.

Use the single **Start/End** button to begin or stop a demonstration. For a target sequence, robot-controlled seats follow the recorded cards automatically; label-rule demonstrations use the robot evaluator. Labels are hidden during demonstrations. Bidding remains available during demonstrations and tests; test playback shows the read-only bidding route without the bid matrix, and its **Information** action remains available. Next move is enabled during recorded-sequence demonstrations and disabled during label demonstrations. The Record target control remains disabled during demonstrations. Doubling status is derived from the auction route. When all 13 tricks are played, a result dialog shows the final contract, doubling, and outcome (for example, `4HXX=`). Robot card plays slide from the player's hand to the trick area, with a configurable pause between automated plays. **Preference → Robot** controls the playback delay and whether robots follow a recorded sequence or labels. **Preference → Sound** contains a card-sound toggle and volume slider. **Explorer → Label.md** displays each phase's six colors in the same effective check order described below; each cell shows its color and whether it overrides or follows DDS. Administrator preferences are saved automatically and restored at sign-in. **Preference → Styles** controls card width, card suit-symbol size, application font size (10–24 px), font color, and background color; it also lets administrators change the asset-tree width, upper-panel height, central-panel height, and the background color of each panel. Test playback fixes card width to 43 px, robot delay to 1200 ms, and sound volume to 50%; move navigation and the human-seat control are hidden. Played cards sit at the four compass points around the center, aligned with its horizontal and vertical axes. During Analysis view, legal cards in the hand to play show the DDS tricks available to that side in compact badges near the bottom-right of each card. Use **Preference → View → Rotate view** to change table orientation. The **DDS: Tricks** control switches between trick counts and the declaring side's margin relative to the contract target on the cards. In the matrix, **DDS: Contract ±** displays `max(0, tricks - 6)` for each seat and strain. The DDS result matrix sits at the upper-right of the table panel; use **Preference → DDS → Show DDS matrix** to toggle it. The matrix remains blank when the solver is unavailable.

The central **Bidding** dialog centers both the auction route and bid matrix, with columns ordered NT, spades, hearts, diamonds, clubs and levels 1 through 7 from top to bottom. NT calls are gray, spades are dark blue, and the other strains retain their distinct colors in both the matrix and auction route. DDS result numbers are enlarged at the bottom of cards and remain independent of the suit-symbol size preference.

Use **Preference → Language** to choose the interface language in a dialog. DDS labels and results remain in their standard notation.

**Preference → View → Analysis/Hidden** controls information visibility and remains changeable during a demonstration. Robots are inactive in Normal mode, and DDS results are shown only in Normal + Analysis. During a demonstration, the human seat, table rotation, and DDS display mode are locked. In a Hidden-view demonstration, a human on the declaring side sees declarer and dummy; a human on defense sees their own hand, and dummy is revealed after their first card in the opening trick. Student test playback hides rule labels while keeping them available to the robot. The other hands' cards are invisible, not shown as card backs. In Analysis view, right-click a card to add or change its color label. To record a target, play all 52 cards in Analysis; the **Record target** button remains visible but disabled until the deal is complete and a scenario is loaded. Clicking it saves the sequence with the scenario and leaves the completed deal visible. **Preference → Robot** selects whether the robot follows the saved sequence or labels.

In label-rule demonstrations, the robot plays seats outside the human-controlled hand(s). A human on the declaring side controls both declarer and dummy; a human on defense controls only their own seat. In Analysis + Normal + Label mode, right-click (or Control-click on macOS) a card to set its label color and sequence. The sequence is unique and contiguous within each color; other colors are not renumbered.

Robot labels are restricted to the current DDS-best group (the legal cards with the highest DDS trick result), except for Red while leading and Blue while discarding; those two colors can deliberately select a non-best card. Leading checks Red ascending first, then the DDS-best group in this order: Orange ascending, uncolored, Purple descending, Blue descending, Green descending, Yellow descending. Discarding checks Blue ascending first, then the DDS-best group in this order: Purple ascending, uncolored, Orange descending, Red descending, Green descending, Yellow descending. Following suit checks only the DDS-best group, in this order: Green ascending, Blue ascending, Purple ascending, uncolored, Orange descending, Red descending, Yellow descending. **Explorer → Label.md** displays the six colored jobs for each phase in effective check order: Red, Orange, Purple, Blue, Green, Yellow when leading; Green, Blue, Purple, Orange, Red, Yellow when following suit; and Blue, Purple, Orange, Red, Green, Yellow when discarding. The uncolored fallback is described here but has no color cell. Each matrix cell shows the color and whether it overrides or follows DDS. If DDS provides no best-card group, only configured overrides can select a card.

## Requirements

- Python 3.10 or newer
- Dependencies in `requirements.txt` (PyQt6 and cryptography)
- Optional: the `dds3` native extension for DDS-backed analysis and robot moves. The application still runs without it, but DDS-dependent features are unavailable.

The DDS source is included as a Git submodule. Clone the repository with the submodule initialized:

```bash
git clone --recurse-submodules https://github.com/Jelly0200/Bridge-Demonstration-Tool.git
cd Bridge-Demonstration-Tool
```

If you already cloned the repository without its submodule, run `git submodule update --init --recursive` from the project root. A GitHub ZIP download does not initialize submodules.

## Install and run

For a basic install without DDS, run from the project root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.main
```

### Enable DDS (optional)

`dds3` is a native extension and is not installed by `requirements.txt`. For this repository, the DDS build uses Python 3.14, so use a Python 3.14 environment to install and run the application with DDS enabled. A native extension built for one Python version or operating system may not work with another.

First install Bazelisk and a C++ compiler. On macOS, you can install Bazelisk with `brew install bazelisk`; see [`dds/docs/python_interface.md`](dds/docs/python_interface.md) for platform-specific build prerequisites. Windows is not officially supported by the DDS project.

If DDS is your goal, you can skip the basic `.venv` setup above. From the project root, create and activate a Python 3.14 environment, install the application dependencies, build the DDS wheel, and install it into that same environment:

```bash
python3.14 -m venv .venv314
source .venv314/bin/activate
python -m pip install -r requirements.txt

cd dds
bazelisk build -c opt //python:dds3_wheel_dist
python -m pip install bazel-bin/python/dist/*.whl
cd ..

python -c "import dds3; print('DDS is ready')"
python -m src.main
```

The import check should print `DDS is ready` without an error. If it fails, check that the wheel was built and installed successfully and that the application is being run with the same Python 3.14 environment. If you already have an active Python 3.14 environment, use it instead of creating `.venv314`.

On Windows, activate the environment with `.venv\Scripts\activate` instead.

The database manager initializes the SQLite schema from `schema.sql` and uses `bridge_tool.db` in the current working directory by default. Launch the application from the project root to keep the database there.

## Tests

Run the full unittest suite from the project root:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
```

`QT_QPA_PLATFORM=offscreen` allows Qt UI tests to run without opening windows. On Windows, set `QT_QPA_PLATFORM=offscreen` in the shell before running the command.

The suite covers database/repository behavior, administrator registration, board and rule editors, bridge logic, robot label selection, table behavior, and DDS wrapper behavior. DDS wrapper tests use mocks and do not require the native solver.

## Data model

`schema.sql` defines the SQLite schema:

| Table | Purpose |
| --- | --- |
| `Administration` | Administrator accounts and optional expiration dates |
| `Folder` | Per-administrator folder hierarchy |
| `CaseStudy` | Groups boards within a folder |
| `BoardConfiguration` | Dealer and vulnerability |
| `Board` | Four PBN hands and the board's case/configuration |
| `Scenario` | Auction, contract, declarer, doubling status, target mode, target sequence, and optional information text |
| `Label` | Ordered card labels attached to a scenario |
| `Test`, `Rule`, `Test_Scenario` | Test definitions, scoring rules, and scenario candidates attached to problems |
| `Student` | Student account name and salted password hash |
| `Student_Test` | Student test assignments and one-time completion status |
| `Test_Result` | Submitted score and scenario results linked to a test and student |

The database schema includes student accounts and test-related tables. Student passwords are stored as salted PBKDF2 hashes. Test results reference both the test and the student; legacy results without a student link remain readable after migration.

## Project layout

```text
assets/                         UI assets and styles
config/                         Application settings and constants
schema.sql                      SQLite schema
src/
├── core/                       Bridge logic, deal parsing, scoring, DDS wrapper, report helper
├── database/                   SQLite manager, repository, and data models
├── robot/                      Robot move selection and label evaluation
├── security/                   Password hashing and verification
└── ui/
    ├── dialogs/                 Login, registration, board, scenario, rule, and report dialogs
    ├── views/                   Asset tree, bridge table, analysis, and test construction
    └── widgets/                 Hand display, bidding box, and DDS panel
tests/                           unittest suite
requirements.txt                 Python dependencies
```

## Implementation boundaries

- Student registration and test assignment are performed by a signed-in administrator from Test → Student management. Students enter the numeric ID shown at registration and their password at Administrator → Student login; only assigned, incomplete tests are available, and a completed assignment cannot be run again.
- Administrator → Export administrator data lets you select folders, cases, boards, and tests, then packages them for a separate administrator account. Required parent assets and test dependencies are included automatically; student accounts, assignments, and results are excluded.
- Administrator → Set my account expiration changes only the signed-in administrator's own optional expiration date. Once expired, the account cannot sign in and any active session is signed out.
- Each test run selects one candidate scenario per problem; candidate scenarios remain attached to the problem for subsequent runs.
- The main integrated workflow includes administrator asset management, scenario-based table demonstration, test construction, and Lockdown test runs.
- `dds3` is optional and is not installed by the requirements file. When available, the main table displays its double-dummy trick-count matrix; a broader DDS analysis dashboard is not integrated.
- Test → Generate test report summarizes persisted results for the signed-in administrator and can export the report to PDF.
- The robot agent combines available DDS recommendations with label rules and a legal-card fallback. DDS-equivalent lower-ranked cards are included when checking best-play labels. It is not a general-purpose bridge-playing engine.
