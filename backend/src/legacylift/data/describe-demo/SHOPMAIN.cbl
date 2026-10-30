       IDENTIFICATION DIVISION.
       PROGRAM-ID. SHOPMAIN.
      *----------------------------------------------------------------
      * SHOPMAIN - price one batch of shop orders.
      * 1. Load inventory.dat into a table laid out by ITEMDEF.
      * 2. Read orders.dat.
      * 3. CALL STOCKCHK to see if each item is in stock.
      *----------------------------------------------------------------
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT INVENTORY-FILE ASSIGN TO "inventory.dat"
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT ORDER-FILE ASSIGN TO "orders.dat"
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD  INVENTORY-FILE.
       01  INVENTORY-LINE          PIC X(36).
       FD  ORDER-FILE.
       01  ORDER-LINE              PIC X(9).

       WORKING-STORAGE SECTION.
       01  WS-ITEM-COUNT           PIC 99 VALUE ZERO.
       01  WS-ORDER-QTY            PIC 999 VALUE ZERO.
       01  WS-IN-STOCK             PIC X VALUE "N".
       01  WS-ITEM-TABLE.
           05  WS-ITEM OCCURS 5 TIMES.
               COPY ITEMDEF.

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           PERFORM LOAD-INVENTORY.
           PERFORM PRICE-ORDERS.
           STOP RUN.
       LOAD-INVENTORY.
           DISPLAY "Loading inventory".
       PRICE-ORDERS.
           CALL "STOCKCHK" USING WS-ITEM(1) WS-ORDER-QTY WS-IN-STOCK.
           DISPLAY "In stock: " WS-IN-STOCK.
