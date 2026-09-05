from __future__ import annotations

import json
from html import escape
from pathlib import Path
from threading import Thread
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
SUMMARIES_DIR = ROOT / "summaries"
PORT = 8765


def load_books():
    books = []
    if not SUMMARIES_DIR.exists():
        return books

    for book_dir in sorted(SUMMARIES_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not book_dir.is_dir():
            continue
        files = {
            path.stem: path.read_text(encoding="utf-8", errors="replace")
            for path in book_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".md"
        }
        if not files:
            continue
        books.append(
            {
                "title": book_dir.name,
                "overview": files.get("overview", ""),
                "chapters": files.get("chapters", ""),
                "clippings": files.get("clippings", ""),
            }
        )
    return books


HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Kindle Notes UI</title>
  <style>
    :root {
      --bg: #0f172a;
      --panel: #111827;
      --panel-2: #1f2937;
      --border: #334155;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --accent: #60a5fa;
      --accent-2: #34d399;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: linear-gradient(180deg, var(--bg), #020817);
      color: var(--text);
    }

    .layout {
      display: grid;
      grid-template-columns: 320px 1fr;
      min-height: 100vh;
    }

    .sidebar {
      background: rgba(17, 24, 39, 0.9);
      border-right: 1px solid var(--border);
      padding: 16px;
      overflow-y: auto;
    }

    .sidebar h1 {
      margin: 0 0 16px;
      font-size: 1.3rem;
    }

    .search-box {
      width: 100%;
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: var(--panel-2);
      color: var(--text);
      margin: 0 0 12px;
    }

    .book-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .book-item {
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px 12px;
      cursor: pointer;
      transition: border-color 0.2s ease, transform 0.2s ease;
      text-align: left;
      color: var(--text);
      width: 100%;
    }

    .book-item:hover, .book-item.active {
      border-color: var(--accent);
      transform: translateX(2px);
    }

    .content {
      padding: 20px;
      overflow-y: auto;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border);
    }

    .header h2 {
      margin: 0;
      font-size: 1.8rem;
    }

    .tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }

    .tab {
      background: var(--panel-2);
      color: var(--text);
      border: 1px solid var(--border);
      padding: 8px 12px;
      border-radius: 8px;
      cursor: pointer;
    }

    .tab.active {
      background: var(--accent);
      color: #08111f;
      border-color: var(--accent);
      font-weight: 700;
    }

    .markdown {
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px 20px;
      line-height: 1.6;

    }
    .markdown pre {
      white-space: pre-wrap;       /* Since CSS 2.1 */
      white-space: -moz-pre-wrap;  /* Mozilla, since 1999 */
      white-space: -pre-wrap;      /* Opera 4-6 */
    white-space: -o-pre-wrap;    /* Opera 7 */
    word-wrap: break-word; 
    }

    .placeholder {
      color: var(--muted);
      border: 1px dashed var(--border);
      border-radius: 10px;
      padding: 18px;
      background: rgba(17, 24, 39, 0.4);
    }

    @media (max-width: 800px) {
      .layout {
        grid-template-columns: 1fr;
      }
      .sidebar {
        border-right: none;
        border-bottom: 1px solid var(--border);
      }
    }
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <h1>Kindle Notes</h1>
      <input id="search" class="search-box" type="text" placeholder="Search books..." />
      <div id="book-list" class="book-list"></div>
    </aside>

    <main class="content">
      <div id="empty-state" class="placeholder">Select a book to view its summaries and highlights.</div>
      <div id="book-view" style="display:none;">
        <div class="header">
          <h2 id="book-title">Book</h2>
        </div>
        <div class="tabs">
          <button class="tab active" data-tab="overview">Overview</button>
          <button class="tab" data-tab="chapters">Chapters</button>
          <button class="tab" data-tab="clippings">Clippings</button>
        </div>
        <div id="markdown" class="markdown"></div>
      </div>
    </main>
  </div>

  <script>
    const state = { books: [], selected: null };

    function escapeHtml(value = '') {
      return value
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    function renderBooks() {
      const search = document.getElementById('search').value.trim().toLowerCase();
      const list = document.getElementById('book-list');
      list.innerHTML = '';

      const filtered = state.books.filter((book) =>
        book.title.toLowerCase().includes(search)
      );

      if (!filtered.length) {
        list.innerHTML = '<div class="placeholder">No books found.</div>';
        return;
      }

      filtered.forEach((book) => {
        const btn = document.createElement('button');
        btn.className = 'book-item' + (state.selected && state.selected.title === book.title ? ' active' : '');
        btn.textContent = book.title;
        btn.addEventListener('click', () => selectBook(book));
        list.appendChild(btn);
      });
    }

    function selectBook(book) {
      state.selected = book;
      const bookTitle = document.getElementById('book-title');
      const markdown = document.getElementById('markdown');
      const emptyState = document.getElementById('empty-state');
      const bookView = document.getElementById('book-view');
      bookTitle.textContent = book.title;
      emptyState.style.display = 'none';
      bookView.style.display = 'block';
      renderBooks();
      showTab('overview');
    }

    function showTab(tabName) {
      if (!state.selected) return;

      const tabButtons = document.querySelectorAll('.tab');
      tabButtons.forEach((button) => {
        button.classList.toggle('active', button.dataset.tab === tabName);
      });

      const content = state.selected[tabName] || 'No content available for this section.';
      document.getElementById('markdown').innerHTML = `<pre>${escapeHtml(content)}</pre>`;
    }

    document.getElementById('search').addEventListener('input', renderBooks);
    document.querySelectorAll('.tab').forEach((button) => {
      button.addEventListener('click', () => showTab(button.dataset.tab));
    });

    fetch('/api/books')
      .then((response) => response.json())
      .then((books) => {
        state.books = books;
        renderBooks();
        if (books.length) {
          selectBook(books[0]);
        }
      })
      .catch((error) => {
        const list = document.getElementById('book-list');
        list.innerHTML = '<div class="placeholder">Unable to load books. Check the summaries folder.</div>';
        console.error(error);
      });
  </script>
</body>
</html>
"""


class NotesHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if self.path == "/api/books":
            payload = json.dumps(load_books()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        super().do_GET()

    def log_message(self, format, *args):
        return


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), NotesHandler)
    print(f"Open http://127.0.0.1:{PORT} to view the UI")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down UI server")
        server.server_close()


if __name__ == "__main__":
    main()
