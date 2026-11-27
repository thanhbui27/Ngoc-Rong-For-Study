"""Open the native folder picker for the local Clone Studio UI."""

from __future__ import annotations

import sys
from pathlib import Path
from tkinter import Tk, filedialog


def main() -> None:
    initial = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home()
    while not initial.is_dir() and initial != initial.parent:
        initial = initial.parent
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(parent=root, initialdir=str(initial),
                                           title="Chọn thư mục lưu dữ liệu clone", mustexist=True)
        if selected:
            print(str(Path(selected).resolve()), flush=True)
    finally:
        root.destroy()


if __name__ == "__main__":
    main()
