package security;

import static org.junit.Assert.*;
import org.junit.Test;

public class PasswordHashTest {
    @Test
    public void newPasswordsFitAccountColumnAndVerify() {
        String first = PasswordHash.hash("mật khẩu thử 123");
        String second = PasswordHash.hash("mật khẩu thử 123");
        assertTrue(first.length() <= 100);
        assertNotEquals(first, second);
        assertTrue(PasswordHash.matches("mật khẩu thử 123", first));
        assertFalse(PasswordHash.matches("wrong", first));
        assertFalse(PasswordHash.matches("mật khẩu thử 123", "pbkdf2$bad"));
    }

    @Test
    public void legacyPasswordsCanBeMigrated() {
        assertTrue(PasswordHash.isLegacy("old-password"));
        assertTrue(PasswordHash.matches("old-password", "old-password"));
        assertFalse(PasswordHash.matches("wrong", "old-password"));
        assertFalse(PasswordHash.isLegacy(PasswordHash.hash("new-password")));
    }
}
