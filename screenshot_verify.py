"""Capture just the Epigenetics & Wearables page to verify fix."""
import asyncio
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8503"
CHROME = "/root/.cache/ms-playwright/chromium-1194/chrome-linux/chrome"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROME,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=2,
        )
        page = await context.new_page()

        await page.goto(BASE, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(8000)

        # Navigate to Epigenetics & Wearables
        radio = page.locator('label:has-text("Epigenetics & Wearables")').first
        await radio.click()
        await page.wait_for_timeout(5000)

        await page.screenshot(
            path="/home/user/Claude/screenshots/epigenetics_and_wearables_fixed.png",
            full_page=True,
        )
        print("Saved fixed screenshot")

        # Also check Cross-Domain Engine (has expanders for recommendations)
        radio2 = page.locator('label:has-text("Cross-Domain Engine")').first
        await radio2.click()
        await page.wait_for_timeout(5000)

        await page.screenshot(
            path="/home/user/Claude/screenshots/cross-domain_engine_fixed.png",
            full_page=True,
        )
        print("Saved cross-domain screenshot")

        # Also check Unified Report (has expander for Raw JSON)
        radio3 = page.locator('label:has-text("Unified Report")').first
        await radio3.click()
        await page.wait_for_timeout(5000)

        await page.screenshot(
            path="/home/user/Claude/screenshots/unified_report_fixed.png",
            full_page=True,
        )
        print("Saved unified report screenshot")

        await browser.close()

asyncio.run(main())
