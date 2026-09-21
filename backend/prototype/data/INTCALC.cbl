       IDENTIFICATION DIVISION.
       PROGRAM-ID. INTCALC.
      ******************************************************************
      *  INTCALC - Calculate and apply simple annual interest          *
      *            Called by BANKMAIN.                                 *
      *  USING : ACCOUNT-RECORD (by reference)                         *
      *          WS-DAYS        (by value)                             *
      ******************************************************************
       ENVIRONMENT DIVISION.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-INTEREST             PIC S9(9)V99  COMP-3 VALUE ZERO.
       01  WS-YEAR-DAYS            PIC 9(03)     VALUE 365.

       LINKAGE SECTION.
       COPY ACCTDEF.
       01  LS-DAYS                 PIC 9(03).

       PROCEDURE DIVISION USING ACCOUNT-RECORD
                                LS-DAYS.
       MAIN-PARA.
           IF ACCT-ACTIVE AND ACCT-BALANCE > ZERO
              COMPUTE WS-INTEREST ROUNDED =
                  ACCT-BALANCE * ACCT-RATE * LS-DAYS / WS-YEAR-DAYS
              ADD WS-INTEREST TO ACCT-BALANCE
           END-IF
           GOBACK.