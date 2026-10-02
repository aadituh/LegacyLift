       IDENTIFICATION DIVISION.
       PROGRAM-ID. BANKMAIN.
      *----------------------------------------------------------------
      * BANKMAIN - nightly batch for LegacyLift Bank.
      * 1. Load every account from accounts.dat into a table.
      * 2. Post each line of transactions.dat (CALL "TXNPOST").
      * 3. Add 30 days of interest to each account (CALL "INTCALC").
      * 4. Print a statement with the new balances.
      *----------------------------------------------------------------
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ACCOUNT-FILE ASSIGN TO "accounts.dat"
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT TXN-FILE ASSIGN TO "transactions.dat"
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD  ACCOUNT-FILE.
       01  ACCOUNT-LINE            PIC X(43).
       FD  TXN-FILE.
       01  TXN-LINE                PIC X(16).

       WORKING-STORAGE SECTION.
       01  WS-END-OF-FILE          PIC X VALUE "N".
           88  END-OF-FILE         VALUE "Y".
       01  WS-ACCOUNT-COUNT        PIC 99 VALUE ZERO.
       01  WS-IDX                  PIC 99 VALUE ZERO.
       01  WS-FOUND                PIC 99 VALUE ZERO.
       01  WS-DAYS                 PIC 999 VALUE 30.
       01  WS-RESULT               PIC XX.
       01  WS-INTEREST             PIC S9(7)V99 VALUE ZERO.
       01  WS-TOTAL-BALANCE        PIC S9(9)V99 VALUE ZERO.
       01  WS-TOTAL-INTEREST       PIC S9(7)V99 VALUE ZERO.
       01  WS-POSTED               PIC 999 VALUE ZERO.
       01  WS-REJECTED             PIC 999 VALUE ZERO.

       01  WS-ACCOUNT-TABLE.
           05  WS-ACCOUNT OCCURS 10 TIMES.
               COPY ACCTDEF.

       01  WS-TRANSACTION.
           COPY TXNDEF.

       01  WS-TXN-LINE.
           05  FILLER              PIC XX VALUE SPACES.
           05  TL-ACCT-ID          PIC X(6).
           05  FILLER              PIC X VALUE SPACE.
           05  TL-TYPE             PIC X.
           05  TL-AMOUNT           PIC Z,ZZZ,ZZ9.99.
           05  FILLER              PIC XX VALUE SPACES.
           05  TL-RESULT           PIC X(24).

       01  WS-HEADING              PIC X(60) VALUE
           "ID     NAME                 T S      BALANCE   INTEREST".
       01  WS-STATEMENT-LINE.
           05  SL-ACCT-ID          PIC X(6).
           05  FILLER              PIC X VALUE SPACE.
           05  SL-NAME             PIC X(20).
           05  FILLER              PIC X VALUE SPACE.
           05  SL-TYPE             PIC X.
           05  FILLER              PIC X VALUE SPACE.
           05  SL-STATUS           PIC X.
           05  SL-BALANCE          PIC -,---,--9.99.
           05  SL-INTEREST         PIC ----,--9.99.

       01  WS-MONEY                PIC -,---,---,--9.99.
       01  WS-COUNT-OUT            PIC ZZ9.

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           DISPLAY "LEGACYLIFT BANK - NIGHTLY BATCH"
           PERFORM LOAD-ACCOUNTS
           PERFORM POST-TRANSACTIONS
           PERFORM PRINT-STATEMENT
           STOP RUN.

       LOAD-ACCOUNTS.
           OPEN INPUT ACCOUNT-FILE
           PERFORM UNTIL END-OF-FILE
               READ ACCOUNT-FILE
                   AT END
                       SET END-OF-FILE TO TRUE
                   NOT AT END
                       ADD 1 TO WS-ACCOUNT-COUNT
                       MOVE ACCOUNT-LINE
                           TO WS-ACCOUNT(WS-ACCOUNT-COUNT)
               END-READ
           END-PERFORM
           CLOSE ACCOUNT-FILE.

       POST-TRANSACTIONS.
           DISPLAY "POSTING TRANSACTIONS"
           MOVE "N" TO WS-END-OF-FILE
           OPEN INPUT TXN-FILE
           PERFORM UNTIL END-OF-FILE
               READ TXN-FILE INTO WS-TRANSACTION
                   AT END
                       SET END-OF-FILE TO TRUE
                   NOT AT END
                       PERFORM POST-ONE-TRANSACTION
               END-READ
           END-PERFORM
           CLOSE TXN-FILE
           MOVE WS-POSTED TO WS-COUNT-OUT
           DISPLAY "POSTED:   " WS-COUNT-OUT
           MOVE WS-REJECTED TO WS-COUNT-OUT
           DISPLAY "REJECTED: " WS-COUNT-OUT.

       POST-ONE-TRANSACTION.
           PERFORM FIND-ACCOUNT
           IF WS-FOUND = ZERO
               MOVE "NA" TO WS-RESULT
           ELSE
               CALL "TXNPOST" USING WS-ACCOUNT(WS-FOUND)
                                    WS-TRANSACTION
                                    WS-RESULT
           END-IF
           MOVE TXN-ACCT-ID TO TL-ACCT-ID
           MOVE TXN-TYPE TO TL-TYPE
           MOVE TXN-AMOUNT TO TL-AMOUNT
           EVALUATE WS-RESULT
               WHEN "OK"
                   MOVE "POSTED" TO TL-RESULT
                   ADD 1 TO WS-POSTED
               WHEN "OD"
                   MOVE "POSTED, OVERDRAFT FEE" TO TL-RESULT
                   ADD 1 TO WS-POSTED
               WHEN "CL"
                   MOVE "REJECTED: ACCOUNT CLOSED" TO TL-RESULT
                   ADD 1 TO WS-REJECTED
               WHEN "NA"
                   MOVE "REJECTED: NO ACCOUNT" TO TL-RESULT
                   ADD 1 TO WS-REJECTED
               WHEN OTHER
                   MOVE "REJECTED: BAD TYPE" TO TL-RESULT
                   ADD 1 TO WS-REJECTED
           END-EVALUATE
           DISPLAY WS-TXN-LINE.

       FIND-ACCOUNT.
           MOVE ZERO TO WS-FOUND
           PERFORM VARYING WS-IDX FROM 1 BY 1
                   UNTIL WS-IDX > WS-ACCOUNT-COUNT
               IF ACCT-ID(WS-IDX) = TXN-ACCT-ID
                   MOVE WS-IDX TO WS-FOUND
               END-IF
           END-PERFORM.

       PRINT-STATEMENT.
           DISPLAY "STATEMENT AFTER " WS-DAYS " DAYS OF INTEREST"
           DISPLAY WS-HEADING
           PERFORM VARYING WS-IDX FROM 1 BY 1
                   UNTIL WS-IDX > WS-ACCOUNT-COUNT
               CALL "INTCALC" USING WS-ACCOUNT(WS-IDX)
                                    WS-DAYS
                                    WS-INTEREST
               ADD WS-INTEREST TO WS-TOTAL-INTEREST
               ADD ACCT-BALANCE(WS-IDX) TO WS-TOTAL-BALANCE
               MOVE ACCT-ID(WS-IDX) TO SL-ACCT-ID
               MOVE ACCT-NAME(WS-IDX) TO SL-NAME
               MOVE ACCT-TYPE(WS-IDX) TO SL-TYPE
               MOVE ACCT-STATUS(WS-IDX) TO SL-STATUS
               MOVE ACCT-BALANCE(WS-IDX) TO SL-BALANCE
               MOVE WS-INTEREST TO SL-INTEREST
               DISPLAY WS-STATEMENT-LINE
           END-PERFORM
           MOVE WS-TOTAL-BALANCE TO WS-MONEY
           DISPLAY "TOTAL BALANCE:  " WS-MONEY
           MOVE WS-TOTAL-INTEREST TO WS-MONEY
           DISPLAY "TOTAL INTEREST: " WS-MONEY.
