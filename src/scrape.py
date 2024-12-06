import os
import time
import zipfile
from io import BytesIO
from pathlib import Path

from browserbase.types import Extension, SessionCreateResponse
from playwright.async_api import Playwright, async_playwright

from src.config import settings

PATH_TO_EXTENSION = "./extensions/bypass-paywalls"


def zip_extension(path: Path = PATH_TO_EXTENSION, save_local: bool = False) -> BytesIO:
    """
    Create an in-memory zip file from the contents of the given folder.
    Mark save_local=True to save the zip file to a local file.
    """
    # Ensure we're looking at an extension
    assert "manifest.json" in os.listdir(
        path
    ), "No manifest.json found in the extension folder."

    # Create a BytesIO object to hold the zip file in memory
    memory_zip = BytesIO()

    # Create a ZipFile object
    with zipfile.ZipFile(memory_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        # Recursively walk through the directory
        for root, _, files in os.walk(path):
            for file in files:
                # Create the full file path
                file_path = os.path.join(root, file)
                # Calculate the archive name (path relative to the root directory)
                archive_name = os.path.relpath(file_path, path)
                # Add the file to the zip
                zf.write(file_path, archive_name)

    if save_local:
        with open(f"{path}.zip", "wb") as f:
            f.write(memory_zip.getvalue())

    return memory_zip


def create_extension() -> str:
    zip_data = zip_extension(save_local=True)
    extension: Extension = settings.browserbase.extensions.create(
        file=("extension.zip", zip_data.getvalue())
    )
    return extension.id


def get_extension(id: str) -> Extension:
    return settings.browserbase.extensions.retrieve(id)


def delete_extension(id: str) -> None:
    settings.browserbase.extensions.delete(id)


async def run(url: str, proxy: bool = False, load_extension: bool = False) -> None:
    async with async_playwright() as playwright:
        try:
            if load_extension:
                extension_id = None
                extension_id = create_extension()
                extension = get_extension(extension_id)
                session: SessionCreateResponse = settings.browserbase.sessions.create(
                    project_id=settings.BROWSERBASE_PROJECT_ID,
                    extension_id=extension.id,
                    proxies=proxy,
                )
                print(f"Created session with extension, with ID: {session.id}")
            else:
                session: SessionCreateResponse = settings.browserbase.sessions.create(
                    project_id=settings.BROWSERBASE_PROJECT_ID, proxies=proxy
                )
                print(f"Created session with ID: {session.id}")

            try:
                browser = await playwright.chromium.connect_over_cdp(
                    session.connect_url
                )
                context = browser.contexts[0]
                page = context.pages[0]

                await page.goto(url)
                if load_extension:
                    # scroll down as some websites need to load more content
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    time.sleep(3)

                # get html
                html = await page.content()
                # save to tmp/b.html
                with open("tmp/b.html", "w") as f:
                    f.write(html)
            finally:
                await page.close()
                await browser.close()

        except Exception as e:
            print(e)
