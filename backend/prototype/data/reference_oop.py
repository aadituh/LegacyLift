from decimal import Decimal
from typing import List

class Account:
    def __init__(self, account_number: int, owner: str, balance: Decimal = Decimal('0.00')):
        self.account_number = account_number
        self.owner = owner
        self.balance = balance

    def deposit(self, amount: Decimal):
        self.balance += amount
        print(f"Deposit processed for account {self.account_number}")

    def withdraw(self, amount: Decimal):
        self.balance -= amount
        print(f"Withdrawal processed for account {self.account_number}")

    def generate_report(self):
        print(f"Account Balance Report: {self.balance}")