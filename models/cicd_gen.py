# models/cicd_gen.py
from __future__ import annotations
from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

Platform = Literal["github_actions", "jenkins"]
SCM = Literal["github", "gitlab", "bitbucket", "azure_repos", "other"]
Registry = Literal["ecr", "ghcr", "gcr", "acr", "dockerhub", "custom"]
DeployTarget = Literal["argocd", "helm", "kustomize", "kubectl", "ecs", "cloud_run", "none"]

class TriggerSpec(BaseModel):
    on_push: bool = True
    push_branches: List[str] = Field(default_factory=lambda: ["main"])
    pull_request: bool = True
    pr_branches: List[str] = Field(default_factory=lambda: ["*"])
    tags: List[str] = Field(default_factory=list)               # e.g. ["v*"]
    schedules: List[str] = Field(default_factory=list)          # list of cron strings
    paths_include: List[str] = Field(default_factory=list)
    paths_ignore: List[str] = Field(default_factory=list)
    manual_dispatch: bool = True

class RepositorySpec(BaseModel):
    scm: SCM = "github"
    default_branch: str = "main"
    protected_branches: List[str] = Field(default_factory=lambda: ["main"])
    require_pr_reviews: bool = True

class RegistryAuth(BaseModel):
    # Generic secrets; platform-specific are allowed too
    username_secret: Optional[str] = None
    password_secret: Optional[str] = None
    aws_access_key_id_secret: Optional[str] = None
    aws_secret_access_key_secret: Optional[str] = None
    aws_region: Optional[str] = None
    aws_role_to_assume: Optional[str] = None
    gcp_workload_identity_provider: Optional[str] = None
    gcp_service_account: Optional[str] = None
    acr_login_server: Optional[str] = None

class BuildSpec(BaseModel):
    docker_context: str = "."
    dockerfile_path: str = "Dockerfile"
    image_repository: str = "owner/app"        # e.g. 1234567890.dkr.ecr.us-east-1.amazonaws.com/myapp
    registry: Registry = "dockerhub"
    registry_hostname: Optional[str] = None    # required for custom
    tag_strategy: Literal["sha", "semver", "branch", "timestamp"] = "sha"
    cache: bool = True
    build_args: Dict[str, str] = Field(default_factory=dict)
    multi_arch: List[str] = Field(default_factory=list)         # e.g. ["linux/amd64","linux/arm64"]
    matrix: Dict[str, List[str]] = Field(default_factory=dict)  # generic axes
    auth: RegistryAuth = Field(default_factory=RegistryAuth)

class TestSpec(BaseModel):
    run_tests: bool = True
    commands: List[str] = Field(default_factory=lambda: ["pytest -q"])
    working_dir: Optional[str] = None
    coverage_threshold: Optional[float] = None

class ArgoCDSpec(BaseModel):
    app_name: str = "myapp"
    server: Optional[str] = None                # e.g. https://argocd.example.com
    namespace: str = "default"
    project: Optional[str] = None
    sync_flags: List[str] = Field(default_factory=lambda: ["--prune", "--timeout", "180"])

class HelmSpec(BaseModel):
    release: str = "myapp"
    chart: str = "./chart"
    namespace: str = "default"
    values_files: List[str] = Field(default_factory=list)
    set_values: Dict[str, str] = Field(default_factory=dict)

class KustomizeSpec(BaseModel):
    path: str = "./k8s/overlays/prod"
    namespace: Optional[str] = None

class KubectlSpec(BaseModel):
    manifests_path: str = "./k8s"
    namespace: Optional[str] = None

class DeploySpec(BaseModel):
    target: DeployTarget = "argocd"
    argocd: Optional[ArgoCDSpec] = None
    helm: Optional[HelmSpec] = None
    kustomize: Optional[KustomizeSpec] = None
    kubectl: Optional[KubectlSpec] = None

class EnvironmentStage(BaseModel):
    name: str = "prod"
    branch_filter: List[str] = Field(default_factory=lambda: ["main"])
    auto_deploy: bool = True
    requires_approval: bool = False
    approval_users: List[str] = Field(default_factory=list)

class NotificationsSpec(BaseModel):
    provider: Optional[Literal["slack", "teams"]] = None
    webhook_secret: Optional[str] = None
    channel: Optional[str] = None

class ConcurrencySpec(BaseModel):
    group: str = "ci-${{ github.ref || env.BRANCH_NAME }}"
    cancel_in_progress: bool = True

class SecuritySpec(BaseModel):
    # optional scanning steps toggles (lightweight)
    trivy_scan: bool = False
    snyk_scan: bool = False

class CISpec(BaseModel):
    platform: Platform = "github_actions"
    repository: RepositorySpec = Field(default_factory=RepositorySpec)
    triggers: TriggerSpec = Field(default_factory=TriggerSpec)
    build: BuildSpec = Field(default_factory=BuildSpec)
    tests: TestSpec = Field(default_factory=TestSpec)
    deploy: DeploySpec = Field(default_factory=DeploySpec)
    environments: List[EnvironmentStage] = Field(default_factory=lambda: [EnvironmentStage()])
    notifications: NotificationsSpec = Field(default_factory=NotificationsSpec)
    concurrency: ConcurrencySpec = Field(default_factory=ConcurrencySpec)
    security: SecuritySpec = Field(default_factory=SecuritySpec)
    workflow_name: str = "CI/CD"
    jenkins_agent_label: Optional[str] = "docker"   # used if platform=jenkins
    jenkinsfile_style: Literal["declarative", "scripted"] = "declarative"

class CICDRequest(BaseModel):
    description: str = Field(..., description="Plain English summary of what to build/deploy, clouds, clusters, etc.")
    spec: CISpec

class CICDResponse(BaseModel):
    pipeline: str
    notes: List[str] = Field(default_factory=list)
    filename: str = ".github/workflows/deploy.yml"
