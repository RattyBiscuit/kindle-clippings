import json
from pathlib import Path

import dateutil.parser
import jinja2
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


class PandaClipping(Clipping):

    def __init__(self, clipping_dict):
        self.title_author = clipping_dict["title_author"]
        try:
            self.page = int(clipping_dict["page"])
        except ValueError:
            self.page = None
        self.start_location = clipping_dict["start_location"]
        self.end_location = clipping_dict["end_location"]
        self.date = clipping_dict["date"]
        self.text = clipping_dict["text"]


class ClippingsReader:
    def __init__(self, clippings_file_path: str = "clippings_files/My Clippings.txt"):
        self._clippings_file_path = clippings_file_path
        self.clippings = Clippings()
        self.clippings_by_title_author = {}
        self.summaries_by_title_author = {}
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
        self._load_templates()
        self._load_settings()
        self._load_clippings_file()

    def _load_templates(self):
        self.templates = {}
        template_dir = Path("templates")
        for template in template_dir.glob("template_*.jinja"):
            name = template.stem.split("_")[1]
            text = template.read_text()
            self.templates[name] = text

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
        clippings_for_df = self.__filter_raw_clippings()
        self.df = pd.DataFrame(clippings_for_df)
        df = self.df.copy()
        df = self.__concat_clippings(df)
        df = self.__drop_where_start_matches(df)

        self.df = df
        self.__add_clippings_to_dict()

    def __concat_clippings(self, df):
        df.loc[:, "start_location"] = df.loc[:, "start_location"].astype(int)
        df.loc[:, "end_location"] = df.loc[:, "end_location"].astype(int)
        df = df.sort_values(
            by=["title_author", "start_location", "end_location", "date"],
        ).reset_index(drop=True)
        df["next_start_location"] = df["start_location"].shift(-1)
        df["next_end_location"] = df["end_location"].shift(-1)
        df["next_title_author"] = df["title_author"].shift(-1)
        df["next_text"] = df["text"].shift(-1)
        df["next_index"] = df.index + 1
        df["index"] = df.index

        records_to_merge = df[
            (df["title_author"] == df["next_title_author"])
            & (df["end_location"] == df["next_start_location"])
        ]
        if records_to_merge.empty:
            return df
        df["text"] = df.apply(self.__merge_text, axis=1)
        indices_to_drop = records_to_merge["next_index"].dropna().astype(int).tolist()

        df = df[~(df["index"].isin(indices_to_drop))]
        return self.__concat_clippings(df)

    def __merge_text(self, row):
        if row["title_author"] != row["next_title_author"]:
            return row["text"]
        if int(row["end_location"]) == int(row["next_start_location"]):
            return row["text"] + " " + row["next_text"]
        return row["text"]

    def __filter_raw_clippings(self):
        clippings_for_df = []
        limit_text = "<You have reached the clipping limit for this item>"
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
        return clippings_for_df

    def __drop_where_start_matches(self, df):
        # Convert 'date' column to datetime
        df["date"] = pd.to_datetime(df["date"])

        # Find the index of the max date for each group
        idx = df.groupby(["title_author", "start_location"])["date"].idxmax()

        # Use the indices to get the corresponding rows
        latest_rows = df.loc[idx].reset_index(drop=True)
        return latest_rows

    def __add_clippings_to_dict(self):
        for clippings in self.df.to_dict("records"):
            clipping = PandaClipping(clippings)
            self.clippings.add_clipping(clipping)

    def __group_clippings(self):
        """
        Group clippings by title and author.

        This function takes the clippings parsed from the file and groups them by title and author.
        It first sorts the clippings by date and then iterates over each clipping, adding it to
        the self.clippings_by_title_author dictionary. If the title and author are not already in the
        dictionary, it adds them and creates a new list for the clippings. If the title and author are
        already in the dictionary, it simply appends the clipping to the existing list.
        """
        clippings = sorted(
            self.clippings.clippings,
            key=lambda c: (c.start_location, pd.to_datetime(c.date)),
        )
        for clipping in clippings:
            self.clippings_by_title_author.setdefault(clipping.title_author, [])
            self.clippings_by_title_author[clipping.title_author].append(clipping)

    def make_markdown(self):
        for title_author, clippings in self.clippings_by_title_author.items():
            self.__get_summary(title_author)
            self.__make_clippings(title_author, clippings)
            self._make_markdown(title_author)

    def __make_clippings(self, title_author, clippings):
        options = {"clippings": clippings}
        output_folder = Path("summaries") / title_author
        output_file = output_folder / "clippings.md"
        if output_file.exists():
            output_file.unlink()
        with open(output_file, "w") as f:
            template = jinja2.Template(self.templates["clippings"])
            f.write(template.render(options))

    def __get_summary(self, title_author):
        summary_folder = Path("summaries") / f"{title_author}"
        self.summaries_by_title_author.setdefault(title_author, {})
        if not summary_folder.exists():
            return
        for summary_file in summary_folder.glob("*.md"):
            self.summaries_by_title_author[title_author][
                summary_file.stem
            ] = summary_file.read_text()

    def __make_options(self, title_author):
        options = {}
        summary = self.summaries_by_title_author[title_author]
        if summary:
            for key, value in summary.items():
                options[key] = value
        return options

    def _make_markdown(self, title_author):
        clips = []
        output_folder = Path("/mnt/c/Users/Alan/Obsidian/BibleNotes")
        if not output_folder.is_dir():
            output_folder = Path("/home/alan/git/BibleNotes")
        output_file = output_folder / "Book Summaries" / f"{title_author}.md"

        options = self.__make_options(title_author)
        template = jinja2.Template(self.templates["output"])
        output_file.write_text(template.render(options))
        return clips


reader = ClippingsReader()
reader.parse()
reader.make_markdown()
