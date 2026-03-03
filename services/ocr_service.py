"""
OCR 服务抽象层。

支持多种 OCR 提供商(Tesseract, Azure, 百度等)。
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class OCRService(ABC):
    """OCR 服务抽象基类"""

    @abstractmethod
    async def extract_text(self, file_path: str) -> str:
        """从图片/PDF 中提取文字"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """服务名称"""
        pass


class MockOCR(OCRService):
    """
    Mock OCR 服务（用于开发和测试）

    模拟 OCR 处理，返回固定文本，避免依赖 Tesseract 安装。
    """

    def __init__(self, mock_text: str = "Mock OCR result: 这是测试文本"):
        """
        初始化 Mock OCR。

        Args:
            mock_text: 模拟的 OCR 识别结果
        """
        self.mock_text = mock_text
        self._service_name = "Mock OCR (Development)"
        logger.info("初始化 Mock OCR 服务（开发模式）")

    async def extract_text(self, file_path: str) -> str:
        """
        模拟从 PDF 或图片中提取文字。

        Args:
            file_path: 文件路径

        Returns:
            模拟的文本内容
        """
        logger.info(f"Mock OCR: 模拟处理文件 {file_path}")

        # 模拟处理时间
        import asyncio
        await asyncio.sleep(0.1)

        result = f"{self.mock_text}\n\n来源文件: {file_path.split('/')[-1]}"
        logger.info(f"Mock OCR: 提取完成，共 {len(result)} 字符")
        return result

    @property
    def name(self) -> str:
        return self._service_name


class TesseractOCR(OCRService):
    """
    本地 Tesseract OCR（生产环境）

    需要安装 Tesseract 和语言包。
    """

    def __init__(self, lang: str = 'chi_sim+eng'):
        """
        初始化 Tesseract OCR。

        Args:
            lang: 语言包,默认中英文混合
        """
        try:
            import pytesseract
            from PIL import Image
            self.pytesseract = pytesseract
            self.Image = Image
            self.lang = lang
            logger.info(f"初始化 Tesseract OCR (语言: {lang})")

            # 测试 Tesseract 是否可用
            try:
                version = self.pytesseract.get_tesseract_version()
                logger.info(f"Tesseract 版本: {version}")
            except Exception as e:
                logger.warning(f"无法获取 Tesseract 版本: {e}")

        except ImportError as e:
            raise ImportError(
                "请安装依赖: pip install pytesseract pdf2image pillow\n"
                "系统依赖: sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim"
            )

    async def extract_text(self, file_path: str) -> str:
        """
        从 PDF 或图片中提取文字。

        Args:
            file_path: 文件路径

        Returns:
            提取的文本内容
        """
        try:
            # 将 PDF 转为图片
            if file_path.endswith('.pdf'):
                logger.info(f"将 PDF 转为图片: {file_path}")
                images = self._pdf_to_images(file_path)
            else:
                images = [self.Image.open(file_path)]

            # 提取文字
            all_text = []
            for i, img in enumerate(images, 1):
                logger.debug(f"OCR 处理第 {i}/{len(images)} 页")
                text = self.pytesseract.image_to_string(img, lang=self.lang)
                all_text.append(f"\n--- 第 {i} 页 ---\n{text}")

            result = '\n'.join(all_text)
            logger.info(f"OCR 提取完成,共 {len(result)} 字符")
            return result

        except Exception as e:
            logger.error(f"OCR 提取失败: {e}", exc_info=True)
            raise

    def _pdf_to_images(self, pdf_path: str):
        """
        使用 pdf2image 将 PDF 转为图片。

        Args:
            pdf_path: PDF 文件路径

        Returns:
            PIL.Image 列表
        """
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path, dpi=200)
            logger.info(f"PDF 转换完成,共 {len(images)} 页")
            return images
        except ImportError:
            raise ImportError("请安装 pdf2image: pip install pdf2image")
        except Exception as e:
            logger.error(f"PDF 转图片失败: {e}")
            raise

    @property
    def name(self) -> str:
        return f"Tesseract OCR (语言: {self.lang})"


class OCRServiceFactory:
    """OCR 服务工厂"""

    @staticmethod
    def create_service(config: dict) -> OCRService:
        """
        根据配置创建 OCR 服务。

        Args:
            config: {
                'provider': 'mock' | 'tesseract' | 'azure' | 'baidu',
                'lang': 'chi_sim+eng',  # 可选
                'api_key': str,  # 云服务需要
                'endpoint': str  # 云服务需要
            }

        Returns:
            OCRService 实例
        """
        provider = config.get('provider', 'mock')

        if provider == 'mock':
            return MockOCR()

        elif provider == 'tesseract':
            return TesseractOCR(lang=config.get('lang', 'chi_sim+eng'))

        elif provider == 'azure':
            # 预留: Azure Computer Vision
            raise NotImplementedError("Azure OCR 尚未实现,请使用 mock 或 tesseract")

        elif provider == 'baidu':
            # 预留: 百度 OCR
            raise NotImplementedError("百度 OCR 尚未实现,请使用 mock 或 tesseract")

        else:
            raise ValueError(f"未知的 OCR 提供商: {provider}")
