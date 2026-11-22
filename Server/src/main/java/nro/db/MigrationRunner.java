package nro.db;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Applies forward-only, versioned SQL migrations from the repository. */
public final class MigrationRunner {

    private static final String HISTORY_TABLE = "schema_migrations";
    private static final Pattern FILE_NAME = Pattern.compile("V([0-9]+)__([A-Za-z0-9_-]+)\\.sql");

    private MigrationRunner() {
    }

    public static void main(String[] args) throws Exception {
        boolean apply = Arrays.asList(args).contains("--apply");
        if (apply && Arrays.asList(args).contains("--dry-run")) {
            throw new IllegalArgumentException("Choose either --dry-run or --apply, not both.");
        }
        for (String arg : args) {
            if (!"--apply".equals(arg) && !"--dry-run".equals(arg)) {
                throw new IllegalArgumentException("Usage: MigrationRunner [--dry-run|--apply]");
            }
        }

        Path configPath = Path.of(System.getProperty("nro.server.config",
                "Server/resources/config/server.properties"));
        Path migrationsPath = Path.of(System.getProperty("nro.migrations.dir", "db/migrations"));
        Properties config = loadProperties(configPath);
        String host = required(config, "server.db.ip");
        String port = config.getProperty("server.db.port", "3306").trim();
        String database = required(config, "server.db.name");
        String user = required(config, "server.db.us");
        String password = required(config, "server.db.pw");
        String driver = config.getProperty("server.db.driver", "com.mysql.cj.jdbc.Driver").trim();
        String url = "jdbc:mysql://" + host + ":" + port + "/" + database
                + "?useUnicode=true&characterEncoding=utf8&serverTimezone=UTC";

        Class.forName(driver);
        List<Migration> migrations = loadMigrations(migrationsPath);
        try (Connection connection = DriverManager.getConnection(url, user, password)) {
            boolean historyExists = historyTableExists(connection);
            if (apply && !historyExists) {
                ensureHistoryTable(connection);
                historyExists = true;
            }
            Map<String, String> applied = historyExists ? loadApplied(connection) : Map.of();
            List<Migration> pending = new ArrayList<>();

            for (Migration migration : migrations) {
                String existingChecksum = applied.get(migration.version);
                if (existingChecksum == null) {
                    pending.add(migration);
                } else if (!existingChecksum.equals(migration.checksum)) {
                    throw new IllegalStateException("Applied migration V" + migration.version
                            + " has changed. Add a new migration instead of editing an applied file: "
                            + migration.path.getFileName());
                }
            }

            System.out.printf("Database: %s@%s:%s/%s%n", user, host, port, database);
            if (pending.isEmpty()) {
                System.out.println("No pending database migrations.");
                return;
            }
            for (Migration migration : pending) {
                System.out.println((apply ? "Applying " : "Pending ") + migration.path.getFileName());
            }
            if (!apply) {
                System.out.println("Dry run only. Pass --apply to execute pending migrations.");
                return;
            }

            for (Migration migration : pending) {
                applyMigration(connection, migration);
            }
            System.out.println("Database migrations complete.");
        }
    }

    private static Properties loadProperties(Path path) throws IOException {
        Properties properties = new Properties();
        try (var input = Files.newInputStream(path)) {
            properties.load(input);
        }
        return properties;
    }

    private static String required(Properties properties, String key) {
        String value = properties.getProperty(key);
        if (value == null || value.isBlank() || value.startsWith("replace-with-")) {
            throw new IllegalStateException("Missing or placeholder database setting: " + key);
        }
        return value.trim();
    }

    private static List<Migration> loadMigrations(Path directory) throws Exception {
        if (!Files.isDirectory(directory)) {
            throw new IllegalStateException("Migration directory not found: " + directory.toAbsolutePath());
        }
        List<Migration> migrations = new ArrayList<>();
        try (var files = Files.list(directory)) {
            for (Path path : files.filter(Files::isRegularFile).sorted().toList()) {
                Matcher matcher = FILE_NAME.matcher(path.getFileName().toString());
                if (!matcher.matches()) {
                    throw new IllegalStateException("Invalid migration filename: " + path.getFileName());
                }
                if (matcher.group(1).length() > 32) {
                    throw new IllegalStateException("Migration version is too long: " + path.getFileName());
                }
                byte[] bytes = Files.readAllBytes(path);
                migrations.add(new Migration(matcher.group(1), matcher.group(2), path,
                        new String(bytes, StandardCharsets.UTF_8), sha256(bytes)));
            }
        }
        migrations.sort(Comparator.comparing(migration -> new java.math.BigInteger(migration.version)));
        for (int i = 1; i < migrations.size(); i++) {
            if (new java.math.BigInteger(migrations.get(i - 1).version)
                    .equals(new java.math.BigInteger(migrations.get(i).version))) {
                throw new IllegalStateException("Duplicate migration version: V" + migrations.get(i).version);
            }
        }
        return migrations;
    }

    private static void ensureHistoryTable(Connection connection) throws SQLException {
        String sql = "CREATE TABLE IF NOT EXISTS `" + HISTORY_TABLE + "` ("
                + "`version` VARCHAR(32) NOT NULL PRIMARY KEY,"
                + "`description` VARCHAR(200) NOT NULL,"
                + "`checksum` CHAR(64) NOT NULL,"
                + "`installed_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                + ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";
        try (Statement statement = connection.createStatement()) {
            statement.execute(sql);
        }
    }

    private static boolean historyTableExists(Connection connection) throws SQLException {
        try (ResultSet results = connection.getMetaData().getTables(
                connection.getCatalog(), null, HISTORY_TABLE, new String[] { "TABLE" })) {
            return results.next();
        }
    }

    private static Map<String, String> loadApplied(Connection connection) throws SQLException {
        Map<String, String> applied = new HashMap<>();
        try (Statement statement = connection.createStatement();
                ResultSet results = statement.executeQuery(
                        "SELECT `version`, `checksum` FROM `" + HISTORY_TABLE + "`")) {
            while (results.next()) {
                applied.put(results.getString(1), results.getString(2));
            }
        }
        return applied;
    }

    private static void applyMigration(Connection connection, Migration migration) throws Exception {
        boolean oldAutoCommit = connection.getAutoCommit();
        connection.setAutoCommit(false);
        try {
            try (Statement statement = connection.createStatement()) {
                for (String sql : splitStatements(migration.sql)) {
                    statement.execute(sql);
                }
            }
            try (PreparedStatement statement = connection.prepareStatement(
                    "INSERT INTO `" + HISTORY_TABLE + "` (`version`, `description`, `checksum`) VALUES (?, ?, ?)")) {
                statement.setString(1, migration.version);
                statement.setString(2, migration.description);
                statement.setString(3, migration.checksum);
                statement.executeUpdate();
            }
            connection.commit();
        } catch (Exception e) {
            connection.rollback();
            throw new IllegalStateException("Migration " + migration.path.getFileName()
                    + " failed; transaction rolled back where supported.", e);
        } finally {
            connection.setAutoCommit(oldAutoCommit);
        }
    }

    private static List<String> splitStatements(String script) {
        List<String> statements = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        char quote = 0;
        boolean lineComment = false;
        boolean blockComment = false;
        for (int i = 0; i < script.length(); i++) {
            char c = script.charAt(i);
            char next = i + 1 < script.length() ? script.charAt(i + 1) : 0;
            if (lineComment) {
                if (c == '\n') {
                    lineComment = false;
                    current.append('\n');
                }
                continue;
            }
            if (blockComment) {
                if (c == '*' && next == '/') {
                    blockComment = false;
                    i++;
                }
                continue;
            }
            if (quote == 0 && c == '-' && next == '-' && (i + 2 == script.length()
                    || Character.isWhitespace(script.charAt(i + 2)))) {
                lineComment = true;
                i++;
                continue;
            }
            if (quote == 0 && c == '#') {
                lineComment = true;
                continue;
            }
            if (quote == 0 && c == '/' && next == '*') {
                blockComment = true;
                i++;
                continue;
            }
            if (quote != 0) {
                current.append(c);
                if (c == '\\' && i + 1 < script.length()) {
                    current.append(script.charAt(++i));
                } else if (c == quote) {
                    if (next == quote) {
                        current.append(script.charAt(++i));
                    } else {
                        quote = 0;
                    }
                }
                continue;
            }
            if (c == '\'' || c == '"' || c == '`') {
                quote = c;
                current.append(c);
            } else if (c == ';') {
                addStatement(statements, current);
            } else {
                current.append(c);
            }
        }
        if (quote != 0 || blockComment) {
            throw new IllegalArgumentException("Unclosed quote or block comment in migration SQL.");
        }
        addStatement(statements, current);
        return statements;
    }

    private static void addStatement(List<String> statements, StringBuilder current) {
        String sql = current.toString().trim();
        if (!sql.isEmpty()) {
            statements.add(sql);
        }
        current.setLength(0);
    }

    private static String sha256(byte[] bytes) throws NoSuchAlgorithmException {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
        StringBuilder hex = new StringBuilder(digest.length * 2);
        for (byte value : digest) {
            hex.append(String.format("%02x", value));
        }
        return hex.toString();
    }

    private record Migration(String version, String description, Path path, String sql, String checksum) {
    }
}
