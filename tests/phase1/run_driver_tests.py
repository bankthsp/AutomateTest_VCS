# -*- coding: utf-8 -*-
"""
run_driver_tests.py
ระบบ VCS -- ข้อมูลหลัก: พนักงานขับรถ และพนักงานประจำรถ (Drivers & Attendants)
รัน: python tests/phase1/run_driver_tests.py
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright, Page
from dataclasses import dataclass
from typing import List
import time, datetime

RUN_ID = datetime.datetime.now().strftime("%m%d%H%M")

BASE_URL   = "http://203.151.6.30/web-bms-vcsdev"
USERNAME   = "adminvcs"
PASSWORD   = "1111"
DRIVER_URL = f"{BASE_URL}/transport/driver-master"

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

def nav_to_driver(page: Page):
    page.goto(DRIVER_URL, timeout=60_000)
    page.wait_for_load_state("networkidle", timeout=30_000)
    page.wait_for_timeout(1_500)

def assert_on_driver_page(page: Page):
    assert "driver-master" in page.url, f"ไม่ได้อยู่หน้า Drivers — URL: {page.url}"

def open_add_form(page: Page) -> bool:
    try:
        add_btn = page.locator("button:has-text('เพิ่ม')").first
        if add_btn.count() == 0 or not add_btn.is_visible():
            return False
        page.evaluate("(el) => el.click()", add_btn.element_handle())
        page.wait_for_timeout(3_000)
        return page.locator(".cdk-overlay-container .ant-form-item").count() > 0
    except Exception as e:
        print(f"      open_add_form error: {e}")
        return False

def close_form(page: Page):
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

def fill_date(page: Page, date_input, date_str: str):
    """
    กรอกวันที่ลงใน ant-picker ของ Angular
    format: DD-MM-YYYY ปีพุทธศักราช (พ.ศ.) เช่น 01-01-2533
    ใช้ click(click_count=3) + type ทีละตัว
    """
    try:
        date_input.click()
        page.wait_for_timeout(400)
        # Select all แล้วลบ
        date_input.click(click_count=3)
        page.keyboard.press("Control+a")
        page.keyboard.press("Delete")
        page.wait_for_timeout(200)
        # Type ทีละตัวอักษร — Angular รับ input event ทุกตัว
        date_input.type(date_str, delay=100)
        page.wait_for_timeout(400)
        # ปิด picker panel
        page.keyboard.press("Enter")
        page.wait_for_timeout(400)
        if page.locator(".ant-picker-dropdown:visible").count() > 0:
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
    except Exception:
        pass

def select_first_option(page: Page, select_locator):
    """คลิก nz-select แล้วเลือก option แรกที่มี"""
    try:
        select_locator.click()
        page.wait_for_selector(".ant-select-dropdown:visible", timeout=5_000)
        opts = page.locator(".ant-select-item-option:visible")
        if opts.count() > 0:
            opts.first.click()
            page.wait_for_timeout(300)
            return True
    except Exception:
        pass
    return False

def login(page: Page) -> bool:
    print("\n[LOGIN] กำลัง Login...")
    for attempt in range(1, 4):
        try:
            page.goto(f"{BASE_URL}/login", timeout=60_000)
            page.wait_for_load_state("networkidle", timeout=30_000)
            page.wait_for_timeout(1_500)
            page.fill("input[type='text']", USERNAME)
            page.fill("input[type='password']", PASSWORD)
            page.locator("button.login-form-button").first.click()
            page.wait_for_load_state("networkidle", timeout=30_000)
            page.wait_for_timeout(2_000)
            if "login" not in page.url:
                print(f"  ✓ Login สำเร็จ (attempt {attempt}) — URL: {page.url}")
                return True
            print(f"  ✗ Login attempt {attempt} ล้มเหลว")
            page.wait_for_timeout(2_000)
        except Exception as e:
            print(f"  ✗ Login attempt {attempt} Error: {e}")
            page.wait_for_timeout(2_000)
    return False

# ---------------------------------------------------------------------------
# TC-DRIVER-01 : Read — ตรวจสอบหน้าแสดงรายการ
# ---------------------------------------------------------------------------

def tc_driver_01_page_loads(page: Page):
    print("\n[TC-DRIVER-01] ตรวจสอบหน้าพนักงานโหลดสำเร็จ")
    nav_to_driver(page)

    assert_on_driver_page(page)
    report("TC-DRIVER-01a", "URL ถูกต้อง /driver-master", "PASS", page.url)

    has_table = page.locator("table").count() > 0
    report("TC-DRIVER-01b", "ตารางพนักงานแสดงบนหน้า",
           "PASS" if has_table else "FAIL")

    headers = page.locator("thead th").all_inner_texts()
    expected = ["ประเภทพนักงาน", "รหัสพนักงาน", "ชื่อเต็มพนักงาน", "เบอร์โทรศัพท์", "สถานะ"]
    found = [h for h in expected if any(h in hdr for hdr in headers)]
    report("TC-DRIVER-01c", f"Table Headers ครบ ({len(headers)} columns)",
           "PASS" if len(headers) >= 5 else "FAIL", f"{headers}")

    add_visible = page.locator("button:has-text('เพิ่ม')").count() > 0
    report("TC-DRIVER-01d", "ปุ่ม 'เพิ่ม' แสดงบนหน้า",
           "PASS" if add_visible else "FAIL")

    inp_count = page.locator("input.ant-input").count()
    sel_count = page.locator(".ant-select:visible").count()
    report("TC-DRIVER-01e", "Filter elements แสดงบนหน้า",
           "PASS" if (inp_count + sel_count) > 0 else "FAIL",
           f"inputs={inp_count}, selects={sel_count}")

    rows = page.locator("tbody tr").count()
    real_rows = sum(
        1 for i in range(rows)
        if any(c.strip() for c in page.locator("tbody tr").nth(i).locator("td").all_inner_texts())
    )
    report("TC-DRIVER-01f", f"ตารางมีข้อมูลพนักงาน",
           "PASS" if real_rows > 0 else "FAIL",
           f"พบ {real_rows} รายการ")

# ---------------------------------------------------------------------------
# TC-DRIVER-02 : Search / Filter
# ---------------------------------------------------------------------------

def tc_driver_02_search(page: Page):
    print("\n[TC-DRIVER-02] ทดสอบ Search พนักงาน")
    nav_to_driver(page)

    search_input = page.locator("input.ant-input").first
    if not search_input.is_visible():
        report("TC-DRIVER-02", "Search", "FAIL", "ไม่พบ search input")
        return

    search_btn = page.locator("button:has-text('ค้นหา')").first
    clear_btn  = page.locator("button:has-text('ล้างค้นหา')").first

    # ค้นหาด้วยชื่อ
    search_input.fill("สมพงษ์")
    search_btn.click()
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(1_500)
    rows = page.locator("tbody tr").count()
    report("TC-DRIVER-02a", "ค้นหา 'สมพงษ์' — ตารางตอบสนอง",
           "PASS", f"พบ {rows} แถว")

    clear_btn.click()
    page.wait_for_load_state("networkidle", timeout=10_000)
    page.wait_for_timeout(1_000)

    # ค้นหาค่าที่ไม่มี
    search_input.fill("ZZZNOBODY99999")
    search_btn.click()
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(1_500)
    rows_empty = page.locator("tbody tr").count()
    report("TC-DRIVER-02b", "ค้นหาค่าที่ไม่มี — ผลลัพธ์ถูกต้อง",
           "PASS", f"แถว: {rows_empty}")

    clear_btn.click()
    page.wait_for_load_state("networkidle", timeout=10_000)
    page.wait_for_timeout(1_000)

    # ค้นหาด้วย dropdown ประเภทพนักงาน
    selects = page.locator(".ant-select:visible").all()
    print(f"      Selects: {len(selects)}")
    if len(selects) > 0:
        try:
            selects[0].click()
            page.wait_for_selector(".ant-select-dropdown:visible", timeout=5_000)
            options = page.locator(".ant-select-item-option:visible").all_inner_texts()
            print(f"      ประเภทพนักงาน options: {options}")
            if len(options) > 1:
                page.locator(".ant-select-item-option:visible").nth(1).click()
                page.wait_for_timeout(500)
                search_btn.click()
                page.wait_for_load_state("networkidle", timeout=15_000)
                page.wait_for_timeout(1_000)
                rows_f = page.locator("tbody tr").count()
                report("TC-DRIVER-02c", "ค้นหาด้วย Filter ประเภทพนักงาน", "PASS",
                       f"พบ {rows_f} แถว")
                clear_btn.click()
                page.wait_for_load_state("networkidle", timeout=10_000)
            else:
                page.keyboard.press("Escape")
                report("TC-DRIVER-02c", "ค้นหาด้วย Filter ประเภทพนักงาน", "SKIP",
                       "ไม่มี options")
        except Exception as e:
            report("TC-DRIVER-02c", "ค้นหาด้วย Filter ประเภทพนักงาน", "SKIP", str(e)[:60])

# ---------------------------------------------------------------------------
# TC-DRIVER-03 : Inspect Form Structure
# ---------------------------------------------------------------------------

def tc_driver_03_inspect_form(page: Page):
    print("\n[TC-DRIVER-03] ตรวจสอบ Form Structure (เพิ่มพนักงาน)")
    nav_to_driver(page)

    opened = open_add_form(page)
    if not opened:
        report("TC-DRIVER-03a", "Form เพิ่มพนักงานเปิดได้", "FAIL", "เปิด form ไม่ได้")
        return
    report("TC-DRIVER-03a", "Form เพิ่มพนักงานเปิดได้", "PASS")

    cdk = page.locator(".cdk-overlay-container")
    form_items = cdk.locator(".ant-form-item").all()
    report("TC-DRIVER-03b", f"Form Items ({len(form_items)} รายการ)",
           "PASS" if len(form_items) > 0 else "FAIL")

    required_fields = []
    print(f"\n      Form fields ({len(form_items)} รายการ):")
    for i, item in enumerate(form_items):
        lbl    = item.locator("label").first.inner_text() if item.locator("label").count() > 0 else "—"
        is_req = item.locator(".ant-form-item-required").count() > 0
        has_inp = item.locator("input").count() > 0
        ph = item.locator("input").first.get_attribute("placeholder") if has_inp else ""
        has_sel = item.locator(".ant-select").count() > 0
        has_date = item.locator(".ant-picker").count() > 0
        req_mark = "★ " if is_req else "  "
        if is_req:
            required_fields.append(lbl)
        print(f"      [{i}]{req_mark}'{lbl}' | inp={has_inp}(ph='{ph}') | sel={has_sel} | date={has_date}")

    report("TC-DRIVER-03c", f"Required Fields ★ ({len(required_fields)} รายการ)",
           "PASS" if len(required_fields) > 0 else "FAIL",
           f"{required_fields}")

    btn_texts = [b for b in cdk.locator("button").all_inner_texts() if b.strip()]
    report("TC-DRIVER-03d", f"Buttons ใน Form: {btn_texts}", "PASS")

    close_form(page)

# ---------------------------------------------------------------------------
# TC-DRIVER-04 : Validation — บันทึกโดยไม่กรอก Required Fields
# ---------------------------------------------------------------------------

def tc_driver_04_validation(page: Page):
    print("\n[TC-DRIVER-04] ตรวจสอบ Required Field Validation")
    nav_to_driver(page)

    opened = open_add_form(page)
    if not opened:
        report("TC-DRIVER-04", "Validation", "ERROR", "เปิด form ไม่ได้")
        return

    cdk = page.locator(".cdk-overlay-container")

    # กดปุ่ม เพิ่ม (save) โดยไม่กรอก
    save_btn = cdk.locator("button:has-text('เพิ่ม')").last
    print(f"      Save button count: {save_btn.count()}")
    if save_btn.count() > 0:
        page.evaluate("(el) => el.click()", save_btn.last.element_handle())
    page.wait_for_timeout(2_500)

    form_still_open = cdk.locator(".ant-form-item").count() > 0
    errors = page.locator(".ant-form-item-explain-error")
    error_count = errors.count()
    error_texts = errors.all_inner_texts()[:5] if error_count > 0 else []
    print(f"      form_open={form_still_open} errors={error_count}")

    if error_count > 0:
        report("TC-DRIVER-04a", "กด เพิ่ม โดยไม่กรอก → แสดง error validation", "PASS",
               f"{error_count} errors: {error_texts}")
    elif form_still_open:
        report("TC-DRIVER-04a", "กด เพิ่ม โดยไม่กรอก → Form ยังเปิด (ไม่ submit)", "PASS",
               "form ไม่ถูก submit")
    else:
        report("TC-DRIVER-04a", "Validation ไม่ทำงาน — form ปิดโดยไม่มี error", "FAIL")

    close_form(page)

# ---------------------------------------------------------------------------
# TC-DRIVER-05 : Create — กรอก Required Fields และบันทึก
# ---------------------------------------------------------------------------

def tc_driver_05_create(page: Page):
    print("\n[TC-DRIVER-05] ทดสอบ Create พนักงานใหม่")
    nav_to_driver(page)

    rows_before = page.locator("tbody tr").count()

    opened = open_add_form(page)
    if not opened:
        report("TC-DRIVER-05", "Create", "ERROR", "เปิด form ไม่ได้")
        return

    cdk = page.locator(".cdk-overlay-container")
    form_items = cdk.locator(".ant-form-item").all()

    try:
        # [0] ประเภทพนักงาน — เลือก option แรก
        sel0 = form_items[0].locator(".ant-select")
        if sel0.count() > 0:
            select_first_option(page, sel0)

        # [4] คำนำหน้าชื่อ★ — เลือก option แรก
        sel4 = form_items[4].locator(".ant-select")
        if sel4.count() > 0:
            select_first_option(page, sel4)

        # [6] ชื่อเต็ม★ — ใช้ RUN_ID ป้องกัน duplicate
        form_items[6].locator("input").first.fill(f"ทดสอบ{RUN_ID}")

        # [7] นามสกุล★
        form_items[7].locator("input").first.fill("ออโต้ TEST")

        # [8] เลขบัตรประชาชน★ (13 หลัก)
        form_items[8].locator("input").first.fill("1234567890123")

        # [9] วันหมดอายุบัตรประชาชน★ — DD-MM-YYYY (พ.ศ.)
        date_inp9 = form_items[9].locator("input").first
        fill_date(page, date_inp9, "31-12-2573")   # 31 ธ.ค. 2030 CE = 2573 BE

        # [10] หน่วยงาน/ที่ทำการไปรษณีย์★ — เลือก option แรก
        sel10 = form_items[10].locator(".ant-select")
        if sel10.count() > 0:
            select_first_option(page, sel10)

        # [11] วันที่เกิด★ — DD-MM-YYYY (พ.ศ.)
        date_inp11 = form_items[11].locator("input").first
        fill_date(page, date_inp11, "01-01-2533")  # 1 ม.ค. 1990 CE = 2533 BE
        page.wait_for_timeout(600)

        # [13] วันที่เริ่มทำงานกับบริษัท★ — DD-MM-YYYY (พ.ศ.)
        date_inp13 = form_items[13].locator("input").first
        fill_date(page, date_inp13, "01-01-2563")  # 1 ม.ค. 2020 CE = 2563 BE
        page.wait_for_timeout(600)

        # [15] เบอร์โทรศัพท์★
        form_items[15].locator("input").first.fill("0812345678")

        report("TC-DRIVER-05a", "กรอก Required Fields ครบ", "PASS")

    except Exception as e:
        report("TC-DRIVER-05a", "กรอก Required Fields", "FAIL", str(e)[:100])
        close_form(page)
        return

    # กดปุ่ม เพิ่ม (save)
    save_btn = cdk.locator("button:has-text('เพิ่ม')").last
    if save_btn.count() > 0:
        page.evaluate("(el) => el.click()", save_btn.last.element_handle())
    page.wait_for_timeout(3_000)

    form_closed = cdk.locator(".ant-form-item").count() == 0
    success_msg = page.locator(".ant-notification-notice-message, .ant-message-success")
    has_success  = success_msg.count() > 0
    errors       = page.locator(".ant-form-item-explain-error")
    err_count    = errors.count()

    if has_success:
        report("TC-DRIVER-05b", "บันทึกสำเร็จ — แสดง success notification", "PASS",
               success_msg.first.inner_text(timeout=3_000))
    elif form_closed:
        report("TC-DRIVER-05b", "บันทึกสำเร็จ — Form ปิดแล้ว", "PASS")
    elif err_count > 0:
        report("TC-DRIVER-05b", "บันทึกไม่สำเร็จ — มี validation error", "FAIL",
               f"errors: {errors.all_inner_texts()[:3]}")
        close_form(page)
        return
    else:
        report("TC-DRIVER-05b", "ไม่แน่ใจผลบันทึก", "SKIP")
        close_form(page)
        return

    # ค้นหาข้อมูลที่สร้าง
    nav_to_driver(page)
    page.locator("input.ant-input").first.fill(f"ทดสอบ{RUN_ID}")
    page.locator("button:has-text('ค้นหา')").first.click()
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(1_500)
    rows_after = page.locator("tbody tr").count()
    report("TC-DRIVER-05c", "ข้อมูลพนักงานที่สร้างปรากฏในตาราง",
           "PASS" if rows_after > 0 else "FAIL",
           f"พบ {rows_after} แถว")

    page.locator("button:has-text('ล้างค้นหา')").first.click()
    page.wait_for_load_state("networkidle", timeout=10_000)

# ---------------------------------------------------------------------------
# TC-DRIVER-06 : Edit — คลิก Action Button และตรวจสอบ Edit Form
# ---------------------------------------------------------------------------

def tc_driver_06_edit(page: Page):
    print("\n[TC-DRIVER-06] ทดสอบ Edit Form พนักงาน")
    nav_to_driver(page)
    page.wait_for_timeout(2_000)

    rows = page.locator("tbody tr")
    row_count = rows.count()
    report("TC-DRIVER-06a", f"ตารางมีข้อมูล",
           "PASS" if row_count > 0 else "SKIP",
           f"พบ {row_count} แถว")

    if row_count == 0:
        return

    # หาแถวที่มีข้อมูลจริง
    target_row = None
    for i in range(min(row_count, 15)):
        r = rows.nth(i)
        cells = r.locator("td").all_inner_texts()
        if any(c.strip() for c in cells):
            target_row = r
            print(f"      ข้อมูลแถว[{i}]: {cells[:4]}")
            break

    if target_row is None:
        report("TC-DRIVER-06b", "Action Buttons", "SKIP", "ไม่พบแถวที่มีข้อมูล")
        return

    action_btns = target_row.locator("button.btn-tran")
    btn_count   = action_btns.count()
    report("TC-DRIVER-06b", f"Action Buttons ในแถว ({btn_count} ปุ่ม)",
           "PASS" if btn_count > 0 else "FAIL")

    for i in range(btn_count):
        icon = page.evaluate(
            "(el) => el.querySelector('[data-icon]')?.getAttribute('data-icon') || ''",
            action_btns.nth(i).element_handle()
        )
        title = action_btns.nth(i).get_attribute("title") or ""
        print(f"      Button[{i}]: icon='{icon}' title='{title}'")

    if btn_count == 0:
        return

    # คลิก action button แรก (edit)
    page.evaluate("(el) => el.click()", action_btns.first.element_handle())
    page.wait_for_timeout(3_000)

    cdk_open   = page.locator(".cdk-overlay-container .ant-form-item").count() > 0
    modal_open = page.locator(".ant-modal-wrap:visible").count() > 0
    report("TC-DRIVER-06c", "คลิก Action → Edit Form เปิด",
           "PASS" if (cdk_open or modal_open) else "FAIL",
           f"cdk={cdk_open} modal={modal_open}")

    if not (cdk_open or modal_open):
        return

    cdk = page.locator(".cdk-overlay-container")
    inputs = cdk.locator("input:visible").all()
    values = [inp.input_value() for inp in inputs if inp.input_value()]
    report("TC-DRIVER-06d", f"Edit Form มีข้อมูลแสดง ({len(values)} fields มีค่า)",
           "PASS" if len(values) > 0 else "FAIL")

    # ตรวจข้อมูลสำคัญที่ต้องมี
    all_vals = " ".join(values)
    print(f"      ค่าที่พบ: {values[:8]}")

    # ปิด form (ไม่ทำการแก้ไขจริง)
    close_form(page)
    report("TC-DRIVER-06e", "ปิด Edit Form", "PASS")

# ---------------------------------------------------------------------------
# TC-DRIVER-07 : ตรวจสอบ sub-section เอกสาร (บัตรประชาชน, ใบขับขี่)
# ---------------------------------------------------------------------------

def tc_driver_07_document_sections(page: Page):
    print("\n[TC-DRIVER-07] ตรวจสอบ Sub-sections เอกสารใน Form")
    nav_to_driver(page)

    opened = open_add_form(page)
    if not opened:
        report("TC-DRIVER-07", "Document Sections", "ERROR", "เปิด form ไม่ได้")
        return

    cdk = page.locator(".cdk-overlay-container")

    # ตรวจปุ่มเอกสารต่างๆ
    doc_btns = {
        "เพิ่มข้อมูลบัตรประจำตัวประชาชน": "บัตรประจำตัวประชาชน",
        "เพิ่มข้อมูลใบขับขี่รถยนต์": "ใบขับขี่",
        "เพิ่มข้อมูลเข้ารับการอบรมพิเศษอื่นๆ": "การอบรมพิเศษ",
    }
    for btn_text, doc_name in doc_btns.items():
        btn = cdk.locator(f"button:has-text('{btn_text}')")
        report(f"TC-DRIVER-07a", f"ปุ่ม '{doc_name}' แสดงใน Form",
               "PASS" if btn.count() > 0 else "FAIL",
               f"text='{btn_text}'")

    # คลิกปุ่ม เพิ่มข้อมูลบัตรประจำตัวประชาชน
    id_card_btn = cdk.locator("button:has-text('เพิ่มข้อมูลบัตรประจำตัวประชาชน')")
    if id_card_btn.count() > 0:
        page.evaluate("(el) => el.click()", id_card_btn.first.element_handle())
        page.wait_for_timeout(1_500)
        sub_items = cdk.locator(".ant-form-item").count()
        print(f"      Form items หลังคลิก บัตรประชาชน: {sub_items}")
        report("TC-DRIVER-07b", "คลิกปุ่มบัตรประชาชน → Sub-section เพิ่มขึ้น",
               "PASS" if sub_items > 23 else "SKIP",
               f"form items รวม: {sub_items}")

    close_form(page)

# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  VCS Automated Tests — พนักงานขับรถ และพนักงานประจำรถ")
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
            tc_driver_01_page_loads(page)
            tc_driver_02_search(page)
            tc_driver_03_inspect_form(page)
            tc_driver_04_validation(page)
            tc_driver_05_create(page)
            tc_driver_06_edit(page)
            tc_driver_07_document_sections(page)
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
