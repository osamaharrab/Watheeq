#!/usr/bin/env python3
"""Verify the Watheeq assessment pack fixtures and record provenance.

Run from the pack root:

    python scripts/verify_pack.py

Writes PACK_VERIFICATION.json. Commit it. If a checksum does not match, you are not working from
the fixtures we issued; stop and email Big before continuing.
"""
import argparse, datetime, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = json.loads((Path(__file__).parent / 'pack_checksums.json').read_text(encoding='utf-8'))
KAGGLE_URL = 'https://www.kaggle.com/datasets/maddraf/sbanational-csv'


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaggle-csv', default='data/raw/SBAnational.csv')
    ap.add_argument('--out', default='PACK_VERIFICATION.json')
    args = ap.parse_args()

    results, ok = [], True
    for rel, want in sorted(EXPECTED.items()):
        p = ROOT / rel
        if not p.exists():
            results.append(dict(path=rel, status='MISSING')); ok = False; continue
        got = sha256(p)
        status = 'OK' if got == want else 'MODIFIED'
        if status != 'OK':
            ok = False
        results.append(dict(path=rel, status=status, sha256=got, size_bytes=p.stat().st_size))

    kag = ROOT / args.kaggle_csv
    if kag.exists():
        kaggle = dict(present=True, path=str(args.kaggle_csv), source_url=KAGGLE_URL,
                      size_bytes=kag.stat().st_size, sha256=sha256(kag))
    else:
        kaggle = dict(present=False, path=str(args.kaggle_csv), source_url=KAGGLE_URL,
                      note='Not downloaded at time of verification.')

    out = dict(
        pack='Watheeq candidate assessment pack',
        issued_by='Watheeq',
        verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        fixtures_ok=ok, fixtures=results, kaggle_dataset=kaggle,
        note='Supplied fixtures are synthetic material produced by Watheeq for candidate '
             'assessment. No figure in them is a real commercial, registry or statistical fact.')
    (ROOT / args.out).write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(dict(fixtures_ok=ok,
                          checked=len(results),
                          problems=[r['path'] for r in results if r['status'] != 'OK'],
                          kaggle_present=kaggle['present'],
                          written=args.out), indent=2))
    sys.exit(0 if ok else 2)


if __name__ == '__main__':
    main()
