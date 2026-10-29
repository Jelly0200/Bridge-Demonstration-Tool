PRAGMA foreign_keys = ON;

-- 1. Administration Table
CREATE TABLE IF NOT EXISTS Administration (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL UNIQUE,
    Password TEXT NOT NULL,
    ExpiresAt TEXT NULL
);

-- 2. Folder Hierarchy (Self-referencing tree)
CREATE TABLE IF NOT EXISTS Folder (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    AdministrationId INTEGER NOT NULL,
    ParentFolderId INTEGER NULL,
    Name TEXT NOT NULL,
    FOREIGN KEY (AdministrationId) REFERENCES Administration(Id) ON DELETE CASCADE,
    FOREIGN KEY (ParentFolderId) REFERENCES Folder(Id) ON DELETE CASCADE
);

-- 3. Case Table (Collection of related boards)
CREATE TABLE IF NOT EXISTS CaseStudy (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    FolderId INTEGER NOT NULL,
    Name TEXT NOT NULL,
    FOREIGN KEY (FolderId) REFERENCES Folder(Id) ON DELETE CASCADE
);

-- 4. Board Configuration Table
CREATE TABLE IF NOT EXISTS BoardConfiguration (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    Dealer TEXT NOT NULL DEFAULT 'SOUTH' CHECK(Dealer IN ('SOUTH', 'WEST', 'NORTH', 'EAST')),
    Vulnerability TEXT NOT NULL DEFAULT 'NONE' CHECK(Vulnerability IN ('NONE', 'NS', 'EW', 'BOTH'))
);

-- 5. Board Table
CREATE TABLE IF NOT EXISTS Board (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    CaseId INTEGER NOT NULL,
    BoardConfigurationId INTEGER NOT NULL,
    SouthHandPbn TEXT NOT NULL,
    WestHandPbn TEXT NOT NULL,
    NorthHandPbn TEXT NOT NULL,
    EastHandPbn TEXT NOT NULL,
    Description TEXT NULL,
    FOREIGN KEY (CaseId) REFERENCES CaseStudy(Id) ON DELETE CASCADE,
    FOREIGN KEY (BoardConfigurationId) REFERENCES BoardConfiguration(Id) ON DELETE RESTRICT
);

-- 6. Scenario Table
CREATE TABLE IF NOT EXISTS Scenario (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    BoardId INTEGER NOT NULL,
    Name TEXT NOT NULL DEFAULT '',
    Information TEXT NULL,
    BiddingRoute TEXT NOT NULL,
    Declarer TEXT NOT NULL CHECK(Declarer IN ('SOUTH', 'WEST', 'NORTH', 'EAST')),
    Contract TEXT NOT NULL,
    RiskStatus TEXT NOT NULL DEFAULT 'NONE' CHECK(RiskStatus IN ('NONE', 'DOUBLE', 'REDOUBLE')),
    IsTargeted INTEGER NOT NULL DEFAULT 0 CHECK(IsTargeted IN (0, 1)),
    TargetedSequence JSON NULL,
    FOREIGN KEY (BoardId) REFERENCES Board(Id) ON DELETE CASCADE
);

-- 7. Label Table (Robot card behavioral modifiers)
CREATE TABLE IF NOT EXISTS Label (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    ScenarioId INTEGER NOT NULL,
    Sequence INTEGER NOT NULL,
    Color TEXT NOT NULL,
    Card TEXT NOT NULL,
    FOREIGN KEY (ScenarioId) REFERENCES Scenario(Id) ON DELETE CASCADE
);

-- 8. Test Master Table
CREATE TABLE IF NOT EXISTS Test (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    AdministrationId INTEGER NOT NULL,
    Name TEXT NOT NULL,
    FOREIGN KEY (AdministrationId) REFERENCES Administration(Id) ON DELETE CASCADE
);

-- 9. Rule Table (Scoring criteria for tests)
CREATE TABLE IF NOT EXISTS Rule (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    Contracts JSON NOT NULL,
    Rules JSON NOT NULL
);

-- 10. Test Scenario Junction Table
CREATE TABLE IF NOT EXISTS Test_Scenario (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    TestId INTEGER NOT NULL,
    Sequence INTEGER NOT NULL,
    ScenarioId INTEGER NOT NULL,
    RuleId INTEGER NOT NULL,
    FOREIGN KEY (TestId) REFERENCES Test(Id) ON DELETE CASCADE,
    FOREIGN KEY (ScenarioId) REFERENCES Scenario(Id) ON DELETE CASCADE,
    FOREIGN KEY (RuleId) REFERENCES Rule(Id) ON DELETE RESTRICT
);

-- 11. Student Table
CREATE TABLE IF NOT EXISTS Student (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL UNIQUE,
    Password TEXT NOT NULL
);

-- 12. Tests assigned to students; a completed assignment cannot be run again.
CREATE TABLE IF NOT EXISTS Student_Test (
    StudentId INTEGER NOT NULL,
    TestId INTEGER NOT NULL,
    AssignedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CompletedAt DATETIME NULL,
    PRIMARY KEY (StudentId, TestId),
    FOREIGN KEY (StudentId) REFERENCES Student(Id) ON DELETE CASCADE,
    FOREIGN KEY (TestId) REFERENCES Test(Id) ON DELETE CASCADE
);

-- 13. Test Result Table
CREATE TABLE IF NOT EXISTS Test_Result (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    TestId INTEGER NOT NULL,
    StudentId INTEGER NOT NULL,
    ApplicantName TEXT NOT NULL,
    Contracts JSON NOT NULL,
    Score INTEGER NOT NULL,
    SubmittedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (TestId) REFERENCES Test(Id) ON DELETE CASCADE,
    FOREIGN KEY (StudentId) REFERENCES Student(Id) ON DELETE RESTRICT
);