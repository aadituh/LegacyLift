"""Small files for a repeatable Postman demo project."""

DEMO_FILES = (
    (
        "hello_team.cbl",
        "program",
        """IDENTIFICATION DIVISION.
PROGRAM-ID. HELLO-TEAM.
DATA DIVISION.
WORKING-STORAGE SECTION.
01 WS-NAME PIC X(20) VALUE "LegacyLift".
01 WS-COUNT PIC 9(3) VALUE 1.
PROCEDURE DIVISION.
DISPLAY "Hello, " WS-NAME.
ADD 1 TO WS-COUNT.
DISPLAY "Demo count: " WS-COUNT.
STOP RUN.
""",
    ),
    ("account.cpy", "copybook", "01 ACCOUNT-NAME PIC X(20).\n"),
    ("accounts.dat", "data", "Ada,123\n"),
)
