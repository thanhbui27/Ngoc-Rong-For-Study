package nro.manager;

import nro.jdbc.DBService;
import nro.models.item.MinipetTemplate;
import nro.models.Part;
import nro.models.PartManager;
import nro.resources.Resources;
import nro.utils.Log;
import java.io.File;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.HashMap;
import java.util.Map;

/**
 * @author outcast c-cute hột me 😳
 */

public class MiniPetManager implements IManager<MinipetTemplate> {

    private static final MiniPetManager INSTANCE = new MiniPetManager();

    private List<MinipetTemplate> list = new ArrayList<>();

    public static MiniPetManager gI() {
        return INSTANCE;
    }

    public void load() {
        list.clear();
        Map<Integer, Boolean> images = new HashMap<>();
        try (java.sql.Connection con = DBService.gI().getConnectionForGame()) {
            PreparedStatement ps = con.prepareStatement("SELECT m.* FROM mini_pet m "
                    + "JOIN item_template i ON i.id=m.id_temp "
                    + "JOIN part h ON h.id=m.head AND h.TYPE=0 "
                    + "JOIN part b ON b.id=m.body AND b.TYPE=1 "
                    + "JOIN part l ON l.id=m.leg AND l.TYPE=2 WHERE i.TYPE IN (18,21)");
            ResultSet rs = ps.executeQuery();
            while (rs.next()) {
                int id = rs.getInt("id_temp");
                short head = rs.getShort("head");
                short body = rs.getShort("body");
                short leg = rs.getShort("leg");
                if (!hasImages(head, images) || !hasImages(body, images) || !hasImages(leg, images)) {
                    Log.warning("Mini pet " + id + " thiếu ảnh part; không nạp ngoại hình lỗi");
                    continue;
                }
                add(new MinipetTemplate(id, head, body, leg));
            }
            ps.close();
            rs.close();
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    private boolean hasImages(short id, Map<Integer, Boolean> images) {
        Part part = PartManager.getInstance().find(id);
        if (part == null || part.getPartData() == null) return false;
        File folder = Resources.getInstance().find(0).getFolder();
        for (int[] frame : part.getPartData()) {
            if (frame == null || frame.length == 0 || frame[0] <= 0) continue;
            boolean available = images.computeIfAbsent(frame[0], image -> {
                for (int zoom = 1; zoom <= 4; zoom++) {
                    if (!new File(folder, "image/" + zoom + "/icon/" + image + ".png").isFile()) return false;
                }
                return true;
            });
            if (!available) return false;
        }
        return true;
    }

    @Override
    public void add(MinipetTemplate minipetTemplate) {
        list.add(minipetTemplate);
    }

    @Override
    public void remove(MinipetTemplate minipetTemplate) {
        list.remove(minipetTemplate);
    }

    @Override
    public MinipetTemplate findByID(int id) {
        for (MinipetTemplate temp : list) {
            if (temp.getId() == id) {
                return temp;
            }
        }
        return null;
    }
}
