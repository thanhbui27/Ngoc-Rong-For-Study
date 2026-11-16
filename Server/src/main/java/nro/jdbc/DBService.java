package nro.jdbc;

import java.sql.Connection;
import java.sql.SQLException;
import nro.utils.Log;

/** Provides an independent pooled connection for each database operation. */
public class DBService {

    public static String DRIVER = "com.mysql.cj.jdbc.Driver";
    public static String URL = "jdbc:#0://#1:#2/#3";
    public static String DB_HOST = "localhost";
    public static int DB_PORT = 3306;
    public static String DB_NAME = "";
    public static String DB_USER = "root";
    public static String DB_PASSWORD = "";
    public static int MIN_IDLE = 2;
    public static int MAX_POOL_SIZE = 12;
    public static boolean CACHE_PREPARED_STATEMENTS = true;
    public static int PREPARED_STATEMENT_CACHE_SIZE = 50;
    public static int PREPARED_STATEMENT_SQL_LIMIT = 2048;

    private static final DBService INSTANCE = new DBService();

    public static DBService gI() {
        return INSTANCE;
    }

    public Connection getConnectionForLogin() throws SQLException { return getConnection(); }
    public Connection getConnectionForLogout() throws SQLException { return getConnection(); }
    public Connection getConnectionForSaveData() throws SQLException { return getConnection(); }
    public Connection getConnectionForGame() throws SQLException { return getConnection(); }
    public Connection getConnectionForClan() throws SQLException { return getConnection(); }
    public Connection getConnectionForAutoSave() throws SQLException { return getConnection(); }
    public Connection getConnectionForSaveHistory() throws SQLException { return getConnection(); }
    public Connection getConnectionForGetPlayer() throws SQLException { return getConnection(); }
    public Connection getConnectionCreatPlayer() throws SQLException { return getConnection(); }

    public Connection getConnection() throws SQLException {
        return DBHika.getConnection();
    }

    public void release(Connection connection) {
        if (connection != null) {
            try {
                connection.close();
            } catch (SQLException e) {
                Log.error(DBService.class, e, "Cannot return database connection to pool");
            }
        }
    }
}
