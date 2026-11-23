# Ngoc-Rong-For-Study

Source code for the Ngọc Rồng game and login servers, with a clean MariaDB seed. This repository is for study and local development.

## Build

Requires JDK 17+ and Maven. Run `mvn clean package` in both `Login` and `Server`, then copy each `target/*-jar-with-dependencies.jar` to `Login/Login.jar` and `Server/Server.jar` respectively. Start each process from its own module directory so relative resource paths resolve.

## Configuration

Copy `.env.example` to `.env`, `Login/server.ini.example` to `Login/server.ini`, and `Server/resources/config/server.properties.example` to `Server/resources/config/server.properties`. Set private passwords and keys in those local files. The two Java configs must use the same database credentials.

`compose.yaml` is an optional MariaDB setup. Check for an existing compatible DB/container before running `docker compose up -d db`; reuse it when available. For a new database, Compose imports `ngocrong-clean.sql`, which contains schema and game templates without existing accounts or characters. The historical `ngocrong.sql` contains old account and character data, is currently tracked in this public repository, and should not be used as the fresh seed.

See [DEPLOY.md](DEPLOY.md) for VPS sizing, ports, and legacy password migration.

## Server 14 costume/pet reference

The observed server 14 item templates and part data are staged under
`Server/resources/reference/server14/`. Migration V4 adds them to a separate
`reference_item_template` table because this fork reuses some item IDs with
different meanings. V5 corrects four verified costume head mappings; V6 adds
the 55 server parts whose IDs are absent from the BE seed; V7 stores all 2,097
server parts in an isolated reference table. Existing part rows
and pet mappings are preserved. Missing downloaded icon and normal/data PNGs have been
filled for zoom levels x1–x4 without overwriting existing files. See the reference
directory's README for provenance, gaps, and reproduction commands.

## Admin item catalog

NPC `Kho admin` appears on Đảo Kame (map 5, near x=1260) only to accounts
whose server session has admin permission. It lists the BE's loaded item
templates by category, 50 items per page. Purchases are free and grant one
plain template item to the admin's bag; no shop-specific bonus options or
special pickup effects are applied. The server checks admin permission,
location, and the currently selected page again when processing each purchase.
Apply `db/migrations/V8__add_admin_catalog_npc.sql` to an existing database
before restarting the game server. Fresh seeds already include NPC template 80.
