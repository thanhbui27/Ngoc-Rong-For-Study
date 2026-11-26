package nro.manager;

import nro.jdbc.DBService;
import nro.models.player.PetFollow;
import nro.models.item.ItemTemplate;
import nro.server.Manager;

import java.io.DataInputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

/**
 * @author outcast c-cute hột me 😳
 */

public class PetFollowManager extends AbsManager<PetFollow> {

    private static final PetFollowManager INSTANCE = new PetFollowManager();

    public static PetFollowManager gI() {
        return INSTANCE;
    }

    public void load() {
        list.clear();
        try (java.sql.Connection con = DBService.gI().getConnectionForGame()) {
            PreparedStatement ps = con.prepareStatement(
                    "SELECT p.* FROM pet_follow p JOIN item_template t ON t.id = p.id_temp WHERE t.TYPE = 72");
            ResultSet rs = ps.executeQuery();
            while (rs.next()) {
                int id = rs.getInt("id_temp");
                int iconID = rs.getInt("icon");
                int w = rs.getInt("width");
                int h = rs.getInt("height");
                byte nFrame = rs.getByte("frame");
                add(new PetFollow(id, iconID, w, h, nFrame));
            }
            ps.close();
            rs.close();
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
        // Type-72 pets can use their item icon as a static follow image until
        // an animated pet_follow sprite is configured.
        for (ItemTemplate item : Manager.ITEM_TEMPLATES) {
            if (item.type != 72) {
                continue;
            }
            PetFollow configured = findByID(item.id);
            if (configured != null && hasValidSprite(configured)) {
                continue;
            }
            int[] size = iconSize(item.iconID);
            if (size != null) {
                if (configured != null) {
                    remove(configured);
                }
                add(new PetFollow(item.id, item.iconID, size[0], size[1], (byte) 1));
            }
        }
    }

    private static boolean hasValidSprite(PetFollow pet) {
        int[] size = iconSize(pet.getIconID());
        return size != null && pet.getNFrame() > 0 && pet.getWidth() == size[0]
                && pet.getHeight() > 0 && (long) pet.getHeight() * pet.getNFrame() <= size[1];
    }

    private static int[] iconSize(int iconId) {
        if (iconId < 0) {
            return null;
        }
        Path path = Path.of("resources", "normal", "image", "1", "icon", iconId + ".png");
        try (DataInputStream image = new DataInputStream(Files.newInputStream(path))) {
            if (image.readLong() != 0x89504E470D0A1A0AL || image.readInt() != 13
                    || image.readInt() != 0x49484452) {
                return null;
            }
            int width = image.readInt();
            int height = image.readInt();
            return width > 0 && width <= Short.MAX_VALUE && height > 0 && height <= Short.MAX_VALUE
                    ? new int[]{width, height} : null;
        } catch (IOException e) {
            return null;
        }
    }

    @Override
    public PetFollow findByID(int id) {
        for (PetFollow pet : list) {
            if (pet.getId() == id) {
                return pet;
            }
        }
        return null;
    }
}
