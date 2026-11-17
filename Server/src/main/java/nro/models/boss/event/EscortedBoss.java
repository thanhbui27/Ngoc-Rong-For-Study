package nro.models.boss.event;

import nro.consts.ConstPlayer;
import nro.consts.ConstRatio;
import nro.models.boss.Boss;
import nro.models.boss.BossData;
import nro.models.player.Player;
import nro.services.MapService;
import nro.services.PlayerService;
import nro.utils.Util;

public abstract class EscortedBoss extends Boss {

    protected Player escort;

    public EscortedBoss(int id, BossData data) {
        super(id, data);
    }

    @Override
    public void attack() {
        move();
    }

    public void move() {
        if (zone == null) {
            return;
        }
        if (Util.isTrue(50, ConstRatio.PER100)) {
            if (escort == null) {
                int x = location.x + Util.nextInt(-50, 50);
                if (x < 35) {
                    x = 35;
                } else if (x > this.zone.map.mapWidth - 35) {
                    x = this.zone.map.mapWidth - 35;
                }
                int y = location.y;
                if (location.y > 50) {
                    y = this.zone.map.yPhysicInTop(x, y - 50);
                }
                goToXY(x, y, false);
            } else {
                int d = Util.getDistance(this, escort);
                if (d > 24) {
                    int x = 0;
                    if (location.x < escort.location.x) {
                        x = location.x + Util.nextInt(12, 36);
                    } else {
                        x = location.x - Util.nextInt(12, 36);
                    }
                    if (x < 35) {
                        x = 35;
                    } else if (x > this.zone.map.mapWidth - 35) {
                        x = this.zone.map.mapWidth - 35;
                    }
                    int y = escort.location.y;
                    if (location.y > 50) {
                        y = this.zone.map.yPhysicInTop(x, y - 50);
                    }
                    goToXY(x, y, false);
                }
            }
        }
    }

    public void joinMapEscort() {
        if (escort == null || escort.zone == null) {
            stopEscorting();
            return;
        }
        if (!MapService.gI().isMapVS(escort.zone.map.mapId)) {
            this.location.x = escort.location.x + Util.nextInt(-10, 10);
            this.location.y = escort.location.y;
            MapService.gI().goToMap(this, escort.zone);
            escort.zone.load_Me_To_Another(this);
        } else {
            stopEscorting();
        }
    }

    public void setEscort(Player escort) {
        if (escort == null) {
            return;
        }
        if (this.escort != null && this.escort != escort) {
            this.escort.setEscortedBoss(null);
        }
        this.escort = escort;
        escort.setEscortedBoss(this);
        PlayerService.gI().changeAndSendTypePK(this, ConstPlayer.NON_PK);
    }

    public void stopEscorting() {
        changeStatus(LEAVE_MAP);
        if (this.escort != null) {
            this.escort.setEscortedBoss(null);
        }
        this.escort = null;
    }
}
