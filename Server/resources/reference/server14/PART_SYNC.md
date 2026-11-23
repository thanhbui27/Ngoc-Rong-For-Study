# SQL part reconciliation

The two BE SQL dumps, `ngocrong-clean.sql` and `ngocrong.sql`, originally had
identical `part`, `cai_trang` and `mini_pet` rows. No SQL dump from the remote
game server is available. The remote evidence consists of 2,112 item templates
decoded from the Dragonboy252 cache used during a server 14 session, plus the
2,097-part binary fetched from the server resource endpoint.

The BE seed originally contained parts 0–2041. Of the overlapping IDs, 1,167
parts were identical to server 14 and 875 had different frames or types. To
preserve existing BE characters, V6 appends only server 14 parts 2042–2096.
Both seed SQL files now contain those 55 additional rows. The BE code reads
the `part` table in ID order and increments its game-data version to send the
new part count to clients after deployment. Existing part IDs 0–2041 are not
rewritten. The old `update_data/part` file is not the served source here;
`PartManager` serializes the SQL table.

V7 stores all 2,097 observed server parts in a separate `reference_part`
table, including the 875 that conflict with an existing BE part ID. This
preserves the complete remote part set in SQL without replacing any sprite
used by current BE characters. `part.bin` in this directory is the original
binary snapshot.

For costume/avatar items, 299 server 14 templates have the same type, gender,
name and icon ID as the BE seed. Of these, 77 have a known server part ID and
an existing BE `cai_trang` row. Seventy-three head mappings already referred
to the same part frames. V5 and both SQL seeds correct the remaining four:

| Item ID | Item | Old head | Verified head |
| ---: | --- | ---: | ---: |
| 210 | Avatar | 17 | 0 |
| 386 | Nón Noel Xám | 227 | 277 |
| 872 | Avatar Gohan 1 | 857 | 856 |
| 873 | Avatar Gohan 2 | 856 | 857 |

V5 updates an existing DB only when the old head and item identity still match
the checked values. Existing custom changes therefore remain untouched.

The remaining costume and pet mapping cannot be reconstructed exactly from
the observed item template: it has at most one `part_id`, often `-1`, while
the BE needs head/body/leg/bag or pet head/body/leg. Some identical item IDs
have different meanings in this BE fork. No unverified mapping was inserted
into `cai_trang` or `mini_pet`; doing so would change existing characters to
unrelated sprites. The reference catalog retains all observed metadata for
future reconciliation.
