package nro.models.item;

import org.junit.Test;
import static org.junit.Assert.*;

public class VisualEquipmentTest {
    private ItemTemplate item(int id, int type, int part, int gender) {
        ItemTemplate item = new ItemTemplate();
        item.id = (short) id;
        item.type = (byte) type;
        item.part = (short) part;
        item.gender = (byte) gender;
        return item;
    }

    @Test public void renamedAndClonedMountsUseTemplatePartForBothTypes() {
        assertEquals(30012, VisualEquipment.mount(item(1131, 23, 12, 3), 0, p -> p == 12));
        assertEquals(30066, VisualEquipment.mount(item(2136, 24, 66, 3), 2, p -> p == 66));
        assertEquals(30006, VisualEquipment.mount(item(2151, 23, 6, 3), 0, p -> true));
    }

    @Test public void unavailableAndUnrelatedItemsNeverBecomeDifferentMounts() {
        assertEquals(-1, VisualEquipment.mount(item(1131, 23, 12, 3), 0, p -> false));
        assertEquals(-1, VisualEquipment.mount(item(1131, 5, 12, 3), 0, p -> true));
        assertEquals(-1, VisualEquipment.mount(item(349, 24, -1, 1), 0, p -> true));
        assertEquals(-1, VisualEquipment.mount(item(1000, 23, -1, 3), 0, p -> true));
        assertEquals(-1, VisualEquipment.mount(item(1000, 23, 3000, 3), 0, p -> true));
        assertEquals(349, VisualEquipment.mount(item(349, 24, -1, 3), 0, p -> false));
    }
}
