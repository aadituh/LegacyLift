       IDENTIFICATION DIVISION.
       PROGRAM-ID. INTCALC.
      *----------------------------------------------------------------
      * INTCALC - add simple interest for a number of days.
      * Called by BANKMAIN. Only active accounts with a positive
      * balance earn interest:
      *   interest = balance * yearly rate * days / 365, rounded
      *----------------------------------------------------------------
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-DAYS-IN-YEAR         PIC 999 VALUE 365.

       LINKAGE SECTION.
       01  LS-ACCOUNT.
           COPY ACCTDEF.
       01  LS-DAYS                 PIC 999.
       01  LS-INTEREST             PIC S9(7)V99.

       PROCEDURE DIVISION USING LS-ACCOUNT LS-DAYS LS-INTEREST.
       CALCULATE-INTEREST.
           MOVE ZERO TO LS-INTEREST
           IF ACCT-ACTIVE AND ACCT-BALANCE > ZERO
               COMPUTE LS-INTEREST ROUNDED =
                   ACCT-BALANCE * ACCT-RATE * LS-DAYS / WS-DAYS-IN-YEAR
               ADD LS-INTEREST TO ACCT-BALANCE
           END-IF
           GOBACK.
