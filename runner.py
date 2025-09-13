import json

import dateutil.parser
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

    def _get_date_added(self, split_line):
        date_added = super()._get_date_added(split_line)
        if date_added:
            py_date = dateutil.parser.parse(date_added)
            return py_date
        return date_added


class ClippingsReader:
    def __init__(self, clippings_file="My Clippings.txt"):
        self.clippings_file = clippings_file
        self.clippings = Clippings()
        self.clippings_by_title_author = {}
        self.__read_settings()
        self.__load_clippings_file()

    def __read_settings(self):
        with open("settings.json") as f:
            self.settings = json.load(f)

    def __load_clippings_file(self):
        # Load raw clippings from a file
        with open("My Clippings.txt", "r", encoding="utf-8") as file:
            self.raw_clippings = file.read().split("==========")

    def parse(self):
        self.__parse_clippings()
        self.__group_clippings()

    def __parse_clippings(self):
        # Parse clippings
        for raw_clipping in self.raw_clippings:
            if raw_clipping.strip():  # Skip empty clippings
                clipping = Clipping(raw_clipping, self.settings)
                drop_clipping = False
                if not clipping.text:
                    drop_clipping = True
                elif (
                    "<You have reached the clipping limit for this item>"
                    in clipping.text
                ):
                    drop_clipping = True
                if clipping.title_author in self.settings["drops"]:
                    for drop in self.settings["drops"][clipping.title_author]:
                        if (
                            int(drop["start"]) == clipping.start_location
                            and int(drop["end"]) == clipping.end_location
                        ):
                            drop_clipping = True
                            break
                if not drop_clipping:
                    self.clippings.add_clipping(clipping)

    def __group_clippings(self):
        clippings = sorted(self.clippings.clippings, key=lambda c: c.date)
        for clipping in clippings:
            self.clippings_by_title_author.setdefault(clipping.title_author, [])
            self.clippings_by_title_author[clipping.title_author].append(clipping)

    def make_markdown(self):
        for title_author, clippings in self.clippings_by_title_author.items():
            if not title_author.startswith("Lawrence"):
                continue
            self._make_markdown(title_author, clippings)
            break

    def _make_markdown(self, title_author, clippings):
        print(title_author)
        clips = []
        for clipping in clippings:
            clip_text = [
                clipping.text,
                f'<div style="text-align: right">Page {clipping.page} (Location {clipping.start_location}-{clipping.end_location})</div>',
                "",
            ]
            clips.append("\n".join(clip_text))
        print("\n---\n\n".join(clips))
        return clips


reader = ClippingsReader()
reader.parse()
reader.make_markdown()
