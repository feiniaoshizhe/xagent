from xagent.db.models.business import CitationFormat, ResponseStyle
from xagent.domain.agent_config.repository import AgentConfigRepository
from xagent.domain.agent_config.service import AgentConfigService


class DummyAgentConfigRepository(AgentConfigRepository):
    def __init__(self) -> None:  # type: ignore[super-init-not-called]
        pass


def test_default_agent_config_shape() -> None:
    service = AgentConfigService(DummyAgentConfigRepository())
    config = service._default_config()  # noqa: SLF001

    assert config.id == "default"
    assert config.response_style == ResponseStyle.CONCISE
    assert config.citation_format == CitationFormat.INLINE
    assert config.max_steps_multiplier == 1.0
    assert config.temperature == 0.7
