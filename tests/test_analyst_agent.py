from __future__ import annotations

from chad.agent.analyst import (
    AnalysisInput,
    AnalysisReport,
    AnalystEngine,
    DatasetSummary,
    EvidenceLink,
    UncertaintyReport,
)
from chad.rag.document import FileDocument


def test_analyst_engine_dataset_csv_analysis() -> None:
    csv_data = """id,age,score,department
1,25,88.5,Engineering
2,30,92.0,Engineering
3,22,,Marketing
4,45,75.0,Sales
5,35,90.5,Sales
6,28,85.0,Engineering
"""
    engine = AnalystEngine()
    report = engine.analyze_dataset(csv_data, filename="employees.csv", query="Analyze employee performance")

    assert isinstance(report, AnalysisReport)
    assert report.title == "Dataset Analysis: employees.csv"
    assert report.query == "Analyze employee performance"
    assert report.dataset_summary is not None
    assert report.dataset_summary.row_count == 6
    assert report.dataset_summary.column_count == 4
    assert "age" in report.dataset_summary.numeric_stats
    assert "score" in report.dataset_summary.numeric_stats

    # Null value check
    assert report.dataset_summary.null_counts["score"] == 1
    assert report.uncertainty.missing_data_count == 1
    assert report.uncertainty.sample_size_warning is False

    # Evidence links check
    assert len(report.evidence_links) > 0
    assert report.evidence_links[0].source_type == "dataset"


def test_analyst_engine_dataset_dict_list_small_sample() -> None:
    records = [
        {"product": "Widget A", "price": 10.0, "qty": 100},
        {"product": "Widget B", "price": 25.0, "qty": 50},
    ]
    engine = AnalystEngine()
    report = engine.analyze_dataset(records, filename="inventory.json", query="Check inventory levels")

    assert report.dataset_summary is not None
    assert report.dataset_summary.row_count == 2
    assert report.uncertainty.sample_size_warning is True
    assert any("Small sample size" in r for r in report.uncertainty.reasons)


def test_analyst_engine_empty_dataset() -> None:
    engine = AnalystEngine()
    report = engine.analyze_dataset("", filename="empty.csv")

    assert report.dataset_summary is None
    assert report.uncertainty.overall_uncertainty == 1.0


def test_analyst_engine_document_analysis_short() -> None:
    engine = AnalystEngine()
    doc_text = "The quarterly revenue grew by 15% year-over-year. Operating costs remained flat."
    report = engine.analyze_document(doc_text, filename="q3_report.txt", query="What was the revenue growth?")

    assert isinstance(report, AnalysisReport)
    assert report.title == "Document Analysis: q3_report.txt"
    assert "q3_report.txt" in report.summary
    assert len(report.evidence_links) == 1
    assert report.evidence_links[0].source_type == "document"


def test_analyst_engine_large_document_workflow() -> None:
    engine = AnalystEngine()
    # Generate large text that triggers multi-chunking (>3 chunks with 1000 char limit)
    paragraphs = [
        f"Paragraph {i}: " + ("CHAD agent system provides agentic AI capabilities. " * 25)
        for i in range(1, 20)
    ]
    large_text = "\n\n".join(paragraphs)

    report = engine.analyze_document(large_text, filename="large_architecture.txt")

    assert "Large document workflow engaged" in report.key_findings[0]
    assert len(report.evidence_links) > 1
    assert report.evidence_links[0].source_type == "chunk"


def test_analyst_engine_file_document_input() -> None:
    engine = AnalystEngine()
    file_doc = FileDocument.create("sample.txt", b"Line 1: System overview.\nLine 2: System details.")
    report = engine.analyze_document(file_doc, query="Extract overview")

    assert report.title == "Document Analysis: sample.txt"
    assert len(report.evidence_links) > 0


def test_analyst_engine_image_analysis() -> None:
    engine = AnalystEngine()
    image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xff"
    report = engine.analyze_image(image_bytes, filename="arch_diagram.png", query="Analyze architecture diagram")

    assert isinstance(report, AnalysisReport)
    assert report.title == "Image Analysis: arch_diagram.png"
    assert len(report.evidence_links) == 1
    assert report.evidence_links[0].source_type == "image"
    assert "width" in report.structured_metrics


def test_analyst_engine_multi_source() -> None:
    engine = AnalystEngine()
    inputs = [
        AnalysisInput(
            input_type="dataset",
            content=[{"metric": "latency", "val": 120}, {"metric": "throughput", "val": 5000}],
            filename="metrics.json",
        ),
        AnalysisInput(
            input_type="document",
            content="System latency improved after gateway optimization.",
            filename="notes.md",
        ),
        AnalysisInput(
            input_type="image",
            content=b"dummy_png_bytes",
            filename="chart.png",
        ),
    ]

    report = engine.analyze_multi_source(inputs, query="Synthesize system performance")

    assert report.title == "Multi-Source Synthesized Analysis Report"
    assert len(report.evidence_links) == 3
    assert report.structured_metrics["source_count"] == 3


def test_analysis_report_serialization() -> None:
    link = EvidenceLink(
        id="EV-01",
        source_type="dataset",
        source_id="test.csv",
        location="row 1",
        snippet="data snippet",
        confidence=0.9,
    )
    uncertainty = UncertaintyReport(
        overall_uncertainty=0.1,
        reasons=("Slight variance",),
    )
    summary = DatasetSummary(
        row_count=10,
        column_count=2,
        column_names=("a", "b"),
        column_types={"a": "numeric", "b": "text"},
        null_counts={"a": 0, "b": 0},
        numeric_stats={"a": {"min": 1.0, "max": 10.0, "mean": 5.5, "median": 5.5}},
    )
    report = AnalysisReport(
        title="Test Report",
        query="Test query",
        summary="Test summary",
        key_findings=("Finding 1",),
        evidence_links=(link,),
        uncertainty=uncertainty,
        dataset_summary=summary,
    )

    d = report.to_dict()
    assert d["title"] == "Test Report"
    assert d["evidence_links"][0]["id"] == "EV-01"

    md = report.to_markdown()
    assert "# Test Report" in md
    assert "## Evidence Links" in md
    assert "## Uncertainty Assessment" in md
