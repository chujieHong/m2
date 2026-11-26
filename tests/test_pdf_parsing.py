from pathlib import Path

from PIL import Image
import pytest

from kb import ingestion
from kb.pdf_parsing import parse_pdf


SAMPLE = Path(__file__).resolve().parents[1] / "output/pdf/day16_mixed_sample.pdf"
APPLICATION = "用户可在购买后7天内申请退款。"
USAGE = "累计使用时长超过2小时的订单不支持退款。"
ARRIVAL = "审核通过后，退款将在3个工作日内原路退回。"


def fake_ocr(outputs: list[list[str]]):
    pending = iter(outputs)

    def recognize(image: Image.Image) -> list[str]:
        assert image.mode == "RGB"
        return next(pending)

    return recognize


def test_mixed_images_are_read_and_hidden_text_is_not_duplicated():
    pages = parse_pdf(SAMPLE, ocr=fake_ocr([
        [USAGE], [APPLICATION], [ARRIVAL], [ARRIVAL], [],
    ]))

    assert [page.page for page in pages] == [1, 2, 3, 4, 5]
    assert pages[0].ocr_regions == 0  # 普通文字页不加载 OCR。
    assert not pages[1].native_text and USAGE in pages[1].text
    assert "关键规则" in pages[2].native_text
    assert APPLICATION not in pages[2].native_text
    assert APPLICATION in pages[2].text and ARRIVAL in pages[2].text
    assert pages[2].ocr_regions == 2
    assert pages[3].text.count(ARRIVAL) == 1
    assert pages[3].ocr_text == ARRIVAL  # 原始识别结果仍保留。
    assert pages[3].duplicates_removed == 1
    assert not pages[4].text and pages[4].warnings


def test_different_numbers_are_kept_for_review_instead_of_fuzzy_dedup():
    conflicting = ARRIVAL.replace("3", "9")
    pages = parse_pdf(SAMPLE, ocr=fake_ocr([
        [USAGE], [APPLICATION], [ARRIVAL], [conflicting], [],
    ]))
    assert ARRIVAL in pages[3].text
    assert conflicting in pages[3].text
    assert pages[3].duplicates_removed == 0
    assert pages[3].warnings


def test_matching_text_elsewhere_on_page_does_not_hide_image_text():
    elsewhere = "退款说明：关键规则位于下面两张图片中。"
    pages = parse_pdf(SAMPLE, ocr=fake_ocr([
        [USAGE], [elsewhere], [ARRIVAL], [ARRIVAL], [],
    ]))
    assert pages[2].text.count(elsewhere) == 2


def test_ocr_failure_is_not_treated_as_an_empty_page():
    def fail(image: Image.Image) -> list[str]:
        raise RuntimeError("OCR unavailable")

    with pytest.raises(RuntimeError, match="OCR unavailable"):
        parse_pdf(SAMPLE, ocr=fail)


def test_time_cleanup_preserves_original_ocr_text():
    raw = "客服时间09:00一18:00。"
    pages = parse_pdf(SAMPLE, ocr=fake_ocr([
        [raw], [APPLICATION], [ARRIVAL], [ARRIVAL], [],
    ]))
    assert pages[1].ocr_text == raw
    assert "09:00-18:00" in pages[1].text


def test_load_document_uses_mixed_parser_and_keeps_original_page_numbers(monkeypatch):
    recognize = fake_ocr([[USAGE], [APPLICATION], [ARRIVAL], [ARRIVAL], []])
    monkeypatch.setattr(
        ingestion, "parse_pdf", lambda path: parse_pdf(path, ocr=recognize),
    )
    with pytest.warns(UserWarning, match="第 5 页"):
        sections = ingestion.load_document(SAMPLE)
    assert [section.page for section in sections] == [1, 2, 3, 4]
    assert all(section.source == SAMPLE.name for section in sections)
    assert APPLICATION in sections[2].text and ARRIVAL in sections[2].text


def test_table_rows_are_returned_once_with_body_and_source_preserved():
    path = SAMPLE.with_name("day16_table_sample.pdf")
    page = parse_pdf(path)[0]
    sections = ingestion.load_document(path)

    assert "基础版" in page.native_text  # 原始文字层仍供追查。
    assert "基础版" not in page.text and "专业版" not in page.text
    assert "申请期限与到账时限是不同字段" in page.text
    assert len(sections) == 3
    assert sections[1].heading_path[-2:] == ("表格1", "数据行1")
    assert sections[2].heading_path[-2:] == ("表格1", "数据行2")
    assert all(section.page == 1 and section.source == path.name for section in sections)
    assert sum("专业版" in section.text for section in sections) == 1


def test_failed_table_conversion_keeps_original_body(monkeypatch):
    from kb import pdf_parsing

    def fail(table, title):
        raise ValueError("表头不完整")

    monkeypatch.setattr(pdf_parsing, "table_to_text_rows", fail)
    page = parse_pdf(SAMPLE.with_name("day16_table_sample.pdf"))[0]
    assert not page.tables
    assert "基础版" in page.text and "专业版" in page.text
    assert any("表头不完整" in note for note in page.warnings)
