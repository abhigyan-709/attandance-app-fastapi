# models/cli_gen.py
from typing import List, Literal, Optional, Dict
from pydantic import BaseModel, Field

OS = Literal["linux", "mac", "windows"]
Target = Literal["python_click", "bash", "powershell"]
Complexity = Literal["basic", "standard", "advanced"]

class CLISpec(BaseModel):
    os: OS = "linux"
    workdir: Optional[str] = None
    target: Target = "python_click"
    command_name: str = "tool"
    complexity: Complexity = "standard"

    # quick toggles
    common_flags: Dict[str, bool] = Field(
        default_factory=lambda: {"verbose": True, "dry_run": True, "log_file": False}
    )

    # freeform extras: one per line if coming from UI (we’ll pass already split list)
    # formats like: "--bucket:str:required:Target S3 bucket"
    # or "--days:int:7:How many days to keep"
    custom_options: List[str] = Field(default_factory=list)

    # ENV vars the tool may use: {"AWS_ACCESS_KEY_ID":"desc", ...}
    env_vars: Dict[str, str] = Field(default_factory=dict)

    # python-only libs mostly (click is implied when target=python_click)
    dependencies: List[str] = Field(default_factory=list)

    # optional scheduler snippet generation
    # {"type":"cron"|"systemd"|"schtasks", "expression":"0 3 * * *"}
    scheduler: Optional[Dict[str, str]] = None

class CLIGenerateRequest(BaseModel):
    description: str = Field(..., description="Plain-English CLI task description.")
    spec: CLISpec

class CLIResponse(BaseModel):
    code: str
    notes: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    usage: str = ""
    filename: str = "cli.py"
