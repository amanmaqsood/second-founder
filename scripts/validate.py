"""Validate the distributable skill and its unconfigured public template.

Uses only the Python standard library. This catches packaging mistakes and
common accidental private artifacts; it is not a substitute for reviewing a diff.
"""
import ast
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIRECTORY = Path("skills/second-founder")
IGNORED_DIRECTORIES = {".git", ".venv", "venv", "__pycache__", "node_modules"}
TEXT_SUFFIXES = {".md", ".json", ".py", ".yaml", ".yml", ".toml", ".txt"}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
)
LOCAL_HOME = re.compile(r"\b[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9_.-]+|/Users/[A-Za-z0-9_.-]+/")


def validate_repository(root):
    """Return actionable errors, without printing file contents or secrets."""
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    skill = root / SKILL_DIRECTORY
    main = skill / "SKILL.md"
    require(main.is_file(), "Missing skills/second-founder/SKILL.md")
    if main.is_file():
        text = main.read_text(encoding="utf-8-sig")
        header = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
        require(header is not None, "SKILL.md needs YAML frontmatter")
        if header:
            fields = dict(re.findall(r"^([a-z_-]+):\s*(.+)$", header.group(1), re.M))
            require(fields.get("name") == "second-founder", "Skill name must be second-founder")
            require(bool(fields.get("description", "").strip()), "Skill description is required")

    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in IGNORED_DIRECTORIES for part in relative.parts) or not path.is_file():
            continue
        if (path.suffix.lower() in {".sqlite", ".sqlite3", ".db", ".pem", ".p12", ".pfx"}
                or path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example")
                or ".second-founder" in relative.parts):
            errors.append(f"Private runtime or credential artifact must not ship: {relative}")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
            if path.suffix == ".json":
                json.loads(text)
            elif path.suffix == ".py":
                ast.parse(text, filename=str(relative))
        except (UnicodeError, ValueError, SyntaxError) as exc:
            errors.append(f"Invalid source file {relative}: {type(exc).__name__}")
            continue
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            errors.append(f"Possible embedded secret in {relative}; inspect and remove it")
        if LOCAL_HOME.search(text):
            errors.append(f"Machine-specific home path in {relative}")
        if path.suffix != ".md":
            continue
        # Ignore examples inside fenced code; validate actual inline Markdown links.
        prose = re.sub(r"^(```|~~~).*?^\1[^\n]*$", "", text, flags=re.M | re.S)
        for match in re.finditer(r"\]\((<[^>]*>|[^\s)]+)(?:\s+\"[^\"]*\")?\)", prose):
            target = match.group(1).strip("<>")
            if target.startswith("#") or urlsplit(target).scheme or target.startswith("//"):
                continue
            local = unquote(urlsplit(target).path)
            if not local:
                continue
            resolved = (path.parent / local).resolve()
            if not resolved.is_relative_to(root.resolve()):
                errors.append(f"Local reference leaves repository: {relative} -> {target}")
            elif not resolved.exists():
                errors.append(f"Broken local reference: {relative} -> {target}")

    template = skill / "assets/project-profile.json"
    try:
        profile = json.loads(template.read_text(encoding="utf-8-sig"))
        require(profile.get("setup_status") == "unconfigured", "Public template must be unconfigured")
        authority = profile.get("authority", {})
        require(authority.get("source") is None, "Template must not inherit owner authorization")
        require(authority.get("resource_bindings_verified") is False, "Template must have unverified resources")
        safe_categories = {"aggregate_analytics", "market_research", "local_drafting"}
        categories = authority.get("allowed_categories", [])
        require(isinstance(categories, list) and all(item in safe_categories for item in categories),
                "Template must not grant publication, deployment, installation, spending or outreach")
        require(authority.get("separately_enabled_categories") == [], "Template must not enable extra authority")
        require(profile.get("budget", {}).get("additional_spend_limit") == 0, "Template spending limit must be zero")
        automation = profile.get("automation", {})
        require(automation.get("enabled") is False, "Template automation must be inactive")
        for field in ("provider", "automation_id", "daily_time", "timezone", "runtime", "working_directory"):
            require(automation.get(field) is None, f"Template automation.{field} must be unset")
        project = profile.get("project", {})
        for field in ("id", "name", "workspace", "repository", "canonical_domain", "audience", "language", "timezone"):
            require(project.get(field) is None, f"Template project.{field} must be unset")
        for name, connection in profile.get("connections", {}).items():
            require(connection.get("status") == "unverified", f"Template connection {name} must be unverified")
            for field, value in connection.items():
                if field not in {"status", "analytics_read_only"}:
                    require(value is None, f"Template connection {name}.{field} must be unset")
        require(profile.get("connections", {}).get("database", {}).get("analytics_read_only") is True,
                "Database analytics must default to read-only")
        social = profile.get("social", {})
        require(social.get("brand_accounts") == [] and social.get("personal_amplification_accounts") == [],
                "Template social accounts must be empty")
        require(social.get("shared_calendar_database") is None, "Template must not bind a personal calendar")
        require(social.get("shared_account_limits_verified") is False, "Template account limits must be unverified")
        require(profile.get("state", {}).get("founder_database") is None, "Template must not bind a state database")
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        errors.append(f"Invalid public profile template: {type(exc).__name__}")
    return errors


if __name__ == "__main__":
    problems = validate_repository(ROOT)
    print(json.dumps({"ok": not problems, "errors": problems}, indent=2))
    raise SystemExit(bool(problems))
