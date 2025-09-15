# services/cicd_gen.py
import os
import re
from typing import List, Tuple
import google.generativeai as genai
from models.cicd_gen import CICDRequest, CICDResponse, CISpec

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SYSTEM_INSTRUCTIONS = """You generate production-ready CI/CD pipeline files.
You support GitHub Actions YAML and Jenkins Jenkinsfile (Declarative or Scripted).
Follow these rules:
- Only output ONE code block: 
  - GitHub Actions: use ```yaml
  - Jenkins: use ```groovy
- After the code block, output a short rationale inside ```notes with 3–10 concise bullets.
- Respect triggers (push/PR/tags/schedules), branch filters, paths include/exclude, manual dispatch.
- Implement multi-stage Docker build (BuildKit) and image tagging strategy (sha/semver/branch/timestamp).
- Log in to registries (ECR/GHCR/GCR/ACR/Docker Hub/custom) using provided secret names or cloud logins.
- Run tests when requested; fail pipeline on test failure. Allow optional coverage thresholds.
- Support matrix builds when requested.
- Add concurrency/group settings when provided.
- For deploy:
  - ArgoCD: use the Argo CD CLI (`argocd login` if needed; or assume SSO configured) then `argocd app sync`.
  - Helm: `helm upgrade --install` with values files and --set key=val pairs.
  - Kustomize: `kubectl apply -k <path>`.
  - Kubectl: `kubectl apply -f <manifests>`.
- Add environment-specific jobs with branch filters and optional manual approvals (GitHub envs or Jenkins input step).
- Keep secrets referenced as env/with: ${{ secrets.NAME }} or Jenkins credentials() helpers; DO NOT invent secret values.
- For AWS ECR, use official setup steps (aws-actions/configure-aws-credentials + aws ECR login) or Jenkins with withAWS/cli login.
- Keep YAML/Groovy syntactically valid; no trailing commentary inside code block.
- Keep workflow fast & minimal but realistic.
"""

PROMPT_TEMPLATE = """Project:
{desc}

Structured spec (JSON-like):
{spec}

Generate a {platform} pipeline that:
- Builds a Docker image from {dockerfile} (context {context}) and pushes to {image_repo}.
- Uses tag strategy: {tag_strategy}; multi-arch: {multi_arch}; cache: {cache}.
- Triggers: push={push}, pr={pr}, tags={tags}, schedules={schedules}, branches={branches}.
- Runs tests: {tests}; commands={test_cmds}; coverage={coverage}.
- Deployment target: {deploy_target}; env stages: {[e.name for e in envs]}.
- Notifications: {notify}; Concurrency: group='{concurrency_group}', cancel_in_progress={cancel_in_progress}.
- Registry: {registry} (host={reg_host}); registry auth/secrets present where provided.

Output ONLY the pipeline file in a single fenced code block (yaml for GHA, groovy for Jenkins), then a ```notes block.
"""

def _extract_blocks(text: str) -> Tuple[str, List[str]]:
    pipeline = ""
    notes: List[str] = []

    # Try yaml or groovy blocks
    m = re.search(r"```(yaml|yml|groovy)\s+([\s\S]*?)```", text, re.IGNORECASE)
    if m:
        pipeline = m.group(2).strip()
    else:
        # fallback: any fenced code
        m2 = re.search(r"```[\w]*\s+([\s\S]*?)```", text)
        pipeline = (m2.group(1).strip() if m2 else text.strip())

    n = re.search(r"```notes\s+([\s\S]*?)```", text, re.IGNORECASE)
    if n:
        raw = n.group(1).strip()
        for line in raw.splitlines():
            line = line.strip("-•* \t")
            if line:
                notes.append(line)

    return pipeline, notes

def _default_filename(spec: CISpec) -> str:
    return "Jenkinsfile" if spec.platform == "jenkins" else ".github/workflows/deploy.yml"

def generate_cicd(req: CICDRequest) -> CICDResponse:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not configured")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_INSTRUCTIONS,
    )

    s = req.spec
    prompt = PROMPT_TEMPLATE.format(
        desc=req.description,
        spec=s.model_dump(),
        platform=("Jenkinsfile" if s.platform == "jenkins" else "GitHub Actions workflow"),
        dockerfile=s.build.dockerfile_path,
        context=s.build.docker_context,
        image_repo=s.build.image_repository,
        tag_strategy=s.build.tag_strategy,
        multi_arch=", ".join(s.build.multi_arch) if s.build.multi_arch else "none",
        cache=s.build.cache,
        push=s.triggers.on_push,
        pr=s.triggers.pull_request,
        tags=", ".join(s.triggers.tags) if s.triggers.tags else "none",
        schedules=", ".join(s.triggers.schedules) if s.triggers.schedules else "none",
        branches=", ".join(s.triggers.push_branches),
        tests=s.tests.run_tests,
        test_cmds=", ".join(s.tests.commands),
        coverage=(s.tests.coverage_threshold if s.tests.coverage_threshold is not None else "none"),
        deploy_target=s.deploy.target,
        envs=s.environments,
        notify=(s.notifications.provider or "none"),
        concurrency_group=s.concurrency.group,
        cancel_in_progress=s.concurrency.cancel_in_progress,
        registry=s.build.registry,
        reg_host=s.build.registry_hostname or "default",
    )

    resp = model.generate_content(prompt)
    text = resp.text or ""
    pipeline, notes = _extract_blocks(text)
    filename = _default_filename(s)

    # tiny sanity checks
    if s.platform == "github_actions" and "jobs:" not in pipeline:
        notes.insert(0, "Generated workflow missing 'jobs:'—please review.")
    if s.platform == "jenkins" and "pipeline {" not in pipeline and "node {" not in pipeline:
        notes.insert(0, "Generated Jenkinsfile missing a valid pipeline block—please review.")

    return CICDResponse(pipeline=pipeline, notes=notes, filename=filename)
