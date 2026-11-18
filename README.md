# Ngoc-Rong-For-Study

Source code for the Ngọc Rồng game and login servers, with a clean MariaDB seed. This repository is for study and local development.

## Build

Requires JDK 17+ and Maven. Run `mvn clean package` in both `Login` and `Server`, then copy each `target/*-jar-with-dependencies.jar` to `Login/Login.jar` and `Server/Server.jar` respectively. Start each process from its own module directory so relative resource paths resolve.

## Configuration

Copy `.env.example` to `.env`, `Login/server.ini.example` to `Login/server.ini`, and `Server/resources/config/server.properties.example` to `Server/resources/config/server.properties`. Set private passwords and keys in those local files. The two Java configs must use the same database credentials.

`compose.yaml` is an optional MariaDB setup. Check for an existing compatible DB/container before running `docker compose up -d db`; reuse it when available. For a new database, Compose imports `ngocrong-clean.sql`, which contains schema and game templates without existing accounts or characters. The historical `ngocrong.sql` contains old account and character data, is currently tracked in this public repository, and should not be used as the fresh seed.

See [DEPLOY.md](DEPLOY.md) for VPS sizing, ports, and legacy password migration.
