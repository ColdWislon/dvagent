Fixture repo for cockpit.py self-test (uvm-gen `<ip>_verif/` layout).
Run from this directory:
  python3 ../cockpit.py fake_repo/uart_verif --root fake_repo --out /tmp/uart.html
  python3 ../cockpit.py --all --root fake_repo
uart_verif: all sources populated (review/lint/triage/session/vplan/
placeholder/exclusion) — expect pending=4, placeholders=1, clusters=2,
milestone M1, orphans VP-103 + VP-104 (VP-104 appears only in the
exclusion queue, which the tag scan deliberately does not read).
spi_verif: empty — expect "no data" states. Not real IPs; exclude from
CI scans. Delete generated *.html before committing.
