"""Built-in files for the demo project created by ``POST /api/projects/demo``.

``DEMO_FILES`` holds ``(name, kind, content)`` tuples; the project service
turns each into a ``SourceFile``. ``store_report.cbl`` uses only statements
the converter supports, so its Python output runs with no review notes.
"""

from legacylift.models import FileKind

DEMO_FILES = (
    (
        "store_report.cbl",
        FileKind.PROGRAM,
        """IDENTIFICATION DIVISION.
PROGRAM-ID. STORE-REPORT.
DATA DIVISION.
WORKING-STORAGE SECTION.
01 WS-STORE PIC X(20) VALUE "LegacyLift Market".
01 WS-CUSTOMER PIC X(20) VALUE "Ada".
01 WS-ITEM PIC X(20) VALUE "Coffee".
01 WS-ITEM-PRICE PIC 9(3) VALUE 12.
01 WS-SHIPPING PIC 9(3) VALUE 5.
01 WS-DISCOUNT PIC 9(3) VALUE 3.
01 WS-TOTAL PIC 9(4) VALUE 0.
01 WS-ORDER-NUMBER PIC 9(4) VALUE 1042.
PROCEDURE DIVISION.
DISPLAY "=== " WS-STORE " ===".
DISPLAY "Order #: " WS-ORDER-NUMBER.
DISPLAY "Customer: " WS-CUSTOMER.
DISPLAY "Item: " WS-ITEM.
DISPLAY "Price: $" WS-ITEM-PRICE.
DISPLAY "Shipping: $" WS-SHIPPING.
DISPLAY "Discount: $" WS-DISCOUNT.
MOVE WS-ITEM-PRICE TO WS-TOTAL.
ADD WS-SHIPPING TO WS-TOTAL.
SUBTRACT WS-DISCOUNT FROM WS-TOTAL.
DISPLAY "Amount due: $" WS-TOTAL.
DISPLAY "Thanks for your order!".
STOP RUN.
""",
    ),
    ("order.cpy", FileKind.COPYBOOK, "01 ORDER-NUMBER PIC 9(4).\n"),
    ("orders.dat", FileKind.DATA, "1042,Ada,Coffee\n"),
)
