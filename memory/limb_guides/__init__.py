"""Limb Guides - 肢体使用指南

存储"怎么用自己的肢体"的知识。

这些指南是 GenesisX 自己生成的，描述如何使用自己拥有的肢体（organs/limbs/）。

与 skills/ 的区别：
- limb_guides/ = 怎么用自己的肢体（Docker容器）
- skills/ = 怎么调用外部工具/第三方API（网上下载的）
"""
from .file_ops_guide import FileOpsGuide
from .web_fetcher_guide import WebFetcherGuide
from .data_analysis_guide import DataAnalysisGuide
from .pdf_processing_guide import PDFProcessingGuide

__all__ = [
    "FileOpsGuide",
    "WebFetcherGuide",
    "DataAnalysisGuide",
    "PDFProcessingGuide",
]
