"""Markdown section-aware document chunker for SyncOps RAG system."""

import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

@dataclass
class DocumentChunk:
    chunk_id: str
    source_file: str
    section_heading: str
    content: str
    char_length: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def parse_markdown_sections(markdown_text: str, filename: str) -> list[dict[str, str]]:
    """
    Parses markdown text into logical sections based on # and ## headings.
    Preserves heading hierarchy and section boundaries.
    """
    lines = markdown_text.splitlines()
    sections: list[dict[str, str]] = []
    
    current_heading = "Overview"
    current_lines: list[str] = []
    
    for line in lines:
        stripped = line.strip()
        # Match markdown headings (e.g. # Title, ## 1. Symptoms, ### Subsection)
        if stripped.startswith("#"):
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append({"heading": current_heading, "content": body})
                current_lines = []
            current_heading = stripped.lstrip("#").strip()
        else:
            current_lines.append(line)
            
    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append({"heading": current_heading, "content": body})
            
    return sections

def chunk_runbook_corpus(
    runbooks_dir: Path,
    chunk_size: int = 350,
    chunk_overlap: int = 60
) -> list[DocumentChunk]:
    """
    Iterates through all Markdown runbooks, parses section headings, and splits
    content into overlapping chunks with source metadata.
    """
    chunks: list[DocumentChunk] = []
    markdown_files = sorted(list(runbooks_dir.glob("*.md")))
    
    for f in markdown_files:
        text = f.read_text(encoding="utf-8")
        sections = parse_markdown_sections(text, f.name)
        
        for sec_idx, sec in enumerate(sections):
            heading = sec["heading"]
            content = sec["content"]
            
            # If section content fits within chunk_size, keep as single chunk
            if len(content) <= chunk_size:
                chunk_id = f"{f.stem}_s{sec_idx}_c0"
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    source_file=f.name,
                    section_heading=heading,
                    content=f"[{heading}] {content}",
                    char_length=len(content)
                ))
            else:
                # Sliding window chunking with overlap
                start = 0
                chunk_idx = 0
                step = max(50, chunk_size - chunk_overlap)
                while start < len(content):
                    end = min(len(content), start + chunk_size)
                    sub_text = content[start:end].strip()
                    if sub_text:
                        chunk_id = f"{f.stem}_s{sec_idx}_c{chunk_idx}"
                        chunks.append(DocumentChunk(
                            chunk_id=chunk_id,
                            source_file=f.name,
                            section_heading=heading,
                            content=f"[{heading}] {sub_text}",
                            char_length=len(sub_text)
                        ))
                        chunk_idx += 1
                    if end >= len(content):
                        break
                    start += step

    return chunks
