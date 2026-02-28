"""Capture screenshots of each GenomeInsight Streamlit page."""
import asyncio
from playwright.async_api import async_playwright

PAGES = [
    "Overview",
    "Genome & Blood",
    "Microbiome",
    "Epigenetics & Wearables",
    "Cross-Domain Engine",
    "Unified Report",
    "Architecture",
]

BASE = "http://127.0.0.1:8502"
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

        # First load — let Streamlit fully initialize
        await page.goto(BASE, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(8000)

        for name in PAGES:
            try:
                # Open sidebar if collapsed
                sidebar = page.locator('section[data-testid="stSidebar"]')
                if not await sidebar.is_visible():
                    btn = page.locator('[data-testid="stSidebarCollapsedControl"] button')
                    if await btn.count() > 0 and await btn.first.is_visible():
                        await btn.first.click()
                        await page.wait_for_timeout(1000)

                # Click the radio option for this page
                radio = page.locator(f'label:has-text("{name}")').first
                if await radio.is_visible():
                    await radio.click()
                    await page.wait_for_timeout(5000)  # longer wait for render
                else:
                    print(f"  Could not find radio for: {name}")
            except Exception as e:
                print(f"  Warning selecting {name}: {e}")

            fname = name.lower().replace(" ", "_").replace("&", "and")
            path = f"/home/user/Claude/screenshots/{fname}.png"
            await page.screenshot(path=path, full_page=True)
            print(f"Saved: {path}")

        await browser.close()

asyncio.run(main())
