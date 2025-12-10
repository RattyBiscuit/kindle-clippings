import shutil
import sqlite3
from pathlib import Path

import lxml.etree as etree

logos_notes_dir = Path("~").expanduser() / "LogosDocs" / "NotesToolManager"
shutil.copy(str(logos_notes_dir / "notestool.db"), "notes.db")


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


con = sqlite3.connect("notes.db")
con.row_factory = dict_factory
cur = con.cursor()


# execute a query and iterate over the result
# for row in cur.execute(
#     """SELECT * FROM Notebooks WHERE "Title" = 'Commentary Quotes'; """
# ):
#     print(row)
#     1


class ConvertLogosXML:
    markdown = ""
    source = ""

    def __init__(self, content_rich_text):
        self.__convert(content_rich_text)

    def __convert(self, content_rich_text):
        lines = []
        content_rich_text = f"<div>{content_rich_text}</div>"
        root = etree.fromstring(content_rich_text)
        for paragraph in root.xpath(".//Paragraph"):
            line = ""
            runs = paragraph.xpath(".//Run")
            for i, run in enumerate(runs):
                parent = run.getparent()
                is_link = parent.tag == "UriLink"
                text = run.get("Text")
                is_italic = run.get("FontItalic")
                is_bold = run.get("FontBold")
                is_super = run.get("FontVariant") == "Superscript"
                if is_italic:
                    # must check italic first as used for identifying book name
                    if i > 0:
                        prefix = ""
                        previous_line = runs[i - 1].get("Text")
                        prefix = previous_line.strip().split(" ")[-1]
                        prefix = prefix.replace(",", " - ")
                    self.source = prefix + text
                    text = f"*{text}*"
                if is_bold:
                    text = f"**{text}**"
                if is_super:
                    text = f"<sup>{text}</sup>"
                if is_link:
                    text = f"[{text}]({parent.get('Uri')})"
                line += text
            lines.append(line)
        self.markdown = "\n".join(lines)


for row in cur.execute(
    """
SELECT
    Notes."CreatedDate",
    "ContentRichText"

FROM
    Notes
INNER JOIN Notebooks ON ("NotebookExternalId" = "Notebooks"."ExternalId")
WHERE
    Notes."IsDeleted" = 0
    AND Notes."IsTrashed" = 0
    AND "Title" = 'Commentary Quotes'
    --AND LOWER("FoldedContent") like LOWER('%craftiness%')
ORDER BY
    Notes."CreatedDate" ASC; """
):

    for k, v in row.items():
        if k == "ContentRichText":
            converted = ConvertLogosXML(v)
            v = converted.markdown
        print("\n\n", converted.source, "\n\n", v)

    # print("")
