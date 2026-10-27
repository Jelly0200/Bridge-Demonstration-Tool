from PyQt6.QtWidgets import QDialog, QTextBrowser, QVBoxLayout


class InstructionsDialog(QDialog):
    """Present the localized application guide."""

    ENGLISH_INSTRUCTIONS = """\
# Manage your bridge assets

Sign in to manage your own folders, cases, boards, and scenarios. Asset data is
stored locally in SQLite.

## Asset Tree

- Select a folder and press **Add** to create a child folder or a case.

- Select a case and press **Add** to create a board using PBN input or the
  visual card picker. A board also stores vulnerability and dealer information.
  PBN hands have live previews; the card picker identifies seats by color and
  can randomize remaining cards when every seat has either 0 or 13 cards.

- Select a board and press **Add** to create a scenario. A scenario contains an
  auction, a human seat, robot rules (Label or Target), a view (Analysis or
  Hidden), and a mode (Normal or Demonstration).

- Select any asset and press **Move** to choose a valid new parent. Review the
  source and destination preview before confirming; folders, cases, and boards
  carry their descendants with them.

- Select a folder, case, or scenario and press **Edit** to rename it.

- Select a board and press **Edit** to rename it or reconstruct its hands,
  vulnerability, and dealer.

- Select any folder, case, board, or scenario and press **Duplicate** to copy it
  with its descendants, including scenario information and labels.

- Use the **Administrator**, **Tool**, **Test**, and **Explorer** menus for
  account, application, test, and project-document actions. Use **Explorer** to
  read `README.md` and `requirements.txt`; asset actions remain in the asset tree.
- **Tool > Language** opens a choice dialog before changing the interface
  language. **Tool > Keyboard shortcuts** opens a reference for the available
  keyboard and context-menu shortcuts.
- **Administrator > Export administrator data** saves this administrator's
  workspace as one encrypted `.bdtpack` file. Choose and confirm a separate
  passphrase of at least 12 characters; keep it safe because it cannot be
  recovered. **Administrator > Import administrator data** verifies the
  passphrase and adds the package contents to the currently signed-in account
  without overwriting existing assets. Student accounts linked to the exported
  tests and their assignments and results are included. The administrator's
  login credentials are not exported.
- **Test > Student management** lets an administrator register student
  accounts and assign or remove tests. **Administrator > Student login** starts
  a student's assigned-test session. **Test > Examine test results** displays
  individual results; **Test > Generate test report** summarizes scores and
  scenario difficulty, ranks the top three contestants, and offers PDF export.
- The test-construction screen has a red close button at its upper-right corner.

## Robot rules in Normal mode

Use Label rules to annotate cards, or Target rules to record a target sequence.
Right-click a card (Control-click on macOS) to edit its label. Sequence numbers
are counted independently for each color. In the orders below, **uncolored**
means a card without a label; **DDS-best group** means the legal cards with the
highest DDS result for the current position.

**Core Principle**: Only **Red** (for leading) and **Blue** (for discarding) can force the robot to play a card outside the DDS-best group (i.e., non-optimal plays to test human players). All other colors strictly select from within the **DDS-best group**.

### Leading

1. Red, ascending sequence (can select cards outside the DDS-best group).
2. Within the DDS-best group, select the first available card in this priority order:
   - Orange (ascending sequence)
   - Uncolored
   - Purple (descending sequence)
   - Blue (descending sequence)
   - Green (descending sequence)
   - Yellow (descending sequence)

### Discarding

1. Blue, ascending sequence (can select cards outside the DDS-best group).
2. Within the DDS-best group, select the first available card in this priority order:
   - Purple (ascending sequence)
   - Uncolored
   - Orange (descending sequence)
   - Red (descending sequence)
   - Green (descending sequence)
   - Yellow (descending sequence)

### Following suit

Within the DDS-best group, select the first available card in this priority order:
1. Green (ascending sequence)
2. Blue (ascending sequence)
3. Purple (ascending sequence)
4. Uncolored
5. Orange (descending sequence)
6. Red (descending sequence)
7. Yellow (descending sequence)

### General advice

- Use Red (when leading) or Blue (when discarding) to force non-optimal lines for testing or demonstration scenarios.
- Use Purple as the primary preference tool for DDS-optimal discards.
- Use Green during follow-suit to prioritize a specific equivalent DDS-best card that poses the maximum psychological test to the human player.
- Use Yellow on key honors or sensitive cards so they are ranked last among DDS-best options, preventing the robot from giving away information unnecessarily.

## Demonstrations and scenarios

In Demonstration mode, robots play the non-human seats using either the recorded
Target sequence or Label rules. Choose Analysis or Hidden view to switch between
a double-dummy perspective and a real-game perspective. In a Hidden-view
demonstration, a human on the declaring side sees declarer and dummy face up. A
human on defense sees their own hand and dummy face up; their partner's hand and
declarer's hand are invisible.

A scenario's optional plain-text **Information** can be edited in **Settings**.
It is shown to students during a test and remains linked to the scenario through
the test-scenario relationship.

## Lockdown and running tests

Choose **Administrator > Administration Lockdown** and confirm the administrator
password. The asset pane becomes a restricted command terminal. Type **Help** to
see available commands and **Exit** to leave lockdown and return to the
unsigned application state.

- `Run (BoardName)ScenarioName` plays that scenario's recorded target sequence
  using Target rules and Hidden view.
- `Run TestName` starts an available test. In administrator lockdown, the
  student is prompted for an ID and password; the test must be assigned to that
  student. A student can instead choose **Administrator > Student login**, which enters
  Lockdown automatically and lists their available tests. Students can only run
  assigned tests and cannot run individual scenarios. Each assigned test is
  available once; completing it saves the result and removes it from the
  student's available-test list.
- A test run plays one randomly selected candidate scenario per problem using
  Label rules and Hidden view. Student accounts are registered and tests
  assigned by an administrator. The result links to the student account and
  the password is stored as a hash.

After each test scenario, the result and score are shown with a button to
continue. The final test score and student ID are saved locally. **Test > Run
Test** also enters lockdown and lets the administrator select a saved test.
Use **Test > Examine test results** to review submitted results.

## Monitor

The Monitor shows aggregate asset counts for all administrators, including
your own account, together with local runtime history and recent application
errors. It does not expose administrators' saved asset contents.

## Tests

Sign in as an administrator and choose **Test construction** to create and
manage tests. Each test supports a title, multiple problems, and a scoring
matrix:

- Each problem uses one administrator-selected case and one or more candidate
  scenarios from that case. A test run randomly selects one candidate per
  problem, so it does not run every candidate scenario.
- Contract rows are generated from the distinct final contracts in the selected
  scenarios. Administrators edit acceptable result stasis (such as **=**, **-1**,
  **-2**, **+1**, or **+2**) and enter a score for each contract/stasis cell.
- The test-construction screen saves tests locally and lets administrators
  reopen, edit, and delete them.
- Settings for a candidate scenario, including its auction, contract, doubling
  status, labels, and information, are loaded into the test scene from that
  scenario.

Test runs use the administrator's contract/stasis score matrix. Generate a
report from **Test > Generate test report** to review overall statistics,
contestant scores by problem, scenario difficulty, and the top three contestants.
The report can be exported as a PDF in English or Chinese.

DDS values are shown separately and are not translated.
"""

    CHINESE_INSTRUCTIONS = """\
# 管理桥牌资源

登录后可管理自己的文件夹、牌例、牌局和场景。资源数据保存在本机 SQLite 数据库中。

## 资源树

- 选择文件夹并点击“添加”，可创建子文件夹或牌例。

- 选择牌例并点击“添加”，可用 PBN 输入或可视化选牌器创建牌局。牌局还保存局况和发牌者。
  PBN 手牌会实时预览；选牌器会用颜色标明座位，并可在每个座位已有 0 张或 13 张牌时
  随机分配剩余牌。

- 选择牌局并点击“添加”，可创建场景。场景包含叫牌过程、人类座位、机器人规则（标签或目标）、
  视图（分析或隐藏）和模式（普通或演示）。

- 选择任意资源并点击“移动”以选择有效的新父级位置。确认前请检查来源和目标预览；
  移动文件夹、牌例或牌局时，其子资源也会一起移动。

- 选择文件夹、牌例或场景并点击“编辑”，可重命名。

- 选择牌局并点击“编辑”，可重命名或重新设置手牌、局况和发牌者。

- 选择文件夹、牌例、牌局或场景并点击“复制”，可复制该资源及其子资源，
  包括场景信息和标签。

- 使用“管理员”“工具”“测试”和“资源管理器”菜单执行账户、应用、测试和资源操作。
- “管理员 > 导出管理员数据”可将当前管理员的工作区保存为单个加密 `.bdtpack` 文件。
  请设置并确认至少 12 个字符的独立加密口令并妥善保管；口令无法找回。
  “管理员 > 导入管理员数据”会先验证口令，再将数据添加到当前登录的管理员账户，
  不会覆盖现有资源。与导出测试关联的学生账户、分配记录和成绩也会包含在文件中；
  管理员登录凭证不会导出。
- “资源管理器”用于查看 `README.md` 和 `requirements.txt`；资源树中的添加、编辑、删除和复制操作仍在资源树中进行。
- “工具 > 语言”会先打开语言选择窗口；“工具 > 键盘快捷键”会打开快捷键说明窗口。
- “测试 > 学生管理”可由管理员注册学生账户并分配或移除测试；“管理员 > 学生登录”会自动启动学生锁定会话。“测试 > 查看测试结果”可查看提交记录；“测试 > 生成测试报告”可汇总成绩、题目表现和场景难度、列出前三名并导出 PDF。
- 中文界面下，“资源管理器 > 项目说明（README.md）”会打开中文说明；菜单仍只保留一个项目说明入口。
- 练习构建页面右上角的红色叉号按钮可关闭页面。

## 普通模式下的机器人规则

可使用“标签”规则标记牌，或使用“目标”规则记录目标出牌序列。右键点击牌（macOS 上按住
Control 点击）可编辑标签。每种颜色的序号独立计算。以下顺序中，“无颜色”指没有标签的牌；
“DDS 最佳牌组”指当前局面下合法牌中 DDS 结果最高的牌。

**核心原则**：只有**红色**（领打时）和**蓝色**（垫牌时）可以强行让机器人选择 DDS 最佳牌组之外的牌（即非最优出牌，用于测试或特殊演示）。对于所有其他规则，机器人只能严格在 **DDS 最佳牌组** 内部挑选一张牌。

### 领出

1. 红色，序号升序（可选择 DDS 最佳牌组之外的牌）。
2. 在 DDS 最佳牌组内部，按以下优先级顺序选择第一张可用的牌：
   - 橙色（序号升序）
   - 无颜色
   - 紫色（序号降序）
   - 蓝色（序号降序）
   - 绿色（序号降序）
   - 黄色（序号降序）

### 垫牌

1. 蓝色，序号升序（可选择 DDS 最佳牌组之外的牌）。
2. 在 DDS 最佳牌组内部，按以下优先级顺序选择第一张可用的牌：
   - 紫色（序号升序）
   - 无颜色
   - 橙色（序号降序）
   - 红色（序号降序）
   - 绿色（序号降序）
   - 黄色（序号降序）

### 跟牌

在 DDS 最佳牌组内部，按以下优先级顺序选择第一张可用的牌：
1. 绿色（序号升序）
2. 蓝色（序号升序）
3. 紫色（序号升序）
4. 无颜色
5. 橙色（序号降序）
6. 红色（序号降序）
7. 黄色（序号降序）

### 通用建议

- 在需要故意选择非最优路线（放水或制造测试场景）时，领打时使用红色，垫牌时使用蓝色。
- 紫色作为 DDS 最优垫牌时的主要偏好控制工具。
- 跟牌时使用绿色，可以在 DDS 评估出的多个等价最佳牌中，优先打出能给人类玩家带来最大心理考验或选择难题的牌。
- 对关键大牌或敏感牌标记黄色，使其在 DDS 最佳选项中的优先级排在最后，避免机器人无谓暴露信息或提前送出大牌。

## 演示与场景

在“演示”模式下，机器人会使用已记录的目标序列或标签规则操作非人类座位。选择“分析”或“隐藏”
视图，可在双明手视角与真实牌局视角之间切换。在“隐藏”视图的演示中，人类座位属于庄家方时，
庄家和明手的手牌正面朝上；人类座位属于防守方时，人类座位和明手正面朝上，其搭档与庄家的
手牌不可见。

场景可包含可选的纯文本“信息”，可在“设置”中编辑。测试过程中会向学生显示该信息，
并通过测试与场景的关联关系保留。

## 锁定模式与运行测试

选择“管理员 > 管理员锁定模式”并再次输入管理员密码。资源面板将变为仅支持有限命令的终端。
输入 **Help** 查看命令，输入 **Exit** 可退出锁定模式并返回未登录状态。

- `Run (牌局名称)场景名称` 使用目标规则和隐藏视图自动播放该场景已记录的目标序列。
- `Run 测试名称` 运行可用测试。在管理员锁定模式中，学生需要输入 ID 和密码，且该测试必须已分配给该学生。
  学生也可选择“管理员 > 学生登录”，自动进入锁定模式并查看可参加的测试。学生只能运行已分配的测试，
  不能单独运行场景；每项测试分配只能完成一次，完成后会从可用列表中移除并保存结果。
- 每道题有多个候选场景时，每次测试只随机运行其中一个，并使用标签规则和隐藏视图。管理员负责注册学生账户和分配测试；
  系统会核验学生 ID 和密码，成绩会关联到学生账户，密码以哈希形式保存。

每个测试场景结束后会显示结果和分数，并提供继续按钮。最终测试分数和学生 ID 会保存在本机。
“测试 > 运行测试”也可进入锁定模式并选择已保存的测试。“测试 > 查看测试结果”可查看提交记录。

## 监控

“监控”显示所有管理员（包括当前账户）的资源数量汇总，以及本机运行记录和近期应用错误；
不会公开管理员保存的资源内容。

## 测试

以管理员身份登录后，选择“练习构建”即可创建和管理测试。每个测试支持标题、多个题目和评分矩阵：

- 每道题使用管理员指定的一个牌例，并从该牌例中选择一个或多个候选场景。每次运行测试时，
  每道题只会随机选择一个候选场景，不会运行该题的全部候选场景。
- 定约行根据所选场景中不同的最终定约自动生成。管理员可编辑可接受的结果差值（例如 **=**、**-1**、
  **-2**、**+1** 或 **+2**），并为每个定约/结果差值单元格填写分数。
- 测试构建页面会将测试保存在本机，管理员可重新打开、编辑或删除测试。
- 候选场景的叫牌、定约、加倍状态、标签和信息会从原场景加载到测试场景中。

测试运行使用管理员设置的定约/结果差值评分矩阵。“测试 > 生成测试报告”可查看总体统计、考生题目得分矩阵、场景难度统计和前三名，并可导出为中英文 PDF。

DDS 数值独立显示，不进行翻译。
"""

    def __init__(self, language="en", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Instructions")
        self.resize(900, 720)
        layout = QVBoxLayout(self)
        self.instructions = QTextBrowser()
        self.instructions.setMarkdown(
            self.CHINESE_INSTRUCTIONS
            if language == "zh"
            else self.ENGLISH_INSTRUCTIONS
        )
        layout.addWidget(self.instructions)