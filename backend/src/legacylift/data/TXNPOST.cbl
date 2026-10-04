       IDENTIFICATION DIVISION.
       PROGRAM-ID. TXNPOST.
      *----------------------------------------------------------------
      * TXNPOST - post one deposit or withdrawal to one account.
      * Called by BANKMAIN. Sets LS-RESULT to:
      *   OK  posted
      *   OD  posted, balance went below zero, overdraft fee charged
      *   CL  rejected, the account is closed
      *   BT  rejected, the transaction type is not D or W
      *----------------------------------------------------------------
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-OVERDRAFT-FEE        PIC 9(3)V99 VALUE 35.00.

       LINKAGE SECTION.
       01  LS-ACCOUNT.
           COPY ACCTDEF.
       01  LS-TRANSACTION.
           COPY TXNDEF.
       01  LS-RESULT               PIC XX.

       PROCEDURE DIVISION USING LS-ACCOUNT LS-TRANSACTION LS-RESULT.
       POST-TRANSACTION.
           MOVE "OK" TO LS-RESULT
           EVALUATE TRUE
               WHEN ACCT-CLOSED
                   MOVE "CL" TO LS-RESULT
               WHEN TXN-DEPOSIT
                   ADD TXN-AMOUNT TO ACCT-BALANCE
               WHEN TXN-WITHDRAWAL
                   SUBTRACT TXN-AMOUNT FROM ACCT-BALANCE
                   IF ACCT-BALANCE < ZERO
                       SUBTRACT WS-OVERDRAFT-FEE FROM ACCT-BALANCE
                       MOVE "OD" TO LS-RESULT
                   END-IF
               WHEN OTHER
                   MOVE "BT" TO LS-RESULT
           END-EVALUATE
           GOBACK.
