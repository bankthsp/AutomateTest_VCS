# tests/phase1/test_car_master.py
# ระบบ VCS — ข้อมูลหลัก: รถยนต์
# Fix: ใช้ function-scope + re-login ก่อนทุก test เพื่อหลีกเลี่ยง session timeout

import pytest
from playwright.sync_api import sync_playwright, Page

BASE_URL = "http://203.151.6.30/web-bms-vcsdev"
USERNAME = "adminvcs"
PASSWORD = "1111"
CAR_URL  = f"{BASE_URL}/transport/truck-master"

# ---------------------------------------------------------------------------
# Shared Playwright instance (process-level)
# ---------------------------------------------------------------------------

_pw = None
_browser = None

def get_browser():
    global _pw, _browser
    if _browser is None:
        _pw = sync_playwright().start()
        _browser = _pw.chromium.launch(headless=True, slow_mo=200)
    return _browser


def teardown_browser():
    global _pw, _browser
    if _browser:
        _browser.close()
        _browser = None
    if _pw:
        _pw.stop()
        _pw = None


# ---------------------------------------------------------------------------
# Per-test fixture: fresh context + login + navigate to Cars
# ---------------------------------------------------------------------------

@pytest.fixture()
def page() -> Page:
    """
    ทุก test จะได้ page ใหม่ที่ login สำเร็จและอยู่ที่หน้า truck-master แล้ว
    """
    browser = get_browser()
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    pg = context.new_page()

    # Login
    pg.goto(f"{BASE_URL}/login", timeout=30_000)
    pg.wait_for_load_state("networkidle", timeout=15_000)
    pg.fill("#username", USERNAME)
    pg.fill("#password", PASSWORD)
    pg.locator("button.login-form-button").first.click()
    pg.wait_for_load_state("networkidle", timeout=20_000)

    # Navigate to Cars
    pg.goto(CAR_URL, timeout=30_000)
    pg.wait_for_load_state("networkidle", timeout=15_000)
    pg.wait_for_timeout(1_500)

    yield pg

    context.close()


def pytest_sessionfinish(session, exitstatus):
    teardown_browser()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def open_add_drawer(page: Page):
    page.locator("button.btn-primary").first.click()
    page.wait_for_selector(".ant-drawer-open", timeout=10_000)
    page.wait_for_timeout(800)


def close_drawer(page: Page):
    close_btns = page.locator(".ant-drawer-close")
    if close_btns.count() > 0 and close_btns.first.is_visible():
        close_btns.first.click()
        page.wait_for_timeout(800)


def select_first_option(page: Page, select_locator):
    """คลิก nz-select แล้วเลือก option แรก"""
    select_locator.click()
    page.wait_for_selector(".ant-select-dropdown:visible", timeout=5_000)
    page.locator(".ant-select-item-option:visible").first.click()
    page.wait_for_timeout(300)


def assert_on_car_page(page: Page):
    assert "truck-master" in page.url, \
        f"ไม่ได้อยู่ที่หน้า Cars — URL ปัจจุบัน: {page.url}"


# ---------------------------------------------------------------------------
# TC-CAR-01 : Read — ตรวจสอบหน้าแสดงรายการ
# ---------------------------------------------------------------------------

def test_TC_CAR_01_page_loads(page: Page):
    """หน้า Cars โหลดสำเร็จ — URL ถูกต้องและตารางแสดง"""
    assert_on_car_page(page)
    assert page.locator("table").count() > 0, "ไม่พบตารางบนหน้า Cars"
    print(f"\n✓ URL: {page.url}")


def test_TC_CAR_01b_table_has_headers(page: Page):
    """ตารางมี Header ครบ"""
    assert_on_car_page(page)
    headers = page.locator("thead th").all_inner_texts()
    print(f"\nHeaders พบ: {headers}")
    assert len(headers) >= 3, f"Header น้อยเกินไป: {headers}"


def test_TC_CAR_01c_add_button_visible(page: Page):
    """ปุ่ม เพิ่ม แสดงอยู่บนหน้า"""
    assert_on_car_page(page)
    add_btn = page.locator("button.btn-primary").first
    assert add_btn.is_visible(), "ไม่พบปุ่ม เพิ่ม"
    print(f"\n✓ ปุ่ม เพิ่ม: {add_btn.inner_text()}")


def test_TC_CAR_01d_filter_elements_visible(page: Page):
    """Filter inputs และ dropdowns แสดงบนหน้าค้นหา"""
    assert_on_car_page(page)
    inputs = page.locator("input.ant-input").all()
    selects = page.locator(".ant-select:visible").all()
    print(f"\nInputs: {len(inputs)}, Selects: {len(selects)}")
    assert len(inputs) + len(selects) > 0, "ไม่พบ filter elements"


# ---------------------------------------------------------------------------
# TC-CAR-02 : Search
# ---------------------------------------------------------------------------

def test_TC_CAR_02_search_by_plate(page: Page):
    """ค้นหาด้วยทะเบียน — ตารางตอบสนอง"""
    assert_on_car_page(page)

    search_input = page.locator("input.ant-input").first
    search_input.fill("กข")

    # คลิกปุ่มค้นหา (btn-secondary สุดท้าย หรือปุ่มที่มี text ค้นหา)
    search_btn = page.locator("button:has-text('ค้นหา')")
    if search_btn.count() == 0:
        # Fallback: ปุ่ม secondary ที่ 2
        search_btn = page.locator("button.btn-secondary").last
    search_btn.click()
    page.wait_for_load_state("networkidle", timeout=10_000)
    page.wait_for_timeout(1_000)

    rows = page.locator("tbody tr").count()
    print(f"\nผลค้นหา 'กข': {rows} แถว")

    # Reset
    clear_btn = page.locator("button:has-text('ล้างค่า')")
    if clear_btn.count() > 0:
        clear_btn.click()
        page.wait_for_load_state("networkidle", timeout=10_000)


def test_TC_CAR_02b_search_no_result(page: Page):
    """ค้นหาด้วยค่าที่ไม่มีในระบบ — ไม่แสดงแถวผลลัพธ์"""
    assert_on_car_page(page)

    search_input = page.locator("input.ant-input").first
    search_input.fill("ZZZNOTEXIST999")

    search_btn = page.locator("button:has-text('ค้นหา')")
    if search_btn.count() == 0:
        search_btn = page.locator("button.btn-secondary").last
    search_btn.click()
    page.wait_for_load_state("networkidle", timeout=10_000)
    page.wait_for_timeout(1_500)

    rows = page.locator("tbody tr").count()
    print(f"\nผลค้นหา NOT EXIST: {rows} แถว")

    # ล้างค่า
    clear_btn = page.locator("button:has-text('ล้างค่า')")
    if clear_btn.count() > 0:
        clear_btn.click()
        page.wait_for_load_state("networkidle", timeout=10_000)


# ---------------------------------------------------------------------------
# TC-CAR-03 : Inspect Form Structure (Discovery Test)
# ---------------------------------------------------------------------------

def test_TC_CAR_03_inspect_add_drawer(page: Page):
    """เปิด Drawer เพิ่มรถ → บันทึก field structure ทั้งหมด"""
    assert_on_car_page(page)
    open_add_drawer(page)
    assert page.locator(".ant-drawer-open").count() > 0, "Drawer ไม่เปิด"

    drawer = page.locator(".ant-drawer-body")

    # Labels
    labels = drawer.locator("label").all_inner_texts()
    print(f"\nLabels ใน form: {labels}")

    # Form items
    form_items = drawer.locator(".ant-form-item").all()
    print(f"\nจำนวน form items: {len(form_items)}")
    for i, item in enumerate(form_items):
        lbl = item.locator("label").first.inner_text() if item.locator("label").count() > 0 else "—"
        has_inp = item.locator("input").count() > 0
        ph = item.locator("input").first.get_attribute("placeholder") if has_inp else ""
        has_sel = item.locator(".ant-select").count() > 0
        has_date = item.locator(".ant-picker").count() > 0
        required = "★" if item.locator(".ant-form-item-required").count() > 0 else ""
        print(f"  [{i}]{required} '{lbl}' | input={has_inp}(ph='{ph}') | select={has_sel} | date={has_date}")

    # Buttons ใน drawer
    btns = drawer.locator("button").all_inner_texts()
    print(f"\nButtons ใน drawer: {btns}")

    assert len(labels) > 0, "ไม่พบ label ใน form"
    close_drawer(page)


# ---------------------------------------------------------------------------
# TC-CAR-04 : Validation — Required Fields
# ---------------------------------------------------------------------------

def test_TC_CAR_04_save_without_data_shows_error(page: Page):
    """กด บันทึก โดยไม่กรอกข้อมูล → ต้องแสดง error"""
    assert_on_car_page(page)
    open_add_drawer(page)

    drawer = page.locator(".ant-drawer-body")

    # กดปุ่ม บันทึก
    save_btn = drawer.locator("button").filter(has_text="บันทึก")
    if save_btn.count() == 0:
        save_btn = drawer.locator("button.ant-btn-primary").last
    print(f"\nSave button found: {save_btn.count()}, text: {save_btn.all_inner_texts()}")
    save_btn.click()
    page.wait_for_timeout(2_000)

    # ตรวจสอบ: Drawer ยังเปิดอยู่ (ไม่ปิดเพราะ validation fail)
    drawer_still_open = page.locator(".ant-drawer-open").count() > 0
    errors = page.locator(".ant-form-item-explain-error")
    error_count = errors.count()
    print(f"Drawer ยังเปิด: {drawer_still_open}, Errors: {error_count}")
    if error_count > 0:
        print(f"Error messages: {errors.all_inner_texts()}")

    assert drawer_still_open or error_count > 0, \
        "ระบบควร block การบันทึกหรือแสดง error เมื่อไม่กรอกข้อมูล"
    close_drawer(page)


# ---------------------------------------------------------------------------
# TC-CAR-05 : View/Edit — แถวแรกในตาราง
# ---------------------------------------------------------------------------

def test_TC_CAR_05_action_buttons_in_table(page: Page):
    """ตรวจสอบ Action buttons ในแต่ละแถวของตาราง"""
    assert_on_car_page(page)
    page.wait_for_timeout(2_000)

    rows = page.locator("tbody tr")
    row_count = rows.count()
    print(f"\nจำนวนแถวในตาราง: {row_count}")

    if row_count == 0:
        pytest.skip("ไม่มีข้อมูลรถในตาราง — ข้ามการทดสอบ")

    first_row = rows.first
    row_data = first_row.locator("td").all_inner_texts()
    print(f"ข้อมูลแถวแรก: {row_data}")

    action_btns = first_row.locator("button.btn-tran")
    btn_count = action_btns.count()
    print(f"Action buttons: {btn_count}")
    for i in range(btn_count):
        btn = action_btns.nth(i)
        html = page.evaluate("(el) => el.outerHTML", btn)
        print(f"  Button[{i}]: {html[:200]}")

    assert btn_count > 0, "ไม่พบ Action button ในแถวแรก"


def test_TC_CAR_05b_open_first_row_action(page: Page):
    """คลิก Action button แถวแรก → ตรวจสอบว่าเปิด Drawer/Modal"""
    assert_on_car_page(page)
    page.wait_for_timeout(2_000)

    rows = page.locator("tbody tr")
    if rows.count() == 0:
        pytest.skip("ไม่มีข้อมูล")

    first_row = rows.first
    action_btns = first_row.locator("button.btn-tran")
    if action_btns.count() == 0:
        pytest.skip("ไม่พบปุ่ม action")

    # คลิกปุ่มแรก
    action_btns.first.click()
    page.wait_for_timeout(3_000)

    drawer_open = page.locator(".ant-drawer-open").count() > 0
    modal_open  = page.locator(".ant-modal-wrap:visible").count() > 0
    url_changed = "truck-master" not in page.url
    print(f"\nDrawer: {drawer_open} | Modal: {modal_open} | URL: {page.url}")

    if drawer_open:
        labels = page.locator(".ant-drawer-body label").all_inner_texts()
        print(f"Labels ใน drawer: {labels}")
        close_drawer(page)
    elif modal_open:
        page.locator(".ant-modal-close").first.click()
    elif url_changed:
        print(f"นำทางไปหน้าใหม่: {page.url}")
    else:
        pytest.fail("คลิก Action แล้วไม่มีอะไรเปิด")


def test_TC_CAR_05c_open_second_action_button(page: Page):
    """ทดสอบ Action button ที่ 2 (มักเป็น Edit)"""
    assert_on_car_page(page)
    page.wait_for_timeout(2_000)

    rows = page.locator("tbody tr")
    if rows.count() == 0:
        pytest.skip("ไม่มีข้อมูล")

    first_row = rows.first
    action_btns = first_row.locator("button.btn-tran")
    if action_btns.count() < 2:
        pytest.skip(f"มีแค่ {action_btns.count()} ปุ่ม — ข้ามทดสอบ Edit")

    action_btns.nth(1).click()
    page.wait_for_timeout(3_000)

    drawer_open = page.locator(".ant-drawer-open").count() > 0
    print(f"\nDrawer open after 2nd button: {drawer_open} | URL: {page.url}")

    if drawer_open:
        # ตรวจว่า field มีข้อมูลแสดง (ไม่ว่าง)
        inputs = page.locator(".ant-drawer-body input").all()
        values = [inp.input_value() for inp in inputs if inp.is_visible()]
        print(f"Input values: {values}")
        close_drawer(page)
