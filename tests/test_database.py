from wipwn_tools import database


def test_stats_nonzero():
    stats = database.stats()
    assert stats["vuln_entries"] > 0
    assert stats["vendors"] > 0
    assert stats["pin_count"] > 0


def test_find_router():
    vendor, info = database.find_router("Archer C7")
    assert vendor == "TP-Link"
    assert info["pixie_dust"] is True
    assert "12345670" in info["default_pins"]
