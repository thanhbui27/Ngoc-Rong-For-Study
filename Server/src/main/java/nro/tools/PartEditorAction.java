package nro.tools;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.concurrent.ConcurrentHashMap;
import nro.jdbc.DBService;
import nro.server.io.Message;
import nro.server.io.Session;
import security.PasswordHash;

/** Admin-only part editor action carried by the existing game connection. */
public final class PartEditorAction {
    private static final int MAX_REQUEST = 5_000_000;
    private static final int REPLY_CHUNK = 8_192;
    private static final ConcurrentHashMap<String, Attempts> AUTH_ATTEMPTS = new ConcurrentHashMap<>();

    private static final class Attempts {
        int failures;
        long until;
    }

    private PartEditorAction() {}

    public static void handle(Session session, Message message) {
        int requestId = -1;
        try {
            requestId = message.reader().readInt();
            boolean last = message.reader().readBoolean();
            int size = message.reader().readUnsignedShort();
            if (size > 900 || size > message.reader().available()) throw new IllegalArgumentException("Gói tin không hợp lệ");
            if (session.partEditorRequest == null || session.partEditorRequestId != requestId) {
                session.partEditorRequest = new ByteArrayOutputStream();
                session.partEditorRequestId = requestId;
            }
            if (session.partEditorRequest.size() + size > MAX_REQUEST) throw new IllegalArgumentException("Yêu cầu quá lớn");
            byte[] chunk = new byte[size];
            message.reader().readFully(chunk);
            session.partEditorRequest.write(chunk);
            if (!last) return;
            JsonObject envelope = JsonParser.parseString(session.partEditorRequest.toString(StandardCharsets.UTF_8)).getAsJsonObject();
            session.partEditorRequest = null;
            String action = envelope.get("action").getAsString();
            JsonObject request = envelope.getAsJsonObject("params");
            if (request == null) request = new JsonObject();
            JsonObject result;
            if ("auth".equals(action)) {
                authenticate(session, request);
                result = new JsonObject();
                result.addProperty("ok", true);
            } else {
                if (!session.partEditorAuthenticated) throw new SecurityException("Cần đăng nhập tài khoản admin");
                result = PartEditorServer.executeGameAction(action, request);
            }
            reply(session, requestId, result);
        } catch (Exception ex) {
            session.partEditorRequest = null;
            JsonObject error = new JsonObject();
            error.addProperty("error", ex.getMessage() == null ? "Lỗi xử lý action" : ex.getMessage());
            reply(session, requestId, error);
        }
    }

    private static void authenticate(Session session, JsonObject request) throws Exception {
        session.partEditorAuthenticated = false;
        Attempts attempts = AUTH_ATTEMPTS.computeIfAbsent(session.ipAddress, key -> new Attempts());
        synchronized (attempts) {
            if (System.currentTimeMillis() > attempts.until) attempts.failures = 0;
            if (attempts.failures >= 5) throw new SecurityException("Thử lại sau một phút");
        }
        String username = request.get("username").getAsString();
        String password = request.get("password").getAsString();
        if (username.length() > 128 || password.length() > 256) throw new SecurityException("Tài khoản không hợp lệ");
        try (Connection connection = DBService.gI().getConnectionForLogin();
             PreparedStatement statement = connection.prepareStatement(
                     "SELECT password,is_admin,ban FROM account WHERE username=? LIMIT 1")) {
            statement.setString(1, username);
            try (ResultSet row = statement.executeQuery()) {
                if (!row.next() || !row.getBoolean("is_admin") || row.getBoolean("ban")
                        || !PasswordHash.matches(password, row.getString("password"))) {
                    synchronized (attempts) {
                        attempts.failures++;
                        attempts.until = System.currentTimeMillis() + 60_000;
                    }
                    throw new SecurityException("Sai tài khoản admin hoặc mật khẩu");
                }
            }
        }
        AUTH_ATTEMPTS.remove(session.ipAddress);
        session.partEditorAuthenticated = true;
        // The normal game login clears this countdown too. Part Studio authenticates
        // separately, so otherwise Client.update() disconnects it after ~40 seconds.
        session.timeWait = 0;
    }

    private static void reply(Session session, int requestId, JsonObject result) {
        byte[] bytes = result.toString().getBytes(StandardCharsets.UTF_8);
        for (int offset = 0; offset < bytes.length; offset += REPLY_CHUNK) {
            int length = Math.min(REPLY_CHUNK, bytes.length - offset);
            Message response = new Message(-126);
            try {
                response.writer().writeInt(requestId);
                response.writer().writeBoolean(offset + length >= bytes.length);
                response.writer().writeShort(length);
                response.writer().write(bytes, offset, length);
                session.doSendMessage(response);
            } catch (Exception ignored) {
                response.cleanup();
                return;
            }
        }
    }
}
