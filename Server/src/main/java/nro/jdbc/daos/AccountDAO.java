package nro.jdbc.daos;

import security.PasswordHash;

import nro.jdbc.DBService;
import nro.server.Manager;
import nro.server.io.Session;
import nro.utils.Log;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Timestamp;

/**
 *
 * @author 💖 YTB ThanhBN 💖
 * 
 *
 */
public class AccountDAO {

    public static boolean updateAccount(Session session, String newPassword) {
        try (Connection con = DBService.gI().getConnectionForGetPlayer();
                PreparedStatement ps = con.prepareStatement(
                        "update account set password = ? where id = ? and username = ?")) {
            ps.setString(1, PasswordHash.hash(newPassword));
            ps.setInt(2, session.userId);
            ps.setString(3, session.uu);
            return ps.executeUpdate() == 1;
        } catch (Exception e) {
            Log.error(AccountDAO.class, e);
            return false;
        }
    }

    public static void updateLastTimeLoginAllAccount() {
        try (Connection con = DBService.gI().getConnectionForGame();
                PreparedStatement ps = con.prepareStatement("update account set last_time_login = '2000-01-01', "
                        + "last_time_logout = '2001-01-01' where server_login = ?")) {
            ps.setInt(1, Manager.SERVER);
            ps.executeUpdate();
        } catch (Exception e) {
            Log.error(AccountDAO.class, e);
        }
    }

    public static void updateAccoutLogout(Session session) {
        if (session.uu != null && session.pp != null) {
            try (Connection con = DBService.gI().getConnectionForGame();
                    PreparedStatement ps = con.prepareStatement("update account set last_time_logout = ? where id = ?")) {
                ps.setTimestamp(1, new Timestamp(System.currentTimeMillis()));
                ps.setInt(2, session.userId);
                ps.executeUpdate();
            } catch (Exception e) {
                Log.error(AccountDAO.class, e);
            }
        }
    }

    public static void banAccount(Session session) {
        try (Connection con = DBService.gI().getConnectionForGetPlayer();
                PreparedStatement ps = con.prepareStatement("update account set ban = 1 where id = ? and username = ?")) {
            ps.setInt(1, session.userId);
            ps.setString(2, session.uu);
            ps.executeUpdate();
        } catch (Exception e) {
            Log.error(AccountDAO.class, e);
        }
    }

    public static int createAccount(String user, String password) {
        try (Connection con = DBService.gI().getConnectionForGetPlayer()) {
            try (PreparedStatement check = con.prepareStatement("select id from account where username = ?")) {
                check.setString(1, user);
                try (ResultSet existing = check.executeQuery()) {
                    if (existing.next()) {
                        System.out.println("Tạo thất bại do tài khoản đã tồn tại");
                        return -1;
                    }
                }
            }
            try (PreparedStatement insert = con.prepareStatement("insert into account(username,password) values (?,?)",
                    Statement.RETURN_GENERATED_KEYS)) {
                insert.setString(1, user);
                insert.setString(2, PasswordHash.hash(password));
                insert.executeUpdate();
                try (ResultSet keys = insert.getGeneratedKeys()) {
                    if (keys.next()) {
                        System.out.println("Tạo tài khoản thành công!");
                        return keys.getInt(1);
                    }
                }
            }
        } catch (Exception e) {
            Log.error(AccountDAO.class, e);
        }
        return -1;
    }

}
