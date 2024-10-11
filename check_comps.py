"""
Simple script that checks for new WCA competitions in Canada and updates a text
file if any were found.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from inspect import cleandoc
from pathlib import Path

import requests

SEARCH_RANGE = timedelta(days=7)
COUNTRY_CODE = "CA"
TXT_PATH = Path.home().joinpath("wca.txt")
FIRST_LINE = "Upcoming WCA events in Canada (in ~/wca.txt)"


@dataclass
class Competition:
    """A WCA competition."""

    # pylint: disable=too-many-instance-attributes

    cid: str
    name: str
    website: str
    city: str
    announced_at: str
    registration_open: str
    registration_close: str
    start_date: str
    end_date: str

    def is_registration_closed(self) -> bool:
        """Decide whether the registration period for this event has passed."""
        try:
            reg_close = datetime.strptime(
                self.registration_close, "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        except ValueError:
            return False
        return reg_close < datetime.now()

    def __str__(self) -> str:
        return cleandoc(
            f"""
            {self.name}
                City:         {self.city}
                Date:         {self.start_date} to {self.end_date}
                Registration: {self.registration_open} to {self.registration_close}
                Website:      {self.website}
            """
        ).strip()


def get_recently_announced_competitions() -> list[Competition]:
    """
    Fetch the list of recently-announced competitions from the WCA API.
    """
    announced_after = datetime.now() - SEARCH_RANGE
    url = (
        "https://www.worldcubeassociation.org/api/v0/competitions"
        + f"?country_iso2={COUNTRY_CODE}"
        + f"&announced_after={announced_after.strftime('%Y-%m-%d')}"
    )
    response = requests.get(url, timeout=60)
    if response.status_code // 100 != 2:
        raise ValueError(f"Request to {url} failed with status {response.status_code}.")
    data = response.json()
    return [
        Competition(
            cid=c["id"],
            name=c["name"],
            website=c["website"],
            city=c["city"],
            announced_at=c["announced_at"],
            registration_open=c["registration_open"],
            registration_close=c["registration_close"],
            start_date=c["start_date"],
            end_date=c["end_date"],
        )
        for c in data
    ]


def store_comps(comps: list[Competition]) -> None:
    """Update the text file with the new competitions."""
    comps = sorted(comps, key=lambda c: c.announced_at)
    try:
        old_text = TXT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        old_text = ""
    lines = old_text.split("\n")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for i, line in enumerate(lines):
        if line.startswith(FIRST_LINE):
            lines[i] = f"{FIRST_LINE} as of {now}"
    if not any(ln.startswith(FIRST_LINE) for ln in lines):
        lines = [f"{FIRST_LINE} as of {now}"] + lines
    msg = "\n".join(lines).strip()
    msg += "\n\n"
    msg += "\n\n".join([str(c) for c in comps])
    msg += "\n"
    TXT_PATH.write_text(msg, encoding="utf-8")


def main() -> None:
    """Run the script."""
    new_comps = get_recently_announced_competitions()
    store_comps(new_comps)


if __name__ == "__main__":
    main()
