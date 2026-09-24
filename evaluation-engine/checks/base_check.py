from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from playwright.async_api import Page


@dataclass
class CheckResult:
    passed: bool
    actual_value: str
    expected_value: str
    evidence_html: Optional[str] = None    # captured DOM snippet
    evidence_screenshot: Optional[bytes] = None
    error: Optional[str] = None            # set if the check itself errored


class BaseCheck(ABC):
    @abstractmethod
    async def run(self, page: Page, assertion: dict) -> CheckResult:
        """
        Execute the check against the live page.
        assertion: dict with keys — selector, expected_result, wait_ms, check_type
        """
        ...