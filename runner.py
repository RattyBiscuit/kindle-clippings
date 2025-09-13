import json

from anyascii import anyascii
from clippy import Clipping, Clippings


class Clipping(Clipping):

    def __init__(self, raw_line, settings={}):
        self.settings = settings
        split_line = [anyascii(s.strip()) for s in raw_line.split("\n") if s]
        joined_line = "\n".join(split_line)
        super().__init__(joined_line)

    def _get_title_author(self, split_line):
        title_author = super()._get_title_author(split_line)
        return self.settings["renames"].get(title_author, title_author)


with open("settings.json") as f:
    settings = json.load(f)

# Load raw clippings from a file
with open("My Clippings.txt", "r", encoding="utf-8") as file:
    raw_clippings = file.read().split("==========")


# Parse clippings
clippings = Clippings()
for raw_clipping in raw_clippings:
    if raw_clipping.strip():  # Skip empty clippings
        this_clipping = Clipping(raw_clipping, settings)
        drop_clipping = False
        if not this_clipping.text:
            drop_clipping = True
        if this_clipping.title_author in settings["drops"]:
            for drop in settings["drops"][this_clipping.title_author]:
                if (
                    int(drop["start"]) == this_clipping.start_location
                    and int(drop["end"]) == this_clipping.end_location
                ):
                    drop_clipping = True
                    break
        if not drop_clipping:
            clippings.add_clipping(this_clipping)

titles = set()

for clipping in clippings.clippings:
    if clipping.title_author == "ESV Bible":
        print(clipping)
    titles.add(clipping.title_author)
print("")
for title in sorted(titles):
    print(title)
print("")
1
