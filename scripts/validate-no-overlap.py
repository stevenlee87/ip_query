#!/usr/bin/env python3
"""验证各数据源区间两两不重叠（SQL 改写为'候选+JS校验'的前提）。"""
import csv
import gzip
import ipaddress
import sys
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def ip_to_int(s: str) -> int:
    try:
        return int(ipaddress.ip_address(s.strip()))
    except ValueError as exc:
        raise SystemExit(f"无效 IP 地址 {s!r}: {exc}") from exc


def check_ranges(name: str, rows):
    """rows: iterable of (start_int, end_int)。要求排序后 prev_end < next_start。"""
    prev_end = -1
    prev_start = -1
    count = 0
    overlaps = []
    for start, end in rows:
        if start > end:
            overlaps.append(f"行 {count}: start>end ({start} > {end})")
        if start <= prev_end:
            overlaps.append(
                f"行 {count}: 重叠 start={start} <= prev_end={prev_end} (prev_start={prev_start})"
            )
            if len(overlaps) >= 5:
                break
        prev_start, prev_end = start, max(prev_end, end) if start <= prev_end else end
        count += 1
    status = "✅ 不重叠" if not overlaps else f"❌ {overlaps[:5]}"
    print(f"{name}: {count} 行 → {status}")
    return not overlaps


def iter_simple_csv(path, version):
    try:
        f = open(path, newline="", encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"无法读取 {path}: {exc}") from exc
    with f:
        for row in csv.reader(f):
            if not row:
                continue
            start, end = row[0], row[1]
            try:
                addr = ipaddress.ip_address(start)
            except ValueError as exc:
                raise SystemExit(f"{path} 中存在无效 IP {start!r}: {exc}") from exc
            if addr.version != version:
                continue
            yield ip_to_int(start), ip_to_int(end)


def iter_dbip_city(path, version):
    try:
        f = gzip.open(path, "rt", encoding="utf-8", newline="")
    except OSError as exc:
        raise SystemExit(f"无法读取 {path}: {exc}") from exc
    with f:
        for row in csv.reader(f):
            if not row or len(row) < 2:
                continue
            start, end = row[0], row[1]
            try:
                addr = ipaddress.ip_address(start)
            except ValueError as exc:
                raise SystemExit(f"{path} 中存在无效 IP {start!r}: {exc}") from exc
            if addr.version != version:
                continue
            yield ip_to_int(start), ip_to_int(end)


def main():
    ok = True
    city_csv = RAW / "dbip-city" / "dbip-city-lite-2026-09.csv.gz"
    checks = [
        ("country v4 (iptoasn)", RAW / "iptoasn-country" / "iptoasn-country-ipv4.csv",
         lambda p: iter_simple_csv(p, 4)),
        ("country v6 (iptoasn)", RAW / "iptoasn-country" / "iptoasn-country-ipv6.csv",
         lambda p: iter_simple_csv(p, 6)),
        ("asn v4 (iptoasn)", RAW / "iptoasn-asn" / "iptoasn-asn-ipv4.csv",
         lambda p: iter_simple_csv(p, 4)),
        ("asn v6 (iptoasn)", RAW / "iptoasn-asn" / "iptoasn-asn-ipv6.csv",
         lambda p: iter_simple_csv(p, 6)),
        ("city v4 (dbip 2026-09)", city_csv, lambda p: iter_dbip_city(p, 4)),
        ("city v6 (dbip 2026-09)", city_csv, lambda p: iter_dbip_city(p, 6)),
    ]
    for name, path, it in checks:
        if not path.exists():
            print(f"{name}: ⚠️ 文件不存在 {path}")
            ok = False
            continue
        ok &= check_ranges(name, it(path))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
