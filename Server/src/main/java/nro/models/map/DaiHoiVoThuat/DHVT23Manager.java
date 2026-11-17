package nro.models.map.DaiHoiVoThuat;

import nro.utils.Util;
import nro.utils.Log;

import java.util.ArrayList;
import java.util.List;

/**
 * @author outcast c-cute hột me 😳
 */
public class DHVT23Manager {

    private static DHVT23Manager i;
    private long lastUpdate;
    private static final List<DHVT23> list = new ArrayList<>();
    private static final List<DHVT23> toRemove = new ArrayList<>();

    public static synchronized DHVT23Manager gI() {
        if (i == null) {
            i = new DHVT23Manager();
        }
        return i;
    }

    public void update() {
        if (Util.canDoWithTime(lastUpdate, 1000)) {
            lastUpdate = System.currentTimeMillis();
            synchronized (list) {
                for (DHVT23 mc : list) {
                    try {
                        mc.update();
                    } catch (Exception e) {
                        Log.error(DHVT23Manager.class, e);
                        try {
                            mc.endChallenge();
                        } catch (Exception cleanupError) {
                            Log.error(DHVT23Manager.class, cleanupError);
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

    public void add(DHVT23 mc) {
        synchronized (list) {
            list.add(mc);
        }
    }

    public void remove(DHVT23 mc) {
        synchronized (toRemove) {
            toRemove.add(mc);
        }
    }
}
