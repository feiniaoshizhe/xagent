from xagent.core.errors import ApiError
from xagent.db.models.business import SourceType
from xagent.domain.sources.repository import SourceRepository
from xagent.domain.sources.schemas import CreateSourceRequest
from xagent.domain.sources.service import SourceService


class DummySourceRepository(SourceRepository):
    def __init__(self) -> None:  # type: ignore[super-init-not-called]
        pass


def test_build_payload_defaults_for_github() -> None:
    service = SourceService(DummySourceRepository())

    payload = service._build_payload(  # noqa: SLF001
        SourceType.GITHUB,
        CreateSourceRequest(
            type=SourceType.GITHUB,
            label="Nuxt Docs",
            repo="nuxt/nuxt",
        ).model_dump(),
        None,
    )

    assert payload["base_path"] == "/docs"
    assert payload["branch"] == "main"
    assert payload["output_path"] == "nuxt-docs"


def test_build_payload_rejects_invalid_youtube() -> None:
    service = SourceService(DummySourceRepository())

    try:
        service._build_payload(  # noqa: SLF001
            SourceType.YOUTUBE,
            CreateSourceRequest(
                type=SourceType.YOUTUBE,
                label="Channel",
            ).model_dump(),
            None,
        )
    except ApiError as exc:
        assert exc.status_code == 400
        assert exc.message == "Validation error"
    else:  # pragma: no cover
        raise AssertionError("Expected ApiError")
