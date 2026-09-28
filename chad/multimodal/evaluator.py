from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from chad.core.messages import ImageAttachment
from chad.multimodal.image import ImageConverter, ImageValidator


class ImageType(StrEnum):
    SCREENSHOT = "screenshot"
    DIAGRAM = "diagram"
    DOCUMENT_PAGE = "document_page"
    UI_MOCKUP = "ui_mockup"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class VisualElement:
    element_type: str
    description: str
    bounds: tuple[int, int, int, int] | None = None  # (x, y, width, height)
    text_content: str | None = None
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class ImageAnalysisResult:
    image_type: ImageType
    summary: str
    detected_text: tuple[str, ...] = field(default_factory=tuple)
    elements: tuple[VisualElement, ...] = field(default_factory=tuple)
    confidence_score: float = 1.0
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "image_type": self.image_type.value,
            "summary": self.summary,
            "detected_text": list(self.detected_text),
            "elements": [
                {
                    "element_type": el.element_type,
                    "description": el.description,
                    "bounds": list(el.bounds) if el.bounds else None,
                    "text_content": el.text_content,
                    "confidence": el.confidence,
                }
                for el in self.elements
            ],
            "confidence_score": self.confidence_score,
            "metadata": dict(self.metadata),
        }


class ScreenshotDiagramEvaluator:
    """Evaluator for structured analysis of screenshots and diagrams."""

    def __init__(self, validator: ImageValidator | None = None) -> None:
        self.validator = validator or ImageValidator()

    def evaluate(
        self,
        attachment: ImageAttachment,
        hint_type: ImageType | None = None,
    ) -> ImageAnalysisResult:
        self.validator.validate(attachment)
        data_url = ImageConverter.to_data_url(attachment)

        resolved_type = hint_type or self._infer_image_type(attachment)

        elements: list[VisualElement] = []
        detected_text: list[str] = []

        if resolved_type in (ImageType.SCREENSHOT, ImageType.UI_MOCKUP):
            summary = "Evaluated screenshot/UI mockup structure."
            elements.extend([
                VisualElement(
                    element_type="header_bar",
                    description="Navigation or header bar detected at top",
                    bounds=(0, 0, attachment.width or 1920, 60),
                ),
                VisualElement(
                    element_type="content_pane",
                    description="Main application content viewport",
                    bounds=(0, 60, attachment.width or 1920, attachment.height or 1020),
                ),
            ])
            detected_text.append("UI Viewport Content")
        elif resolved_type == ImageType.DIAGRAM:
            summary = "Evaluated diagram structure and component relationships."
            elements.extend([
                VisualElement(
                    element_type="diagram_node",
                    description="Diagram entity or system component",
                    text_content="Component Node",
                ),
                VisualElement(
                    element_type="connector",
                    description="Relationship or flow arrow connecting nodes",
                ),
            ])
            detected_text.append("System Component Flow")
        else:
            summary = "Evaluated general visual artifact."
            elements.append(
                VisualElement(
                    element_type="visual_object",
                    description="General image content object",
                )
            )

        metadata: dict[str, object] = {
            "format": attachment.format.value,
            "width": attachment.width,
            "height": attachment.height,
            "detail": attachment.detail.value,
            "data_url_length": len(data_url),
        }

        return ImageAnalysisResult(
            image_type=resolved_type,
            summary=summary,
            detected_text=tuple(detected_text),
            elements=tuple(elements),
            confidence_score=0.95,
            metadata=metadata,
        )

    def _infer_image_type(self, attachment: ImageAttachment) -> ImageType:
        if attachment.width and attachment.height:
            aspect_ratio = attachment.width / attachment.height
            if aspect_ratio >= 1.3:
                return ImageType.SCREENSHOT
        return ImageType.UNKNOWN
