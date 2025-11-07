import shutil
import sqlite3
from pathlib import Path

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
for row in cur.execute(
    """
SELECT
    "Title",
    "NotebookExternalId",
    "ContentRichText",
    Notes."CreatedDate",
    *


FROM
    Notes
INNER JOIN Notebooks ON ("NotebookExternalId" = "Notebooks"."ExternalId")
WHERE LOWER("FoldedContent") like LOWER('%genuine contact with the living God%'); """
):

    print("")
    for k, v in row.items():
        print(k, "\t", v)

    print("")
