package nro.tools;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

/** Small game-protocol bridge for the local browser editor. */
public final class GamePartEditorClient implements AutoCloseable {
    private static final int AUTH_RESPONSE_TIMEOUT_MS = 30_000;
    private static final int EDITOR_RESPONSE_TIMEOUT_MS = 60 * 60 * 1_000;
    private final Socket socket = new Socket();
    private final DataInputStream input;
    private final DataOutputStream output;
    private byte[] keys;
    private int readIndex;
    private int writeIndex;
    private int nextRequestId;

    public GamePartEditorClient(String host, int port) throws IOException {
        socket.connect(new InetSocketAddress(host, port), 5_000);
        socket.setSoTimeout(8_000);
        input = new DataInputStream(socket.getInputStream());
        output = new DataOutputStream(socket.getOutputStream());
        output.writeByte(-27);
        output.writeShort(0);
        output.flush();
        int command = input.readByte();
        int length = input.readUnsignedShort();
        if (command != -27 || length < 2 || length > 1024) throw new IOException("Không nhận được handshake từ game server");
        byte[] handshake = new byte[length];
        input.readFully(handshake);
        int keyCount = handshake[0] & 255;
        if (keyCount == 0 || keyCount + 1 > length) throw new IOException("Handshake không hợp lệ");
        keys = new byte[keyCount];
        keys[0] = handshake[1];
        for (int i = 1; i < keyCount; i++) keys[i] = (byte) (handshake[i + 1] ^ keys[i - 1]);
        socket.setSoTimeout(AUTH_RESPONSE_TIMEOUT_MS);
    }

    public synchronized JsonObject request(String action, JsonObject params) throws IOException {
        int requestId = ++nextRequestId;
        JsonObject envelope = new JsonObject();
        envelope.addProperty("action", action);
        envelope.add("params", params);
        byte[] bytes = envelope.toString().getBytes(StandardCharsets.UTF_8);
        if (bytes.length > 5_000_000) throw new IOException("Yêu cầu quá lớn");
        for (int offset = 0; offset < bytes.length; offset += 900) {
            int length = Math.min(900, bytes.length - offset);
            ByteArrayOutputStream frame = new ByteArrayOutputStream(length + 7);
            DataOutputStream data = new DataOutputStream(frame);
            data.writeInt(requestId);
            data.writeBoolean(offset + length >= bytes.length);
            data.writeShort(length);
            data.write(bytes, offset, length);
            send(-126, frame.toByteArray());
        }
        ByteArrayOutputStream reply = new ByteArrayOutputStream();
        while (true) {
            int command = decode(input.readByte(), true) & 255;
            int high = decode(input.readByte(), true) & 255;
            int low = decode(input.readByte(), true) & 255;
            int length = (high << 8) | low;
            if (length > 16_384) throw new IOException("Phản hồi quá lớn cho một gói tin");
            byte[] payload = new byte[length];
            input.readFully(payload);
            for (int i = 0; i < payload.length; i++) payload[i] = decode(payload[i], true);
            if (command != 130) continue; // -126; ignore other game messages
            DataInputStream response = new DataInputStream(new java.io.ByteArrayInputStream(payload));
            int receivedId = response.readInt();
            boolean last = response.readBoolean();
            int chunkSize = response.readUnsignedShort();
            if (receivedId != requestId || chunkSize > response.available()) throw new IOException("Phản hồi part editor không hợp lệ");
            byte[] chunk = new byte[chunkSize];
            response.readFully(chunk);
            reply.write(chunk);
            if (reply.size() > 10_000_000) throw new IOException("Phản hồi vượt giới hạn");
            if (last) break;
        }
        try {
            JsonObject result = JsonParser.parseString(reply.toString(StandardCharsets.UTF_8)).getAsJsonObject();
            if ("auth".equals(action) && !result.has("error")) socket.setSoTimeout(EDITOR_RESPONSE_TIMEOUT_MS);
            return result;
        }
        catch (Exception ex) { throw new IOException("JSON phản hồi không hợp lệ", ex); }
    }

    private void send(int command, byte[] payload) throws IOException {
        output.writeByte(decode((byte) command, false));
        output.writeByte(decode((byte) (payload.length >> 8), false));
        output.writeByte(decode((byte) payload.length, false));
        for (byte b : payload) output.writeByte(decode(b, false));
        output.flush();
    }

    private byte decode(byte value, boolean read) {
        int index = read ? readIndex++ : writeIndex++;
        return (byte) (value ^ keys[index % keys.length]);
    }

    @Override public void close() throws IOException { socket.close(); }
}
