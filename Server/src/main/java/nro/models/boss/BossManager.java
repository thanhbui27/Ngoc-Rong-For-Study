package nro.models.boss;

import nro.utils.Log;
import java.util.concurrent.CopyOnWriteArrayList;
import nro.models.player.Player;
import nro.utils.Util;

/**
 *
 * @author 💖 YTB ThanhBN 💖
 * 
 *
 */
public class BossManager {

    public static final CopyOnWriteArrayList<Boss> BOSSES_IN_GAME;
    private static BossManager intance;

    static {
        BOSSES_IN_GAME = new CopyOnWriteArrayList<>();
    }
    private int bossId = -1_000_000_000;

    public synchronized int nextBossId() {
        if (bossId == Integer.MIN_VALUE) {
            throw new IllegalStateException("Đã hết ID boss động");
        }
        return bossId--;
    }

    public void updateAllBoss() {
        Boss[] bosses = BOSSES_IN_GAME.toArray(new Boss[0]);
        for (int i = bosses.length - 1; i >= 0; i--) {
            Boss boss = bosses[i];
            if (boss != null) {
                try {
                    boss.update();
                } catch (Exception e) {
                    Log.error(BossManager.class, e);
                }
            }
        }
    }

    private BossManager() {

    }

    public static synchronized BossManager gI() {
        if (intance == null) {
            intance = new BossManager();
        }
        return intance;
    }

    public Boss getBossTau77ByPlayer(Player player) {
        int bossId = Util.createIdDuongTank((int) player.id) - 10000000;
        Boss[] bosses = BOSSES_IN_GAME.toArray(new Boss[0]);
        for (int i = bosses.length - 1; i >= 0; i--) {
            Boss boss = bosses[i];
            if (boss.id == bossId) {
                return boss;
            }
        }
        return null;
    }

    public Boss getBossById(int bossId) {
        Boss[] bosses = BOSSES_IN_GAME.toArray(new Boss[0]);
        for (int i = bosses.length - 1; i >= 0; i--) {
            Boss boss = bosses[i];
            if (boss.id == bossId) {
                return boss;
            }
        }
        return null;
    }

    public void activateBossIfPresent(int bossId) {
        Boss boss = getBossById(bossId);
        if (boss != null) {
            boss.changeToAttack();
        }
    }

    public void restBossIfPresent(int bossId) {
        Boss boss = getBossById(bossId);
        if (boss != null) {
            boss.setJustRest();
        }
    }

    public void addBoss(Boss boss) {
        BOSSES_IN_GAME.addIfAbsent(boss);
    }

    public void removeBoss(Boss boss) {
        BOSSES_IN_GAME.remove(boss);
        boss.dispose();
    }
}
