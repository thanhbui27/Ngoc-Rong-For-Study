import com.google.gson.GsonBuilder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;

/** Read-only visual catalog export via an already established local DB tunnel. */
public class ReadVisualDatabase {
    public static void main(String[] args) throws Exception {
        Properties config = new Properties();
        try (var input = Files.newInputStream(Path.of(args[0]))) { config.load(input); }
        int port = Integer.parseInt(args[1]);
        if (port < 1 || port > 65535) throw new IllegalArgumentException("Invalid port");
        String database = config.getProperty("server.db.name");
        if (database == null || !database.matches("[A-Za-z0-9_]+")) throw new IllegalArgumentException("Invalid database");
        String url = "jdbc:mysql://127.0.0.1:" + port + "/" + database
                + "?useUnicode=true&characterEncoding=utf8&connectTimeout=5000&socketTimeout=30000";
        Map<String, Object> result = new LinkedHashMap<>();
        Class.forName("com.mysql.cj.jdbc.Driver");
        try (Connection connection = DriverManager.getConnection(url, config.getProperty("server.db.us"), config.getProperty("server.db.pw"))) {
            connection.setReadOnly(true);
            for (String table : List.of("item_template", "cai_trang", "mini_pet", "pet_follow", "part", "head_avatar",
                    "flag_bag", "img_by_name", "admin_catalog_item_source", "admin_part_alias", "admin_editor_image_alias",
                    "admin_catalog_icon_alias", "reference_item_template", "reference_part", "schema_migrations", "admin_editor_state")) {
                List<Map<String, String>> rows = new ArrayList<>();
                try (Statement statement = connection.createStatement(); ResultSet data = statement.executeQuery("SELECT * FROM `" + table + "`")) {
                    ResultSetMetaData fields = data.getMetaData();
                    while (data.next()) {
                        Map<String, String> row = new LinkedHashMap<>();
                        for (int index = 1; index <= fields.getColumnCount(); index++) row.put(fields.getColumnLabel(index), data.getString(index));
                        rows.add(row);
                    }
                }
                result.put(table, rows);
                System.out.println(table + ": " + rows.size());
            }
        }
        Path output = Path.of(args[2]);
        Files.createDirectories(output.toAbsolutePath().getParent());
        Files.writeString(output, new GsonBuilder().setPrettyPrinting().create().toJson(result));
    }
}
