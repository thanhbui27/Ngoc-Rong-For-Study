package nro.models.map.VoDaiSinhTu;

import java.util.HashSet;
import java.util.Set;
import nro.consts.ConstMap;
import nro.models.map.Zone;
import nro.models.npc.Npc;
import nro.models.player.Player;
import nro.server.io.Message;
import nro.services.MapService;
import nro.services.Service;
import nro.services.func.ChangeMapService;
import nro.utils.Log;
import nro.utils.Util;

/**
 * @author outcast c-cute hột me 😳
 */
public class VoDaiSinhTuService {

    private static VoDaiSinhTuService i;
    private final Set<Zone> reservedArenas = new HashSet<>();
    private final Set<Player> challengers = new HashSet<>();

    public static synchronized VoDaiSinhTuService gI() {
        if (i == null) {
            i = new VoDaiSinhTuService();
        }
        return i;
    }

    public synchronized boolean startChallenge(Player player) {
        if (player == null || player.zone == null || player.zone.map.mapId != 112
                || challengers.contains(player)) {
            return false;
        }
        Zone zone = player.zone;
        if (zone.getNumOfBosses() > 0 || !reservedArenas.add(zone)) {
            Service.getInstance().sendThongBao(player, "Võ đài đang có trận đấu, hãy chọn khu khác");
            return false;
        }
        challengers.add(player);
        try {
            Util.setTimeout(() -> {
                if (player.zone != zone) {
                    releaseArena(zone, player);
                    return;
                }
                VoDaiSinhTu mc = null;
                try {
                    mc = new VoDaiSinhTu();
                    mc.setPlayer(player);
                    mc.setArena(zone);
                    mc.setNpc(zone.getReferee());
                    mc.toTheNextRound();
                    if (!mc.isEnded()) {
                        VoDaiSinhTuManager.gI().add(mc);
                        npcChat(player, "Số thứ tự của ngươi là 1\n chuẩn bị thi đấu nhé", zone.map.npcs.get(0));
                    }
                } catch (Exception e) {
                    Log.error(VoDaiSinhTuService.class, e);
                    if (mc != null) {
                        mc.endChallenge();
                    } else {
                        releaseArena(zone, player);
                    }
                }
            }, 500, "start vo dai st");
            return true;
        } catch (Exception e) {
            releaseArena(zone, player);
            Log.error(VoDaiSinhTuService.class, e);
            return false;
        }
    }

    public void npcChat(Player player, String text, Npc npc) {
        Message msg;
        try {
            msg = new Message(124);
            msg.writer().writeShort(npc.tempId);
            msg.writer().writeUTF(text);
            player.sendMessage(msg);
            msg.cleanup();
        } catch (Exception e) {
            Log.error(Service.class, e);
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
        Zone map = MapService.gI().getMapWithRandZone(mapId);
        if (map != null && map.getNumOfBosses() < 1 && !reservedArenas.contains(map)) {
            return map;
        }
        return null;
    }

    public synchronized void releaseArena(Zone zone, Player player) {
        reservedArenas.remove(zone);
        challengers.remove(player);
    }
}
