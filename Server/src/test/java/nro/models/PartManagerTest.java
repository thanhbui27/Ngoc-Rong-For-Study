package nro.models;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;

import org.junit.Test;

public class PartManagerTest {

    @Test
    public void padsMalformedBodyAndLegPartsToClientFrameCounts() {
        int[][] threeFrames = {{1, 2, 3}, {4, 5, 6}, {7, 8, 9}};

        int[][] body = PartManager.normalizePartData(1904, (byte) 1, threeFrames);
        int[][] leg = PartManager.normalizePartData(1905, (byte) 2, threeFrames);

        assertEquals(17, body.length);
        assertEquals(14, leg.length);
        assertArrayEquals(threeFrames[2], body[2]);
        assertArrayEquals(new int[] {0, 0, 0}, body[16]);
        assertArrayEquals(new int[] {0, 0, 0}, leg[13]);
    }

    @Test
    public void rejectsUnsupportedPartType() {
        assertThrows(IllegalStateException.class,
                () -> PartManager.normalizePartData(42, (byte) 4, new int[0][]));
    }
}
