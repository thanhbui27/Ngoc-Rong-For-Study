# Image comparison with the existing BE assets

Audit scope: every downloaded icon from the server 14 selected set and the
server 15 part-image set, plus every downloaded `data/zoomN` PNG. Images were
compared only at the **same ID/path and zoom level**. Byte SHA-256 was checked
first; byte-different PNGs were decoded and compared pixel by pixel with
System.Drawing. Existing BE files were identified from Git-tracked paths
before these imports; the new files are untracked until committed.

| Zoom | Downloaded icon IDs | Existing icons pixel-identical | Existing icons pixel-different | Existing empty files | New icons copied | Missing after sync |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| x1 | 14,234 | 0 | 9,925 | 12 | 4,297 | 0 |
| x2 | 14,233 | 893 | 9,203 | 10 | 4,127 | 0 |
| x3 | 14,233 | 846 | 9,250 | 10 | 4,127 | 0 |
| x4 | 14,233 | 9,952 | 248 | 0 | 4,033 | 0 |

| Zoom | Downloaded `data` PNGs | Existing pixel-identical | Existing pixel-different | New copied | Missing after sync |
| --- | ---: | ---: | ---: | ---: | ---: |
| x1 | 118 | 92 | 0 | 26 | 0 |
| x2 | 1,248 | 935 | 93 | 220 | 0 |
| x3 | 1,249 | 931 | 94 | 224 | 0 |
| x4 | 1,245 | 949 | 77 | 219 | 0 |

The pre-existing pixel-different files and the 0-byte files were **not
overwritten**. For example, BE's x1 icon `2955.png` is an existing 0-byte
file, while the downloaded image is a valid PNG. The explicit "skip existing"
rule leaves that path untouched. Some x4 collisions also have different
dimensions; icon 16840 is 248×216 in BE and 188×140 in the downloaded set.

Among downloaded icons, exact PNG duplicates occur across distinct IDs:
235 groups at x1, 182 at x2, 182 at x3 and 216 at x4. For example, IDs 17
and 17698 have identical x4 PNG bytes. These are shared graphics, not missing
files; no deduplication changed their ID paths. The 404 selected icons found
in both server 14 and server 15 downloads at each zoom were byte-identical.

Reproduce with `tools/audit_observed_images.py` (byte hashes) followed by
`tools/audit_observed_pixels.ps1` (pixel comparison). Neither script writes to
the asset trees.
