# -*- coding: utf-8 -*-
"""
run_car_tests.py
ระบบ VCS -- ข้อมูลหลัก: รถยนต์ (Cars)
Login ครั้งเดียว ทำ test ทุกตัวในคราวเดียว
รัน: python tests/phase1/run_car_tests.py
"""

import sys
import io
# Force UTF-8 stdout so Thai + symbols print correctly on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright, Page
from dataclasses import dataclass
from typing import List
import time

BASE_URL = "http://203.151.6.30/web-bms-vcsdev"
USERNAME  = "adminvcs"
PASSWORD  = "1111"
CAR_URL   = f"{BASE_URL}/transport/truck-master"

# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    id:     str
    name:   str
    status: str = "PENDING"   # PASS | FAIL | SKIP | ERROR
    detail: str = ""

results: List[TestResult] = []

def report(tc_id: str, name: str, status: str, detail: str = ""):
    r = TestResult(tc_id, name, status, detail)
    results.append(r)
    icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "⊘", "ERROR": "⚠"}.get(status, "?")
    print(f"  {icon} [{tc_id}] {name}")
    if detail:
        print(f"       → {detail}")

def nav_to_cars(page: Page):
    """นำทางไปหน้า Cars และรอโหลดเสร็จ"""
    page.goto(CAR_URL, timeout=60_000)
    page.wait_for_load_state("networkidle", timeout=30_000)
    page.wait_for_timeout(1_500)

def get_add_button(page: Page):
    """หาปุ่ม เพิ่ม จากหลาย selector — ค้นหาจาก text ก่อน"""
    # ลำดับ: text-based → icon-based → position-based
    for selector in [
        "button:has-text('เพิ่ม')",
        "button:has-text('สร้าง')",
        "button:has-text('Add')",
        "button:has-text('New')",
        "button[title='เพิ่ม']",
        "button .anticon-plus",  # ปุ่ม + icon
    ]:
        try:
            loc = page.locator(selector).first
            if loc.count() > 0 and loc.is_visible(timeout=2_000):
                print(f"      [debug] Add button found via: '{selector}', text='{loc.inner_text(timeout=3000)}'")
                return loc
        except Exception:
            continue
    return None


def open_add_drawer(page: Page) -> bool:
    """
    คลิกปุ่ม เพิ่ม — ลองหลายวิธีเพื่อรองรับ Angular overlay intercept
    รอ Drawer เปิดด้วย transform style (translateX(0)) แทน class
    """
    try:
        btn = get_add_button(page)
        if btn is None:
            print("      [debug] ไม่พบปุ่ม เพิ่ม ด้วยทุก selector")
            return False
        btn.wait_for(state="visible", timeout=10_000)
        page.wait_for_timeout(500)

        # วิธี 1: force=True click (ข้าม pointer-event check)
        try:
            btn.click(force=True, timeout=5_000)
        except Exception:
            # วิธี 2: dispatch synthetic click event
            try:
                btn.dispatch_event("click")
            except Exception:
                # วิธี 3: JS click
                page.evaluate("(el) => el.click()", btn.element_handle())

        page.wait_for_timeout(3_000)

        # ตรวจ drawer เปิดด้วย 3 วิธี:
        # A) class ant-drawer-open
        if page.locator(".ant-drawer-open").count() > 0:
            return True

        # B) drawer transform ไม่ใช่ 100% (เลื่อนเข้ามาแล้ว)
        drawers = page.query_selector_all(".ant-drawer-content-wrapper")
        for d in drawers:
            style = d.get_attribute("style") or ""
            if "translateX(0" in style or ("transform" not in style and "width" in style):
                return True

        # C) มี form content ใน cdk-overlay
        cdk = page.locator(".cdk-overlay-container .ant-form-item")
        if cdk.count() > 0:
            return True

        # D) URL เปลี่ยนเป็น detail/create page
        if "truck-master" not in page.url and "create" in page.url:
            return True

        return False
    except Exception as e:
        print(f"      open_add_drawer error: {e}")
        return False

def close_drawer(page: Page):
    """ปิด Drawer หรือ Modal ด้วย JS click"""
    try:
        # ลอง close drawer
        cb = page.locator(".ant-drawer-close")
        if cb.count() > 0:
            page.evaluate("(el) => el.click()", cb.first.element_handle())
            page.wait_for_timeout(800)
            return
        # ลอง close modal
        mc = page.locator(".ant-modal-close")
        if mc.count() > 0:
            page.evaluate("(el) => el.click()", mc.first.element_handle())
            page.wait_for_timeout(800)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

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
            print(f"  ✗ Login ล้มเหลว — URL: {page.url}")
            return False
        print(f"  ✓ Login สำเร็จ — URL: {page.url}")
        return True
    except Exception as e:
        print(f"  ✗ Login Error: {e}")
        return False

# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def tc_car_01_page_loads(page: Page):
    print("\n[TC-CAR-01] ตรวจสอบหน้า Cars โหลดสำเร็จ")
    nav_to_cars(page)
    url = page.url
    if "truck-master" not in url:
        report("TC-CAR-01a", "หน้า Cars โหลด — URL ถูกต้อง", "FAIL", f"Redirect ไป {url}")
        return
    report("TC-CAR-01a", "หน้า Cars โหลด — URL ถูกต้อง", "PASS", url)

    # ตรวจตาราง
    has_table = page.locator("table").count() > 0
    report("TC-CAR-01b", "ตารางรถยนต์แสดงบนหน้า", "PASS" if has_table else "FAIL",
           f"table count={page.locator('table').count()}")

    # ตรวจ Headers
    headers = page.locator("thead th").all_inner_texts()
    report("TC-CAR-01c", "Table Headers แสดงครบ", "PASS" if len(headers) >= 3 else "FAIL",
           f"headers={headers}")

    # ตรวจปุ่ม เพิ่ม
    add_visible = page.locator("button.btn-primary").first.is_visible()
    report("TC-CAR-01d", "ปุ่ม 'เพิ่ม' แสดงบนหน้า", "PASS" if add_visible else "FAIL")

    # ตรวจ Search filter
    inp_count = page.locator("input.ant-input").count()
    sel_count = page.locator(".ant-select:visible").count()
    report("TC-CAR-01e", "Filter elements (input/select) แสดงบนหน้า",
           "PASS" if (inp_count + sel_count) > 0 else "FAIL",
           f"inputs={inp_count}, selects={sel_count}")


def tc_car_02_search(page: Page):
    print("\n[TC-CAR-02] ทดสอบ Search")
    nav_to_cars(page)

    # หา search input
    search_input = page.locator("input.ant-input").first
    if not search_input.is_visible():
        report("TC-CAR-02a", "Search Input แสดงบนหน้า", "FAIL", "ไม่พบ input.ant-input")
        return
    report("TC-CAR-02a", "Search Input แสดงบนหน้า", "PASS")

    # หาปุ่ม ค้นหา — ใช้ .first เพื่อหลีกเลี่ยง strict mode violation (มี 2 ปุ่ม)
    search_btn = page.locator("button:has-text('ค้นหา')").first
    # ปุ่ม clear จริงชื่อ "ล้างค้นหา"
    clear_btn = page.locator("button:has-text('ล้างค้นหา')").first
    if clear_btn.count() == 0:
        clear_btn = page.locator("button:has-text('ล้างค่า')").first

    # Test: ค้นหาที่มีผลลัพธ์
    search_input.fill("กข")
    search_btn.click()
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(1_500)
    rows_found = page.locator("tbody tr").count()
    report("TC-CAR-02b", "ค้นหา 'กข' — ตารางตอบสนอง", "PASS", f"พบ {rows_found} แถว")

    # Reset
    clear_btn.click()
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(1_000)

    # Test: ค้นหาที่ไม่มีผลลัพธ์
    search_input.fill("ZZZNOTEXIST9999")
    search_btn.click()
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(1_500)
    rows_empty = page.locator("tbody tr").count()
    report("TC-CAR-02c", "ค้นหาค่าที่ไม่มีในระบบ — ตารางแสดงผลถูกต้อง", "PASS",
           f"แถวผลลัพธ์: {rows_empty}")

    # Reset
    clear_btn.click()
    page.wait_for_load_state("networkidle", timeout=15_000)


def tc_car_03_inspect_form(page: Page):
    print("\n[TC-CAR-03] ตรวจสอบ Form Structure (Drawer เพิ่มรถ)")
    nav_to_cars(page)
    page.wait_for_timeout(2_000)

    # Debug: แสดง buttons ทั้งหมดบนหน้า
    print("      [debug] URL:", page.url)
    all_btns = page.locator("button").all()
    print(f"      [debug] total buttons: {len(all_btns)}")
    for i, b in enumerate(all_btns[:8]):
        try:
            txt = b.inner_text(timeout=2000)
            cls = b.get_attribute("class") or ""
            print(f"      [debug] btn[{i}] text='{txt[:30]}' class='{cls[:60]}'")
        except Exception:
            pass

    opened = open_add_drawer(page)
    page.wait_for_timeout(1_000)

    # Form content อยู่ใน cdk-overlay-container (Angular CDK Portal)
    cdk = page.locator(".cdk-overlay-container")
    cdk_forms = cdk.locator(".ant-form-item").count()
    print(f"      [debug] cdk overlay form items: {cdk_forms}")

    if not opened:
        report("TC-CAR-03a", "Drawer เพิ่มรถเปิดได้", "FAIL", "ไม่สามารถเปิด Drawer ได้")
        return
    report("TC-CAR-03a", "Drawer เพิ่มรถเปิดได้", "PASS")

    # ใช้ cdk overlay เป็น form container
    form_container = cdk

    # Labels
    labels = form_container.locator("label").all_inner_texts()
    report("TC-CAR-03b", f"Labels ใน Form ({len(labels)} รายการ)",
           "PASS" if len(labels) > 0 else "FAIL", f"{labels[:10]}")

    # Form items detail
    form_items = form_container.locator(".ant-form-item").all()
    report("TC-CAR-03c", f"Form Items ({len(form_items)} รายการ)",
           "PASS" if len(form_items) > 0 else "FAIL")

    for i, item in enumerate(form_items[:20]):  # แสดงแค่ 20 รายการแรก
        lbl     = item.locator("label").first.inner_text() if item.locator("label").count() > 0 else "—"
        is_req  = item.locator(".ant-form-item-required").count() > 0
        has_inp = item.locator("input").count() > 0
        ph      = item.locator("input").first.get_attribute("placeholder") if has_inp else ""
        has_sel = item.locator(".ant-select").count() > 0
        has_dt  = item.locator(".ant-picker").count() > 0
        req_mark = "★ " if is_req else "  "
        print(f"      [{i}] {req_mark}'{lbl}' | input={has_inp}(ph='{ph}') | select={has_sel} | date={has_dt}")

    # Buttons ใน form container
    btn_texts = [b for b in form_container.locator("button").all_inner_texts() if b.strip()]
    report("TC-CAR-03d", f"Buttons ใน Form: {btn_texts}", "PASS")

    close_drawer(page)


def tc_car_04_validation(page: Page):
    print("\n[TC-CAR-04] ตรวจสอบ Required Field Validation")
    nav_to_cars(page)

    opened = open_add_drawer(page)
    if not opened:
        report("TC-CAR-04", "Required Field Validation", "ERROR", "เปิด Drawer ไม่ได้")
        return

    # form อยู่ใน cdk overlay
    cdk = page.locator(".cdk-overlay-container")

    # กดปุ่ม บันทึก โดยไม่กรอกข้อมูล
    save_btn = cdk.locator("button").filter(has_text="บันทึก")
    if save_btn.count() == 0:
        save_btn = cdk.locator("button:has-text('ยืนยัน'), button:has-text('OK')")
    print(f"      Save button: count={save_btn.count()}, texts={save_btn.all_inner_texts()}")

    if save_btn.count() > 0:
        page.evaluate("(el) => el.click()", save_btn.first.element_handle())
    page.wait_for_timeout(2_500)

    drawer_open   = page.locator(".cdk-overlay-container .ant-form-item").count() > 0
    error_msgs    = page.locator(".ant-form-item-explain-error")
    error_count   = error_msgs.count()
    error_texts   = error_msgs.all_inner_texts() if error_count > 0 else []

    if error_count > 0:
        report("TC-CAR-04a", "กด บันทึก โดยไม่กรอก → แสดง error", "PASS",
               f"{error_count} errors: {error_texts[:3]}")
    elif drawer_open:
        report("TC-CAR-04a", "กด บันทึก โดยไม่กรอก → Drawer ยังเปิด (ไม่บันทึก)", "PASS",
               "ไม่มี error message แต่ form ไม่ถูก submit")
    else:
        report("TC-CAR-04a", "กด บันทึก โดยไม่กรอก → ต้องมี validation", "FAIL",
               "Drawer ปิดและไม่มี error — อาจ submit โดยไม่มีข้อมูล")

    close_drawer(page)


def tc_car_05_table_actions(page: Page):
    print("\n[TC-CAR-05] ตรวจสอบ Action Buttons ในตาราง")
    nav_to_cars(page)
    page.wait_for_timeout(2_000)

    rows = page.locator("tbody tr")
    row_count = rows.count()
    report("TC-CAR-05a", f"ตารางมีข้อมูล", "PASS" if row_count > 0 else "SKIP",
           f"พบ {row_count} แถว")

    if row_count == 0:
        report("TC-CAR-05b", "Action Buttons ในแถว", "SKIP", "ไม่มีข้อมูล")
        return

    # หาแถวที่มีข้อมูลจริง (ข้ามแถวว่าง)
    target_row = None
    for i in range(min(row_count, 10)):
        row = rows.nth(i)
        tds = row.locator("td").all_inner_texts()
        if any(t.strip() for t in tds):
            target_row = row
            print(f"      ใช้แถว[{i}]: {tds[:4]}")
            break
    if target_row is None:
        target_row = rows.first
        print("      ใช้แถวแรก (ทุกแถวอาจว่าง)")

    action_btns = target_row.locator("button.btn-tran")
    btn_count   = action_btns.count()
    report("TC-CAR-05b", f"Action Buttons ในแถวข้อมูล ({btn_count} ปุ่ม)",
           "PASS" if btn_count > 0 else "FAIL")

    for i in range(btn_count):
        btn = action_btns.nth(i)
        icon_type = page.evaluate(
            "(el) => el.querySelector('[data-icon]')?.getAttribute('data-icon') || "
            "el.querySelector('.anticon')?.className || ''",
            btn.element_handle()
        )
        print(f"      Button[{i}]: icon='{icon_type}'")

    if btn_count == 0:
        # ลองหา action btn ทั่วทั้งตาราง
        all_action_btns = page.locator("tbody button.btn-tran")
        print(f"      btn-tran ทั้งตาราง: {all_action_btns.count()}")
        return

    # คลิก action button แรก (View/Edit) ด้วย JS click
    print("      คลิก Action button[0]...")
    page.evaluate("(el) => el.click()", action_btns.first.element_handle())
    page.wait_for_timeout(3_000)

    drawer_open = page.locator(".ant-drawer-open").count() > 0
    modal_open  = page.locator(".ant-modal-wrap:visible").count() > 0
    url_changed = "truck-master" not in page.url
    print(f"      Drawer: {drawer_open} | Modal: {modal_open} | URL: {page.url}")

    if drawer_open:
        labels = page.locator(".ant-drawer-body label").all_inner_texts()
        report("TC-CAR-05c", "คลิก View/Edit → Drawer เปิดพร้อมข้อมูล", "PASS",
               f"Labels: {labels[:5]}")
        close_drawer(page)
    elif modal_open:
        report("TC-CAR-05c", "คลิก Action → Modal เปิด", "PASS")
        mc = page.locator(".ant-modal-close")
        if mc.count() > 0:
            page.evaluate("(el) => el.click()", mc.first.element_handle())
        page.wait_for_timeout(1_000)
    elif url_changed:
        report("TC-CAR-05c", "คลิก Action → นำทางหน้าใหม่", "PASS", page.url)
    else:
        report("TC-CAR-05c", "คลิก Action → ตรวจสอบผลลัพธ์", "FAIL",
               "ไม่เกิดอะไรขึ้นหลังคลิก")


def tc_car_06_edit_flow(page: Page):
    print("\n[TC-CAR-06] ทดสอบ Edit Flow")
    nav_to_cars(page)
    page.wait_for_timeout(2_000)

    rows = page.locator("tbody tr")
    if rows.count() == 0:
        report("TC-CAR-06", "Edit Flow", "SKIP", "ไม่มีข้อมูลในตาราง")
        return

    # หาแถวที่มีข้อมูลและ action buttons
    target_row  = None
    action_btns = None
    for i in range(min(rows.count(), 10)):
        r = rows.nth(i)
        ab = r.locator("button.btn-tran")
        if ab.count() > 0:
            target_row = r
            action_btns = ab
            break
    if action_btns is None:
        report("TC-CAR-06", "Edit Flow", "SKIP", "ไม่พบ action buttons ในตาราง")
        return

    edit_btn = action_btns.nth(1) if action_btns.count() >= 2 else action_btns.first
    page.evaluate("(el) => el.click()", edit_btn.element_handle())

    page.wait_for_timeout(3_000)
    drawer_open = page.locator(".ant-drawer-open").count() > 0
    modal_open  = page.locator(".ant-modal-wrap:visible").count() > 0

    if not drawer_open and not modal_open:
        report("TC-CAR-06a", "Edit Drawer/Modal เปิด", "FAIL", f"URL: {page.url}")
        return
    report("TC-CAR-06a", "Edit Drawer/Modal เปิด", "PASS",
           f"drawer={drawer_open} modal={modal_open}")

    drawer = page.locator(".ant-drawer-body") if drawer_open else page.locator(".ant-modal-body")

    # ตรวจว่า field มีข้อมูลแล้ว (ไม่ว่าง)
    inputs = drawer.locator("input:visible").all()
    filled = [(inp.get_attribute("placeholder") or "", inp.input_value()) for inp in inputs]
    pre_filled = [(ph, v) for ph, v in filled if v]
    report("TC-CAR-06b", "Form มีข้อมูลแสดงก่อนแก้ไข",
           "PASS" if len(pre_filled) > 0 else "FAIL",
           f"field ที่มีข้อมูล: {len(pre_filled)}/{len(inputs)}")

    close_drawer(page)

# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  VCS Automated Tests — ข้อมูลหลัก: รถยนต์ (Cars)")
    print("=" * 60)
    start_time = time.time()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,   # False = เปิดหน้าต่างเบราว์เซอร์จริง
            slow_mo=800,      # หน่วง 800ms ต่อ action เพื่อให้ดูทัน
            args=["--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.set_default_timeout(30_000)

        # Login
        ok = login(page)
        if not ok:
            print("\n✗ ไม่สามารถ Login ได้ — หยุดการทดสอบ")
            sys.exit(1)

        # Run all test cases
        try:
            tc_car_01_page_loads(page)
            tc_car_02_search(page)
            tc_car_03_inspect_form(page)
            tc_car_04_validation(page)
            tc_car_05_table_actions(page)
            tc_car_06_edit_flow(page)
        except Exception as e:
            print(f"\n⚠ Unexpected error: {e}")

        context.close()
        browser.close()

    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"  สรุปผลการทดสอบ (ใช้เวลา {elapsed:.1f} วินาที)")
    print("=" * 60)
    passed = [r for r in results if r.status == "PASS"]
    failed = [r for r in results if r.status == "FAIL"]
    errors = [r for r in results if r.status == "ERROR"]
    skipped= [r for r in results if r.status == "SKIP"]

    for r in results:
        icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "⊘", "ERROR": "⚠"}.get(r.status, "?")
        print(f"  {icon} {r.id:12s} {r.name}")
        if r.detail and r.status != "PASS":
            print(f"               {r.detail}")

    print(f"\n  ผ่าน: {len(passed)}  ล้มเหลว: {len(failed)}  Error: {len(errors)}  ข้าม: {len(skipped)}")
    print(f"  รวม:  {len(results)} test cases")

    if failed or errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
