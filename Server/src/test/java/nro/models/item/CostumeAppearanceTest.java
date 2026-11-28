package nro.models.item;

import java.util.Map;
import java.util.function.IntUnaryOperator;
import org.junit.Test;
import static org.junit.Assert.*;

public class CostumeAppearanceTest {
    private final IntUnaryOperator types = id -> Map.of(10, 0, 20, 1, 30, 2, 700, 2).getOrDefault(id, -1);
    private final int[] base = {1, 2, 3, -1};

    private ItemTemplate item(int type, int part) {
        ItemTemplate item = new ItemTemplate();
        item.type = (byte) type;
        item.part = (short) part;
        return item;
    }

    @Test public void fullAndPartialCostumesUseEquippedClothesAsBase() {
        assertArrayEquals(new int[]{10, 20, 30, -1}, CostumeAppearance.resolve(
                item(5, -1), new int[]{10, 20, 30, -1}, base, types));
        assertArrayEquals(new int[]{10, 2, 3, -1}, CostumeAppearance.resolve(
                item(5, -1), new int[]{10, -1, -1, -1}, base, types));
        assertArrayEquals(new int[]{1, 2, 3, -1}, base);
    }

    @Test public void staleMappingCannotPreviewUnrelatedItemTypes() {
        assertNull(CostumeAppearance.resolve(item(0, -1), new int[]{10, 20, 30}, base, types));
        assertNull(CostumeAppearance.resolve(item(21, -1), new int[]{10, 20, 30}, base, types));
    }

    @Test public void missingAndWrongSlotMappingsCannotMasqueradeAsCostumes() {
        assertNull(CostumeAppearance.resolve(item(5, -1), null, base, types));
        assertNull(CostumeAppearance.resolve(item(5, 0), new int[]{-1, -1, -1, -1}, base, types));
        assertNull(CostumeAppearance.resolve(item(5, -1), new int[]{700, 20, 30}, base, types));
        assertNull(CostumeAppearance.resolve(item(5, -1), new int[]{99, 20, 30}, base, types));
    }

    @Test public void legacyTemplatePartUsesItsActualSlot() {
        // Quần đi biển has part 700 (type 2), never head 700.
        assertArrayEquals(new int[]{1, 2, 700, -1}, CostumeAppearance.resolve(
                item(5, 700), null, base, types));
        assertArrayEquals(new int[]{10, 2, 3, -1}, CostumeAppearance.resolve(
                item(5, 10), new int[]{-1, -1, -1, -1}, base, types));
    }
}
