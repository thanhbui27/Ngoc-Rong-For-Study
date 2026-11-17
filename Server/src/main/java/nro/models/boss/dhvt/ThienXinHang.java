package nro.models.boss.dhvt;

import java.util.ArrayList;
import java.util.List;
import nro.models.boss.BossData;
import nro.models.boss.BossFactory;
import nro.models.player.Player;
import nro.services.SkillService;
import nro.utils.Log;
import nro.utils.Util;

/**
 * @author outcast c-cute hột me 😳
 */
public class ThienXinHang extends BossDHVT {

    private long lastTimePhanThan;
    private final List<ThienXinHangClone> clones = new ArrayList<>();

    public ThienXinHang(Player player) {
        super(BossFactory.THIEN_XIN_HANG, BossData.THIEN_XIN_HANG);
        this.playerAtt = player;
    }

    @Override
    protected boolean useSpecialSkill() {
        this.playerSkill.skillSelect = this.getSkillSpecial();
        if (SkillService.gI().canUseSkillWithCooldown(this)) {
            SkillService.gI().useSkill(this, null, null, null);
            return true;
        } else {
            return false;
        }
    }

    @Override
    public void attack() {
        try {
            if (!canAttackWithTime(400)) {
                return;
            }
            if (!useSpecialSkill()) {
                performTournamentAttack();
            }
            if (Util.canDoWithTime(lastTimePhanThan, 20000)) {
                lastTimePhanThan = System.currentTimeMillis();
                phanThan();
            }
        } catch (Exception ex) {
            Log.error(ThienXinHang.class, ex);
        }
    }

    private synchronized void phanThan() {
        clones.removeIf(clone -> clone.zone == null);
        clones.add(new ThienXinHangClone(BossFactory.THIEN_XIN_HANG_CLONE, playerAtt));
        clones.add(new ThienXinHangClone(BossFactory.THIEN_XIN_HANG_CLONE1, playerAtt));
        clones.add(new ThienXinHangClone(BossFactory.THIEN_XIN_HANG_CLONE2, playerAtt));
        clones.add(new ThienXinHangClone(BossFactory.THIEN_XIN_HANG_CLONE3, playerAtt));
    }

    @Override
    public synchronized void leaveMap() {
        for (ThienXinHangClone clone : clones) {
            clone.leaveMap();
        }
        clones.clear();
        super.leaveMap();
    }
}
