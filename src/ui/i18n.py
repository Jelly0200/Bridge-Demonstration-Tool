from __future__ import annotations

import re
from typing import Any

from PyQt6 import sip
from PyQt6.QtCore import QObject
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMessageBox, QWidget


ENGLISH_TO_CHINESE = {
    "Bridge Demonstration Tool": "桥牌演示工具",
    "Settings": "设置",
    "View: Analysis": "视图：分析",
    "View: Hidden": "视图：隐藏",
    "Mode: Normal": "模式：普通",
    "Mode: Demonstration": "模式：演示",
    "Demonstrate": "演示",
    "Stop": "停止",
    "Demonstration active": "演示进行中",
    "Rule: Label": "规则：标签",
    "Rule: Target": "规则：目标",
    "Rotate view": "旋转视角",
    "Human seat: SOUTH": "人类座位：南",
    "Human seat: WEST": "人类座位：西",
    "Human seat: NORTH": "人类座位：北",
    "Human seat: EAST": "人类座位：东",
    "NORTH": "北",
    "SOUTH": "南",
    "WEST": "西",
    "EAST": "东",
    "Last move": "上一步",
    "Next move": "下一步",
    "Reset": "重置",
    "Monitor": "监控",
    "Robot card sound": "机器人出牌音效",
    "Control Toolbar": "控制工具栏",
    "Instructions": "使用说明",
    "Administrator:": "管理员：",
    "Asset counts:": "资源数量：",
    "Memory status:": "内存状态：",
    "Application errors:": "应用错误：",
    "No administrator accounts.": "没有管理员账户。",
    "No recorded errors.": "没有已记录的错误。",
    "Folders: ": "文件夹：",
    "    Cases: ": "    牌例：",
    "    Boards: ": "    牌局：",
    "Scenarios: ": "场景：",
    "    Labels: ": "    标签：",
    "Undo snapshots: ": "撤销快照：",
    "Target sequence: ": "目标序列：",
    "Peak process memory: ": "进程内存峰值：",
    "Robot error: ": "机器人错误：",
    "Toggle between side-to-play tricks and contract trick margin.": "切换显示当前方赢墩数或定约所需墩数差。",
    "Enter a lockdown command": "请输入锁定模式命令",
    "Unable to read asset counts: ": "无法读取资源数量：",
    "Label ": "标签 ",
    "Label color for ": "标签颜色：",
    "Label sequence:": "标签顺序：",
    "Randomize remaining cards": "随机分配剩余牌",
    "Seat colors:": "座位颜色：",
    "RED": "红色",
    "ORANGE": "橙色",
    "YELLOW": "黄色",
    "BLUE": "蓝色",
    "PURPLE": "紫色",
    "GREEN": "绿色",
    "Clear label": "清除标签",
    "Welcome back, administrator [": "欢迎回来，管理员 [",
    "]!\nAdvanced access is active.": "]！\n高级权限已激活。",
    "Folder asset": "文件夹资源",
    "Case asset": "牌例资源",
    "Board asset": "牌局资源",
    "Scenario asset": "场景资源",
    "Monitor unavailable": "监控不可用",
    "Unable to read monitoring statistics: ": "无法读取监控统计信息：",
    "Asset operation failed: ": "资源操作失败：",
    "Record target": "记录目标",
    "Stop recording": "停止记录",
    "Demonstration complete": "演示完成",
    "Final result: ": "最终结果：",
    "Search folders, cases, boards, scenarios": "搜索文件夹、牌例、牌局和场景",
    "Add": "添加",
    "Edit": "编辑",
    "Delete": "删除",
    "Test construction": "练习构建",
    "Sign in as an administrator to construct tests.": "请以管理员身份登录后构建测试。",
    "Create tests from your cases and scenarios.": "使用自己的牌例和场景创建测试。",
    "Tests": "测试",
    "New test": "新建测试",
    "Delete test": "删除测试",
    "Test title": "测试标题",
    "Test title:": "测试标题：",
    "Problems": "题目",
    "Add problem": "添加题目",
    "Edit problem": "编辑题目",
    "Remove problem": "删除题目",
    "Save test": "保存测试",
    "Add stasis": "添加结果差值",
    "Enter = or a signed trick difference (for example +3):": "请输入 = 或带符号的墩数差（例如 +3）：",
    "Test problem": "测试题目",
    "Scenarios included (select one or more):": "包含的场景（可多选）：",
    "Acceptable result stasis:": "可接受的结果差值：",
    "Remove selected stasis": "移除所选结果差值",
    "Each scenario has its own scoring rule, even when scenarios share the same contract. Enter a score for every scenario and stasis.": "每个场景都有独立的评分规则，即使场景使用相同定约也不例外。请填写每个场景及结果差值对应的分数。",
    "Invalid stasis": "结果差值无效",
    "Use = or a signed trick difference from -13 to +13.": "请输入 = 或 -13 到 +13 的带符号墩数差。",
    "Duplicate stasis": "结果差值重复",
    "That stasis is already listed.": "该结果差值已存在。",
    "Unable to save problem": "无法保存题目",
    "No cases available": "没有可用牌例",
    "Create a case and at least one scenario before adding a problem.": "请先创建牌例和至少一个场景，再添加题目。",
    "No final contract": "没有最终定约",
    "Unavailable case": "牌例不可用",
    "Complete and save its auction first.": "请先完成并保存该场景的叫牌过程。",
    "Select at least one scenario from the case.": "请至少选择该牌例中的一个场景。",
    "Select scenarios with saved final contracts.": "请选择已保存最终定约的场景。",
    "Add at least one acceptable result stasis.": "请至少添加一个可接受的结果差值。",
    "Score for ": "定约 ",
    " must be a whole number.": " 的分数必须是整数。",
    "A test title is required.": "测试必须填写标题。",
    "Add at least one problem to the test.": "测试至少需要一道题目。",
    "must select scenarios from its case.": "必须选择该牌例中的场景。",
    "has no final contract.": "没有最终定约。",
    "has no scenarios with final contracts.": "没有包含具有最终定约的场景。",
    "must match the selected scenarios' final contracts.": "必须与所选场景的最终定约一致。",
    "needs acceptable contracts.": "需要设置可接受的定约。",
    "needs acceptable results.": "需要设置可接受的结果差值。",
    "has an invalid result stasis.": "结果差值无效。",
    "has duplicate matrix headings.": "评分矩阵的行或列标题重复。",
    "has an invalid scoring matrix.": "评分矩阵无效。",
    "Every score must be a whole number.": "每个分数都必须是整数。",
    "Unable to save test": "无法保存测试",
    "Test saved": "测试已保存",
    "The test and its problems were saved successfully.": "测试及其题目已成功保存。",
    "Case:": "牌例：",
    "Scenarios included": "所含场景",
    "Delete this test and all of its problems?": "确定删除此测试及其所有题目吗？",
    "Unable to delete test": "无法删除测试",
    "Administrator login": "管理员登录",
    "Administrator registration": "管理员注册",
    "Administrator": "管理员",
    "Administration Registration": "管理员注册",
    "Administration Login": "管理员登录",
    "Administration Logout": "管理员退出",
    "Set my account expiration": "设置我的账户有效期",
    "My account expiration": "我的账户有效期",
    "Expiration date:": "有效期至：",
    "This account does not expire": "此账户永不过期",
    "The expiration date cannot be in the past.": "有效期不能早于今天。",
    "Unable to update account expiration": "无法更新账户有效期",
    "Your account will not expire": "您的账户将永不过期",
    "Your account expires after ": "您的账户将于 ",
    "Administrator account expired": "管理员账户已过期",
    "Your administrator account has expired and you have been signed out.": "您的管理员账户已过期，现已退出登录。",
    "Invalid account expiration; administrator signed out": "账户有效期无效，管理员已退出登录",
    "Administrator account expired and was signed out": "管理员账户已过期并退出登录",
    "Administration Lockdown": "管理员锁定模式",
    "Export administrator data": "导出管理员数据",
    "Import administrator data": "导入管理员数据",
    "Choose content to export": "选择要导出的内容",
    "Choose folders, cases, boards, and tests. Student accounts and results are never exported.": "选择要导出的文件夹、牌例、牌局和测试。学生账户及结果不会被导出。",
    "Available content": "可用内容",
    "Folder": "文件夹",
    "Case": "牌例",
    "Board": "牌局",
    "New administrator account:": "新管理员账户：",
    "New administrator account": "新管理员账户",
    "Enter a name for the new account:": "请输入新账户名称：",
    "New account password:": "新账户密码：",
    "New account password": "新账户密码",
    "Enter a password (at least 8 characters):": "请输入至少 8 个字符的密码：",
    "Confirm new account password:": "确认新账户密码：",
    "Re-enter the new account password:": "请再次输入新账户密码：",
    "Nothing selected": "未选择内容",
    "Select at least one folder, case, board, or test to export.": "请至少选择一个要导出的文件夹、牌例、牌局或测试。",
    "Invalid account name": "账户名称无效",
    "The new administrator account name must have at least 3 characters.": "新管理员账户名称至少需要 3 个字符。",
    "Password too short": "密码过短",
    "The new administrator account password must have at least 8 characters.": "新管理员账户密码至少需要 8 个字符。",
    "Passwords do not match": "密码不一致",
    "The new administrator account passwords do not match.": "两次输入的新管理员账户密码不一致。",
    "Create the new administrator account {account} and import the selected content into it?": "创建新的管理员账户 {account} 并将所选内容导入该账户？",
    "Administrator sign-in required": "需要管理员登录",
    "This older package can only be imported while signed in as an administrator.": "此旧版数据包只能在管理员登录后导入。",
    "Save transfer package": "保存数据传输包",
    "Open transfer package": "打开数据传输包",
    "Bridge data package (*.bdtpack)": "桥牌数据包 (*.bdtpack)",
    "Export passphrase": "导出加密口令",
    "Enter a strong export passphrase (at least 12 characters):": "请输入至少 12 个字符的强导出加密口令：",
    "Confirm export passphrase": "确认导出加密口令",
    "Re-enter the export passphrase:": "请再次输入导出加密口令：",
    "Import passphrase": "导入加密口令",
    "Enter the passphrase for this transfer package:": "请输入此数据包的加密口令：",
    "Passphrases do not match": "加密口令不一致",
    "The export passphrases do not match.": "两次输入的导出加密口令不一致。",
    "Unable to export administrator data": "无法导出管理员数据",
    "Transfer package exported": "数据传输包已导出",
    "Administrator data was encrypted and saved to:\n": "管理员数据已加密并保存至：\n",
    "Unable to read transfer package": "无法读取数据传输包",
    "Transfer package verified": "数据传输包验证成功",
    "Package from administrator ": "数据包来源管理员：",
    " contains ": "，包含 ",
    " records.": " 条数据。",
    "Import this package into the signed-in administrator account? Existing data will not be overwritten.": "确定将此数据包导入当前管理员账户吗？现有数据不会被覆盖。",
    "Unable to import administrator data": "无法导入管理员数据",
    "Administrator data imported": "管理员数据已导入",
    "The data was added to ": "数据已添加至管理员 ",
    "An export passphrase is required.": "必须设置导出加密口令。",
    "The passphrase is too long.": "加密口令过长。",
    "Use an export passphrase with at least ": "导出加密口令至少需要 ",
    " characters.": " 个字符。",
    "The selected file is not a valid transfer package.": "所选文件不是有效的数据传输包。",
    "The transfer package version is not supported.": "不支持此数据传输包版本。",
    "The transfer package uses unsupported security settings.": "数据传输包使用了不受支持的安全参数。",
    "The passphrase is incorrect or the transfer package was damaged.": "加密口令错误，或数据传输包已损坏。",
    "The transfer package expands beyond the allowed size.": "解压后的数据包超过允许大小。",
    "The transfer package payload is incomplete or invalid.": "数据传输包内容不完整或无效。",
    "The transfer package payload is invalid.": "数据传输包内容无效。",
    "The transfer package contains invalid data.": "数据传输包包含无效数据。",
    "The transfer package has an unsupported or invalid format.": "数据传输包格式无效或不受支持。",
    "The transfer package does not contain the expected data.": "数据传输包缺少预期的数据。",
    "The transfer package contains a folder cycle.": "数据传输包中的文件夹层级存在循环引用。",
    "A folder references a missing parent folder.": "文件夹引用了不存在的父文件夹。",
    "The imported data violates database relationships.": "导入的数据不符合数据库关系约束。",
    "A student named ": "名为 ",
    " already exists with different credentials.": " 的学生账户已存在，但凭证不同。",
    "Tool": "工具",
    "Instruction": "使用说明",
    "Language": "语言",
    "Keyboard shortcuts": "键盘快捷键",
    "Student Registration": "学生注册",
    "Student registration": "学生注册",
    "Student management": "学生管理",
    "Student login": "学生登录",
    "Student and test assignments": "学生与测试分配",
    "Register a student": "注册学生",
    "Create student account": "创建学生账户",
    "Change student password": "更改学生密码",
    "Change password": "更改密码",
    "Delete student account": "删除学生账户",
    "New password:": "新密码：",
    "Confirm password:": "确认密码：",
    "The passwords do not match.": "两次输入的密码不一致。",
    "Student password changed": "学生密码已更改",
    "Student password changed.": "学生密码已更改。",
    "Student account deleted": "学生账户已删除",
    "Student account deleted. Its test assignments and results were permanently deleted.": "学生账户已删除，其测试分配和成绩记录也已永久删除。",
    "Unable to change student password": "无法更改学生密码",
    "Unable to delete student account": "无法删除学生账户",
    "This permanently deletes the selected student account, all of its test assignments, and all test results. Continue?": "此操作将永久删除所选学生账户、其所有测试分配和成绩记录。是否继续？",
    "Assign test": "分配测试",
    "Remove selected assignment": "移除所选分配",
    "Completed": "已完成",
    "Available": "可用",
    "Test results": "测试结果",
    "Examine test results": "查看测试结果",
    "Generate test report": "生成测试报告",
    "Test report": "测试报告",
    "Export PDF": "导出 PDF",
    "Save test report": "保存测试报告",
    "PDF files (*.pdf)": "PDF 文件 (*.pdf)",
    "Test report generated": "测试报告已生成",
    "Report saved to: ": "报告已保存至：",
    "Generated": "生成时间",
    "Overall statistics": "总体统计",
    "Contestant ability by problem": "考生题目得分矩阵",
    "Scenario difficulty": "场景难度统计",
    "Top three contestants": "成绩前三名",
    "Contestant": "考生",
    "Test attempts": "测试次数",
    "Total score": "总分",
    "Average score": "平均分",
    "Mean score": "平均值",
    "Median score": "中位数",
    "Maximum score": "最高分",
    "Minimum score": "最低分",
    "Score standard deviation": "分数标准差",
    "Count": "次数",
    "Rank": "排名",
    "Scenario": "场景",
    "Problem ": "题目 ",
    "Problem": "题目",
    "Unable to generate test report": "无法生成测试报告",
    "Sign in as an administrator to generate a test report.": "请以管理员身份登录后生成测试报告。",
    "No submissions yet.": "暂无提交记录。",
    "Confirm lockdown": "确认锁定模式",
    "Re-enter the administrator password:": "请再次输入管理员密码：",
    "Lockdown denied": "无法进入锁定模式",
    "The password is incorrect.": "密码错误。",
    "Run Test": "运行测试",
    "Select a test:": "请选择测试：",
    "Test unavailable": "测试不可用",
    "This test is not assigned to the student or has already been completed.": "此测试未分配给该学生，或已完成。",
    "Scenario result": "场景结果",
    "Result could not be saved": "无法保存结果",
    "Unable to open project document": "无法打开项目文档",
    "Could not read ": "无法读取 ",
    "Score": "得分",
    "Submitted": "提交时间",
    "Student registered": "学生已注册",
    "Student name:": "学生姓名：",
    "Student ID:": "学生编号：",
    "Password:": "密码：",
    "Begin test": "开始测试",
    "TEST SESSION": "测试进行中",
    "Test scenario": "测试场景",
    "Scenario information": "场景信息",
    "No additional scenario information is available.": "没有额外的场景信息。",
    "Scenario result": "场景结果",
    "Scenario complete": "场景完成",
    "Declarer tricks": "庄家墩数",
    "Stasis": "结果差值",
    "Scenario score": "场景得分",
    "Proceed to next scenario": "进入下一个场景",
    "Finish test": "完成测试",
    "Test complete": "测试完成",
    "Total score": "总分",
    "Student name": "学生姓名",
    "Student ID": "学生编号",
    "Close": "关闭",
    "Continue": "继续",
    "Choose interface language:": "请选择界面语言：",
    "Close test construction": "关闭练习构建",
    "Possible scenarios (one will be selected per test run):": "候选场景（每次测试每题仅运行其中一个）：",
    " candidate scenarios)": " 个候选场景）",
    "README.md": "项目说明（README.md）",
    "requirements.txt": "依赖清单（requirements.txt）",
    "Test": "测试",
    "Run Test": "运行测试",
    "Explorer": "资源管理器",
    "Duplicate": "复制",
    "Expand all": "全部展开",
    "Collapse all": "全部折叠",
    "Move": "移动",
    "Move asset": "移动资源",
    "Choose a destination:": "请选择目标位置：",
    "Root level": "根目录",
    "No valid destinations": "没有有效的目标位置",
    "There are no other valid destinations for this asset.": "此资源没有其他有效的目标位置。",
    "Review this move before confirming:": "请在确认前检查此次移动：",
    "From: ": "从：",
    "To: ": "到：",
    "This moves the selected asset and all descendants. Continue?": "此操作将移动所选资源及其所有子资源。是否继续？",
    "The asset is already in that location.": "此资源已经位于该位置。",
    "Choose a new parent and review the move before confirming.": "选择新的父级位置，并在确认前检查移动内容。",
    "Expand every folder and its descendants in this asset tree.": "展开此资源树中的所有文件夹及其子项。",
    "Collapse every folder in this asset tree.": "折叠此资源树中的所有文件夹。",
    "Information": "信息",
    "Information:": "信息：",
    "Logout": "退出登录",
    "Administrator: Not signed in": "管理员：未登录",
    "Not signed in": "未登录",
    "Current administrator: Not signed in": "当前管理员：未登录",
    "Asset tree (Folder / Case / Board / Scenario)": "资源树（文件夹 / 牌例 / 牌局 / 场景）",
    "Add a child asset (Insert key or right-click menu).": "添加子资源（Insert 键或右键菜单）。",
    "Edit or rename the selected asset (F2).": "编辑或重命名选中的资源（F2）。",
    "Delete the selected asset and its children (Delete).": "删除选中的资源及其子项（Delete）。",
    "Right-click for actions. Ctrl/Cmd + + or - resizes tree text; Ctrl/Cmd + 0 resets it.": "右键打开操作菜单。Ctrl/Cmd + + 或 - 可调整资源树文字大小；Ctrl/Cmd + 0 可重置。",
    "Select a scenario to view its key play signal.": "选择一个场景以查看其关键出牌信息。",
    "Double-click a scenario to display its deal and play signal.": "双击场景以显示牌局和出牌信息。",
    "No scenario is loaded. Double-click a scenario to display it.": "尚未加载场景。双击一个场景以显示内容。",
    "Recording target sequence. Play legal cards in turn order.": "正在记录目标序列。请按出牌顺序打出合法牌。",
    "Passed out — no card-play demonstration.": "不叫定约——没有出牌演示。",
    "Use Settings to enter a complete, legal auction before card play.": "请先在“设置”中输入完整且合法的叫牌过程。",
    "Record a target sequence before demonstration.": "请先记录目标序列，再开始演示。",
    "Play complete.": "牌局已结束。",
    "Next move is available only for target-rule demonstrations.": "“下一步”仅适用于目标规则演示。",
    "The saved target sequence is complete.": "已完成保存的目标序列。",
    "Target card {card} is not legal for {player or 'the current position'}.": "目标牌 {card} 对 {player or '当前位置'} 不合法。",
    "Target card {card} could not be played.": "无法打出目标牌 {card}。",
    "Target recording requires Analysis view, Normal mode, Rule: Target, and a completed auction.": "记录目标需要分析视图、普通模式、目标规则以及完整叫牌过程。",
    "Target recording requires Analysis view, Normal mode, ": "记录目标需要分析视图、普通模式、",
    "Rule: Target, and a completed auction.": "目标规则以及完整叫牌过程。",
    "Select a label color for ": "选择标签颜色：",
    "Label color for ": "标签颜色：",
    "Apply": "应用",
    "Cancel": "取消",
    "Risk status:": "加倍状态：",
    "Targeted playback:": "目标序列回放：",
    "Disabled": "禁用",
    "Enabled": "启用",
    "Target card sequence (JSON):": "目标出牌序列（JSON）：",
    "Card labels:": "出牌标签：",
    "Sequence": "顺序",
    "Color": "颜色",
    "Card": "牌",
    "Add label": "添加标签",
    "Remove selected": "移除所选项",
    "Scenario rules": "场景规则",
    "Invalid scenario rules": "场景规则无效",
    "New board": "新建牌局",
    "Edit board": "编辑牌局",
    "PBN input": "PBN 输入",
    "Visual card picker": "可视化选牌",
    "Enter all 52 cards to validate the deal.": "请输入全部 52 张牌以验证牌局。",
    "Choose a seat, then click cards to assign or unassign them. Each seat must receive exactly 13 cards.": "选择一个方位，然后点击牌来分配或取消分配。每个方位必须恰好有 13 张牌。",
    "Assign cards to:": "分配给：",
    "Seat colors: SOUTH blue · WEST green · NORTH purple · EAST orange": "方位颜色：南蓝色 · 西绿色 · 北紫色 · 东橙色",
    "Suit": "花色",
    "Cards entered: ": "已输入牌数：",
    "Valid deal: all 52 cards are unique.": "牌局有效：52 张牌均不重复。",
    "Invalid deal: ": "牌局无效：",
    "Each hand must start with its direction, such as N:.": "每手牌必须以方位开头，例如 N:。",
    "Each direction must have exactly one non-empty hand.": "每个方位必须且仅能有一手非空牌。",
    "Dealer:": "发牌人：",
    "Vulnerability:": "局况：",
    "Board name:": "牌局名称：",
    "Optional board name": "可选的牌局名称",
    "Save board": "保存牌局",
    "Invalid deal": "牌局无效",
    "Assign exactly 13 cards to each seat.": "请为每个方位恰好分配 13 张牌。",
    "Valid deal: all 52 cards are assigned exactly once.": "牌局有效：52 张牌均已分配且没有重复。",
    "Assign exactly 13 cards to each seat before saving.": "保存前请为每个方位分配恰好 13 张牌。",
    "Unable to save board: ": "无法保存牌局：",
    "Board #": "牌局 #",
    " was saved successfully.": " 已成功保存。",
    "Analysis": "分析",
    "Hidden": "隐藏",
    "Normal": "普通",
    "Demonstration": "演示",
    "English": "English",
    "Chinese": "中文",
    "Valid deal: all 52 cards are assigned exactly once.": "牌局有效：52 张牌均已分配且没有重复。",
    "Assign exactly 13 cards to each seat before saving.": "保存前请为每个方位分配恰好 13 张牌。",
    "Save": "保存",
    "Saved": "已保存",
    "Save failed": "保存失败",
    "Invalid deal": "牌局无效",
    "Create a case": "新建牌例",
    "Create a child folder": "新建子文件夹",
    "Add child": "添加子项",
    "New folder": "新建文件夹",
    "New child folder": "新建子文件夹",
    "New case": "新建牌例",
    "Add to folder": "添加到文件夹",
    "Folder name:": "文件夹名称：",
    "Case name:": "牌例名称：",
    "Choose what to add:": "请选择要添加的内容：",
    "Sign in or register to manage administrator assets.": "请登录或注册以管理管理员资源。",
    "No saved assets for this administrator.": "该管理员还没有保存的资源。",
    "Sign in or register before adding assets.": "请先登录或注册，再添加资源。",
    "Switch between Chinese and English.": "切换中英文。",
    "Create or load a scenario before changing settings.": "请先创建或加载场景，再修改设置。",
    "Complete the scenario setup and stop recording before demonstration.": "请先完成场景设置并停止记录，再开始演示。",
    "Complete the scenario auction and contract before demonstration.": "请先完成场景叫牌和定约设置，再开始演示。",
    "Administrator: ": "管理员：",
    "Current administrator: ": "当前管理员：",
    "Current view: ": "当前视角：",
    "Label ": "标签 ",
    ": ": "：",
    "NORTH: ": "北：",
    "SOUTH: ": "南：",
    "EAST: ": "东：",
    "WEST: ": "西：",
    "/13": "/13",
    "Signed in as ": "已登录：",
    "Scenario ": "场景 ",
    " loaded": " 已加载",
    "Normal mode selected": "已选择普通模式",
    "Demonstration mode selected": "已选择演示模式",
    "Test construction selected": "已选择练习构建模式",
    "Target play: ": "目标出牌：",
    "Recording target sequence: ": "正在记录目标序列：",
    " cards.": " 张牌。",
    "<br>Next: ": "<br>下一位：",
    "<br>Declarer: ": "<br>庄家：",
    "<br>To play: ": "<br>当前出牌：",
    "Invalid card code in label row ": "标签第 ",
    " needs a positive sequence number.": " 行需要填写正整数顺序号。",
    " must be completed before saving.": " 后才能保存。",
    "Enter a complete legal auction.": "请输入完整且合法的叫牌过程。",
    "Save the scenario before editing rules.": "请先保存场景，再编辑规则。",
    "Bidding route": "叫牌过程",
    "No bidding information.": "没有叫牌信息。",
    "Contract": "定约",
    "Declarer": "庄家",
    "Risk status": "加倍状态",
    "Undo last call": "撤销上一轮叫牌",
    "Scenario Settings": "场景设置",
    "Auction": "叫牌过程",
    "Level": "阶数",
    "Delete asset": "删除资源",
    "Delete ": "删除 ",
    "?\nChild assets will also be deleted.": "？\n其子资源也会一并删除。",
    "Create or load a scenario before changing settings.": "请先创建或加载场景，再修改设置。",
    "Complete the scenario setup and stop recording before demonstration.": "请先完成场景设置并停止记录，再开始演示。",
    "Complete the scenario auction and contract before demonstration.": "请先完成场景叫牌和定约设置，再开始演示。",
    "Select a scenario to view its key play signal.": "选择一个场景以查看其关键出牌信息。",
    "No scenario is loaded. Double-click a scenario to display it.": "尚未加载场景。双击一个场景以显示内容。",
    "Recording target sequence. Play legal cards in turn order.": "正在记录目标序列。请按出牌顺序打出合法牌。",
    "Passed out — no card-play demonstration.": "不叫定约——没有出牌演示。",
    "Play complete.": "牌局已结束。",
    "Next move is available only for target-rule demonstrations.": "“下一步”仅适用于目标规则演示。",
    "The saved target sequence is complete.": "已完成保存的目标序列。",
    "Target card ": "目标牌 ",
    " is not legal for ": " 对 ",
    " could not be played.": " 无法打出。",
    "Target recording requires Analysis view, Normal mode, Rule: Target, and a completed auction.": "记录目标需要分析视图、普通模式、目标规则以及完整叫牌过程。",
    "Current view: ": "当前视角：",
    "Robot could not choose a legal move for ": "机器人无法为 ",
    ". Check scenario labels.": "。请检查场景标签。",
    "Asset operation failed: ": "资源操作失败：",
    "Unable to save board: ": "无法保存牌局：",
    "Invalid deal": "牌局无效",
    "Choose what to add:": "请选择要添加的内容：",
    "New folder": "新建文件夹",
    "New child folder": "新建子文件夹",
    "New case": "新建牌例",
    "Add to folder": "添加到文件夹",
    "Create a case": "新建牌例",
    "Create a child folder": "新建子文件夹",
    "Administrator: ": "管理员：",
    "Current administrator: ": "当前管理员：",
    "Signed in as ": "已登录：",
    "Scenario ": "场景 ",
    " loaded": " 已加载",
    "Test construction selected": "已选择练习构建模式",
    "Normal mode selected": "已选择普通模式",
    "Demonstration mode selected": "已选择演示模式",
    "Pass": "不叫",
    "Double": "加倍",
    "Redouble": "再加倍",
    "South": "南",
    "West": "西",
    "North": "北",
    "East": "东",
    "Scenario Settings": "场景设置",
    "Undo last call": "撤销上一轮叫牌",
    "Delete asset": "删除资源",
    "Delete ": "删除 ",
    "?\nChild assets will also be deleted.": "？\n其子资源也会一并删除。",
    "Invalid target card: ": "目标牌无效：",
    "The target sequence must be a JSON list.": "目标序列必须是 JSON 列表。",
    "Each target card must be a suit-rank code.": "每张目标牌必须使用花色-牌点代码。",
    "A target sequence cannot repeat a card.": "目标序列中不能重复出现同一张牌。",
    "Add at least one card to enable targeted playback.": "启用目标回放前，请至少添加一张牌。",
    "Complete all fields in label row ": "请填写标签第 ",
    "Label row ": "标签第 ",
    "Label sequence numbers must be positive.": "标签顺序号必须为正整数。",
    "Invalid label color in row ": "标签颜色无效，位于第 ",
    "Administrator login": "管理员登录",
    "Administrator registration": "管理员注册",
    "Target card ": "目标牌 ",
    " is not legal for ": " 对 ",
    " could not be played.": " 无法打出。",
    "The robot could not choose a legal move for ": "机器人无法为 ",
    " choose a legal move. Check DDS availability or scenario labels.": " 选择合法出牌。请检查 DDS 是否可用或场景标签是否正确。",
    "The robot could not play ": "机器人无法为 ",
    " for ": " 出牌：",
}

CHINESE_TO_ENGLISH = {value: key for key, value in ENGLISH_TO_CHINESE.items()}
LEGACY_CHINESE_TO_ENGLISH = {
    "管理员登录 (Admin Login)": "Administrator login",
    "管理员注册 (Administrator Registration)": "Administrator registration",
    "用户名:": "Username:",
    "密 码:": "Password:",
    "🔓 登录 (Login)": "🔓 Login",
    "❌ 取消 (Cancel)": "❌ Cancel",
    "请输入管理员凭证以解锁完整权限：": "Enter administrator credentials to unlock full access:",
    "请输入管理员名称 (例如: admin)": "Enter administrator name (for example: admin)",
    "请输入登录密码": "Enter your password",
    "请输入管理员名称": "Enter administrator name",
    "至少 8 个字符": "At least 8 characters",
    "确认密码：": "Confirm password:",
    "管理员名称：": "Administrator name:",
    "密码：": "Password:",
    "注册": "Register",
    "取消": "Cancel",
    "管理员名称至少需要 3 个字符。": "The administrator name must contain at least 3 characters.",
    "密码至少需要 ": "The password must contain at least ",
    " 个字符。": " characters.",
    "两次输入的密码不一致。": "The passwords do not match.",
    "该管理员名称已被使用，请选择其他名称。": "That administrator name is already in use. Choose another.",
    "管理员账户已创建，并已准备好个人教学资料夹。": "The administrator account and personal workspace are ready.",
    "名称已存在": "Name already exists",
    "密码不一致": "Passwords do not match",
    "密码过短": "Password too short",
    "信息不完整": "Incomplete information",
    "注册成功": "Registration successful",
    "注册失败": "Registration failed",
    "登录成功": "Login successful",
    "登录失败": "Login failed",
    "用户名和密码不能为空！": "Username and password are required.",
    "用户名不存在或密码错误，请重新输入！": "Unknown username or incorrect password. Try again.",
    "无法保存管理员账户：": "Could not save the administrator account: ",
}


def translate_text(text: Any, language: str) -> Any:
    if not isinstance(text, str) or "DDS" in text:
        return text
    if language == "zh" and text in ENGLISH_TO_CHINESE:
        return ENGLISH_TO_CHINESE[text]
    if language == "en":
        if text in CHINESE_TO_ENGLISH:
            return CHINESE_TO_ENGLISH[text]
        if text in LEGACY_CHINESE_TO_ENGLISH:
            return LEGACY_CHINESE_TO_ENGLISH[text]

    translated = text
    replacements = (
        ENGLISH_TO_CHINESE
        if language == "zh"
        else {**CHINESE_TO_ENGLISH, **LEGACY_CHINESE_TO_ENGLISH}
    )
    for source, target in sorted(replacements.items(), key=lambda pair: -len(pair[0])):
        if not source:
            continue
        pattern = re.escape(source)
        if source[0].isascii() and source[0].isalnum():
            pattern = rf"(?<![A-Za-z0-9]){pattern}"
        if source[-1].isascii() and source[-1].isalnum():
            pattern = rf"{pattern}(?![A-Za-z0-9])"
        translated = re.sub(pattern, lambda _match: target, translated)
    return translated


def show_message(parent, kind: str, title: str, text: str, *args):
    current = parent
    while current is not None:
        controller = getattr(current, "language_controller", None)
        if controller is not None:
            language = controller.language
            break
        current = current.parent()
    else:
        language = "en"
    message_method = getattr(QMessageBox, kind)
    return message_method(
        parent,
        translate_text(title, language),
        translate_text(text, language),
        *args,
    )


def exec_and_delete(dialog: Any, *args, **kwargs):
    try:
        return dialog.exec(*args, **kwargs)
    finally:
        dialog.deleteLater()


class BilingualTextController:
    """Translate Qt widget text while retaining its original source string."""

    def __init__(self):
        self.language = "en"
        self._tracked: dict[int, tuple[QObject, dict[str, Any]]] = {}

    def _is_exempt(self, obj: QObject) -> bool:
        object_name = obj.objectName()
        return (
            obj.property("bilingualExempt") is True
            or object_name.startswith("dds_")
            or object_name in {"btn_dds_display", "btn_toggle_dds_matrix"}
        )

    def _wrap_method(
        self,
        obj: QObject,
        state: dict[str, Any],
        setter_name: str,
        getter_name: str | None = None,
        text_argument_index: int = 0,
    ):
        original = getattr(obj, setter_name, None)
        if original is None:
            return
        state_key = f"method:{setter_name}"
        if state_key in state:
            return
        getter = getattr(obj, getter_name, None) if getter_name else None
        state[state_key] = {
            "original": original,
            "source": getter() if getter else None,
            "text_argument_index": text_argument_index,
        }

        def translated_call(*args, **kwargs):
            call_args = list(args)
            if len(call_args) > text_argument_index:
                source = call_args[text_argument_index]
                if isinstance(source, str):
                    state[state_key]["source"] = source
                    call_args[text_argument_index] = translate_text(
                        source,
                        self.language,
                    )
            return original(*call_args, **kwargs)

        setattr(obj, setter_name, translated_call)

    def _wrap_items(self, obj: QObject, state: dict[str, Any]):
        if state.get("items_wrapped"):
            return
        if hasattr(obj, "itemText") and hasattr(obj, "setItemText"):
            try:
                count = obj.count()
                original_set_item_text = obj.setItemText
            except (AttributeError, RuntimeError):
                return
            state["item_texts"] = {
                index: obj.itemText(index)
                for index in range(count)
            }
            state["original_set_item_text"] = original_set_item_text
            state["items_wrapped"] = True

            def set_item_text(index, text):
                state["item_texts"][index] = text
                original_set_item_text(
                    index,
                    translate_text(text, self.language),
                )

            obj.setItemText = set_item_text
            original_add_item = obj.addItem
            original_add_items = obj.addItems

            def add_item(*args):
                values = list(args)
                text_index = 1 if len(values) > 1 else 0
                text = values[text_index]
                if isinstance(text, str):
                    index = obj.count()
                    state["item_texts"][index] = text
                    values[text_index] = translate_text(text, self.language)
                return original_add_item(*values)

            def add_items(texts):
                values = list(texts)
                start_index = obj.count()
                state["item_texts"].update(
                    {
                        start_index + offset: text
                        for offset, text in enumerate(values)
                    }
                )
                return original_add_items(
                    [translate_text(text, self.language) for text in values]
                )

            obj.addItem = add_item
            obj.addItems = add_items
            for index, text in state["item_texts"].items():
                original_set_item_text(
                    index,
                    translate_text(text, self.language),
                )

    def _wrap_tabs(self, obj: QObject, state: dict[str, Any]):
        if (
            state.get("tabs_wrapped")
            or not hasattr(obj, "tabText")
            or not hasattr(obj, "addTab")
        ):
            return
        original_set_tab_text = obj.setTabText
        state["tab_texts"] = {
            index: obj.tabText(index)
            for index in range(obj.count())
        }
        state["original_set_tab_text"] = original_set_tab_text
        state["tabs_wrapped"] = True

        def set_tab_text(index, text):
            state["tab_texts"][index] = text
            original_set_tab_text(index, translate_text(text, self.language))

        obj.setTabText = set_tab_text
        original_add_tab = obj.addTab

        def add_tab(*args):
            values = list(args)
            index = obj.count()
            text_index = 1 if len(values) == 2 else 2
            text = values[text_index]
            state["tab_texts"][index] = text
            values[text_index] = translate_text(text, self.language)
            return original_add_tab(*values)

        obj.addTab = add_tab
        for index, text in state["tab_texts"].items():
            original_set_tab_text(index, translate_text(text, self.language))

    def _wrap_table_headers(self, obj: QObject, state: dict[str, Any]):
        if state.get("table_headers_wrapped") or not hasattr(
            obj,
            "setHorizontalHeaderLabels",
        ):
            return
        state["table_headers_wrapped"] = True
        for axis in ("Horizontal", "Vertical"):
            item_getter = getattr(obj, f"{axis.lower()}HeaderItem")
            setter_name = f"set{axis}HeaderLabels"
            original = getattr(obj, setter_name, None)
            if original is None:
                continue
            section_count = (
                obj.columnCount() if axis == "Horizontal" else obj.rowCount()
            )
            labels = [
                item_getter(index).text() if item_getter(index) else ""
                for index in range(section_count)
            ]
            state[f"{axis.lower()}_headers"] = list(labels)
            state[f"original_{axis.lower()}_headers"] = original

            def set_labels(values, *, name=axis.lower(), original_setter=original):
                source = list(values)
                state[f"{name}_headers"] = source
                original_setter(
                    [translate_text(label, self.language) for label in source]
                )

            setattr(obj, setter_name, set_labels)
            original(
                [translate_text(label, self.language) for label in labels]
            )

    def _install_object(self, obj: QObject):
        if sip.isdeleted(obj) or not isinstance(obj, (QWidget, QAction)):
            return
        if self._is_exempt(obj):
            return
        state = getattr(obj, "_bilingual_text_state", None)
        if state is None:
            state = {}
            setattr(obj, "_bilingual_text_state", state)
        object_id = id(obj)
        if object_id not in self._tracked:
            self._tracked[object_id] = (obj, state)
            obj.destroyed.connect(
                lambda _destroyed=None, key=object_id: getattr(
                    self,
                    "_tracked",
                    {},
                ).pop(key, None)
            )

        for setter, getter in (
            ("setText", "text"),
            ("setWindowTitle", "windowTitle"),
            ("setToolTip", "toolTip"),
            ("setPlaceholderText", "placeholderText"),
            ("showMessage", "currentMessage"),
        ):
            self._wrap_method(obj, state, setter, getter)

        if hasattr(obj, "itemText"):
            self._wrap_items(obj, state)
        if hasattr(obj, "tabText"):
            self._wrap_tabs(obj, state)
        if hasattr(obj, "setHorizontalHeaderLabels"):
            self._wrap_table_headers(obj, state)

    def install(self, root: QObject):
        if not isinstance(root, QObject) or sip.isdeleted(root):
            return
        self._install_object(root)
        for obj in root.findChildren(QObject):
            self._install_object(obj)
        self.set_language(self.language)

    def set_language(self, language: str):
        if language not in {"en", "zh"}:
            raise ValueError(f"Unsupported language: {language}")
        self.language = language
        for object_id, (obj, state) in tuple(self._tracked.items()):
            if sip.isdeleted(obj):
                self._tracked.pop(object_id, None)
                continue
            if self._is_exempt(obj):
                continue
            for key, method_state in state.items():
                if key == "item_texts":
                    original = state["original_set_item_text"]
                    for index, source in method_state.items():
                        original(index, translate_text(source, language))
                elif key == "tab_texts":
                    original = state["original_set_tab_text"]
                    for index, source in method_state.items():
                        original(index, translate_text(source, language))
                elif key in {"horizontal_headers", "vertical_headers"}:
                    axis = key.removesuffix("_headers")
                    original = state[f"original_{axis}_headers"]
                    source = method_state
                    original(
                        [
                            translate_text(label, language)
                            for label in source
                        ]
                    )
                elif key.startswith("method:"):
                    source = method_state["source"]
                    if not isinstance(source, str):
                        continue
                    args = [translate_text(source, language)]
                    if method_state["text_argument_index"] > 0:
                        args = [0] * method_state["text_argument_index"] + args
                    method_state["original"](*args)
