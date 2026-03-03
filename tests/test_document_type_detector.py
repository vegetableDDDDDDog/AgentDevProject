"""
测试文档类型检测器。
"""

import pytest
import os
from services.document_type_detector import DocumentTypeDetector
from services.database import KnowledgeBase


@pytest.fixture
def detector():
    """创建检测器实例"""
    return DocumentTypeDetector(ocr_threshold=10)


@pytest.fixture
def mock_knowledge_base(db_session):
    """创建模拟知识库"""
    from services.database import Tenant

    tenant = Tenant(id="tenant_test", name="test", display_name="Test")
    db_session.add(tenant)
    db_session.commit()

    kb = KnowledgeBase(
        tenant_id="tenant_test",
        name="测试知识库",
        collection_name="test_kb_collection",
        ocr_threshold=10
    )
    db_session.add(kb)
    db_session.commit()
    return kb


def test_detect_text_file(detector, mock_knowledge_base):
    """测试检测文本文件"""
    result = detector.detect_document_type("test.md", mock_knowledge_base)

    assert result['type'] == 'text'
    assert result['needs_ocr'] is False
    assert '文本文件' in result['reason']


def test_detect_markdown_file(detector, mock_knowledge_base):
    """测试检测 Markdown 文件"""
    result = detector.detect_document_type("README.markdown", mock_knowledge_base)

    assert result['type'] == 'text'
    assert result['needs_ocr'] is False
    assert '文本文件' in result['reason']


def test_detect_plain_text_file(detector, mock_knowledge_base):
    """测试检测纯文本文件"""
    result = detector.detect_document_type("notes.txt", mock_knowledge_base)

    assert result['type'] == 'text'
    assert result['needs_ocr'] is False
    assert '文本文件' in result['reason']


def test_detect_excel_file(detector, mock_knowledge_base):
    """测试检测 Excel 文件"""
    result = detector.detect_document_type("data.xlsx", mock_knowledge_base)

    assert result['type'] == 'excel'
    assert result['needs_ocr'] is False
    assert 'openpyxl' in result['reason']


def test_detect_xls_file(detector, mock_knowledge_base):
    """测试检测旧版 Excel 文件"""
    result = detector.detect_document_type("legacy.xls", mock_knowledge_base)

    assert result['type'] == 'excel'
    assert result['needs_ocr'] is False
    assert 'openpyxl' in result['reason']


def test_detect_image_file_png(detector, mock_knowledge_base):
    """测试检测 PNG 图片文件"""
    result = detector.detect_document_type("scan.png", mock_knowledge_base)

    assert result['type'] == 'image'
    assert result['needs_ocr'] is True
    assert 'OCR' in result['reason']


def test_detect_image_file_jpg(detector, mock_knowledge_base):
    """测试检测 JPG 图片文件"""
    result = detector.detect_document_type("photo.jpg", mock_knowledge_base)

    assert result['type'] == 'image'
    assert result['needs_ocr'] is True
    assert 'OCR' in result['reason']


def test_detect_image_file_jpeg(detector, mock_knowledge_base):
    """测试检测 JPEG 图片文件"""
    result = detector.detect_document_type("photo.jpeg", mock_knowledge_base)

    assert result['type'] == 'image'
    assert result['needs_ocr'] is True
    assert 'OCR' in result['reason']


def test_detect_image_file_tiff(detector, mock_knowledge_base):
    """测试检测 TIFF 图片文件"""
    result = detector.detect_document_type("scan.tiff", mock_knowledge_base)

    assert result['type'] == 'image'
    assert result['needs_ocr'] is True
    assert 'OCR' in result['reason']


def test_detect_image_file_bmp(detector, mock_knowledge_base):
    """测试检测 BMP 图片文件"""
    result = detector.detect_document_type("image.bmp", mock_knowledge_base)

    assert result['type'] == 'image'
    assert result['needs_ocr'] is True
    assert 'OCR' in result['reason']


def test_detect_unsupported_file(detector, mock_knowledge_base):
    """测试不支持的文件类型"""
    with pytest.raises(ValueError, match="不支持的文件类型"):
        detector.detect_document_type("video.mp4", mock_knowledge_base)


def test_detect_unsupported_file_zip(detector, mock_knowledge_base):
    """测试不支持的 ZIP 文件类型"""
    with pytest.raises(ValueError, match="不支持的文件类型"):
        detector.detect_document_type("archive.zip", mock_knowledge_base)


def test_custom_ocr_threshold():
    """测试自定义 OCR 阈值"""
    detector = DocumentTypeDetector(ocr_threshold=20)
    assert detector.ocr_threshold == 20


def test_default_ocr_threshold():
    """测试默认 OCR 阈值"""
    detector = DocumentTypeDetector()
    assert detector.ocr_threshold == 10


def test_case_insensitive_extension(detector, mock_knowledge_base):
    """测试文件扩展名大小写不敏感"""
    result1 = detector.detect_document_type("test.TXT", mock_knowledge_base)
    assert result1['type'] == 'text'

    result2 = detector.detect_document_type("test.PDF", mock_knowledge_base)
    # PDF files require actual file analysis, so we'll just check it doesn't crash
    assert 'type' in result2

    result3 = detector.detect_document_type("test.PNG", mock_knowledge_base)
    assert result3['type'] == 'image'
