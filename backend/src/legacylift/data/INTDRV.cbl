       IDENTIFICATION DIVISION.
       PROGRAM-ID. INTDRV.
      *----------------------------------------------------------------
      * INTDRV - call INTCALC for the first account in accounts.dat
      * (Alice) with 30 days and DISPLAY the interest. Used only to
      * record GnuCOBOL stdout for tests (issue #98). INTCALC itself
      * has a LINKAGE SECTION and cannot run alone.
      *
      * Alice's accounts.dat line maps to ACCTDEF as:
      *   ACCT-BALANCE PIC S9(7)V99 SIGN LEADING SEPARATE = +001250050
      *     → 12500.50 (not 1250.05)
      *   ACCT-RATE PIC 9V9999 = 00250 → 0.0250
      *----------------------------------------------------------------
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ACCOUNT-FILE ASSIGN TO "accounts.dat"
               ORGANIZATION IS LINE SEQUENTIAL.
       DATA DIVISION.
       FILE SECTION.
       FD  ACCOUNT-FILE.
       01  ACCOUNT-LINE            PIC X(43).
       WORKING-STORAGE SECTION.
       01  WS-ACCOUNT.
           COPY ACCTDEF.
       01  WS-DAYS                 PIC 999 VALUE 30.
       01  WS-INTEREST             PIC S9(7)V99.
       PROCEDURE DIVISION.
           OPEN INPUT ACCOUNT-FILE
           READ ACCOUNT-FILE INTO WS-ACCOUNT
               AT END
                   DISPLAY "NO-ACCOUNT"
                   STOP RUN
           END-READ
           CLOSE ACCOUNT-FILE
           CALL "INTCALC" USING WS-ACCOUNT WS-DAYS WS-INTEREST
           DISPLAY WS-INTEREST
           STOP RUN.
