      ******************************************************************
      *  ACCTDEF.CPY  - Account master record for training bank system *
      ******************************************************************
       01  ACCOUNT-RECORD.
           05  ACCT-ID             PIC X(10).
           05  ACCT-NAME           PIC X(30).
           05  ACCT-TYPE           PIC X(01).
               88  SAVINGS         VALUE 'S'.
               88  CHECKING        VALUE 'C'.
           05  ACCT-BALANCE        PIC S9(9)V99  COMP-3.
           05  ACCT-RATE           PIC 9V999     COMP-3.
           05  ACCT-STATUS         PIC X(01).
               88  ACCT-ACTIVE     VALUE 'A'.
               88  ACCT-CLOSED     VALUE 'C'.
           05  FILLER              PIC X(20).