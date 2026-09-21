       IDENTIFICATION DIVISION.
       PROGRAM-ID. BANKMAIN.
      ******************************************************************
      *  BANKMAIN - Training driver for a small finance shop            *
      *  Holds three sample accounts in WORKING-STORAGE, calls INTCALC *
      *  to post 30 days of interest, then prints a mini statement.    *
      ******************************************************************
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-DAYS                 PIC 9(03) VALUE 30.
       01  WS-IDX                  PIC 9(02) VALUE ZERO.
       01  WS-TOTAL-BAL            PIC S9(11)V99 COMP-3 VALUE ZERO.

       01  WS-ACCOUNT-TABLE.
           05  WS-ACCT OCCURS 3 TIMES.
               COPY ACCTDEF.

       01  WS-HEADER.
           05  FILLER              PIC X(40) VALUE
               "ID         NAME                 TYPE   BALANCE".
       01  WS-LINE.
           05  DL-ID               PIC X(10).
           05  FILLER              PIC X(01) VALUE SPACE.
           05  DL-NAME             PIC X(20).
           05  FILLER              PIC X(01) VALUE SPACE.
           05  DL-TYPE             PIC X(01).
           05  FILLER              PIC X(04) VALUE SPACE.
           05  DL-BAL              PIC ---,---,--9.99.

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           PERFORM LOAD-SAMPLE-ACCOUNTS
           PERFORM VARYING WS-IDX FROM 1 BY 1 UNTIL WS-IDX > 3
               CALL "INTCALC" USING WS-ACCT(WS-IDX)
                                    WS-DAYS
               ADD ACCT-BALANCE OF WS-ACCT(WS-IDX) TO WS-TOTAL-BAL
           END-PERFORM
           PERFORM PRINT-STATEMENT
           STOP RUN.

       LOAD-SAMPLE-ACCOUNTS.
           MOVE "1000000001"          TO ACCT-ID     OF WS-ACCT(1)
           MOVE "ALICE JOHNSON"       TO ACCT-NAME   OF WS-ACCT(1)
           MOVE "S"                   TO ACCT-TYPE   OF WS-ACCT(1)
           MOVE 12500.50              TO ACCT-BALANCE OF WS-ACCT(1)
           MOVE 0.025                 TO ACCT-RATE    OF WS-ACCT(1)
           MOVE "A"                   TO ACCT-STATUS  OF WS-ACCT(1)

           MOVE "1000000002"          TO ACCT-ID     OF WS-ACCT(2)
           MOVE "BOB SMITH"           TO ACCT-NAME   OF WS-ACCT(2)
           MOVE "C"                   TO ACCT-TYPE   OF WS-ACCT(2)
           MOVE 3400.00               TO ACCT-BALANCE OF WS-ACCT(2)
           MOVE 0.005                 TO ACCT-RATE    OF WS-ACCT(2)
           MOVE "A"                   TO ACCT-STATUS  OF WS-ACCT(2)

           MOVE "1000000003"          TO ACCT-ID     OF WS-ACCT(3)
           MOVE "CAROL LEE"           TO ACCT-NAME   OF WS-ACCT(3)
           MOVE "S"                   TO ACCT-TYPE   OF WS-ACCT(3)
           MOVE 8750.25               TO ACCT-BALANCE OF WS-ACCT(3)
           MOVE 0.030                 TO ACCT-RATE    OF WS-ACCT(3)
           MOVE "A"                   TO ACCT-STATUS  OF WS-ACCT(3).

       PRINT-STATEMENT.
           DISPLAY "=== MONTHLY INTEREST STATEMENT ==="
           DISPLAY WS-HEADER
           PERFORM VARYING WS-IDX FROM 1 BY 1 UNTIL WS-IDX > 3
               MOVE ACCT-ID     OF WS-ACCT(WS-IDX) TO DL-ID
               MOVE ACCT-NAME   OF WS-ACCT(WS-IDX) TO DL-NAME
               MOVE ACCT-TYPE   OF WS-ACCT(WS-IDX) TO DL-TYPE
               MOVE ACCT-BALANCE OF WS-ACCT(WS-IDX) TO DL-BAL
               DISPLAY WS-LINE
           END-PERFORM
           DISPLAY "----------------------------------------"
           MOVE WS-TOTAL-BAL TO DL-BAL
           DISPLAY "TOTAL BALANCE AFTER INTEREST: " DL-BAL.