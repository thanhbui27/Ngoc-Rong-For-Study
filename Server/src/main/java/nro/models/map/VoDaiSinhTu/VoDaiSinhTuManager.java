package nro.models.map.VoDaiSinhTu;

import nro.utils.Util;
import nro.utils.Log;

import java.util.ArrayList;
import java.util.List;

/**
 * @author outcast c-cute hột me 😳
 */
public class VoDaiSinhTuManager {

    private static VoDaiSinhTuManager i;
    private long lastUpdate;
    private static final List<VoDaiSinhTu> list = new ArrayList<>();
    private static final List<VoDaiSinhTu> toRemove = new ArrayList<>();

    public static synchronized VoDaiSinhTuManager gI() {
        if (i == null) {
            i = new VoDaiSinhTuManager();
        }
        return i;
    }

    public void update() {
        if (Util.canDoWithTime(lastUpdate, 1000)) {
            lastUpdate = System.currentTimeMillis();
            synchronized (list) {
                for (VoDaiSinhTu mc : list) {
                    try {
                        mc.update();
                    } catch (Exception e) {
                        Log.error(VoDaiSinhTuManager.class, e);
                        try {
                            mc.endChallenge();
                        } catch (Exception cleanupError) {
                            Log.error(VoDaiSinhTuManager.class, cleanupError);
                        }
                    }
                }
                synchronized (toRemove) {
                    list.removeAll(toRemove);
                    toRemove.clear();
                }
            }
        }
    }

    public void add(VoDaiSinhTu mc) {
        synchronized (list) {
            list.add(mc);
        }
    }

    public void remove(VoDaiSinhTu mc) {
        synchronized (toRemove) {
            toRemove.add(mc);
        }
    }
}
