from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote

import yaml


LOGGER = logging.getLogger("agent_skills_mcp")
if not LOGGER.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    LOGGER.addHandler(_handler)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False

SUPPORTED_SKILL_ROOTS = (
    "skills",
    ".agents/skills",
    ".github/skills",
    ".claude/skills",
)
TEXT_ASSET_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".py", ".sh"}
TOKEN_RE = re.compile(r"[a-z0-9]+")
VERSION_RE = re.compile(r"\d+")


class SkillError(RuntimeError):
    pass


@dataclass(slots=True)
class SkillRecord:
    name: str
    description: str
    dir: str
    skill_md: str
    source_root: str
    body: str
    assets: dict[str, str]
    frontmatter: dict[str, Any]
    model_invocation_disabled: bool
    version_key: tuple[int, ...]
    freshness_key: tuple[Any, ...]
    identity_key: tuple[Any, ...]


def _repository_root() -> Path:
    env_root = os.getenv("AGENT_SKILLS_REPO_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def _bundled_root() -> Path | None:
    candidate = Path(__file__).resolve().parent / "skill_bundle"
    if candidate.is_dir():
        return candidate
    return None


def _candidate_skill_roots() -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []

    bundled_root = _bundled_root()
    if bundled_root is not None:
        for spec in SUPPORTED_SKILL_ROOTS:
            candidate = (bundled_root / spec).resolve()
            if candidate.is_dir():
                roots.append((f"bundled/{spec}", candidate))

    repo_root = _repository_root()
    override = os.getenv("AGENT_SKILLS_ROOTS")
    root_specs = [part.strip() for part in override.split(os.pathsep)] if override else list(SUPPORTED_SKILL_ROOTS)

    for spec in root_specs:
        if not spec:
            continue
        path = Path(spec)
        if not path.is_absolute():
            path = repo_root / spec
        path = path.resolve()
        try:
            path.relative_to(repo_root)
        except ValueError:
            continue
        if path.is_dir():
            try:
                label = path.relative_to(repo_root).as_posix()
            except ValueError:
                label = path.as_posix()
            candidate = (label, path)
            if candidate not in roots:
                roots.append(candidate)
    return roots


def _extract_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text.strip()

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text.strip()

    closing_index: int | None = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        raise SkillError("SKILL.md starts with frontmatter but is missing a closing --- delimiter")

    raw_frontmatter = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1:]).strip()
    try:
        parsed = yaml.safe_load(raw_frontmatter) or {}
    except yaml.YAMLError as exc:
        raise SkillError(f"Malformed SKILL.md frontmatter: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SkillError("SKILL.md frontmatter must be a YAML mapping")
    return parsed, body


def _version_key(frontmatter: dict[str, Any]) -> tuple[int, ...]:
    version_value = frontmatter.get("version")
    if version_value in (None, ""):
        metadata = frontmatter.get("metadata")
        if isinstance(metadata, dict):
            version_value = metadata.get("version")
    if version_value in (None, ""):
        return ()
    return tuple(int(part) for part in VERSION_RE.findall(str(version_value)))


def _is_truthy_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _model_invocation_disabled(frontmatter: dict[str, Any]) -> bool:
    metadata = frontmatter.get("metadata")
    sources = [frontmatter]
    if isinstance(metadata, dict):
        sources.append(metadata)

    for source in sources:
        for key in ("disable-model-invocation", "disable_model_invocation"):
            if key in source and _is_truthy_flag(source.get(key)):
                return True
    return False


def _iter_skill_files(skill_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            continue
        if skill_dir not in resolved.parents and resolved != skill_dir:
            continue
        files.append(path)
    return files


def _load_text_assets(skill_dir: Path) -> dict[str, str]:
    assets: dict[str, str] = {}
    for path in _iter_skill_files(skill_dir):
        if path.name == "SKILL.md" or path.suffix.lower() not in TEXT_ASSET_EXTENSIONS:
            continue
        try:
            assets[path.relative_to(skill_dir).as_posix()] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    return assets


def _iter_script_files(skill_dir: Path) -> list[Path]:
    script_files: list[Path] = []
    for path in _iter_skill_files(skill_dir):
        rel_path = path.relative_to(skill_dir)
        if not rel_path.parts or rel_path.parts[0] != "scripts":
            continue
        if "__pycache__" in rel_path.parts:
            continue
        if path.suffix.lower() != ".py":
            continue
        script_files.append(path)
    return script_files


def _skill_identity_key(skill_dir: Path) -> tuple[Any, ...]:
    entries: list[tuple[str, int, int, int]] = []
    for path in _iter_skill_files(skill_dir):
        try:
            stat_result = path.stat()
        except OSError:
            continue
        entries.append((path.relative_to(skill_dir).as_posix(), stat_result.st_dev, stat_result.st_ino, stat_result.st_size))
    return tuple(entries)


def _freshness_key(skill_dir: Path, frontmatter: dict[str, Any], root_rank: int) -> tuple[Any, ...]:
    newest_mtime_ns = 0
    file_count = 0
    for path in _iter_skill_files(skill_dir):
        try:
            stat_result = path.stat()
        except OSError:
            continue
        newest_mtime_ns = max(newest_mtime_ns, stat_result.st_mtime_ns)
        file_count += 1

    # Newer versions win first, then newest file activity, then richer skill dirs.
    return (_version_key(frontmatter), newest_mtime_ns, file_count, -root_rank, skill_dir.as_posix())


def _read_skill_dir(skill_dir: Path, source_root: str, root_rank: int, root_path: Path | None = None) -> SkillRecord:
    real_dir = skill_dir.resolve()
    effective_root = root_path.resolve() if root_path is not None else _repository_root()
    try:
        real_dir.relative_to(effective_root)
    except ValueError as exc:
        raise SkillError(f"{skill_dir} resolves outside the skill root {effective_root}") from exc
    skill_md = real_dir / "SKILL.md"
    if not skill_md.is_file():
        raise SkillError(f"{real_dir} is not a valid skill directory because SKILL.md is missing")

    frontmatter, body = _extract_frontmatter(skill_md.read_text(encoding="utf-8"))
    name = str(frontmatter.get("name") or real_dir.name).strip()
    description = str(frontmatter.get("description") or "").strip()
    assets = _load_text_assets(real_dir)
    return SkillRecord(
        name=name,
        description=description,
        dir=real_dir.as_posix(),
        skill_md=skill_md.as_posix(),
        source_root=source_root,
        body=body,
        assets=assets,
        frontmatter=frontmatter,
        model_invocation_disabled=_model_invocation_disabled(frontmatter),
        version_key=_version_key(frontmatter),
        freshness_key=_freshness_key(real_dir, frontmatter, root_rank),
        identity_key=_skill_identity_key(real_dir),
    )


def _better_skill(existing: SkillRecord, candidate: SkillRecord) -> SkillRecord:
    if candidate.dir == existing.dir or candidate.identity_key == existing.identity_key:
        return existing if existing.dir <= candidate.dir else candidate
    if candidate.freshness_key > existing.freshness_key:
        return candidate
    return existing


def _collect_skills(*, include_model_invocation_disabled: bool) -> list[SkillRecord]:
    skills_by_name: dict[str, SkillRecord] = {}
    for root_rank, (source_root, root_path) in enumerate(_candidate_skill_roots()):
        for child in sorted(root_path.iterdir()):
            if not child.is_dir():
                continue
            try:
                skill = _read_skill_dir(child, source_root, root_rank, root_path)
            except SkillError as exc:
                LOGGER.warning("Skipping invalid skill at %s: %s", child, exc)
                continue
            if not include_model_invocation_disabled and skill.model_invocation_disabled:
                continue
            existing = skills_by_name.get(skill.name)
            skills_by_name[skill.name] = skill if existing is None else _better_skill(existing, skill)
    return sorted(skills_by_name.values(), key=lambda skill: skill.name)


def _all_skills() -> list[SkillRecord]:
    return _collect_skills(include_model_invocation_disabled=True)


def _public_skills() -> list[SkillRecord]:
    return _collect_skills(include_model_invocation_disabled=False)


def _find_skill_by_name(name: str, *, include_model_invocation_disabled: bool = False) -> SkillRecord:
    lower_name = name.strip().lower()
    visible_skills = _all_skills() if include_model_invocation_disabled else _public_skills()
    for skill in visible_skills:
        if skill.name.lower() == lower_name:
            return skill

    for source_root, root_path in _candidate_skill_roots():
        candidate_dir = root_path / name
        if not candidate_dir.exists():
            continue
        skill_md = candidate_dir / "SKILL.md"
        if not skill_md.exists():
            raise SkillError(f"Skill '{name}' exists at {candidate_dir} but SKILL.md is missing")
        try:
            skill = _read_skill_dir(candidate_dir, source_root, 0, root_path)
        except SkillError as exc:
            raise SkillError(f"Skill '{name}' is invalid: {exc}") from exc
        if include_model_invocation_disabled or not skill.model_invocation_disabled:
            return skill
    raise SkillError(f"Skill '{name}' was not found under {_repository_root().as_posix()}")


def _tokenize(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


def _score_skill(skill: SkillRecord, query_tokens: set[str], cwd_tokens: set[str]) -> int:
    score = 0
    name_tokens = _tokenize(skill.name)
    desc_tokens = _tokenize(skill.description)
    body_tokens = _tokenize(skill.body)
    dir_tokens = _tokenize(skill.dir)

    score += 4 * len(query_tokens & name_tokens)
    score += 3 * len(query_tokens & desc_tokens)
    score += 1 * len(query_tokens & body_tokens)
    if cwd_tokens:
        score += 2 * len(cwd_tokens & dir_tokens)
        score += 1 * len(cwd_tokens & body_tokens)
    return score


def _resolve_entrypoint(skill: SkillRecord) -> Path:
    skill_dir = Path(skill.dir)
    script_files = _iter_script_files(skill_dir)
    if not script_files:
        raise SkillError(
            f"Skill '{skill.name}' has no runnable Python scripts under {skill_dir / 'scripts'}"
        )
    if len(script_files) > 1:
        choices = ", ".join(path.relative_to(skill_dir).as_posix() for path in script_files)
        raise SkillError(
            f"Skill '{skill.name}' has multiple runnable Python scripts; specify one explicitly: {choices}"
        )
    return script_files[0]


def _resolve_script_path(skill: SkillRecord, relative_path: str = "") -> Path:
    if not relative_path.strip():
        return _resolve_entrypoint(skill)

    skill_dir = Path(skill.dir)
    candidate = (skill_dir / relative_path).resolve()
    try:
        candidate.relative_to(skill_dir)
    except ValueError as exc:
        raise SkillError(f"Script path '{relative_path}' escapes skill '{skill.name}'") from exc

    if not candidate.exists() or not candidate.is_file() or candidate.suffix.lower() != ".py":
        raise SkillError(f"Script '{relative_path}' was not found as a Python file in skill '{skill.name}'")

    rel_path = candidate.relative_to(skill_dir)
    if not rel_path.parts or rel_path.parts[0] != "scripts":
        raise SkillError(f"Script '{relative_path}' must live under the skill's scripts/ directory")
    if "__pycache__" in rel_path.parts:
        raise SkillError(f"Script '{relative_path}' is not runnable")
    return candidate


def _normalize_argv(argv: list[str] | None) -> list[str]:
    if argv is None:
        return []
    if not isinstance(argv, list) or any(not isinstance(item, str) for item in argv):
        raise SkillError("argv must be a JSON array of strings")
    return list(argv)


def _resolve_python_executable() -> str:
    override = os.getenv("AGENT_SKILLS_PYTHON", "").strip()
    if override:
        return override

    repo_root = _repository_root()
    candidates = [
        repo_root / ".venv" / "bin" / "python",
        repo_root / ".venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    return sys.executable


def _skill_directory_tree(skill_dir: Path) -> str:
    lines = [f"Skill Directory: {skill_dir}"]
    for path in sorted(skill_dir.rglob("*")):
        if path == skill_dir:
            continue
        rel_path = path.relative_to(skill_dir).as_posix()
        suffix = "/" if path.is_dir() else ""
        lines.append(f"- {rel_path}{suffix}")
    return "\n".join(lines)


def read_skill_resource(name: str, relative_path: str = "") -> str | bytes:
    skill = _find_skill_by_name(name)
    skill_dir = Path(skill.dir)
    normalized = unquote(relative_path.strip()).strip("/")
    if not normalized:
        return _skill_directory_tree(skill_dir)

    resource_path = (skill_dir / normalized).resolve()
    try:
        resource_path.relative_to(skill_dir)
    except ValueError as exc:
        raise SkillError(f"Resource path '{relative_path}' escapes skill directory '{name}'") from exc
    if not resource_path.exists() or not resource_path.is_file():
        raise SkillError(f"Resource '{relative_path}' was not found in skill '{name}'")

    data = resource_path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data


def find_agent_skill(query: str, cwd: str = "") -> list[dict[str, Any]]:
    skills = _public_skills()
    if not skills:
        raise SkillError("No supported skill roots were found or no valid skills could be loaded")

    query_tokens = _tokenize(query)
    cwd_tokens = _tokenize(cwd)
    ranked = []
    for skill in skills:
        score = _score_skill(skill, query_tokens, cwd_tokens)
        ranked.append(
            {
                "name": skill.name,
                "description": skill.description,
                "score": score,
                "source_root": skill.source_root,
                "dir": skill.dir,
            }
        )

    ranked.sort(key=lambda item: (-item["score"], item["name"]))
    return ranked


def load_agent_skill(name: str) -> str:
    skill = _find_skill_by_name(name)
    sections = [
        f"Name: {skill.name}",
        f"Description: {skill.description}",
        f"Source Root: {skill.source_root}",
        f"Skill Path: {skill.dir}",
        "",
        "Instructions:",
        skill.body or "",
        "",
        "Bundled Assets:",
    ]
    if not skill.assets:
        sections.append("<none>")
    else:
        for rel_path, content in sorted(skill.assets.items()):
            sections.extend([f"--- {rel_path} ---", content, ""])
    return "\n".join(sections).rstrip()


def run_agent_skill(name: str, script_path: str = "", argv: list[str] | None = None) -> dict[str, Any]:
    skill = _find_skill_by_name(name)
    entrypoint = _resolve_script_path(skill, script_path)
    normalized_argv = _normalize_argv(argv)
    run_cwd = os.getenv("AGENT_SKILLS_RUN_CWD", "").strip() or skill.dir
    result = subprocess.run(
        [
            _resolve_python_executable(),
            str(entrypoint),
            *normalized_argv,
        ],
        cwd=run_cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def build_mcp(**fastmcp_settings: Any) -> Any:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("agent-skills", **fastmcp_settings)

    @mcp.tool(name="find_agent_skill")
    def find_agent_skill_tool(query: str, cwd: str = "") -> list[dict[str, Any]]:
        return find_agent_skill(query=query, cwd=cwd)

    @mcp.tool(name="load_agent_skill")
    def load_agent_skill_tool(name: str) -> str:
        return load_agent_skill(name=name)

    @mcp.tool(name="run_agent_skill")
    def run_agent_skill_tool(name: str, script_path: str = "", argv: list[str] | None = None) -> dict[str, Any]:
        return run_agent_skill(name=name, script_path=script_path, argv=argv)

    # The directory resource lists every file under the skill, and the file resource
    # accepts a URL-encoded relative path so nested files stay addressable.
    @mcp.resource("skill://{name}")
    def skill_directory_resource(name: str) -> str:
        content = read_skill_resource(name=name, relative_path="")
        return content.decode("utf-8") if isinstance(content, bytes) else content

    @mcp.resource("skill-file://{name}/{encoded_path}")
    def skill_file_resource(name: str, encoded_path: str) -> Any:
        return read_skill_resource(name=name, relative_path=encoded_path)

    return mcp


__all__ = [
    "SkillError",
    "SkillRecord",
    "SUPPORTED_SKILL_ROOTS",
    "TEXT_ASSET_EXTENSIONS",
    "_all_skills",
    "_candidate_skill_roots",
    "_extract_frontmatter",
    "_find_skill_by_name",
    "_resolve_python_executable",
    "build_mcp",
    "find_agent_skill",
    "load_agent_skill",
    "read_skill_resource",
    "run_agent_skill",
]
