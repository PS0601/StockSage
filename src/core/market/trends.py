# SPDX-License-Identifier: MIT
"""Google Trends fetching via pytrends."""

import logging
import time

import pandas as pd
from pytrends.request import TrendReq

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
_BASE_BACKOFF_SECONDS = 2.0


class TrendsFetcher:
    """Fetches Google Trends interest-over-time data for a stock."""

    def __init__(self, keyword: str, timeframe: str = "today 12-m", geo="IN"):
        self._keyword = keyword
        self._timeframe = timeframe
        self._geo = geo

    def fetch(self) -> pd.DataFrame:
        # pytrends' built-in retries (retries=/backoff_factor=) pass the old
        # urllib3 option `method_whitelist`, which crashes on urllib3 v2.
        # So we never enable them, and retry here ourselves instead.
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                pt = TrendReq(hl="en-US", tz=330, timeout=(10, 25))
                pt.build_payload(
                    kw_list=[self._keyword],
                    timeframe=self._timeframe,
                    geo=self._geo,
                )
                df = pt.interest_over_time()
                if df is not None and not df.empty:
                    return df.drop(columns=["isPartial"], errors="ignore")

                logger.warning("Empty trends data for %s", self._keyword)
                return pd.DataFrame()

            except Exception as e:
                if attempt == _MAX_ATTEMPTS:
                    logger.warning(
                        "Google Trends failed for %s after %d attempts: %s",
                        self._keyword,
                        attempt,
                        e,
                    )
                    return pd.DataFrame()
                wait = _BASE_BACKOFF_SECONDS * 2 ** (attempt - 1)
                logger.info(
                    "Google Trends attempt %d failed for %s (%s); retrying in %.0fs",
                    attempt,
                    self._keyword,
                    e,
                    wait,
                )
                time.sleep(wait)

        return pd.DataFrame()
