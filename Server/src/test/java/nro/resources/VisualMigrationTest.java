package nro.resources;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;
import org.junit.Test;
import static org.junit.Assert.*;

public class VisualMigrationTest {
    private int scalar(Statement statement, String sql) throws Exception {
        try (ResultSet result = statement.executeQuery(sql)) {
            result.next();
            return result.getInt(1);
        }
    }

    @Test public void repairsOnlyMatchingLegacyRowsAndIsRepeatable() throws Exception {
        try (Connection connection = DriverManager.getConnection("jdbc:h2:mem:visual_repair;MODE=MySQL");
                Statement statement = connection.createStatement()) {
            statement.execute("CREATE TABLE item_template(id INT PRIMARY KEY, TYPE INT, NAME VARCHAR, icon_id INT)");
            statement.execute("CREATE TABLE cai_trang(id_temp INT, head INT, body INT, leg INT)");
            statement.execute("CREATE TABLE pet_follow(id_temp INT, icon INT, width INT, height INT, frame INT)");
            statement.execute("CREATE TABLE mini_pet(id_temp INT)");
            statement.execute("CREATE TABLE reference_item_template(source_server VARCHAR, id INT, item_type INT, name VARCHAR, icon_id INT)");
            statement.execute("INSERT INTO item_template VALUES (1287,35,'Book',1),(1288,5,'Costume',2),(1318,99,'Custom',3),(1350,0,'',4),"
                    + "(2053,5,'Adopted costume',55),(2062,5,'Custom costume',66),(2097,72,'Dragon',14069),(2098,72,'Other',14070)");
            statement.execute("INSERT INTO cai_trang VALUES (1287,1273,1274,1275),(1288,1276,1277,1278),(1318,90,91,92),(1350,1243,1244,1245)");
            statement.execute("INSERT INTO pet_follow VALUES (2053,1,32,32,3),(2062,2,32,32,3),(2097,14069,75,75,8),(2098,14070,75,75,8)");
            statement.execute("INSERT INTO mini_pet VALUES (2053),(2062)");
            statement.execute("INSERT INTO reference_item_template VALUES ('dragon14.teamobi.com:18001',2053,5,'Adopted costume',55),"
                    + "('dragon14.teamobi.com:18001',2062,5,'Original source name',66)");
            Path file = Path.of("db/migrations/V25__repair_stale_visual_mappings.sql");
            if (!Files.isRegularFile(file)) file = Path.of("../db/migrations/V25__repair_stale_visual_mappings.sql");
            String sql = Files.readString(file).replaceAll("(?m)^--.*$", "");
            for (int run = 0; run < 2; run++) {
                for (String query : sql.split(";")) if (!query.isBlank()) statement.execute(query);
                assertEquals(2, scalar(statement, "SELECT COUNT(*) FROM cai_trang"));
                assertEquals(1, scalar(statement, "SELECT COUNT(*) FROM cai_trang WHERE id_temp=1288"));
                assertEquals(1, scalar(statement, "SELECT COUNT(*) FROM cai_trang WHERE id_temp=1318"));
                assertEquals(0, scalar(statement, "SELECT COUNT(*) FROM pet_follow WHERE id_temp=2053"));
                assertEquals(1, scalar(statement, "SELECT COUNT(*) FROM pet_follow WHERE id_temp=2062"));
                assertEquals(1, scalar(statement, "SELECT frame FROM pet_follow WHERE id_temp=2097"));
                assertEquals(17, scalar(statement, "SELECT width FROM pet_follow WHERE id_temp=2097"));
                assertEquals(8, scalar(statement, "SELECT frame FROM pet_follow WHERE id_temp=2098"));
                assertEquals(1, scalar(statement, "SELECT COUNT(*) FROM mini_pet WHERE id_temp=2062"));
                assertEquals(8, scalar(statement, "SELECT COUNT(*) FROM item_template"));
            }
        }
    }
}
