import os
from typing import Any

import openpyxl

from app.config import settings


def parse_excel(file_path: str) -> dict[str, Any]:
    full_path = os.path.join(settings.STORAGE_ROOT, file_path)

    wb = openpyxl.load_workbook(full_path, data_only=True)

    sheets_data = {}
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = []
        for row in ws.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                rows.append([str(cell) if cell is not None else "" for cell in row])
        sheets_data[sheet_name] = rows

    wb.close()

    return {
        "sheet_names": list(sheets_data.keys()),
        "sheets": sheets_data,
        "total_sheets": len(sheets_data),
    }
