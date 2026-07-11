Fixture repo for dashboard.py self-test. Run from this directory:
  python3 ../dashboard.py fake_repo/uart_ip --root fake_repo --out /tmp/uart.html
  python3 ../dashboard.py --all --root fake_repo
uart_ip: all sources populated (review/lint/triage/session/vplan/placeholder/
exclusion) — expect pending=4, placeholders=1, clusters=2, milestone M1,
orphan VP-103. spi_ip: empty — expect "no data" states. Not real IPs; exclude
from CI scans. Delete generated *.html before committing.
