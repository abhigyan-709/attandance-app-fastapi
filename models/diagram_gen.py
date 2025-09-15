from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict

class Node(BaseModel):
    id: str
    label: str
    type: Optional[str] = None       # e.g., "service", "db", "gateway", "worker"
    color: Optional[str] = None      # e.g., hex or keyword

class Edge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None
    style: Optional[str] = None      # e.g., "dashed", "bold"

class DiagramSpec(BaseModel):
    style: Literal["plantuml", "mermaid"] = "mermaid"
    layout: Optional[str] = None     # e.g., "LR" (left-right), "TB"
    theme: Optional[str] = None      # for mermaid: "default", "dark", "forest", etc.
    nodes: List[Node] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)
    options: Dict[str, str] = Field(default_factory=dict)  # extra freeform

class DiagramRequest(BaseModel):
    description: str = Field(..., description="Plain English description of the system.")
    spec: DiagramSpec

class DiagramResponse(BaseModel):
    code: str
    notes: List[str] = Field(default_factory=list)
    filename: str = "diagram.mmd"

class DiagramRenderRequest(BaseModel):
    style: Literal["mermaid", "plantuml"]
    format: Literal["svg", "png"] = "svg"
    code: str
    