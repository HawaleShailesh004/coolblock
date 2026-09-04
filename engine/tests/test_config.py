from engine.config import load_neighborhood_config


def test_neighborhood_config_loads() -> None:
    cfg = load_neighborhood_config()
    assert cfg.id == "edison-eastlake-phoenix-az"
    assert cfg.city == "Phoenix"
    assert cfg.target_epsg == 32612
    assert cfg.grid_resolution_m == 10


def test_bbox_is_sane() -> None:
    cfg = load_neighborhood_config()
    bbox = cfg.bbox_wgs84
    assert bbox.min_lon < bbox.max_lon
    assert bbox.min_lat < bbox.max_lat
    # Sanity: this bbox should sit within the Phoenix metro area.
    assert -113.0 < bbox.min_lon < -111.5
    assert 33.0 < bbox.min_lat < 34.0
