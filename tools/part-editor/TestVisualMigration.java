import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import java.sql.ResultSet;
import java.util.Properties;

/** Rehearse visual migrations against isolated temporary copies, never persistent tables. */
public class TestVisualMigration {
    private static int count(Statement statement, String table) throws Exception {
        try (ResultSet result = statement.executeQuery("SELECT COUNT(*) FROM `" + table + "`")) {
            result.next(); return result.getInt(1);
        }
    }

    public static void main(String[] args) throws Exception {
        Properties config = new Properties();
        try (var input = Files.newInputStream(Path.of(args[0]))) { config.load(input); }
        String url = "jdbc:mysql://127.0.0.1:" + Integer.parseInt(args[1]) + "/" + config.getProperty("server.db.name")
                + "?useUnicode=true&characterEncoding=utf8&connectTimeout=5000&socketTimeout=30000";
        Class.forName("com.mysql.cj.jdbc.Driver");
        try (Connection connection = DriverManager.getConnection(url, config.getProperty("server.db.us"), config.getProperty("server.db.pw"));
                Statement statement = connection.createStatement()) {
            StringBuilder migrations = new StringBuilder();
            for (int index = 2; index < args.length; index++) {
                migrations.append(Files.readString(Path.of(args[index]))).append('\n');
            }
            String sql = migrations.toString().replaceAll("(?m)^--.*$", "");
            for (String table : new String[]{"item_template","cai_trang","mini_pet","part","reference_part","reference_item_template", "admin_part_alias", "admin_catalog_item_source","admin_editor_state"}) {
                String isolated = "test_visual_" + table;
                statement.execute("CREATE TEMPORARY TABLE `" + isolated + "` LIKE `" + table + "`");
                statement.execute("INSERT INTO `" + isolated + "` SELECT * FROM `" + table + "`");
                sql = sql.replace("`" + table + "`", "`" + isolated + "`");
            }
            int before = count(statement, "test_visual_mini_pet");
            int persistentBefore = count(statement, "mini_pet");
            int changedFirst = -1;
            for (int round = 0; round < 2; round++) {
                for (String query : sql.split(";")) if (!query.isBlank()) statement.execute(query);
                String wrongSlots = "SELECT COUNT(*) FROM test_visual_mini_pet m "
                        + "JOIN test_visual_item_template i ON i.id=m.id_temp AND i.TYPE IN (18,21) "
                        + "LEFT JOIN test_visual_part h ON h.id=m.head "
                        + "LEFT JOIN test_visual_part b ON b.id=m.body "
                        + "LEFT JOIN test_visual_part l ON l.id=m.leg "
                        + "WHERE h.TYPE IS NULL OR b.TYPE IS NULL OR l.TYPE IS NULL OR h.TYPE<>0 OR b.TYPE<>1 OR l.TYPE<>2";
                try (ResultSet result = statement.executeQuery(wrongSlots)) {
                    result.next();
                    if (args.length > 3 && result.getInt(1) != 0) throw new IllegalStateException("Incorrect pet slots remain");
                }
                int current = count(statement, "test_visual_part");
                if (round == 0) changedFirst = current;
                else if (current != changedFirst) throw new IllegalStateException("Migration is not repeatable");
                System.out.println("Round " + round + ": isolated mini_pet=" + count(statement, "test_visual_mini_pet")
                        + ", isolated part=" + count(statement, "test_visual_part"));
            }
            if (persistentBefore != count(statement, "mini_pet")) throw new IllegalStateException("Persistent data changed");
            System.out.println("Added mappings in isolated tables: " + (count(statement,"test_visual_mini_pet") - before));
            System.out.println("Persistent mini_pet unchanged: " + persistentBefore);
        }
    }
}
