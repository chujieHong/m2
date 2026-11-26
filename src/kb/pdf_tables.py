from kb.text_cleaning import (
    merge_lines_after_chinese_comma,
    normalize_letters_and_digits,
)

def table_to_text_rows(
    table: list[list[str | None]],
    title: str,
) -> list[tuple[int, str]]:
    if not table:
        return []

    headers = [
        (cell or "").strip()
        for cell in table[0]
    ]

    if not headers or any(not header for header in headers):
        raise ValueError("表头不完整，需要检查原表")

    if len(set(headers)) != len(headers):
        raise ValueError("表头名称重复，需要检查原表")

    rows = []

    for row_number, row in enumerate(table[1:], start=1):
        if len(row) != len(headers):
            raise ValueError("数据行与表头的列数不一致")

        if not any((cell or "").strip() for cell in row):
            continue

        fields = []

        for header, value in zip(headers, row):
            cell = (value or "").strip()
            cell = merge_lines_after_chinese_comma(cell)
            if not cell:
                cell = "（空白或未提取）"

            fields.append(f"{header}：{cell}")

        text = f"{title}\n" + "；".join(fields)
        text = normalize_letters_and_digits(text)
        rows.append((row_number, text))

    return rows