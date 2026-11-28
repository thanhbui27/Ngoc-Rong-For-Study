package nro.services;

import java.io.ByteArrayInputStream;
import java.io.DataInputStream;
import org.junit.Test;
import static org.junit.Assert.*;

public class TitlePacketTest {
    @Test public void removalTargetsOnlyTheTitleAndCannotClearBackEffects() throws Exception {
        var message = TitlePacket.remove(45, 214);
        assertEquals(-128, message.command);
        assertEquals(7, message.getData().length);
        var reader = new DataInputStream(new ByteArrayInputStream(message.getData()));
        assertEquals(1, reader.readByte());
        assertEquals(45, reader.readInt());
        assertEquals(214, reader.readShort());
        assertEquals(0, reader.available());
    }
    @Test public void titlePayloadHasExactlyOneEffectIdAndNoTrailingFields() throws Exception {
        var message = TitlePacket.add(45, 214);
        assertEquals(-128, message.command);
        assertEquals(12, message.getData().length);
        var reader = new DataInputStream(new ByteArrayInputStream(message.getData()));
        assertEquals(0, reader.readByte());
        assertEquals(45, reader.readInt());
        assertEquals(214, reader.readShort());
        assertEquals(1, reader.readByte());
        assertEquals(-1, reader.readByte());
        assertEquals(50, reader.readShort());
        assertEquals(-1, reader.readByte());
        assertEquals(0, reader.available());
    }
}
