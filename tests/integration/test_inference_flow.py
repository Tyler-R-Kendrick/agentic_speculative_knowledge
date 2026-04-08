from src.active_memory.models import WorkingItem
from src.persistence.pipeline import MutationPipeline
from src.retrieval.composer import RetrievalComposer
from src.sidecar.service import ManifoldSidecar
from src.terminus.adapter import TerminusMemoryRepository


class TestInferenceFlow:
    def test_pipeline_persists_ranked_inference_to_inference_branch(self, tmp_path):
        repo = TerminusMemoryRepository(url="http://localhost:9999")
        sidecar = ManifoldSidecar(model_id="sidecar-v1", geometry_version="geo-v1")
        pipeline = MutationPipeline(
            tmp_path,
            enable_terminus=True,
            terminus_repo=repo,
            sidecar=sidecar,
            enable_inference=True,
        )
        item = WorkingItem(
            item_type="observation",
            content="The auth service failed after a certificate rotation. The API started returning 401 errors.",
            session_id="sess-1",
        )

        result = pipeline.run(item, session_id="sess-1")

        assert result.success
        assert result.inference_candidates >= 1
        assert result.inference_branch == "inference/sess-1"
        stored = repo.query_inference_nodes("inference/sess-1")
        assert len(stored) >= 1
        assert stored[0]["ranking_model_id"] == "sidecar-v1"

    def test_sidecar_failure_does_not_block_trusted_persistence(self, tmp_path):
        class FailingSidecar:
            def rank_inference_candidates(self, request):
                raise RuntimeError("sidecar unavailable")

            def rank_facet_candidates(self, request):
                raise RuntimeError("sidecar unavailable")

        repo = TerminusMemoryRepository(url="http://localhost:9999")
        pipeline = MutationPipeline(
            tmp_path,
            enable_terminus=True,
            terminus_repo=repo,
            sidecar=FailingSidecar(),
            enable_inference=True,
        )
        item = WorkingItem(
            item_type="observation",
            content="The task queue drained after the workers were restarted.",
            session_id="sess-2",
        )

        result = pipeline.run(item, session_id="sess-2")

        assert result.success
        assert result.terminus_written >= 1
        assert result.inference_candidates >= 1
        assert result.ranked_inference_candidates == 0
        stored = repo.query_inference_nodes("inference/sess-2")
        assert stored[0]["ranking_score"] is None

    def test_retrieval_suppresses_speculative_results_by_default(self, tmp_path):
        repo = TerminusMemoryRepository(url="http://localhost:9999")
        sidecar = ManifoldSidecar(model_id="sidecar-v1", geometry_version="geo-v1")
        pipeline = MutationPipeline(
            tmp_path,
            enable_terminus=True,
            terminus_repo=repo,
            sidecar=sidecar,
            enable_inference=True,
        )
        item = WorkingItem(
            item_type="observation",
            content="Database writes slowed down after the index rebuild job started.",
            session_id="sess-3",
        )
        pipeline.run(item, session_id="sess-3")

        composer = RetrievalComposer(tmp_path, terminus_retriever=None, terminus_repo=repo)
        trusted = composer.retrieve(include_terminus=True)
        exploratory = composer.retrieve(
            include_terminus=True,
            include_speculative=True,
            inference_branch="inference/sess-3",
        )

        assert trusted["speculative_inference"] == []
        assert len(exploratory["speculative_inference"]) >= 1
