# -*- coding: utf-8 -*-
"""
run_all_tests.py
รัน Test ทั้งหมดของ VCS ต่อเนื่องกัน แล้วแสดงสรุปผลรวม
รัน: python run_all_tests.py
     python run_all_tests.py --phase 1          (เฉพาะ Phase 1)
     python run_all_tests.py --module cars      (เฉพาะโมดูลที่ระบุ)
"""

import sys, io, subprocess, time, argparse, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# รายการ Test Modules ทั้งหมด (เพิ่มเมื่อสร้าง script ใหม่)
# ---------------------------------------------------------------------------

MODULES = [
    {
        "phase": 1,
        "id":    "cars",
        "name":  "รถยนต์ (Cars)",
        "path":  "tests/phase1/run_car_tests.py",
    },
    {
        "phase": 1,
        "id":    "cartypes",
        "name":  "ประเภทรถยนต์ (Car Types)",
        "path":  "tests/phase1/run_cartype_tests.py",
    },
    {
        "phase": 1,
        "id":    "partners",
        "name":  "ข้อมูลคู่ค้า (Partners)",
        "path":  "tests/phase1/run_partner_tests.py",
    },
    {
        "phase": 1,
        "id":    "drivers",
        "name":  "พนักงานขับรถ (Drivers)",
        "path":  "tests/phase1/run_driver_tests.py",
    },
    # {
    #     "phase": 1,
    #     "id":    "postoffices",
    #     "name":  "หน่วยงาน/ไปรษณีย์ (Post Offices)",
    #     "path":  "tests/phase1/run_postoffice_tests.py",
    # },
]

# ---------------------------------------------------------------------------
# Parser output: ดึง PASS/FAIL/SKIP/ERROR count จาก output ของแต่ละ script
# ---------------------------------------------------------------------------

def parse_summary(output: str) -> dict:
    """ดึงตัวเลขสรุปจาก output line: 'ผ่าน: X  ล้มเหลว: Y  Error: Z  ข้าม: W'"""
    result = {"passed": 0, "failed": 0, "error": 0, "skipped": 0, "total": 0}
    for line in output.splitlines():
        if "ผ่าน:" in line and "ล้มเหลว:" in line:
            try:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "ผ่าน:":   result["passed"]  = int(parts[i+1])
                    if p == "ล้มเหลว:": result["failed"]  = int(parts[i+1])
                    if p == "Error:":  result["error"]   = int(parts[i+1])
                    if p == "ข้าม:":   result["skipped"] = int(parts[i+1])
            except (IndexError, ValueError):
                pass
        if "รวม:" in line:
            try:
                idx = line.index("รวม:") + 4
                result["total"] = int(line[idx:].split()[0])
            except (ValueError, IndexError):
                pass
    return result

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_module(module: dict, show_output: bool = True) -> dict:
    path = module["path"]
    if not os.path.exists(path):
        return {
            "module": module,
            "status": "MISSING",
            "output": f"ไม่พบไฟล์: {path}",
            "elapsed": 0,
            "summary": {"passed": 0, "failed": 0, "error": 0, "skipped": 0, "total": 0},
        }

    print(f"\n{'='*60}")
    print(f"  กำลังรัน: {module['name']}")
    print(f"  ไฟล์: {path}")
    print(f"{'='*60}")

    start = time.time()
    proc = subprocess.run(
        [sys.executable, path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.time() - start
    output  = proc.stdout + proc.stderr

    if show_output:
        print(output)

    summary = parse_summary(output)
    status  = "PASS" if proc.returncode == 0 else "FAIL"

    return {
        "module":  module,
        "status":  status,
        "output":  output,
        "elapsed": elapsed,
        "summary": summary,
        "returncode": proc.returncode,
    }

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="VCS Test Runner — รันทุก module")
    parser.add_argument("--phase",  type=int,  help="รันเฉพาะ phase (เช่น 1)")
    parser.add_argument("--module", type=str,  help="รันเฉพาะ module id (เช่น cars, cartypes)")
    parser.add_argument("--quiet",  action="store_true", help="ไม่แสดง output ระหว่างรัน")
    args = parser.parse_args()

    # กรอง modules ตาม argument
    modules = MODULES
    if args.phase:
        modules = [m for m in modules if m["phase"] == args.phase]
    if args.module:
        modules = [m for m in modules if m["id"] == args.module.lower()]

    if not modules:
        print("✗ ไม่พบ module ที่ตรงกับเงื่อนไข")
        sys.exit(1)

    print("=" * 60)
    print("  VCS Automated Test Suite — รันทุก Module")
    print(f"  จำนวน modules: {len(modules)}")
    print("=" * 60)

    # pre-warm: ping server ก่อนเริ่ม เพื่อ warm-up connection
    print("\n  [pre-warm: ตรวจสอบ server ก่อนเริ่มรัน...]")
    import urllib.request, urllib.error
    for _ in range(5):
        try:
            urllib.request.urlopen(
                "http://203.151.6.30/web-bms-vcsdev/login", timeout=10
            )
            print("  [pre-warm: server ตอบสนองแล้ว ✓]")
            break
        except Exception:
            print("  [pre-warm: รอ server... retry]")
            time.sleep(5)

    total_start = time.time()
    all_results = []

    for i, module in enumerate(modules):
        result = run_module(module, show_output=not args.quiet)
        all_results.append(result)
        # cooldown ระหว่าง module — ให้ browser ปิดและ server พัก
        if i < len(modules) - 1:
            print(f"\n  [cooldown 8 วินาที ก่อน module ถัดไป...]")
            time.sleep(8)

    # ---------------------------------------------------------------------------
    # สรุปผลรวมทุก Module
    # ---------------------------------------------------------------------------
    total_elapsed = time.time() - total_start

    print("\n" + "=" * 60)
    print("  สรุปผลการทดสอบทั้งหมด")
    print("=" * 60)

    total_passed  = 0
    total_failed  = 0
    total_error   = 0
    total_skipped = 0
    total_cases   = 0

    for r in all_results:
        s   = r["summary"]
        mod = r["module"]
        icon = "✓" if r["status"] == "PASS" else ("⚠" if r["status"] == "MISSING" else "✗")

        passed_str = f"PASS={s['passed']}"
        fail_str   = f"FAIL={s['failed']}" if s['failed'] > 0 else ""
        err_str    = f"ERR={s['error']}"   if s['error']  > 0 else ""
        skip_str   = f"SKIP={s['skipped']}"if s['skipped']> 0 else ""
        detail = "  ".join(filter(None, [passed_str, fail_str, err_str, skip_str]))

        print(f"  {icon} Phase{mod['phase']} | {mod['name']:<35} {detail}  ({r['elapsed']:.0f}s)")

        total_passed  += s["passed"]
        total_failed  += s["failed"]
        total_error   += s["error"]
        total_skipped += s["skipped"]
        total_cases   += s["total"]

    print("-" * 60)
    print(f"  รวมทั้งหมด:")
    print(f"    ✓ ผ่าน   : {total_passed}")
    print(f"    ✗ ล้มเหลว: {total_failed}")
    print(f"    ⚠ Error  : {total_error}")
    print(f"    ⊘ ข้าม   : {total_skipped}")
    print(f"    รวม TC   : {total_cases}")
    print(f"    เวลารวม  : {total_elapsed:.0f} วินาที ({total_elapsed/60:.1f} นาที)")
    print("=" * 60)

    if total_failed > 0 or total_error > 0:
        print("\n  ✗ มี Test ล้มเหลว — ตรวจสอบ output ด้านบน")
        sys.exit(1)
    else:
        print("\n  ✓ ทุก Test ผ่านหมด!")


if __name__ == "__main__":
    main()
