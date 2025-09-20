import json
from pathlib import Path

import dateutil.parser
import pandas as pd
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

    def to_dict(self):
        return {
            "title_author": self.title_author,
            "page": self.page,
            "start_location": self.start_location,
            "end_location": self.end_location,
            "date": self.date,
            "text": self.text,
        }


class ClippingsReader:
    def __init__(self, clippings_file_path: str = "My Clippings.txt"):
        self._clippings_file_path = clippings_file_path
        self.clippings = Clippings()
        self.clippings_by_title_author = {}
        self.df = pd.DataFrame(
            columns=[
                "title_author",
                "page",
                "start_location",
                "end_location",
                "date",
                "text",
            ]
        )
        self._load_settings()
        self._load_clippings_file()

    def _load_settings(self):
        """
        Load settings from a JSON file.
        """
        with open("settings.json") as file:
            self.settings = json.load(file)

    def _load_clippings_file(self):
        """
        Load raw clippings from a file.
        """
        with open(self._clippings_file_path, "r", encoding="utf-8") as file:
            raw_clippings_data = file.read()
            self._raw_clippings = raw_clippings_data.split("==========")

    def parse(self):
        """
        Parse raw clippings from a file and group them by title and author.
        """
        self.__parse_clippings()
        self.__group_clippings()

    def __parse_clippings(self):
        """
        Parse raw clippings from a file and store them in the Clippings object.

        This function iterates over each raw clipping, creates a Clipping object from it,
        and then checks if the clipping should be dropped according to the settings.
        If the clipping should not be dropped, it is added to the Clippings object.
        """
        limit_text = "<You have reached the clipping limit for this item>"
        clippings_for_df = []
        for raw_clipping in self._raw_clippings:
            if raw_clipping.strip():  # Skip empty clippings
                clipping = Clipping(raw_clipping, self.settings)
                if not clipping.text or limit_text in clipping.text:
                    continue
                if clipping.title_author in self.settings["drops"]:
                    drop_items = self.settings["drops"][clipping.title_author]
                    if isinstance(drop_items, bool):
                        continue
                    drops = self.settings["drops"][clipping.title_author]
                    should_drop = [
                        drop
                        for drop in drops
                        if int(drop["start"]) == clipping.start_location
                        and int(drop["end"]) == clipping.end_location
                    ]
                    if should_drop:
                        continue
                clippings_for_df.append(clipping.to_dict())

                self.clippings.add_clipping(clipping)
        self.df = pd.concat(
            [self.df, pd.DataFrame(clippings_for_df)], ignore_index=True
        )
        print(self.df.head(10))
        1

    def __group_clippings(self):
        """
        Group clippings by title and author.

        This function takes the clippings parsed from the file and groups them by title and author.
        It first sorts the clippings by date and then iterates over each clipping, adding it to
        the self.clippings_by_title_author dictionary. If the title and author are not already in the
        dictionary, it adds them and creates a new list for the clippings. If the title and author are
        already in the dictionary, it simply appends the clipping to the existing list.
        """
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
        output_file = "/mnt/c/Users/Alan/Obsidian/BibleNotes/scratch.md"
        output_file = Path(output_file)
        clips = []
        for clipping in clippings:
            clip_text = [
                clipping.text,
                f'<div style="text-align: right"><i>Page {clipping.page} (Location {clipping.start_location}-{clipping.end_location})</i></div>',
                "",
            ]
            clips.append("\n".join(clip_text))
        md_text = "\n---\n\n".join(clips)
        output_file.write_text(md_text)
        return clips


reader = ClippingsReader()
reader.parse()
reader.make_markdown()
