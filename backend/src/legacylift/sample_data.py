"""Built-in files for the demo project created by ``POST /api/projects/demo``.

``DEMO_FILES`` holds ``(name, kind, content)`` tuples; the project service
turns each into a ``SourceFile``. ``store_report.cbl`` uses only statements
the converter supports, so its Python output runs with no review notes.
``orders.dat`` holds one 24-character record laid out by ``order.cpy``.
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
    (
        "order.cpy",
        FileKind.COPYBOOK,
        (
            "01 ORDER-RECORD.\n"
            "   05 ORDER-NUMBER PIC 9(4).\n"
            "   05 ORDER-CUSTOMER PIC X(10).\n"
            "   05 ORDER-ITEM PIC X(10).\n"
        ),
    ),
    # One fixed-width record laid out by order.cpy: 4 + 10 + 10 characters.
    ("orders.dat", FileKind.DATA, "1042Ada       Coffee    \n"),
)
