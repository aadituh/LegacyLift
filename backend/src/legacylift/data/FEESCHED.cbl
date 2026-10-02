       IDENTIFICATION DIVISION.
       PROGRAM-ID. FEESCHED.
      *----------------------------------------------------------------
      * FEESCHED - print LegacyLift Bank's fee schedule.
      * Uses only simple statements, so LegacyLift converts all of it.
      *----------------------------------------------------------------
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-BANK-NAME            PIC X(15) VALUE "LEGACYLIFT BANK".
       01  WS-OVERDRAFT-FEE        PIC 9(3) VALUE 35.
       01  WS-MONTHLY-FEE          PIC 9(3) VALUE 5.
       01  WS-WIRE-FEE             PIC 9(3) VALUE 25.
       01  WS-TOTAL                PIC 9(4) VALUE 0.

       PROCEDURE DIVISION.
           DISPLAY "FEE SCHEDULE - " WS-BANK-NAME.
           DISPLAY "OVERDRAFT FEE: " WS-OVERDRAFT-FEE.
           DISPLAY "MONTHLY FEE:   " WS-MONTHLY-FEE.
           DISPLAY "WIRE FEE:      " WS-WIRE-FEE.
           MOVE WS-OVERDRAFT-FEE TO WS-TOTAL.
           ADD WS-MONTHLY-FEE TO WS-TOTAL.
           ADD WS-WIRE-FEE TO WS-TOTAL.
           DISPLAY "ALL FEES:      " WS-TOTAL.
           STOP RUN.
