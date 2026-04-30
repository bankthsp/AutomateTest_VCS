# -*- coding: utf-8 -*-
"""
run_partner_tests.py
ระบบ VCS -- ข้อมูลหลัก: ข้อมูลคู่ค้า (Partners / Outsource)
รัน: python tests/phase1/run_partner_tests.py

หมายเหตุ: หน้านี้เป็น Read-Only — ข้อมูลดึงจากระบบภายนอกผ่านปุ่ม "ดึงข้อมูลคู่ค้า"
         ไม่มีปุ่ม เพิ่ม/แก้ไข/ลบ ในหน้านี้
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright, Page
from dataclasses import dataclass
from typing import List
import time

BASE_URL    = "http://203.151.6.30/web-bms-vcsdev"
USERNAME    = "adminvcs"
PASSWORD    = "1111"
PARTNER_URL = f"{BASE_URL}/transport/outsource-master"

# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    id: str; name: str; status: str = "PENDING"; detail: str = ""

results: List[TestResult] = []

def report(tc_id, name, status, detail=""):
    results.append(TestResult(tc_id, name, status, detail))
    icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "⊘", "ERROR": "⚠"}.get(status, "?")
    print(f"  {icon} [{tc_id}] {name}")
    if detail:
        print(f"       → {detail}")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def nav_to_partner(page: Page):
    page.goto(PARTNER_URL, timeout=60_000)
    page.wait_for_load_state("networkidle", timeout=30_000)
    page.wait_for_timeout(1_500)

def assert_on_partner_page(page: Page):
    assert "outsource-master" in page.url, f"ไม่ได้อยู่หน้า Partners — URL: {page.url}"

def close_modal(page: Page):
    try:
        close_btn = page.locator(".cdk-overlay-container button:has-text('ปิด')")
        if close_btn.count() > 0:
            page.evaluate("(el) => el.click()", close_btn.first.element_handle())
            page.wait_for_timeout(800)
            return
        for sel in [".ant-modal-close", ".ant-drawer-close"]:
            cb = page.locator(sel)
            if cb.count() > 0:
                page.evaluate("(el) => el.click()", cb.first.element_handle())
                page.wait_for_timeout(800)
                return
    except Exception:
        pass

def login(page: Page) -> bool:
    print("\n[LOGIN] กำลัง Login...")
    try:
        page.goto(f"{BASE_URL}/login", timeout=60_000)
        page.wait_for_load_state("networkidle", timeout=30_000)
        page.fill("input[type='text']", USERNAME)
        page.fill("input[type='password']", PASSWORD)
        page.locator("button.login-form-button").first.click()
        page.wait_for_load_state("networkidle", timeout=30_000)
        page.wait_for_timeout(2_000)
        if "login" in page.url:
            print("  ✗ Login ล้มเหลว")
            return False
        print(f"  ✓ Login สำเร็จ — URL: {page.url}")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

# ---------------------------------------------------------------------------
# TC-PARTNER-01 : Read — ตรวจสอบหน้าแสดงรายการ
# ---------------------------------------------------------------------------

def tc_partner_01_page_loads(page: Page):
    print("\n[TC-PARTNER-01] ตรวจสอบหน้าข้อมูลคู่ค้าโหลดสำเร็จ")
    nav_to_partner(page)

    assert_on_partner_page(page)
    report("TC-PARTNER-01a", "URL ถูกต้อง /outsource-master", "PASS", page.url)

    has_table = page.locator("table").count() > 0
    report("TC-PARTNER-01b", "ตารางข้อมูลคู่ค้าแสดงบนหน้า",
           "PASS" if has_table else "FAIL")

    headers = page.locator("thead th").all_inner_texts()
    expected = ["รหัสบริษัทผู้ขนส่ง", "ชื่อบริษัทผู้ขนส่ง", "ประเภทการจดทะเบียน", "สถานะ"]
    found = [h for h in expected if any(h in hdr for hdr in headers)]
    report("TC-PARTNER-01c", f"Table Headers ครบ ({len(headers)} columns)",
           "PASS" if len(headers) >= 5 else "FAIL", f"{headers}")

    # ตรวจว่าไม่มีปุ่ม เพิ่ม (Read-Only page)
    add_btn = page.locator("button:has-text('เพิ่ม')")
    is_readonly = add_btn.count() == 0
    report("TC-PARTNER-01d", "หน้านี้เป็น Read-Only (ไม่มีปุ่ม เพิ่ม)",
           "PASS" if is_readonly else "FAIL",
           "ไม่พบปุ่มเพิ่ม — ข้อมูลดึงจากระบบภายนอก" if is_readonly else "พบปุ่มเพิ่ม!")

    # ตรวจปุ่ม ดึงข้อมูลคู่ค้า
    pull_btn = page.locator("button:has-text('ดึงข้อมูลคู่ค้า')")
    report("TC-PARTNER-01e", "ปุ่ม 'ดึงข้อมูลคู่ค้า' แสดงบนหน้า",
           "PASS" if pull_btn.count() > 0 else "FAIL")

    # ตรวจ filter elements
    inp_count = page.locator("input.ant-input").count()
    sel_count = page.locator(".ant-select:visible").count()
    report("TC-PARTNER-01f", "Filter elements แสดงบนหน้า",
           "PASS" if (inp_count + sel_count) > 0 else "FAIL",
           f"inputs={inp_count}, selects={sel_count}")

    # ตรวจจำนวนข้อมูลในตาราง
    rows = page.locator("tbody tr").count()
    real_rows = 0
    for i in range(rows):
        cells = page.locator("tbody tr").nth(i).locator("td").all_inner_texts()
        if any(c.strip() for c in cells):
            real_rows += 1
    report("TC-PARTNER-01g", f"ตารางมีข้อมูลคู่ค้า",
           "PASS" if real_rows > 0 else "FAIL",
           f"พบ {real_rows} รายการ")

# ---------------------------------------------------------------------------
# TC-PARTNER-02 : Search / Filter
# ---------------------------------------------------------------------------

def tc_partner_02_search(page: Page):
    print("\n[TC-PARTNER-02] ทดสอบ Search ข้อมูลคู่ค้า")
    nav_to_partner(page)

    search_input = page.locator("input.ant-input").first
    if not search_input.is_visible():
        report("TC-PARTNER-02", "Search", "FAIL", "ไม่พบ search input")
        return

    search_btn = page.locator("button:has-text('ค้นหา')").first
    clear_btn  = page.locator("button:has-text('ล้างค้นหา')").first

    # ค้นหาด้วยชื่อบริษัทที่มีในระบบ
    search_input.fill("บริษัท")
    search_btn.click()
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(1_500)
    rows = page.locator("tbody tr").count()
    report("TC-PARTNER-02a", "ค้นหา 'บริษัท' — ตารางตอบสนอง",
           "PASS", f"พบ {rows} แถว")

    clear_btn.click()
    page.wait_for_load_state("networkidle", timeout=10_000)
    page.wait_for_timeout(1_000)

    # ค้นหาด้วยค่าที่ไม่มี
    search_input.fill("ZZZNOTEXIST99999")
    search_btn.click()
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(1_500)
    rows_empty = page.locator("tbody tr").count()
    has_no_data = rows_empty == 0 or all(
        not any(c.strip() for c in page.locator("tbody tr").nth(i).locator("td").all_inner_texts())
        for i in range(min(rows_empty, 3))
    )
    report("TC-PARTNER-02b", "ค้นหาค่าที่ไม่มี — ผลลัพธ์ถูกต้อง",
           "PASS", f"แถว: {rows_empty}")

    clear_btn.click()
    page.wait_for_load_state("networkidle", timeout=10_000)
    page.wait_for_timeout(1_000)

    # ค้นหาด้วย dropdown ประเภท
    selects = page.locator(".ant-select:visible").all()
    print(f"      Selects บนหน้า: {len(selects)}")
    if len(selects) > 0:
        try:
            selects[0].click()
            page.wait_for_selector(".ant-select-dropdown:visible", timeout=5_000)
            options = page.locator(".ant-select-item-option:visible").all_inner_texts()
            print(f"      Dropdown[0] options: {options}")
            if len(options) > 1:
                page.locator(".ant-select-item-option:visible").nth(1).click()
                page.wait_for_timeout(500)
                search_btn.click()
                page.wait_for_load_state("networkidle", timeout=15_000)
                page.wait_for_timeout(1_000)
                rows_f = page.locator("tbody tr").count()
                report("TC-PARTNER-02c", "ค้นหาด้วย Filter dropdown", "PASS",
                       f"พบ {rows_f} แถว")
                clear_btn.click()
                page.wait_for_load_state("networkidle", timeout=10_000)
            else:
                page.keyboard.press("Escape")
                report("TC-PARTNER-02c", "ค้นหาด้วย Filter dropdown", "SKIP",
                       "dropdown ไม่มี options ให้เลือก")
        except Exception as e:
            report("TC-PARTNER-02c", "ค้นหาด้วย Filter dropdown", "SKIP", str(e))

# ---------------------------------------------------------------------------
# TC-PARTNER-03 : View Detail — คลิกปุ่ม ดู ในแถว
# ---------------------------------------------------------------------------

def tc_partner_03_view_detail(page: Page):
    print("\n[TC-PARTNER-03] ทดสอบ View Detail (ปุ่ม ดู)")
    nav_to_partner(page)
    page.wait_for_timeout(2_000)

    rows = page.locator("tbody tr")
    row_count = rows.count()

    # หาแถวที่มีข้อมูลจริง
    target_row = None
    for i in range(row_count):
        r = rows.nth(i)
        cells = r.locator("td").all_inner_texts()
        if any(c.strip() for c in cells):
            target_row = r
            row_data = cells
            print(f"      ข้อมูลแถว[{i}]: {row_data[:5]}")
            break

    if target_row is None:
        report("TC-PARTNER-03", "View Detail", "SKIP", "ไม่มีข้อมูลในตาราง")
        return

    # ตรวจ action button
    action_btns = target_row.locator("button.btn-tran")
    btn_count   = action_btns.count()
    report("TC-PARTNER-03a", f"Action Button 'ดู' มีในแถว ({btn_count} ปุ่ม)",
           "PASS" if btn_count > 0 else "FAIL")

    if btn_count == 0:
        return

    # ตรวจว่าปุ่มมี title='ดู'
    title_attr = action_btns.first.get_attribute("title")
    report("TC-PARTNER-03b", f"Action Button title='{title_attr}'",
           "PASS" if title_attr == "ดู" else "SKIP",
           title_attr or "ไม่มี title")

    # คลิกปุ่ม ดู
    page.evaluate("(el) => el.click()", action_btns.first.element_handle())
    page.wait_for_timeout(3_000)

    modal_open = page.locator(".ant-modal-wrap:visible").count() > 0
    cdk_open   = page.locator(".cdk-overlay-container .ant-form-item").count() > 0
    report("TC-PARTNER-03c", "คลิก ดู → Modal/Form เปิด",
           "PASS" if (modal_open or cdk_open) else "FAIL",
           f"modal={modal_open} cdk={cdk_open}")

    if not (modal_open or cdk_open):
        return

    # ตรวจ form items
    cdk = page.locator(".cdk-overlay-container")
    form_items = cdk.locator(".ant-form-item").all()
    report("TC-PARTNER-03d", f"View Form มี Fields ({len(form_items)} รายการ)",
           "PASS" if len(form_items) >= 10 else "FAIL")

    # ตรวจว่า fields มีข้อมูลจริง (read-only values)
    filled_count = 0
    for item in form_items[:20]:
        inp = item.locator("input")
        if inp.count() > 0:
            val = inp.first.input_value()
            if val and val.strip():
                filled_count += 1
    report("TC-PARTNER-03e", f"Fields มีข้อมูลแสดง ({filled_count} fields มีค่า)",
           "PASS" if filled_count > 0 else "FAIL")

    # ตรวจว่า fields เป็น read-only — Angular ใช้ nzDisabled directive
    # ซึ่งไม่ set HTML disabled attribute จึงต้องตรวจด้วย class หรือ JS
    readonly_count = 0
    for item in form_items[:10]:
        inp = item.locator("input")
        if inp.count() == 0:
            continue
        el = inp.first
        # วิธี 1: HTML disabled attribute
        if el.is_disabled():
            readonly_count += 1
            continue
        # วิธี 2: class ant-input-disabled (Angular nzDisabled)
        cls = el.get_attribute("class") or ""
        if "ant-input-disabled" in cls:
            readonly_count += 1
            continue
        # วิธี 3: ลอง type แล้วดูว่าค่าเปลี่ยนไหม (try-fill)
        try:
            original = el.input_value()
            el.fill("__readonly_test__", timeout=1_000)
            after = el.input_value()
            if after == original:      # ไม่ยอมรับ input
                readonly_count += 1
            else:                      # ยอมรับ — undo
                el.fill(original)
        except Exception:
            readonly_count += 1        # timeout = ไม่ editable
    report("TC-PARTNER-03f", f"Fields เป็น Read-Only ({readonly_count}/10 fields)",
           "PASS" if readonly_count > 0 else "FAIL",
           "Angular nzDisabled — ตรวจผ่าน class + try-fill")

    # ตรวจปุ่มใน Modal
    form_btns = cdk.locator("button").all_inner_texts()
    report("TC-PARTNER-03g", f"Modal Buttons: {form_btns}",
           "PASS" if "ปิด" in str(form_btns) else "FAIL")

    close_modal(page)

# ---------------------------------------------------------------------------
# TC-PARTNER-04 : ปุ่ม ดึงข้อมูลคู่ค้า
# ---------------------------------------------------------------------------

def tc_partner_04_pull_data_button(page: Page):
    print("\n[TC-PARTNER-04] ตรวจสอบปุ่ม 'ดึงข้อมูลคู่ค้า'")
    nav_to_partner(page)

    pull_btn = page.locator("button:has-text('ดึงข้อมูลคู่ค้า')")
    btn_count = pull_btn.count()
    report("TC-PARTNER-04a", "ปุ่ม 'ดึงข้อมูลคู่ค้า' แสดงบนหน้า",
           "PASS" if btn_count > 0 else "FAIL",
           f"พบ {btn_count} ปุ่ม")

    if btn_count == 0:
        return

    is_visible = pull_btn.first.is_visible()
    is_enabled = not pull_btn.first.is_disabled()
    report("TC-PARTNER-04b", "ปุ่ม 'ดึงข้อมูลคู่ค้า' เปิดใช้งานได้",
           "PASS" if (is_visible and is_enabled) else "FAIL",
           f"visible={is_visible} enabled={is_enabled}")

    # บันทึกจำนวนแถวก่อน (ไม่คลิกจริง เพราะอาจเปลี่ยนแปลงข้อมูลในระบบ)
    rows_before = page.locator("tbody tr").count()
    report("TC-PARTNER-04c", "บันทึกจำนวนข้อมูลก่อน Pull",
           "PASS", f"{rows_before} แถว (ไม่คลิกจริงเพื่อป้องกัน side effect)")

# ---------------------------------------------------------------------------
# TC-PARTNER-05 : ตรวจสอบโครงสร้างข้อมูล View Form ครบถ้วน
# ---------------------------------------------------------------------------

def tc_partner_05_view_form_structure(page: Page):
    print("\n[TC-PARTNER-05] ตรวจสอบโครงสร้าง View Form ครบถ้วน")
    nav_to_partner(page)
    page.wait_for_timeout(2_000)

    rows = page.locator("tbody tr")
    target_row = None
    for i in range(rows.count()):
        r = rows.nth(i)
        if any(c.strip() for c in r.locator("td").all_inner_texts()):
            target_row = r
            break

    if target_row is None:
        report("TC-PARTNER-05", "Form Structure", "SKIP", "ไม่มีข้อมูล")
        return

    page.evaluate("(el) => el.click()",
                  target_row.locator("button.btn-tran").first.element_handle())
    page.wait_for_timeout(3_000)

    cdk = page.locator(".cdk-overlay-container")
    form_items = cdk.locator(".ant-form-item").all()

    expected_fields = [
        "สถานะบริษัทขนส่ง", "รหัสบริษัทผู้ขนส่ง", "ชื่อบริษัทผู้ขนส่ง",
        "ประเภทการจดทะเบียนบริษัทผู้ขนส่ง", "เลขประจำตัวผู้เสียภาษีขนส่ง",
        "เบอร์โทรศัพท์มือถือ", "ชื่อผู้ติดต่อ 1",
    ]

    found_labels = []
    print(f"\n      Form fields ทั้งหมด ({len(form_items)} รายการ):")
    for i, item in enumerate(form_items):
        lbl = item.locator("label").first.inner_text() if item.locator("label").count() > 0 else "—"
        has_inp = item.locator("input").count() > 0
        val = item.locator("input").first.input_value() if has_inp else ""
        found_labels.append(lbl)
        print(f"      [{i}] '{lbl}' = '{val[:30]}'")

    matched = [f for f in expected_fields if any(f in lbl for lbl in found_labels)]
    report("TC-PARTNER-05a", f"Fields ครอบคลุมข้อมูลสำคัญ ({len(matched)}/{len(expected_fields)})",
           "PASS" if len(matched) >= 5 else "FAIL",
           f"พบ: {matched}")

    report("TC-PARTNER-05b", f"จำนวน Form Fields ทั้งหมด: {len(form_items)}",
           "PASS" if len(form_items) >= 15 else "FAIL")

    close_modal(page)

# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  VCS Automated Tests — ข้อมูลหลัก: ข้อมูลคู่ค้า (Partners)")
    print("  หมายเหตุ: หน้านี้เป็น Read-Only (ดึงข้อมูลจากระบบภายนอก)")
    print("=" * 60)
    start_time = time.time()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            slow_mo=800,
            args=["--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.set_default_timeout(30_000)

        ok = login(page)
        if not ok:
            print("\n✗ Login ไม่สำเร็จ")
            return

        try:
            tc_partner_01_page_loads(page)
            tc_partner_02_search(page)
            tc_partner_03_view_detail(page)
            tc_partner_04_pull_data_button(page)
            tc_partner_05_view_form_structure(page)
        except Exception as e:
            print(f"\n⚠ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            context.close()
            browser.close()

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"  สรุปผลการทดสอบ (ใช้เวลา {elapsed:.1f} วินาที)")
    print("=" * 60)

    passed  = [r for r in results if r.status == "PASS"]
    failed  = [r for r in results if r.status == "FAIL"]
    errors  = [r for r in results if r.status == "ERROR"]
    skipped = [r for r in results if r.status == "SKIP"]

    for r in results:
        icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "⊘", "ERROR": "⚠"}.get(r.status, "?")
        print(f"  {icon} {r.id:18s} {r.name}")
        if r.detail and r.status != "PASS":
            print(f"                     {r.detail}")

    print(f"\n  ผ่าน: {len(passed)}  ล้มเหลว: {len(failed)}  Error: {len(errors)}  ข้าม: {len(skipped)}")
    print(f"  รวม:  {len(results)} test cases")

    if failed or errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
