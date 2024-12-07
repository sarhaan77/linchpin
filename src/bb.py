import os
import time
import zipfile
from io import BytesIO
from pathlib import Path

from browserbase.types import Extension, SessionCreateResponse
from playwright.sync_api import ConsoleMessage, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.config import settings

PATH_TO_EXTENSION = "./extensions/bypass-paywalls"


# //////////////////////////
# Extensions
# //////////////////////////
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


# //////////////////////////
# Captcha
# //////////////////////////


class SolveState:
    """
    A simple class to track the state of the CAPTCHA solution.
    """

    started = False
    finished = False

    # These messages are sent to the browser's console automatically
    # when a CAPTCHA is detected and solved.
    START_MSG = "browserbase-solving-started"
    END_MSG = "browserbase-solving-finished"

    def handle_console(self, msg: ConsoleMessage) -> None:
        """
        Handle messages coming from the browser's console.
        """
        if msg.text == self.START_MSG:
            self.started = True
            print("AI has started solving the CAPTCHA...")
            return

        if msg.text == self.END_MSG:
            self.finished = True
            print("AI solved the CAPTCHA!")
            return


def solve_captcha(browser_tab: Page, target_url: str):
    state = SolveState()
    browser_tab.on("console", state.handle_console)
    browser_tab.goto(target_url)

    try:
        # There's a chance that solving the CAPTCHA is so quick it misses the
        # end message. In this case, this function waits the 10 seconds and
        # the issue is reconciled with the "Solving mismatch" error below.
        with browser_tab.expect_console_message(
            lambda msg: msg.text == SolveState.END_MSG,
            timeout=10000,
        ):
            # Do nothing and wait for the event or timeout
            pass

    except PlaywrightTimeoutError:
        if state.started:
            raise Exception(
                "Timeout: No CAPTCHA solving event detected after 10 seconds"
            )
        # This should only be treated as an error if `state.started` is True,
        # otherwise it just means no CAPTCHA was given.

    # If we didn't see both a start and finish message, raise an error.
    if state.started != state.finished:
        raise Exception(f"Solving mismatch! {state.started=} {state.finished=}")

    if state.started == state.finished == False:
        raise Exception("No CAPTCHA was presented, or was solved too quick to see.")
    else:
        print("CAPTCHA is complete.")

    # Wait for some page content to load.
    # Anything in `body` should be visible
    browser_tab.locator("body").wait_for(state="visible")


def bb_get_html(
    url: str, proxy: bool = False, captcha: bool = False, load_extension: bool = False
) -> str:
    with sync_playwright() as playwright:
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
            else:
                session: SessionCreateResponse = settings.browserbase.sessions.create(
                    project_id=settings.BROWSERBASE_PROJECT_ID, proxies=proxy
                )

            browser = playwright.chromium.connect_over_cdp(session.connect_url)
            context = browser.contexts[0]
            page = context.pages[0]

            if proxy and captcha:
                solve_captcha(page, url)

            page.goto(url)

            if load_extension:
                # scroll down as some websites need to load more content
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                time.sleep(2)

            return page.content()
        except Exception as e:
            raise e
        finally:
            page.close()
            browser.close()
            if load_extension:
                delete_extension(extension_id)
