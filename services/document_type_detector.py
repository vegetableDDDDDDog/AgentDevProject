"""
智能文档类型检测服务。

自动检测文档类型并判断是否需要 OCR 处理。
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class DocumentTypeDetector:
    """智能文档类型检测器"""

    def __init__(self, ocr_threshold: int = 10):
        """
        初始化检测器。

        Args:
            ocr_threshold: 每页少于 N 个字符时触发 OCR(默认 10)
        """
        self.ocr_threshold = ocr_threshold
        logger.info(f"DocumentTypeDetector 初始化,OCR 阈值: {ocr_threshold}")

    def detect_document_type(
        self,
        file_path: str,
        knowledge_base
    ) -> Dict[str, any]:
        """
        检测文档类型和处理策略。

        Args:
            file_path: 文件路径
            knowledge_base: KnowledgeBase ORM 对象

        Returns:
            {
                'type': 'text_pdf' | 'image_pdf' | 'image' | 'text' | 'excel',
                'needs_ocr': bool,
                'reason': str
            }
        """
        file_ext = file_path.lower().split('.')[-1]

        # PDF 处理
        if file_ext == 'pdf':
            return self._analyze_pdf(file_path, knowledge_base)

        # 图片处理
        elif file_ext in ['png', 'jpg', 'jpeg', 'tiff', 'bmp']:
            return {
                'type': 'image',
                'needs_ocr': True,
                'reason': '纯图片文件,需要 OCR'
            }

        # 文本文件
        elif file_ext in ['md', 'txt', 'markdown']:
            return {
                'type': 'text',
                'needs_ocr': False,
                'reason': '文本文件,直接解析'
            }

        # Excel
        elif file_ext in ['xlsx', 'xls']:
            return {
                'type': 'excel',
                'needs_ocr': False,
                'reason': 'Excel 文件,使用 openpyxl 解析'
            }

        else:
            raise ValueError(f"不支持的文件类型: {file_ext}")

    def _analyze_pdf(
        self,
        file_path: str,
        knowledge_base
    ) -> Dict[str, any]:
        """
        分析 PDF 类型(含 OCR 触发阈值判断)。

        Args:
            file_path: PDF 文件路径
            knowledge_base: KnowledgeBase ORM 对象

        Returns:
            检测结果字典
        """
        try:
            import pypdf

            pdf_reader = pypdf.PdfReader(file_path)
            total_pages = len(pdf_reader.pages)

            if total_pages == 0:
                logger.warning(f"PDF 文件为空: {file_path}")
                return {
                    'type': 'image_pdf',
                    'needs_ocr': True,
                    'reason': 'PDF 文件为空'
                }

            # 检查前 3 页的文本内容
            sample_pages = min(3, total_pages)
            total_chars = 0
            has_text = False

            for i in range(sample_pages):
                try:
                    page = pdf_reader.pages[i]
                    text = page.extract_text()
                    char_count = len(text.strip())
                    total_chars += char_count

                    if char_count > 0:
                        has_text = True

                except Exception as e:
                    logger.warning(f"读取第 {i+1} 页失败: {e}")

            avg_chars_per_page = total_chars / sample_pages

            # OCR 触发阈值判断
            threshold = knowledge_base.ocr_threshold or self.ocr_threshold

            if avg_chars_per_page < threshold:
                logger.info(
                    f"PDF 平均每页 {avg_chars_per_page:.1f} 字符 "
                    f"< 阈值 {threshold},判定为扫描件"
                )
                return {
                    'type': 'image_pdf',
                    'needs_ocr': True,
                    'reason': f'平均每页 {avg_chars_per_page:.0f} 字 < 阈值 {threshold}'
                }
            else:
                return {
                    'type': 'text_pdf',
                    'needs_ocr': False,
                    'reason': f'包含文本层(平均 {avg_chars_per_page:.0f} 字/页)'
                }

        except Exception as e:
            logger.error(f"PDF 分析失败: {e}", exc_info=True)
            # 分析失败时默认使用 OCR
            return {
                'type': 'image_pdf',
                'needs_ocr': True,
                'reason': f'PDF 分析异常,降级为 OCR: {str(e)}'
            }
