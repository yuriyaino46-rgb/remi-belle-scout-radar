from remibelle_radar.config import Settings
from remibelle_radar.service import RadarService
from remibelle_radar.sources import XSource


def test_paid_x_api_is_disabled_by_default(tmp_path):
    settings = Settings(
        database_path=tmp_path / "radar.db",
        x_bearer_token="configured-but-must-not-be-used",
    )

    source = RadarService(settings).sources()[0]

    assert isinstance(source, XSource)
    assert source.token is None

