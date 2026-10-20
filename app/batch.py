"""Batch analysis for CSV files."""
import csv
import io
from app.rules import analyze


def parse_csv(file_content: bytes) -> list:
    """Parse CSV file and return list of rows."""
    try:
        text = file_content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        return rows
    except Exception as e:
        raise ValueError(f"Could not parse CSV: {str(e)}")


def batch_analyze(rows: list, text_column: str = "offer_text") -> list:
    """Analyze multiple offers from CSV rows."""
    results = []
    
    for i, row in enumerate(rows):
        if text_column not in row:
            results.append({
                "row": i + 1,
                "error": f"Column '{text_column}' not found"
            })
            continue
        
        text = row.get(text_column, "").strip()
        if not text:
            results.append({
                "row": i + 1,
                "error": "Empty offer text"
            })
            continue
        
        try:
            analysis = analyze(text)
            results.append({
                "row": i + 1,
                "trust_score": analysis["trust_score"],
                "label": analysis["label"],
                "flags_count": len(analysis["flags"]),
                "preview": text[:100]
            })
        except Exception as e:
            results.append({
                "row": i + 1,
                "error": str(e)[:100]
            })
    
    return results


def generate_csv_report(results: list) -> str:
    """Generate CSV report from batch analysis results."""
    output = io.StringIO()
    
    if not results:
        return ""
    
    # Determine columns
    fieldnames = ["row", "trust_score", "label", "flags_count", "preview", "error"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    
    writer.writeheader()
    for result in results:
        writer.writerow(result)
    
    return output.getvalue()
