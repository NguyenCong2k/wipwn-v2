# wipwn v2 (Android/Termux)

Bản nâng cấp của `wipwn` tập trung vào:

- Database WPS/router mới
- Scanner có metadata và trạng thái WPS lock
- Logging ra file
- Quản lý session OneShot
- Report HTML/CSV/JSON
- Kiểm tra môi trường Android/Termux (`doctor`)
- Legacy engine vẫn giữ nguyên trong `legacy_oneshot.py`

> Chỉ dùng trên mạng bạn sở hữu hoặc có văn bản cho phép kiểm thử. Không dùng lên mạng của người khác.

## Cài đặt

```bash
pkg update && pkg upgrade -y
pkg install root-repo -y
pkg install git python wpa-supplicant pixiewps iw openssl tsu -y
git clone https://github.com/NguyenCong2k/wipwn-v2
cd wipwn-v2
chmod +x wipwn.sh
```

## Kiểm tra môi trường

```bash
./wipwn.sh doctor
```

Lệnh này kiểm tra: Android/Termux, root, `python`, `wpa_supplicant`, `pixiewps`, `iw`, interface, `HOME`, `TMPDIR`.

## Quét Wi-Fi/WPS

```bash
./wipwn.sh scan -i wlan0
```

Lưu JSON:

```bash
./wipwn.sh scan -i wlan0 --json scan.json
```

Scanner hiển thị:

- BSSID, SSID, bảo mật, signal
- Có WPS hay không
- WPS lock
- Model thiết bị
- Đánh giá Pixie Dust (`CRITICAL/HIGH/MEDIUM/LOW/UNKNOWN`)

Nếu không có `iw`, scanner fallback sang `termux-wifi-scaninfo`.

## Database

Xem thống kê:

```bash
./wipwn.sh db stats
```

Cập nhật từ upstream:

```bash
./wipwn.sh db update
```

Offline:

```bash
./wipwn.sh db update --offline
```

Nguồn dữ liệu:

- `vulnwsc.txt` (gộp WiFuX + OneShot + OneShot-Extended + fulvius31 fork)
- `database/router_models.json` (54 vendor, default PIN/credential, Pixie rating)
- `database/pins.csv` (3.336 cặp PIN/OUI)

## Session

```bash
./wipwn.sh sessions list
./wipwn.sh sessions export -o sessions.json
```

Session cũ của OneShot nằm ở `~/.wipwn/sessions/*.run`.

## Report

```bash
./wipwn.sh report --format html
./wipwn.sh report --format csv
./wipwn.sh report --format json
```

Mặc định ghi vào `reports/wipwn_report.<format>`.

Nguồn dữ liệu report:

- `reports/stored.csv`
- `store/wipwn_crack_data.txt`

## Attack (legacy engine)

Chỉ chạy khi bạn sở hữu mạng hoặc có văn bản cho phép:

```bash
./wipwn.sh attack --authorized -i wlan0 -b AA:BB:CC:DD:EE:FF -K
```

Hoặc dùng trực tiếp engine cũ:

```bash
su -c 'export HOME=/data/data/com.termux/files/home; export TMPDIR=/data/data/com.termux/files/usr/tmp; export PATH=/data/data/com.termux/files/usr/bin:$PATH; cd /data/data/com.termux/files/home/wipwn-v2 && python legacy_oneshot.py -i wlan0 -K'
```

## Logging

Log mặc định:

```text
~/.wipwn/logs/wipwn.log
```

## Cấu trúc

```text
wipwn.py                  CLI mới
legacy_oneshot.py         engine OneShot cũ (đã decode)
wipwn_tools/
  android.py              kiểm tra Termux/root/PATH
  database.py             database + update
  logger.py               logging
  report.py               report HTML/CSV/JSON
  scanner.py              scan + parse iw
  session.py              session OneShot
database/
  router_models.json
  pins.csv
  vuln_sources.json
vulnwsc.txt
```

## Lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| `wpa_supplicant: not found` | `pkg install wpa-supplicant -y`; chạy qua `wipwn.sh` để có PATH đúng |
| `Read-only file system: '//.wipwn'` | Chạy qua `wipwn.sh`, hoặc set `HOME` về Termux home |
| `Permission denied` | `chmod +x wipwn.sh` |
| Không thấy `wlan0` | `ip link show`; dùng `-i wlan1` nếu cần |
| Root lỗi | Dùng `su`/`tsu`; `wipwn.sh` không tự leo root |

## Giới hạn

WPS trên router đời mới thường bị tắt hoặc đã vá. Pixie Dust chỉ hiệu quả với một số chipset cũ; bruteforce WPS chậm và dễ bị lock. Code nâng cấp không làm thay đổi giới hạn vật lý/firmware.

## License

MIT, giữ license gốc của wipwn/OneShot.
