       IDENTIFICATION DIVISION.
       PROGRAM-ID. MONTHEND.
      *----------------------------------------------------------------
      * MONTHEND - month-end close for the accounting team.
      * For each account: add the month's interest to savings, charge
      * the monthly fee when a checking balance is under the minimum,
      * and print one line. Ends with the totals for the ledger.
      * Starting balances are the nightly batch's statement (BANKMAIN).
      *----------------------------------------------------------------
       DATA DIVISION.
       WORKING-STORAGE SECTION.
           COPY FEERATES.
       01  WS-NAME                 PIC X(14).
       01  WS-TYPE                 PIC X.
       01  WS-BAL                  PIC 9(7)V99.
       01  WS-RATE                 PIC 9V9999.
       01  WS-INT                  PIC 9(5)V99 VALUE ZERO.
       01  WS-FEE                  PIC 9(3)V99 VALUE ZERO.
       01  WS-COUNT                PIC 99 VALUE ZERO.
       01  WS-TOTAL-INT            PIC 9(7)V99 VALUE ZERO.
       01  WS-TOTAL-FEES           PIC 9(5)V99 VALUE ZERO.
       01  WS-TOTAL-BAL            PIC 9(9)V99 VALUE ZERO.

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           DISPLAY "MONTH-END CLOSE - OCTOBER"
           MOVE "ALICE JOHNSON" TO WS-NAME
           MOVE "S" TO WS-TYPE
           MOVE 13027.21 TO WS-BAL
           MOVE 0.0250 TO WS-RATE
           PERFORM CLOSE-ACCOUNT
           MOVE "BOB SMITH" TO WS-NAME
           MOVE "C" TO WS-TYPE
           MOVE 2450.50 TO WS-BAL
           MOVE 0 TO WS-RATE
           PERFORM CLOSE-ACCOUNT
           MOVE "ELENA ROSSI" TO WS-NAME
           MOVE "C" TO WS-TYPE
           MOVE 640.00 TO WS-BAL
           MOVE 0 TO WS-RATE
           PERFORM CLOSE-ACCOUNT
           DISPLAY "ACCOUNTS CLOSED: " WS-COUNT
           DISPLAY "TOTAL INTEREST:  " WS-TOTAL-INT
           DISPLAY "TOTAL FEES:      " WS-TOTAL-FEES
           DISPLAY "TOTAL BALANCE:   " WS-TOTAL-BAL
           STOP RUN.

       CLOSE-ACCOUNT.
           MOVE ZERO TO WS-INT
           MOVE ZERO TO WS-FEE
           IF WS-TYPE = "S"
               COMPUTE WS-INT ROUNDED = WS-BAL * WS-RATE * WS-DAYS / 365
           END-IF
           IF WS-TYPE = "C" AND WS-BAL < WS-MIN-BALANCE
               MOVE WS-MONTHLY-FEE TO WS-FEE
           END-IF
           ADD WS-INT TO WS-BAL
           SUBTRACT WS-FEE FROM WS-BAL
           ADD 1 TO WS-COUNT
           ADD WS-INT TO WS-TOTAL-INT
           ADD WS-FEE TO WS-TOTAL-FEES
           ADD WS-BAL TO WS-TOTAL-BAL
           DISPLAY WS-NAME " " WS-TYPE " " WS-BAL " " WS-INT " " WS-FEE.
