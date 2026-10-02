      *----------------------------------------------------------------
      * ACCTDEF - one bank account, 43 characters in accounts.dat.
      * The program that copies this supplies the group above it.
      *----------------------------------------------------------------
           10  ACCT-ID             PIC X(6).
           10  ACCT-NAME           PIC X(20).
           10  ACCT-TYPE           PIC X.
               88  ACCT-SAVINGS    VALUE "S".
               88  ACCT-CHECKING   VALUE "C".
           10  ACCT-STATUS         PIC X.
               88  ACCT-ACTIVE     VALUE "A".
               88  ACCT-CLOSED     VALUE "C".
           10  ACCT-BALANCE        PIC S9(7)V99
                                   SIGN LEADING SEPARATE.
           10  ACCT-RATE           PIC 9V9999.
