"""
Simple script that checks for new WCA competitions in Canada and updates a text
file if any were found.
"""

import subprocess
from dataclasses import dataclass
from datetime import datetime
from inspect import cleandoc
from pathlib import Path

import requests

COUNTRY_CODE = "CA"
COMPS_FILE = Path.home().joinpath("wca.txt")
COMP_IDS_FILE = Path.home().joinpath("wca-comp-ids.txt")
WCA_ICON = Path.home().joinpath("wca.svg")
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
                Registration: {self.registration_open} to {self.registration_close})
                Website:      {self.website}
            """
        ).strip()


def get_canadian_comps() -> list[Competition]:
    """
    Fetch the list of recently-announced competitions from the WCA API.
    """
    url = (
        "https://www.worldcubeassociation.org/api/v0/competitions"
        + f"?country_iso2={COUNTRY_CODE}"
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


def store_comp_details(comps: list[Competition]) -> None:
    """Update the text file with the new competitions."""
    comps = sorted(comps, key=lambda c: c.announced_at)
    try:
        old_text = COMPS_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        old_text = ""
    lines = old_text.split("\n")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for i, line in enumerate(lines):
        if line.startswith(FIRST_LINE):
            lines[i] = f"{FIRST_LINE} as of {now}:"
    if not any(ln.startswith(FIRST_LINE) for ln in lines):
        lines = [f"{FIRST_LINE} as of {now}"] + lines
    msg = "\n".join(lines).strip()
    msg += "\n\n"
    msg += "\n\n".join([str(c) for c in comps])
    msg += "\n"
    COMPS_FILE.write_text(msg, encoding="utf-8")


def get_old_comp_ids() -> list[str]:
    """Get the list of previously-seen competition IDs."""
    try:
        txt = COMP_IDS_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    return [x.strip() for x in txt.split("\n") if x.strip()]


def store_comp_ids(comp_ids: list[str]) -> None:
    """Update the file storing the list of previously-seen competition IDs."""
    sorted_unique_ids = sorted(set(comp_ids))
    COMP_IDS_FILE.write_text("\n".join(sorted_unique_ids), encoding="utf-8")


# pylint: disable=invalid-name
def notify_new_comps(n: int) -> None:
    """Send a desktop notification for new competitions."""
    comp_or_comps = "competition" if n == 1 else "competitions"
    has_or_have = "has" if n == 1 else "have"
    subprocess.run(
        [
            "notify-send",
            "--icon",
            WCA_ICON.as_posix(),
            f"WCA {comp_or_comps}",
            f"{n} new {comp_or_comps} {has_or_have} been announced in Canada.",
        ],
        check=True,
    )


def main() -> None:
    """Run the script."""
    old_comp_ids = get_old_comp_ids()
    new_comps = get_canadian_comps()
    new_comps = [
        c
        for c in new_comps
        if not c.is_registration_closed() and c.cid not in old_comp_ids
    ]
    # The date in the comp details file needs to be updated whether or not new
    # comps were found
    store_comp_details(new_comps)
    if new_comps:
        store_comp_ids(old_comp_ids + [c.cid for c in new_comps])
        notify_new_comps(n=len(new_comps))


if __name__ == "__main__":
    main()
