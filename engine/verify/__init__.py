"""§7.2's verification layer: unit-aware thermal math (`units.py`), symbolic
calibration (`sensitivity.py`), and independent optimizer cross-checking
(`optimizer_crosscheck.py`). Built against the fallback `docs/adr/0002-*.md`
decided at Phase 0 (no Wolfram Cloud credential in hand): `pint`, `sympy`,
and a second real Python solver (HiGHS) stand in for Wolfram's `Quantity[]`,
`D`/`Solve`, and `NMaximize` respectively -- see `docs/adr/0021-*.md`."""
