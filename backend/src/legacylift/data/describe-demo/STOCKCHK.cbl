       IDENTIFICATION DIVISION.
       PROGRAM-ID. STOCKCHK.
      *----------------------------------------------------------------
      * STOCKCHK - called by SHOPMAIN.
      * Uses the same ITEMDEF layout to compare an order quantity
      * with ITEM-ON-HAND.
      *----------------------------------------------------------------
       DATA DIVISION.
       LINKAGE SECTION.
       01  LS-ITEM.
           COPY ITEMDEF.
       01  LS-QTY                  PIC 999.
       01  LS-IN-STOCK             PIC X.

       PROCEDURE DIVISION USING LS-ITEM LS-QTY LS-IN-STOCK.
       CHECK-STOCK.
           IF LS-QTY <= ITEM-ON-HAND
               MOVE "Y" TO LS-IN-STOCK
           ELSE
               MOVE "N" TO LS-IN-STOCK
           END-IF
           GOBACK.
