// Decompiled with: VMN
package server;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Properties;

public class Config {

    private short listen;
    private String driver;
    private String username;
    private String password;
    private String dbName;
    private String host;
    private short port;
    private int poolMinimumIdle;
    private int poolMaximumSize;
    private short testmode;
    private int secondWaitLogin;

    public Config(String path) {
        try (InputStreamReader input = new InputStreamReader(
                new FileInputStream(new File(path)), StandardCharsets.UTF_8)) {
            System.out.println("load config");
            Properties props = new Properties();
            props.load(input);
            this.listen = Short.parseShort(props.getProperty("server.port"));
            this.driver = props.getProperty("db.driver");
            this.username = props.getProperty("db.user");
            this.password = props.getProperty("db.password");
            this.dbName = props.getProperty("db.name");
            this.host = props.getProperty("db.host");
            this.port = Short.parseShort(props.getProperty("db.port"));
            this.poolMinimumIdle = Integer.parseInt(props.getProperty("db.pool.minIdle", "1"));
            this.poolMaximumSize = Integer.parseInt(props.getProperty("db.pool.maxSize", "4"));
            if (poolMinimumIdle < 0 || poolMaximumSize < 1 || poolMinimumIdle > poolMaximumSize) {
                throw new IllegalArgumentException("Invalid login database pool size");
            }
            this.testmode = Short.parseShort(props.getProperty("admin.mode"));
            this.secondWaitLogin = props.containsKey("wait.login")
                    ? (int) Short.parseShort(props.getProperty("wait.login"))
                    : 5;
        } catch (IOException ex) {
            throw new IllegalStateException("Cannot read login config: " + path, ex);
        }
    }

    public String getJdbcUrl() {
        return "jdbc:mysql://" + this.host + ":" + this.port + "/" + this.dbName;
    }

    public int getPoolMinimumIdle() {
        return poolMinimumIdle;
    }

    public int getPoolMaximumSize() {
        return poolMaximumSize;
    }

    public short getListen() {
        return this.listen;
    }

    public String getDriver() {
        return this.driver;
    }

    public String getUsername() {
        return this.username;
    }

    public String getPassword() {
        return this.password;
    }

    public String getDbName() {
        return this.dbName;
    }

    public String getHost() {
        return this.host;
    }

    public short getPort() {
        return this.port;
    }

    public short getTestmode() {
        return this.testmode;
    }

    public int getSecondWaitLogin() {
        return this.secondWaitLogin;
    }

    public void setListen(short listen) {
        this.listen = listen;
    }

    public void setDriver(String driver) {
        this.driver = driver;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public void setPassword(String password) {
        this.password = password;
    }

    public void setDbName(String dbName) {
        this.dbName = dbName;
    }

    public void setHost(String host) {
        this.host = host;
    }

    public void setPort(short port) {
        this.port = port;
    }

    public void setTestmode(short testmode) {
        this.testmode = testmode;
    }

    public void setSecondWaitLogin(int secondWaitLogin) {
        this.secondWaitLogin = secondWaitLogin;
    }
}
