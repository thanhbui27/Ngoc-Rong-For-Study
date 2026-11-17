package nro.models.map.mabu;

import nro.consts.ConstNpc;
import nro.models.boss.Boss;
import nro.models.boss.BossFactory;
import nro.models.boss.BossManager;
import nro.models.map.Map;
import nro.models.map.Zone;
import nro.models.npc.Npc;
import nro.models.npc.NpcManager;
import nro.models.player.Player;
import nro.services.EffSkinService;
import nro.services.MapService;
import nro.services.NpcService;
import nro.services.Service;
import nro.services.func.ChangeMapService;
import nro.utils.TimeUtil;
import nro.utils.Util;

import java.util.List;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * @author outcast c-cute hột me 😳
 */
public class MabuWar {

    private static MabuWar i;
    public final List<Boss> bosses = new CopyOnWriteArrayList<>();
    private final Set<Zone> pendingMabu = new HashSet<>();
    public static long TIME_OPEN;

    public static long TIME_CLOSE;
    public static final byte HOUR_OPEN = 12;
    public static final byte MIN_OPEN = 0;
    public static final byte SECOND_OPEN = 0;
    public static final byte HOUR_CLOSE = 13;
    public static final byte MIN_CLOSE = 0;
    public static final byte SECOND_CLOSE = 0;
    private int day = -1;
    public boolean initBoss;
    public boolean clearBoss;

    public static synchronized MabuWar gI() {
        if (i == null) {
            i = new MabuWar();
        }
        i.setTime();
        return i;
    }

    public synchronized void setTime() {
        if (i.day == -1 || i.day != TimeUtil.getCurrDay()) {
            if (i.day != -1) {
                removeAllBoss();
                initBoss = false;
                clearBoss = false;
                pendingMabu.clear();
                for (int mapId = 114; mapId <= 120; mapId++) {
                    Map map = MapService.gI().getMapById(mapId);
                    if (map != null) {
                        for (Zone zone : map.zones) {
                            zone.percentMabuEgg = 0;
                            zone.initBossMabu = false;
                            zone.finishMabuWar = false;
                        }
                    }
                }
            }
            i.day = TimeUtil.getCurrDay();
            try {
                this.TIME_OPEN = TimeUtil.getTime(TimeUtil.getTimeNow("dd/MM/yyyy") + " " + HOUR_OPEN + ":" + MIN_OPEN + ":" + SECOND_OPEN, "dd/MM/yyyy HH:mm:ss");
                this.TIME_CLOSE = TimeUtil.getTime(TimeUtil.getTimeNow("dd/MM/yyyy") + " " + HOUR_CLOSE + ":" + MIN_CLOSE + ":" + SECOND_CLOSE, "dd/MM/yyyy HH:mm:ss");
            } catch (Exception e) {
            }
        }
    }

    public boolean isTimeMabuWar() {
        long now = System.currentTimeMillis();
        if (now >= TIME_OPEN && now < TIME_CLOSE) {
            return true;
        }
        return false;
    }

    public String getClosedMessage() {
        return System.currentTimeMillis() < TIME_OPEN
                ? "Đại chiến Mabư chưa tới giờ, mở lúc 12:00"
                : "Đại chiến Mabư đã kết thúc, mở lại lúc 12:00 ngày mai";
    }

    public synchronized void updateEvent() {
        setTime();
        if (isTimeMabuWar()) {
            if (!initBoss) {
                initBoss = true;
                BossFactory.initBossMabuWar();
            }
        } else if (initBoss && !clearBoss) {
            removeAllBoss();
        }
    }

    public synchronized void addBoss(Boss boss) {
        if (boss == null) {
            return;
        }
        if (isTimeMabuWar() && !clearBoss) {
            bosses.add(boss);
        } else {
            boss.leaveMap();
            BossManager.gI().removeBoss(boss);
        }
    }

    public void update(Player player) {
        if (player == null || player.zone == null) {
            return;
        }
        if (MapService.gI().isMapMabuWar(player.zone.map.mapId)) {
            if (isTimeMabuWar()) {
                if (Util.canDoWithTime(player.lastTimeBabiday, 30000)) {
                    if (player.cFlag == 9) {
                        if (Util.isTrue(50, 100)) {
                            Service.getInstance().changeFlag(player, 10);
                            Service.getInstance().sendThongBao(player, "Bạn bị Babiđây thôi miên");
                        }
                    } else if (Util.isTrue(50, 100)) {
                        Service.getInstance().changeFlag(player, 9);
                        Service.getInstance().sendThongBao(player, "Bạn được Ôsin giải trừ phép thuật");
                    }
                    player.lastTimeBabiday = System.currentTimeMillis();
                }
                sendMenuGotoNextFloorMabuWar(player);
                Zone zone = player.zone;
                if (zone.map.mapId == 117) {
                    EffSkinService.gI().setSlow(player, System.currentTimeMillis(), 1000);
                }
                if (zone.map.mapId == 120) {
                    if (!zone.initBossMabu) {
                        Service.getInstance().sendPercentMabuEgg(player, zone.percentMabuEgg);
                        if (zone.percentMabuEgg == 100) {
                            zone.initBossMabu = true;
                        }
                    }
                }
                if (zone.finishMabuWar) {
                    sendMenuFinishMabuWar(player);
                }
            }
            try {
                if (!isTimeMabuWar()) {
                    kickOutOfMap(player);
                }

            } catch (Exception ex) {
                ex.printStackTrace();
            }
        }
    }

    private void kickOutOfMap(Player player) {
        Service.getInstance().sendThongBao(player, getClosedMessage());
        ChangeMapService.gI().changeMapBySpaceShip(player, player.gender + 21, -1, 250);
    }

    public void joinMapMabuWar(Player player) {
        if (!player.isBoss) {
            Service.getInstance().changeFlag(player, 9);
        }
    }

    public synchronized void removeAllBoss() {
        if (!clearBoss) {
            for (Boss boss : bosses) {
                try {
                    boss.leaveMap();
                } catch (Exception e) {
                    nro.utils.Log.error(MabuWar.class, e);
                } finally {
                    BossManager.gI().removeBoss(boss);
                }
            }
            this.bosses.clear();
            pendingMabu.clear();
            clearBoss = true;
        }
    }

    public void sendMenuGotoNextFloorMabuWar(Player player) {
        if (player.zone.map.mapId != 120) {
            if (!player.sendMenuGotoNextFloorMabuWar) {
                if (player.getPowerPoint() >= 20 || player.getPercentPowerPont() >= 20) {
                    NpcService.gI().createMenuConMeo(player, ConstNpc.MENU_MABU_WAR, player.cFlag == 9 ? 4390 : 4388, "Mau theo ta xuống tầng tiếp theo",
                            "Ok");
                    player.sendMenuGotoNextFloorMabuWar = true;
                }
            }
        }
    }

    public void sendMenuFinishMabuWar(Player player) {
        if (!player.sendMenuGotoNextFloorMabuWar) {
            NpcService.gI().createMenuConMeo(player, ConstNpc.MENU_MABU_WAR, 4390, "Trận chiến đã kết thúc,mau rời khỏi đây",
                    "Ok");
            player.sendMenuGotoNextFloorMabuWar = true;
        }
    }

    public void BabidayTalk(Player player, String text) {
        Npc npc = NpcManager.getByIdAndMap(ConstNpc.BABIDAY, player.zone.map.mapId);
        npc.npcChat(text);
    }

    public Zone getMapLastFloor(int mapId) {
        Map map = MapService.gI().getMapById(mapId);
        try {
            if (map != null) {
                for (Zone zone : map.zones) {
                    if (!zone.finishMabuWar) {
                        return zone;
                    }
                }
            }
        } catch (Exception e) {
        }
        return null;
    }

    public synchronized void initMabu(Zone zone) {
        if (zone == null || !isTimeMabuWar() || !pendingMabu.add(zone)) {
            return;
        }
        new Thread(() -> {
            try {
                Thread.sleep(4000);
                if (!isTimeMabuWar()) {
                    return;
                }
                Boss boss = BossFactory.createBoss(BossFactory.MABU_MAP);
                boss.zone = zone;
                addBoss(boss);
            } catch (Exception e) {
                nro.utils.Log.error(MabuWar.class, e);
            }
        }).start();
    }
}
