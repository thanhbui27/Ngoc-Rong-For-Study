package nro.models.item;

import java.util.function.IntUnaryOperator;
import nro.consts.ConstPlayer;
import nro.models.Part;
import nro.models.PartManager;
import nro.models.player.Player;
import nro.server.Manager;

/** One interpretation of costume parts for shop previews and equipped characters. */
public final class CostumeAppearance {
    private CostumeAppearance() {}

    public static int[] resolve(ItemTemplate item, int[] mapped, int[] base,
            IntUnaryOperator partType) {
        if (item == null || item.type != 5) return null;
        int[] result = base.clone();
        boolean visible = false;
        for (int slot = 0; slot < 3; slot++) {
            int id = mapped != null && mapped.length > slot ? mapped[slot] : -1;
            if (id < 0 && item.part > 0 && partType.applyAsInt(item.part) == slot) {
                id = item.part;
            }
            if (id >= 0) {
                // A leg ID in the head slot renders a different sprite or crashes clients.
                if (partType.applyAsInt(id) != slot) return null;
                result[slot] = id;
                visible = true;
            }
        }
        if (mapped != null && mapped.length > 3 && mapped[3] >= 0) {
            result[3] = mapped[3];
            visible = true;
        }
        return visible ? result : null;
    }

    public static int[] forPlayer(Player player, ItemTemplate item) {
        if (item == null || item.type != 5) return null;
        int body = player.gender == ConstPlayer.NAMEC ? 59 : 57;
        int leg = player.gender == ConstPlayer.NAMEC ? 60 : 58;
        if (player.inventory != null) {
            Item shirt = player.inventory.itemsBody.get(0);
            Item pants = player.inventory.itemsBody.get(1);
            if (shirt.isNotNullItem()) body = shirt.template.part;
            if (pants.isNotNullItem()) leg = pants.template.part;
        }
        return resolve(item, mapping(item), new int[]{player.head, body, leg, player.getFlagBag()},
                CostumeAppearance::partType);
    }

    public static boolean isReady(ItemTemplate item) {
        return resolve(item, mapping(item), new int[]{-1, -1, -1, -1},
                CostumeAppearance::partType) != null;
    }

    private static int[] mapping(ItemTemplate item) {
        CaiTrang mapping = Manager.gI().getCaiTrangByItemId(item.id);
        return mapping == null ? null : mapping.getID();
    }

    private static int partType(int id) {
        Part part = PartManager.getInstance().find(id);
        if (part == null || part.getPartData() == null) return -1;
        for (int[] frame : part.getPartData()) {
            if (frame != null && frame.length > 0 && frame[0] > 0
                    && !VisualEquipment.icon(frame[0])) return -1;
        }
        return part.getType();
    }
}
