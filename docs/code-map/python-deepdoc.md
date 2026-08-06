# `deepdoc/` — 文档深度解析导航

> 将各格式文档解析为结构化文本,并通过 ONNX 视觉模型做 OCR、版面分析、表格识别。可作为独立 HTTP 服务部署(默认端口 9390)。

## 目录结构

```
deepdoc/
├── parser/               # 各类文档格式解析器(核心解析逻辑)
│   └── resume/           #   简历专用(两步式 NLP 抽取)
│       └── entities/     #     实体词典(公司/学位/行业/地区/学校)
├── vision/               # 视觉识别:OCR / 版面分析 / 表格结构识别(ONNX 推理)
└── server/               # 独立 HTTP 服务(LitServe),暴露 DLA/OCR/TSR
    ├── adapters/         #   模型包装器(推理 + 格式转换)
    └── endpoints/        #   HTTP 端点(LitAPI)
```

## 解析器 `parser/`

统一出口 `parser/__init__.py:17-41`(内部类重命名为 `PdfParser`/`DocxParser` 等)。

| 格式 | 文件:行号 | 核心类 / 入口 | 说明 |
|---|---|---|---|
| PDF(核心) | `parser/pdf_parser.py:56` | `RAGFlowPdfParser`(`__call__`:1744) | 最重解析器,集成 OCR+版面+表格,含乱码检测、表格旋转、TSR 拼装 |
| PDF(纯文本) | `parser/pdf_parser.py:2071` | `PlainParser`(`__call__`:2072) | pdfplumber 直接抽文本,不走视觉 |
| PDF(视觉大模型) | `parser/pdf_parser.py:2092` | `VisionParser`(`__call__`:2109) | 多模态视觉模型解析 |
| Word | `parser/docx_parser.py:33` | `RAGFlowDocxParser`(`__call__`:160) | 分离表格与正文 |
| Excel | `parser/excel_parser.py:29` | `RAGFlowExcelParser`(`__call__`:268) | 可转 HTML 表格 |
| PPT | `parser/ppt_parser.py:22` | `RAGFlowPptParser`(`__call__`:83) | 逐页抽取 |
| HTML | `parser/html_parser.py:37` | `RAGFlowHtmlParser`(`__call__`:38) | 按 chunk_token_num 分块 |
| EPUB | `parser/epub_parser.py:35` | `RAGFlowEpubParser`(`__call__`:39) | 电子书 |
| JSON | `parser/json_parser.py:27` | `RAGFlowJsonParser`(`__call__`:33) | 递归拆分 |
| Markdown | `parser/markdown_parser.py:26` | `RAGFlowMarkdownParser` | `MarkdownElementExtractor`:154(抽表格/代码块) |
| TXT | `parser/txt_parser.py:23` | `RAGFlowTxtParser`(`__call__`:24) | 按分隔符切分 |
| 图片描述 | `parser/figure_parser.py:201` | `VisionFigureParser`(`__call__`:251) | 视觉模型给图表生成描述 |

**第三方/云端后端**(均继承 `RAGFlowPdfParser`):`docling_parser.py:90` `DoclingParser`、`mineru_parser.py:144` `MinerUParser`、`mistral_parser.py:52` `MistralParser`、`paddleocr_parser.py:179` `PaddleOCRParser`、`opendataloader_parser.py:314`、`somark_parser.py:115`、`tcadp_parser.py:200` `TCADPParser`(腾讯云,`TencentCloudAPIClient`:45)。

**简历解析**(两步式):`parser/resume/step_one.py:75` `refactor(df)`(字段规整)→ `step_two.py:439` `parse(cv)`(实体抽取,用 `entities/` 词典)。

## 视觉识别 `vision/`

统一出口 `vision/__init__.py:82-89`(导出 `OCR/Recognizer/LayoutRecognizer/AscendLayoutRecognizer/TableStructureRecognizer`)。

**ONNX 推理基座**:`vision/recognizer.py:32` `Recognizer`(所有识别器基类);`load_model`(:47)默认从 `rag/res/deepdoc` 加载,缺失时 `snapshot_download` 拉 HF `InfiniFlow/deepdoc`;`__call__`(:394)。

**OCR** `vision/ocr.py`:`load_model`(:70,GPU 用 CUDAExecutionProvider:114 否则 CPU:121);`TextRecognizer`(:129, rec.onnx)、`TextDetector`(:384, det.onnx)、`OCR`(:493 统一封装,`detect`:606/`recognize`:620/`__call__`:644)。

**版面分析 DLA** `vision/layout_recognizer.py`:`LayoutRecognizer`(:33 基类,可经 `DEEPDOC_URL` 走远程)、`LayoutRecognizer4YOLOv10`(:175 默认,layout.onnx)、`AscendLayoutRecognizer`(:252 昇腾 NPU)。

**表格识别 TSR** `vision/table_structure_recognizer.py:30` `TableStructureRecognizer`(tsr.onnx,`__call__`:53,`construct_table`:156 拼 HTML)。

**图像处理**:`vision/operators.py`(变换算子)、`vision/postprocess.py`(`DBPostProcess`:40 检测后处理、`CTCLabelDecode`:318 识别解码)、`vision/seeit.py`(可视化)。

**测试脚本**:`vision/t_ocr.py:37` `main`、`vision/t_recognizer.py:30` `main`。

**ONNX 模型**(HF `InfiniFlow/deepdoc`,存 `rag/res/deepdoc/`):`layout.onnx`(YOLOv10 版面)、`det.onnx`(PP-OCRv4 检测)、`rec.onnx`(PP-OCRv4 识别)、`tsr.onnx`(表格)、`ocr.res`(字符字典)。

## 独立服务 `server/`

基于 LitServe + ONNX Runtime,纯 CPU 可跑,默认端口 9390。

- 入口:`server/deepdoc_server.py:50` `main()`(`if __name__`:89);argparse 接 `--port`/`--model-dir`(默认 `rag/res/deepdoc`:40)/`--disable-dla|ocr|tsr`;`ls.LitServer(...)`:72,挂 `/model` 元数据接口:81。
- 分层:端点层(HTTP)→ 适配器(推理+格式转换)→ `vision/` 复用类 → ONNX Runtime。
- 端点 `server/endpoints/`:`dla_endpoint.py:12` `DLAEndpoint`(`/predict/dla`)、`ocr_endpoint.py` `OCREndpoint`(`/predict/ocr`,form `operator=det|rec`)、`tsr_endpoint.py` `TSREndpoint`(`/predict/tsr`)。
- 适配器 `server/adapters/`:`dla_adapter.py:32` `DLAAdapter`(包 LayoutRecognizer,类别映射 `DLA_CLASS_MAP`:20)、`ocr_adapter.py`、`tsr_adapter.py`。
- 辅助:`server/download_deps.py`、`server/docker_stubs.py`、`server/pyproject.toml`、`server/README.md`。
- 镜像:仓库根 `Dockerfile_deepdoc_oss`。

## 库调用入口速查

- 拿解析器:`from deepdoc.parser import PdfParser, DocxParser, ...`
- 拿视觉类:`from deepdoc.vision import OCR, LayoutRecognizer, TableStructureRecognizer`
- 最核心类:`parser/pdf_parser.py:56` `RAGFlowPdfParser`(编排 OCR+版面+表格主流程;`__images__`:1608、`_line_tag`:1522、`crop`:1946)。
- 视觉基类:`vision/recognizer.py:32` `Recognizer`(ONNX 加载与推理底座)。
- 服务入口:`server/deepdoc_server.py:50` `main()`。
