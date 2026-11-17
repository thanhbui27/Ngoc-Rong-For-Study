package nro.models.map.DaiHoiVoThuat;

import java.util.HashSet;
import java.util.Set;
import nro.consts.ConstMap;
import nro.models.map.Map;
import nro.models.map.Zone;
import nro.models.player.Player;
import nro.server.io.Message;
import nro.services.MapService;
import nro.services.Service;
import nro.services.func.ChangeMapService;
import nro.utils.Util;

/**
 * @author outcast c-cute hột me 😳
 */
public class DHVT23Service {

    private static DHVT23Service i;
    private final Set<Zone> reservedArenas = new HashSet<>();
    private final Set<Player> challengers = new HashSet<>();

    public static synchronized DHVT23Service gI() {
        if (i == null) {
            i = new DHVT23Service();
        }
        return i;
    }

    public synchronized boolean startChallenge(Player player) {
        if (player == null || challengers.contains(player)) {
            return false;
        }
        Zone zone = getMapChalllenge(ConstMap.DAI_HOI_VO_THUAT_129);
        if (zone == null) {
            Service.getInstance().sendThongBao(player, "Võ đài đã đầy, hãy thử lại sau");
            return false;
        }
        challengers.add(player);
        try {
            ChangeMapService.gI().changeMap(player, zone, player.location.x, 360);
            if (player.zone != zone) {
                releaseArena(zone, player);
                return false;
            }
            Util.setTimeout(() -> {
                if (player.zone != zone) {
                    releaseArena(zone, player);
                    return;
                }
                DHVT23 mc = null;
                try {
                    mc = new DHVT23();
                    mc.setPlayer(player);
                    mc.setArena(zone);
                    mc.setNpc(zone.getReferee());
                    mc.toTheNextRound();
                    if (!mc.isEnded()) {
                        DHVT23Manager.gI().add(mc);
                        Service.getInstance().sendThongBao(player, "Số thứ tự của ngươi là 1\n chuẩn bị thi đấu nhé");
                    }
                } catch (Exception e) {
                    nro.utils.Log.error(DHVT23Service.class, e);
                    if (mc != null) {
                        mc.endChallenge();
                    } else {
                        releaseArena(zone, player);
                    }
                }
            }, 500,"Strat dhvt 23");
            return true;
        } catch (Exception e) {
            releaseArena(zone, player);
            nro.utils.Log.error(DHVT23Service.class, e);
            return false;
        }
    }

    public void moveFast(Player pl, int x, int y) {
        Message msg;
        try {
            msg = new Message(58);
            msg.writer().writeInt((int) pl.id);
            msg.writer().writeShort(x);
            msg.writer().writeShort(y);
            msg.writer().writeInt((int) pl.id);
            pl.sendMessage(msg);
            msg.cleanup();
        } catch (Exception e) {
        }
    }

    public void sendTypePK(Player player, Player boss) {
        Message msg;
        try {
            msg = Service.getInstance().messageSubCommand((byte) 35);
            msg.writer().writeInt((int) boss.id);
            msg.writer().writeByte(3);
            player.sendMessage(msg);
            msg.cleanup();
        } catch (Exception e) {
        }
    }

    public synchronized Zone getMapChalllenge(int mapId) {
        Map map = MapService.gI().getMapById(mapId);
        if (map == null) {
            return null;
        }
        for (Zone zone : map.zones) {
            if (zone.getNumOfBosses() < 1 && reservedArenas.add(zone)) {
                return zone;
            }
        }
        return null;
    }

    public synchronized void releaseArena(Zone zone, Player player) {
        reservedArenas.remove(zone);
        challengers.remove(player);
    }
}
