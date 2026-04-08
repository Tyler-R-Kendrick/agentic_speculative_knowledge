import json
import yaml
import pathlib
from typing import Any


class YamlSerializer:
    @staticmethod
    def serialize(data: dict) -> str:
        return yaml.dump(data, sort_keys=True, allow_unicode=True, default_flow_style=False)

    @staticmethod
    def deserialize(text: str) -> dict:
        return yaml.safe_load(text) or {}

    @staticmethod
    def load(path: pathlib.Path) -> dict:
        text = pathlib.Path(path).read_text(encoding="utf-8")
        return YamlSerializer.deserialize(text)

    @staticmethod
    def save(path: pathlib.Path, data: dict) -> None:
        from src.active_memory.atomic_write import atomic_write_text
        content = YamlSerializer.serialize(data)
        atomic_write_text(path, content)


class JsonlSerializer:
    @staticmethod
    def serialize_line(data: dict) -> str:
        return json.dumps(data, ensure_ascii=False, default=str)

    @staticmethod
    def deserialize_line(line: str) -> dict:
        return json.loads(line.strip())

    @staticmethod
    def append_line(path: pathlib.Path, data: dict) -> None:
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = JsonlSerializer.serialize_line(data) + "\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)

    @staticmethod
    def read_all(path: pathlib.Path) -> list[dict]:
        path = pathlib.Path(path)
        if not path.exists():
            return []
        lines = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(JsonlSerializer.deserialize_line(line))
        return lines


class MarkdownFrontmatterSerializer:
    @staticmethod
    def serialize(frontmatter: dict, body: str = "") -> str:
        fm_text = yaml.dump(frontmatter, sort_keys=True, allow_unicode=True, default_flow_style=False)
        return f"---\n{fm_text}---\n\n{body}"

    @staticmethod
    def deserialize(text: str) -> tuple[dict, str]:
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2].lstrip("\n")
                return frontmatter, body
        return {}, text
