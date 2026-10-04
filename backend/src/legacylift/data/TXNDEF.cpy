      *----------------------------------------------------------------
      * TXNDEF - one transaction, 16 characters in transactions.dat.
      * The program that copies this supplies the group above it.
      *----------------------------------------------------------------
           10  TXN-ACCT-ID         PIC X(6).
           10  TXN-TYPE            PIC X.
               88  TXN-DEPOSIT     VALUE "D".
               88  TXN-WITHDRAWAL  VALUE "W".
           10  TXN-AMOUNT          PIC 9(7)V99.
