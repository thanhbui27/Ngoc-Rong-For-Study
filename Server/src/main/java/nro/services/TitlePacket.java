package nro.services;

import java.io.IOException;
import nro.server.io.Message;

/** Fixed -128 wearable-effect payload shared by self and map observers. */
public final class TitlePacket {
    private TitlePacket() { }

    public static Message add(long player, int effect) throws IOException {
        Message msg = new Message(-128);
        msg.writer().writeByte(0);
        msg.writer().writeInt((int) player);
        msg.writer().writeShort(effect);
        msg.writer().writeByte(1);
        msg.writer().writeByte(-1);
        msg.writer().writeShort(50);
        msg.writer().writeByte(-1);
        return msg;
    }

    public static Message remove(long player, int effect) throws IOException {
        Message msg = new Message(-128);
        msg.writer().writeByte(1);
        msg.writer().writeInt((int) player);
        msg.writer().writeShort(effect);
        return msg;
    }
}
