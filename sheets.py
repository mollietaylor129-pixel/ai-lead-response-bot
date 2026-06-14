"""
Google Sheets integration via the gspread library.

Expects a service-account JSON file whose path is set in GOOGLE_CREDENTIALS_PATH,
and a sheet with these columns (row 1 = headers):
  A: Name | B: Email | C: Business | D: Message | E: Timestamp | F: Responded
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

# The scopes needed to read and write Google Sheets
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Column indices (1-based, matching gspread convention)
COL_NAME = 1
COL_EMAIL = 2
COL_BUSINESS = 3
COL_MESSAGE = 4
COL_TIMESTAMP = 5
COL_RESPONDED = 6


class SheetsClient:
    """Thin wrapper around gspread for reading leads and marking replies sent."""

    def __init__(self, credentials_path: str, spreadsheet_id: str, sheet_name: str = "Sheet1"):
        """
        Args:
            credentials_path: Path to the service-account JSON key file.
            spreadsheet_id:   The long ID from the sheet's URL.
            sheet_name:       Tab name inside the spreadsheet (default "Sheet1").
        """
        self._credentials_path = credentials_path
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._worksheet: Optional[gspread.Worksheet] = None

    def _connect(self) -> gspread.Worksheet:
        """Lazily create / return the worksheet connection."""
        if self._worksheet is None:
            creds = Credentials.from_service_account_file(
                self._credentials_path, scopes=_SCOPES
            )
            client = gspread.authorize(creds)
            spreadsheet = client.open_by_key(self._spreadsheet_id)
            self._worksheet = spreadsheet.worksheet(self._sheet_name)
            logger.info("Connected to Google Sheet '%s'", self._sheet_name)
        return self._worksheet

    def get_unresponded_leads(self) -> list[dict]:
        """
        Return all rows where the 'Responded' column is empty.

        Each lead dict contains:
          row_index, name, email, business, message, timestamp
        """
        worksheet = self._connect()
        all_rows = worksheet.get_all_values()

        if not all_rows:
            logger.warning("Sheet appears to be empty (no rows found).")
            return []

        leads = []
        # Start at index 1 to skip the header row; row_index is 1-based for gspread
        for i, row in enumerate(all_rows[1:], start=2):
            # Pad short rows so column lookups never raise IndexError
            row = row + [""] * max(0, COL_RESPONDED - len(row))

            responded = row[COL_RESPONDED - 1].strip()
            if responded:
                continue  # Already handled

            lead = {
                "row_index": i,
                "name": row[COL_NAME - 1].strip(),
                "email": row[COL_EMAIL - 1].strip(),
                "business": row[COL_BUSINESS - 1].strip(),
                "message": row[COL_MESSAGE - 1].strip(),
                "timestamp": row[COL_TIMESTAMP - 1].strip(),
            }

            # Skip rows that are missing critical fields
            if not lead["email"] or not lead["name"]:
                logger.warning("Row %d is missing name or email — skipping.", i)
                continue

            leads.append(lead)

        logger.info("Found %d unresponded lead(s).", len(leads))
        return leads

    def mark_responded(self, row_index: int) -> None:
        """
        Write a UTC timestamp into the 'Responded' column for the given row.

        Args:
            row_index: 1-based row number in the sheet.
        """
        worksheet = self._connect()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        worksheet.update_cell(row_index, COL_RESPONDED, timestamp)
        logger.info("Marked row %d as responded at %s.", row_index, timestamp)
