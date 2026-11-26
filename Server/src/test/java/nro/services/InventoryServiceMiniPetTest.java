package nro.services;

import nro.manager.MiniPetManager;
import nro.models.item.ItemTemplate;
import nro.models.item.MinipetTemplate;
import org.junit.Test;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class InventoryServiceMiniPetTest {

    private static ItemTemplate item(int id, int type) {
        ItemTemplate result = new ItemTemplate();
        result.id = (short) id;
        result.type = (byte) type;
        return result;
    }

    @Test
    public void type18UsesMiniPetOnlyWhenAllThreePartsAreMapped() {
        int id = 32001;
        MinipetTemplate mapping = new MinipetTemplate(id, (short) 1, (short) 2, (short) 3);
        assertFalse(InventoryService.usesMiniPet(item(id, 18)));
        MiniPetManager.gI().add(mapping);
        try {
            assertTrue(InventoryService.usesMiniPet(item(id, 18)));
            assertFalse(InventoryService.usesMiniPet(item(id, 72)));
            assertTrue(InventoryService.usesMiniPet(item(id, 21)));
            mapping.setLeg((short) -1);
            assertFalse(InventoryService.usesMiniPet(item(id, 18)));
            assertFalse(InventoryService.usesMiniPet(item(id, 21)));
        } finally {
            MiniPetManager.gI().remove(mapping);
        }
    }
}
