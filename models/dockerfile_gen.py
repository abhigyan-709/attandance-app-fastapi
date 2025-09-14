# models/dockerfile.py
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict

# High-level app info the model can reason about
class AppSpec(BaseModel):
    runtime: Literal["python", "node", "go", "java", "dotnet", "rust", "php"] = "python"
    # e.g. "3.11", "20", "1.22", "17", "8.0", "1.78", "8.2"
    runtime_version: Optional[str] = None

    base_os: Literal["debian", "ubuntu", "alpine"] = "debian"
    package_manager: Literal["apt", "apk", "dnf", "yum", "none"] = "apt"

    # dependency managers / build tools
    use_poetry: bool = False
    use_pipenv: bool = False
    use_pnpm: bool = False
    use_yarn: bool = False
    build_tool: Optional[str] = None  # e.g. "maven", "gradle", "cargo", "composer"

    # app folders (relative to repo root)
    workdir: str = "/app"
    entrypoint: Optional[str] = None      # e.g. "uvicorn main:app --host 0.0.0.0 --port 8000"
    start_cmd: Optional[List[str]] = None # e.g. ["npm", "start"]

    # copy/install hints
    requirements_files: List[str] = Field(default_factory=list)  # ["requirements.txt","pyproject.toml"]
    lock_files: List[str] = Field(default_factory=list)          # ["poetry.lock","package-lock.json"]
    build_args: Dict[str, str] = Field(default_factory=dict)     # {"NODE_ENV":"production"}
    env: Dict[str, str] = Field(default_factory=dict)            # {"PYTHONDONTWRITEBYTECODE":"1"}
    extra_packages: List[str] = Field(default_factory=list)      # ["curl","bash","tzdata"]
    expose: List[int] = Field(default_factory=list)              # [8000, 3000]
    copy_paths: List[str] = Field(default_factory=list)          # ["./src","./main.py"]

    # image style
    use_multistage: bool = True
    add_healthcheck: bool = True
    nonroot_user: bool = True

class DockerfileRequest(BaseModel):
    description: str = Field(..., description="Plain English description of the project.")
    spec: AppSpec

class DockerfileResponse(BaseModel):
    dockerfile: str
    notes: List[str] = Field(default_factory=list)
    filename: str = "Dockerfile"
