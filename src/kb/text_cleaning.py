import re
def normalize_letters_and_digits(text: str) -> str:
    characters = []

    for character in text:
        is_fullwidth = (
            "０" <= character <= "９"
            or "Ａ" <= character <= "Ｚ"
            or "ａ" <= character <= "ｚ"
        )

        if is_fullwidth:
            character = chr(ord(character) - 0xFEE0)

        characters.append(character)

    return "".join(characters)

def merge_lines_after_chinese_comma(text: str) -> str:
    return re.sub(
        r"，[ \t]*\r?\n[ \t]*(?=[\u4e00-\u9fff])",
        "，",
        text,
    )