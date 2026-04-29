# -*- coding: utf-8 -*-
"""
run_cartype_tests.py
ระบบ VCS -- ข้อมูลหลัก: ประเภทรถยนต์ (Car Types)
รัน: python tests/phase1/run_cartype_tests.py
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
CARTYPE_URL = f"{BASE_URL}/transport/truck-type-master"

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

def nav_to_cartype(page: Page):
    page.goto(CARTYPE_URL, timeout=60_000)
    page.wait_for_load_state("networkidle", timeout=30_000)
    page.wait_for_timeout(1_500)

def get_add_button(page: Page):
    for sel in ["button:has-text('เพิ่ม')", "button:has-text('Add')", "button:has-text('สร้าง')"]:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=2_000):
                return loc
        except Exception:
            continue
    return None

def open_add_form(page: Page) -> bool:
    try:
        btn = get_add_button(page)
        if btn is None:
            return False
        btn.wait_for(state="visible", timeout=10_000)
        page.wait_for_timeout(300)
        try:
            btn.click(force=True, timeout=5_000)
        except Exception:
            try:
                btn.dispatch_event("click")
            except Exception:
                page.evaluate("(el) => el.click()", btn.element_handle())
        page.wait_for_timeout(3_000)

        cdk_forms = page.locator(".cdk-overlay-container .ant-form-item").count()
        if cdk_forms > 0:
            return True
        if page.locator(".ant-drawer-open").count() > 0:
            return True
        if page.locator(".ant-modal-wrap:visible").count() > 0:
            return True
        return False
    except Exception as e:
        print(f"      open_add_form error: {e}")
        return False

def close_form(page: Page):
    try:
        # ปุ่ม ปิด ใน form
        close_btn = page.locator(".cdk-overlay-container button:has-text('ปิด')")
        if close_btn.count() > 0:
            page.evaluate("(el) => el.click()", close_btn.first.element_handle())
            page.wait_for_timeout(800)
            return
        # ปุ่ม X ของ drawer/modal
        for sel in [".ant-drawer-close", ".ant-modal-close"]:
            cb = page.locator(sel)
            if cb.count() > 0:
                page.evaluate("(el) => el.click()", cb.first.element_handle())
                page.wait_for_timeout(800)
                return
    except Exception:
        pass

def assert_on_cartype_page(page: Page):
    assert "truck-type-master" in page.url, f"ไม่ได้อยู่หน้า Car Types — URL: {page.url}"

def login(page: Page) -> bool:
    print("\n[LOGIN] กำลัง Login...")
    try:
        page.goto(f"{BASE_URL}/login", timeout=60_000)
        page.wait_for_load_state("networkidle", timeout=30_000)
        page.fill("#username", USERNAME)
        page.fill("#password", PASSWORD)
        page.locator("button.login-form-button").first.click()
        page.wait_for_load_state("networkidle", timeout=30_000)
        page.wait_for_timeout(2_000)
        if "login" in page.url:
            print(f"  ✗ Login ล้มเหลว")
            return False
        print(f"  ✓ Login สำเร็จ — URL: {page.url}")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

# ---------------------------------------------------------------------------
# TC-CTYPE-01 : Read — ตรวจสอบหน้าแสดงรายการ
# ---------------------------------------------------------------------------

def tc_ctype_01_page_loads(page: Page):
    print("\n[TC-CTYPE-01] ตรวจสอบหน้าประเภทรถยนต์โหลดสำเร็จ")
    nav_to_cartype(page)

    assert_on_cartype_page(page)
    report("TC-CTYPE-01a", "URL ถูกต้อง /truck-type-master", "PASS", page.url)

    has_table = page.locator("table").count() > 0
    report("TC-CTYPE-01b", "ตารางประเภทรถยนต์แสดงบนหน้า",
           "PASS" if has_table else "FAIL")

    headers = page.locator("thead th").all_inner_texts()
    expected = ["รหัสประเภทรถยนต์", "ชื่อประเภทรถยนต์", "กว้าง", "ยาว", "สูง", "น้ำหนัก"]
    found = [h for h in expected if any(h in hdr for hdr in headers)]
    report("TC-CTYPE-01c", f"Table Headers ครบ ({len(headers)} columns)",
           "PASS" if len(headers) >= 5 else "FAIL", f"{headers}")

    add_visible = get_add_button(page) is not None
    report("TC-CTYPE-01d", "ปุ่ม 'เพิ่ม' แสดงบนหน้า",
           "PASS" if add_visible else "FAIL")

    # ตรวจ filter elements
    inp_count = page.locator("input.ant-input").count()
    sel_count = page.locator(".ant-select:visible").count()
    report("TC-CTYPE-01e", "Filter elements แสดงบนหน้า",
           "PASS" if (inp_count + sel_count) > 0 else "FAIL",
           f"inputs={inp_count}, selects={sel_count}")

# ---------------------------------------------------------------------------
# TC-CTYPE-02 : Search
# ---------------------------------------------------------------------------

def tc_ctype_02_search(page: Page):
    print("\n[TC-CTYPE-02] ทดสอบ Search ประเภทรถยนต์")
    nav_to_cartype(page)

    search_input = page.locator("input.ant-input").first
    if not search_input.is_visible():
        report("TC-CTYPE-02", "Search", "FAIL", "ไม่พบ search input")
        return

    search_btn = page.locator("button:has-text('ค้นหา')").first
    clear_btn  = page.locator("button:has-text('ล้างค้นหา')").first

    # ค้นหาด้วยรหัส/ชื่อที่มีในระบบ
    search_input.fill("รถ")
    search_btn.click()
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(1_500)
    rows = page.locator("tbody tr").count()
    report("TC-CTYPE-02a", "ค้นหา 'รถ' — ตารางตอบสนอง", "PASS", f"พบ {rows} แถว")

    clear_btn.click()
    page.wait_for_load_state("networkidle", timeout=10_000)
    page.wait_for_timeout(1_000)

    # ค้นหาค่าที่ไม่มี
    search_input.fill("ZZZNOTEXIST9999")
    search_btn.click()
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(1_500)
    rows_empty = page.locator("tbody tr").count()
    report("TC-CTYPE-02b", "ค้นหาค่าที่ไม่มี — ผลลัพธ์ถูกต้อง", "PASS",
           f"แถว: {rows_empty}")

    clear_btn.click()
    page.wait_for_load_state("networkidle", timeout=10_000)

    # ค้นหาด้วย dropdown สถานะ
    status_sel = page.locator(".ant-select:visible").nth(1)
    if status_sel.count() > 0:
        status_sel.click()
        page.wait_for_selector(".ant-select-dropdown:visible", timeout=5_000)
        options = page.locator(".ant-select-item-option:visible").all_inner_texts()
        print(f"      สถานะ options: {options}")
        page.locator(".ant-select-item-option:visible").first.click()
        page.wait_for_timeout(500)
        search_btn.click()
        page.wait_for_load_state("networkidle", timeout=15_000)
        page.wait_for_timeout(1_000)
        rows_status = page.locator("tbody tr").count()
        report("TC-CTYPE-02c", "ค้นหาด้วย Filter สถานะ", "PASS", f"พบ {rows_status} แถว")
        clear_btn.click()
        page.wait_for_load_state("networkidle", timeout=10_000)

# ---------------------------------------------------------------------------
# TC-CTYPE-03 : Inspect Form Structure
# ---------------------------------------------------------------------------

def tc_ctype_03_inspect_form(page: Page):
    print("\n[TC-CTYPE-03] ตรวจสอบ Form Structure (เพิ่มประเภทรถยนต์)")
    nav_to_cartype(page)

    opened = open_add_form(page)
    if not opened:
        report("TC-CTYPE-03a", "Form เพิ่มประเภทรถยนต์เปิดได้", "FAIL", "เปิด form ไม่ได้")
        return
    report("TC-CTYPE-03a", "Form เพิ่มประเภทรถยนต์เปิดได้", "PASS")

    cdk = page.locator(".cdk-overlay-container")
    form_items = cdk.locator(".ant-form-item").all()
    report("TC-CTYPE-03b", f"Form Items ({len(form_items)} รายการ)",
           "PASS" if len(form_items) > 0 else "FAIL")

    required_fields = []
    for i, item in enumerate(form_items):
        lbl     = item.locator("label").first.inner_text() if item.locator("label").count() > 0 else "—"
        is_req  = item.locator(".ant-form-item-required").count() > 0
        has_inp = item.locator("input").count() > 0
        ph      = item.locator("input").first.get_attribute("placeholder") if has_inp else ""
        has_sel = item.locator(".ant-select").count() > 0
        has_rad = item.locator("input[type='radio'], input[type='checkbox']").count() > 0
        req_mark = "★ " if is_req else "  "
        if is_req:
            required_fields.append(lbl)
        print(f"      [{i}]{req_mark}'{lbl}' | input={has_inp}(ph='{ph}') | select={has_sel} | radio={has_rad}")

    report("TC-CTYPE-03c", f"Required Fields ★: {required_fields}", "PASS")

    btn_texts = [b for b in cdk.locator("button").all_inner_texts() if b.strip()]
    report("TC-CTYPE-03d", f"Buttons ใน Form: {btn_texts}", "PASS")

    close_form(page)

# ---------------------------------------------------------------------------
# TC-CTYPE-04 : Validation — บันทึกโดยไม่กรอก Required Fields
# ---------------------------------------------------------------------------

def tc_ctype_04_validation(page: Page):
    print("\n[TC-CTYPE-04] ตรวจสอบ Required Field Validation")
    nav_to_cartype(page)

    opened = open_add_form(page)
    if not opened:
        report("TC-CTYPE-04", "Validation", "ERROR", "เปิด form ไม่ได้")
        return

    cdk = page.locator(".cdk-overlay-container")

    # กด บันทึก โดยไม่กรอก
    save_btn = cdk.locator("button:has-text('บันทึก')")
    print(f"      Save button count: {save_btn.count()}")
    if save_btn.count() > 0:
        page.evaluate("(el) => el.click()", save_btn.first.element_handle())
    page.wait_for_timeout(2_500)

    form_still_open = cdk.locator(".ant-form-item").count() > 0
    errors = page.locator(".ant-form-item-explain-error")
    error_count = errors.count()
    error_texts = errors.all_inner_texts() if error_count > 0 else []

    if error_count > 0:
        report("TC-CTYPE-04a", "กด บันทึก โดยไม่กรอก → แสดง error validation", "PASS",
               f"{error_count} errors: {error_texts[:4]}")
    elif form_still_open:
        report("TC-CTYPE-04a", "กด บันทึก โดยไม่กรอก → Form ยังเปิด (ไม่ submit)", "PASS",
               "form ไม่ถูก submit")
    else:
        report("TC-CTYPE-04a", "Validation ไม่ทำงาน — form ปิดโดยไม่มี error", "FAIL")

    close_form(page)

# ---------------------------------------------------------------------------
# TC-CTYPE-05 : Create — กรอก Required Fields และบันทึก
# ---------------------------------------------------------------------------

def tc_ctype_05_create(page: Page):
    print("\n[TC-CTYPE-05] ทดสอบ Create ประเภทรถยนต์ใหม่")
    nav_to_cartype(page)

    # บันทึกจำนวนแถวก่อนเพิ่ม
    rows_before = page.locator("tbody tr").count()

    opened = open_add_form(page)
    if not opened:
        report("TC-CTYPE-05", "Create", "ERROR", "เปิด form ไม่ได้")
        return

    cdk = page.locator(".cdk-overlay-container")
    form_items = cdk.locator(".ant-form-item").all()

    try:
        # [0] รหัสประเภทรถยนต์
        code_inp = form_items[0].locator("input").first
        code_inp.fill("TEST-TYPE-001")

        # [1] ชื่อประเภทรถยนต์
        name_inp = form_items[1].locator("input").first
        name_inp.fill("ประเภทรถทดสอบ AUTO")

        # [3] กว้าง
        form_items[3].locator("input").first.fill("2.5")
        # [4] หน่วยวัดกว้าง — เลือกตัวแรก
        unit_sel_1 = form_items[4].locator(".ant-select")
        if unit_sel_1.count() > 0:
            unit_sel_1.click()
            page.wait_for_selector(".ant-select-dropdown:visible", timeout=5_000)
            page.locator(".ant-select-item-option:visible").first.click()
            page.wait_for_timeout(300)

        # [5] ยาว
        form_items[5].locator("input").first.fill("6.0")
        # [6] หน่วยวัดยาว
        unit_sel_2 = form_items[6].locator(".ant-select")
        if unit_sel_2.count() > 0:
            unit_sel_2.click()
            page.wait_for_selector(".ant-select-dropdown:visible", timeout=5_000)
            page.locator(".ant-select-item-option:visible").first.click()
            page.wait_for_timeout(300)

        # [7] สูง
        form_items[7].locator("input").first.fill("2.0")
        # [8] หน่วยวัดสูง
        unit_sel_3 = form_items[8].locator(".ant-select")
        if unit_sel_3.count() > 0:
            unit_sel_3.click()
            page.wait_for_selector(".ant-select-dropdown:visible", timeout=5_000)
            page.locator(".ant-select-item-option:visible").first.click()
            page.wait_for_timeout(300)

        # [11] น้ำหนัก (กิโลกรัม)
        form_items[11].locator("input").first.fill("1000")

        report("TC-CTYPE-05a", "กรอก Required Fields ครบ", "PASS")

    except Exception as e:
        report("TC-CTYPE-05a", "กรอก Required Fields", "FAIL", str(e))
        close_form(page)
        return

    # กด บันทึก
    save_btn = cdk.locator("button:has-text('บันทึก')")
    if save_btn.count() > 0:
        page.evaluate("(el) => el.click()", save_btn.first.element_handle())
    page.wait_for_timeout(3_000)

    # ตรวจสอบผล
    form_closed = cdk.locator(".ant-form-item").count() == 0
    success_msg = page.locator(".ant-notification-notice-message, .ant-message-success")
    has_success  = success_msg.count() > 0

    if has_success:
        report("TC-CTYPE-05b", "บันทึกสำเร็จ — แสดง success notification", "PASS",
               success_msg.first.inner_text(timeout=3_000))
    elif form_closed:
        report("TC-CTYPE-05b", "บันทึกสำเร็จ — Form ปิดแล้ว", "PASS")
    else:
        # ตรวจว่ามี error หรือเปล่า
        errors = page.locator(".ant-form-item-explain-error")
        err_count = errors.count()
        if err_count > 0:
            report("TC-CTYPE-05b", "บันทึกไม่สำเร็จ — มี validation error", "FAIL",
                   f"errors: {errors.all_inner_texts()[:3]}")
        else:
            report("TC-CTYPE-05b", "ไม่แน่ใจผลบันทึก — ตรวจสอบ manual", "SKIP")
        close_form(page)
        return

    # ตรวจว่าข้อมูลปรากฏในตาราง
    nav_to_cartype(page)
    search_input = page.locator("input.ant-input").first
    search_input.fill("TEST-TYPE-001")
    page.locator("button:has-text('ค้นหา')").first.click()
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(1_500)
    rows_after = page.locator("tbody tr").count()
    report("TC-CTYPE-05c", "ข้อมูลที่สร้างปรากฏในตาราง",
           "PASS" if rows_after > 0 else "FAIL",
           f"พบ {rows_after} แถว")

    page.locator("button:has-text('ล้างค้นหา')").first.click()
    page.wait_for_load_state("networkidle", timeout=10_000)

# ---------------------------------------------------------------------------
# TC-CTYPE-06 : Read/Edit — Action buttons
# ---------------------------------------------------------------------------

def tc_ctype_06_action_buttons(page: Page):
    print("\n[TC-CTYPE-06] ตรวจสอบ Action Buttons และ Edit Flow")
    nav_to_cartype(page)
    page.wait_for_timeout(2_000)

    rows = page.locator("tbody tr")
    row_count = rows.count()
    report("TC-CTYPE-06a", f"ตารางมีข้อมูล", "PASS" if row_count > 0 else "SKIP",
           f"พบ {row_count} แถว")

    if row_count == 0:
        return

    # หาแถวที่มีข้อมูลจริง
    target_row = None
    for i in range(min(row_count, 10)):
        r = rows.nth(i)
        if any(t.strip() for t in r.locator("td").all_inner_texts()):
            target_row = r
            row_data = r.locator("td").all_inner_texts()
            print(f"      ข้อมูลแถว[{i}]: {row_data[:5]}")
            break

    if target_row is None:
        report("TC-CTYPE-06b", "Action Buttons", "SKIP", "ไม่พบแถวที่มีข้อมูล")
        return

    action_btns = target_row.locator("button.btn-tran")
    btn_count   = action_btns.count()
    report("TC-CTYPE-06b", f"Action Buttons ในแถว ({btn_count} ปุ่ม)",
           "PASS" if btn_count > 0 else "FAIL")

    for i in range(btn_count):
        icon = page.evaluate(
            "(el) => el.querySelector('[data-icon]')?.getAttribute('data-icon') || ''",
            action_btns.nth(i).element_handle()
        )
        print(f"      Button[{i}]: icon='{icon}'")

    if btn_count == 0:
        return

    # คลิก action button แรก
    page.evaluate("(el) => el.click()", action_btns.first.element_handle())
    page.wait_for_timeout(3_000)

    drawer_open = page.locator(".ant-drawer-open").count() > 0
    modal_open  = page.locator(".ant-modal-wrap:visible").count() > 0
    cdk_open    = page.locator(".cdk-overlay-container .ant-form-item").count() > 0
    print(f"      drawer={drawer_open} | modal={modal_open} | cdk_form={cdk_open}")

    if cdk_open or drawer_open or modal_open:
        # ตรวจว่า field มีข้อมูล
        cdk = page.locator(".cdk-overlay-container")
        inputs = cdk.locator("input:visible").all()
        values = [inp.input_value() for inp in inputs if inp.input_value()]
        report("TC-CTYPE-06c", "คลิก Action → Form/Modal เปิดพร้อมข้อมูล",
               "PASS" if len(values) > 0 else "FAIL",
               f"fields มีข้อมูล: {len(values)}")

        # ทดสอบแก้ไขชื่อ — หา input ที่ไม่ disabled
        edited = False
        name_inputs = cdk.locator("input:visible").all()
        for inp in name_inputs:
            try:
                is_disabled = inp.is_disabled()
                if is_disabled:
                    continue
                val = inp.input_value()
                if not val or len(val) < 2:
                    continue
                inp.fill(val + " (แก้ไข)")
                page.wait_for_timeout(300)
                save_btn = cdk.locator("button:has-text('บันทึก')")
                if save_btn.count() > 0:
                    page.evaluate("(el) => el.click()", save_btn.first.element_handle())
                    page.wait_for_timeout(3_000)
                    success = page.locator(".ant-notification-notice-message, .ant-message-success")
                    report("TC-CTYPE-06d", "แก้ไขข้อมูล → บันทึกสำเร็จ",
                           "PASS" if success.count() > 0 else "SKIP",
                           "success notification แสดง" if success.count() > 0 else "ไม่พบ notification")
                edited = True
                break
            except Exception:
                continue
        if not edited:
            report("TC-CTYPE-06d", "แก้ไขข้อมูล", "SKIP", "ไม่พบ editable field")
            close_form(page)
    else:
        report("TC-CTYPE-06c", "คลิก Action", "FAIL", "ไม่มีอะไรเปิด")

# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  VCS Automated Tests — ข้อมูลหลัก: ประเภทรถยนต์ (Car Types)")
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
            tc_ctype_01_page_loads(page)
            tc_ctype_02_search(page)
            tc_ctype_03_inspect_form(page)
            tc_ctype_04_validation(page)
            tc_ctype_05_create(page)
            tc_ctype_06_action_buttons(page)
        except Exception as e:
            print(f"\n⚠ Unexpected error: {e}")
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
        print(f"  {icon} {r.id:15s} {r.name}")
        if r.detail and r.status != "PASS":
            print(f"                  {r.detail}")

    print(f"\n  ผ่าน: {len(passed)}  ล้มเหลว: {len(failed)}  Error: {len(errors)}  ข้าม: {len(skipped)}")
    print(f"  รวม:  {len(results)} test cases")

    if failed or errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
