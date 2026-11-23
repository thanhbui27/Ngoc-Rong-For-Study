# Server 14 costume and pet reference

This directory stages data observed while Dragonboy252 was connected to
`dragon14.teamobi.com:18001`. The item templates in `item-templates.json` were
decoded from the client cache used in that live session. `part.bin` was fetched
from the server resource endpoint. The decoded item export and part file hashes
are recorded in the JSON. No `ngocrong*.sql` data was used to construct it.

There are 487 type-5 costume/avatar templates and 112 type-18 pet templates.
An item template supplies a name, description, icon ID, one part ID and a few
basic fields. It **does not supply per-item combat option values** or the full
head/body/leg/bag and pet head/body/leg mapping. Most templates have part `-1`.
The item catalog of server 15 has not been verified against server 14, even
though their six downloaded game-data blobs (including part) matched byte for
byte during the capture.

This BE fork has different data at some of the same item IDs. Comparing the
599 relevant IDs with `ngocrong-clean.sql` found 378 differing rows, including
272 differences in type. The BE's served part blob is generated from its SQL
`part` table; its older `update_data/part` file is different from the observed
file and is not used by `PartManager`. V4 imports the observed templates into
**`reference_item_template`**, separate from runtime `item_template`.
V5 corrects four costume head mappings verified against both item identity and
part frames. V6 appends only the 55 non-colliding part IDs 2042–2096. V7 puts
all 2,097 observed parts into a separate `reference_part` SQL table. Existing
item identities, old part rows and pet mappings remain unchanged. The
migrations are applied by the normal runner on deployment; adding these files
alone does not alter a running database.

Missing icon PNGs across all downloaded IDs were added to
`Server/resources/normal/image/{1,2,3,4}/icon/`. Sources were the selected
server 14 download plus the broader server 15 part-image download. Their 404
overlapping selected images at each zoom had identical SHA-256 bytes. Missing
`data/zoomN` PNGs from the server 15 download were also copied to the matching
`Server/resources/normal/data/N` trees. Both sync scripts use exclusive file
creation, so existing BE files are never overwritten. The original runtime
`update_data` files were left as they were.

See [IMAGE_AUDIT.md](IMAGE_AUDIT.md) for byte and pixel comparisons with the
existing BE images, including collisions and empty files.
See [PART_SYNC.md](PART_SYNC.md) for the SQL reconciliation and its limits.

To reproduce the reference snapshot from the captured files in this workspace:

```powershell
python tools/build_observed_catalog.py '..\NRO-server14-assets\items-from-client.json' '..\NRO-server14-assets\game-data\part.bin'
python tools/compare_observed_items.py '..\NRO-server14-assets\items-from-client.json'
python tools/sync_observed_icons.py --server14 '..\NRO-server14-assets' --server15 '..\NRO-server15-assets' --min-id 0
python tools/sync_observed_data.py --server15 '..\NRO-server15-assets'
```

The last two commands are dry runs; add `--apply` to copy absent PNGs. Before
enabling an observed costume or pet in gameplay, verify a unique ID in this BE
fork and obtain its full model mapping in the matching part namespace.
