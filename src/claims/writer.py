import pathlib
from src.claims.models import Claim
from src.active_memory.serializers import JsonlSerializer


class ClaimWriter:
    def __init__(self, root_dir: pathlib.Path):
        self.root_dir = pathlib.Path(root_dir)
        self.claims_file = self.root_dir / "active" / "claims" / "extracted.jsonl"
        self.claims_file.parent.mkdir(parents=True, exist_ok=True)

    def write(self, claim: Claim) -> None:
        data = claim.model_dump(mode="json")
        JsonlSerializer.append_line(self.claims_file, data)

    def write_many(self, claims: list[Claim]) -> None:
        for claim in claims:
            self.write(claim)

    def read_all(self) -> list[Claim]:
        rows = JsonlSerializer.read_all(self.claims_file)
        return [Claim(**row) for row in rows]
