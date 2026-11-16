package security;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.ArrayList;
import java.util.List;
import server.Config;

/** One-time migration for accounts imported from an older SQL dump. */
public final class PasswordMigration {
    private record Account(int id, String password) {
    }

    private PasswordMigration() {
    }

    public static void main(String[] args) throws Exception {
        boolean apply = args.length == 1 && "--apply".equals(args[0]);
        if (args.length > 0 && !apply) {
            throw new IllegalArgumentException("Usage: PasswordMigration [--apply]");
        }
        Config config = new Config(System.getProperty("nro.login.config", "server.ini"));
        Class.forName(config.getDriver());
        int legacyCount = 0;
        int updatedCount = 0;
        int lastId = 0;
        try (Connection connection = DriverManager.getConnection(
                config.getJdbcUrl(), config.getUsername(), config.getPassword());
                PreparedStatement select = connection.prepareStatement(
                        "SELECT id, password FROM account WHERE id > ? ORDER BY id LIMIT 100");
                PreparedStatement update = connection.prepareStatement(
                        "UPDATE account SET password = ? WHERE id = ? AND password = ?")) {
            while (true) {
                select.setInt(1, lastId);
                List<Account> batch = new ArrayList<>();
                try (ResultSet result = select.executeQuery()) {
                    while (result.next()) {
                        batch.add(new Account(result.getInt("id"), result.getString("password")));
                    }
                }
                if (batch.isEmpty()) {
                    break;
                }
                for (Account account : batch) {
                    if (PasswordHash.isLegacy(account.password())) {
                        legacyCount++;
                        if (apply) {
                            update.setString(1, PasswordHash.hash(account.password()));
                            update.setInt(2, account.id());
                            update.setString(3, account.password());
                            updatedCount += update.executeUpdate();
                        }
                    }
                }
                lastId = batch.get(batch.size() - 1).id();
            }
        }
        System.out.println("Legacy passwords: " + legacyCount);
        if (apply) {
            System.out.println("Passwords migrated: " + updatedCount);
        } else {
            System.out.println("Dry run only. Pass --apply to migrate.");
        }
    }
}
