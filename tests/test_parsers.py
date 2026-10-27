from wipwn_tools import scanner


SAMPLE = """
BSS 20:be:b4:c1:6c:f6(on wlan0)
\tfreq: 2437
\tsignal: -75.00 dBm
\tSSID: Linh
\tRSN:\t * Version: 1
\tWPA:\t * Version: 1
\tWPS:\t * Version: 1.0
\t\t * AP setup locked: 0x00000000
\t\t * Model: Ralink Wireless Access Point
\t\t * Model Number: RT2860
\t\t * Device name: RalinkAPS_0
BSS e8:43:68:7c:0d:84(on wlan0)
\tfreq: 2412
\tsignal: -81.00 dBm
\tSSID: Van Anh
\tRSN:\t * Version: 1
\tWPS:\t * Version: 1.0
\t\t * AP setup locked: 0x00000001
"""


def test_parse_iw_scan():
    nets = scanner.parse_iw_scan(SAMPLE)
    assert len(nets) == 2
    assert nets[0]["bssid"] == "20:be:b4:c1:6c:f6"
    assert nets[0]["ssid"] == "Linh"
    assert nets[0]["signal"] == -75.0
    assert nets[0]["wps"] is True
    assert nets[0]["wps_locked"] is False
    assert nets[0]["model"] == "Ralink Wireless Access Point"
    assert nets[1]["wps_locked"] is True
