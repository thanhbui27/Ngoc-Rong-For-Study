package nro.jdbc;

import static org.junit.Assert.*;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;
import org.junit.BeforeClass;
import org.junit.Test;

public class DBServiceTest {
    @BeforeClass
    public static void useIsolatedInMemoryDatabase() {
        DBService.DRIVER = "org.h2.Driver";
        DBService.URL = "jdbc:h2:mem:pooltest;DB_CLOSE_DELAY=-1";
        DBService.DB_USER = "sa";
        DBService.DB_PASSWORD = "";
        DBService.MIN_IDLE = 1;
        DBService.MAX_POOL_SIZE = 3;
    }

    @Test
    public void callersGetIndependentConnectionsAndReturnThem() throws Exception {
        try (Connection first = DBService.gI().getConnectionForGame();
                Connection second = DBService.gI().getConnectionForGame()) {
            assertNotSame(first, second);
            try (Statement statement = first.createStatement()) {
                statement.execute("CREATE TABLE connection_test(id INT PRIMARY KEY)");
                statement.execute("INSERT INTO connection_test VALUES (7)");
            }
            first.close();
            assertTrue(second.isValid(1));
            try (Statement statement = second.createStatement();
                    ResultSet result = statement.executeQuery("SELECT id FROM connection_test")) {
                assertTrue(result.next());
                assertEquals(7, result.getInt(1));
            }
        } finally {
            DBHika.close();
        }
    }
}
