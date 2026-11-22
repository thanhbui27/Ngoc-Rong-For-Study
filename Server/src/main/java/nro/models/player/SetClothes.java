package nro.models.player;

import nro.models.item.Item;
import nro.models.item.ItemOption;

/**
 *
 * @author 💖 YTB ThanhBN 💖
 * 
 *
 */
public class SetClothes {

    public static final int SET_KAIO = 251;
    public static final int SET_CADIC_M = 255;
    public static final int SET_NAIL = 259;
    public static final int SET_GOHAN = 263;
    public static final int SET_CHAMPA = 265;

    private Player player;

    public SetClothes(Player player) {
        this.player = player;
    }

    public byte songoku;
    public byte thienXinHang;
    public byte kirin;

    public byte ocTieu;
    public byte pikkoroDaimao;
    public byte picolo;

    public byte kakarot;
    public byte cadic;
    public byte nappa;

    public byte kaio;
    public byte cadicM;
    public byte nail;
    public byte gohan;
    public byte champa;

    public boolean godClothes;
    public int ctHaiTac = -1;

    public void setup() {
        setDefault();
        setupSKT();
        this.godClothes = true;
        for (int i = 0; i < 5; i++) {
            Item item = this.player.inventory.itemsBody.get(i);
            if (item.isNotNullItem()) {
                if (item.template.id > 567 || item.template.id < 555) {
                    this.godClothes = false;
                    break;
                }
            } else {
                this.godClothes = false;
                break;
            }
        }
        Item ct = this.player.inventory.itemsBody.get(5);
        if (ct.isNotNullItem()) {
            switch (ct.template.id) {
                case 618:
                case 619:
                case 620:
                case 621:
                case 622:
                case 623:
                case 624:
                case 626:
                case 627:
                    this.ctHaiTac = ct.template.id;
                    break;
            }
        }
    }

    private void setupSKT() {
        for (int i = 0; i < 5; i++) {
            Item item = this.player.inventory.itemsBody.get(i);
            if (item.isNotNullItem()) {
                boolean isActSet = false;
                for (ItemOption io : item.itemOptions) {
                    switch (io.optionTemplate.id) {
                        case 129:
                        case 141:
                            isActSet = true;
                            songoku++;
                            break;
                        case 127:
                        case 139:
                            isActSet = true;
                            thienXinHang++;
                            break;
                        case 128:
                        case 140:
                            isActSet = true;
                            kirin++;
                            break;
                        case 131:
                        case 143:
                            isActSet = true;
                            ocTieu++;
                            break;
                        case 132:
                        case 144:
                            isActSet = true;
                            pikkoroDaimao++;
                            break;
                        case 130:
                        case 142:
                            isActSet = true;
                            picolo++;
                            break;
                        case 135:
                        case 138:
                            isActSet = true;
                            nappa++;
                            break;
                        case 133:
                        case 136:
                            isActSet = true;
                            kakarot++;
                            break;
                        case 134:
                        case 137:
                            isActSet = true;
                            cadic++;
                            break;
                        case SET_KAIO:
                            isActSet = true;
                            kaio++;
                            break;
                        case SET_CADIC_M:
                            isActSet = true;
                            cadicM++;
                            break;
                        case SET_NAIL:
                            isActSet = true;
                            nail++;
                            break;
                        case SET_GOHAN:
                            isActSet = true;
                            gohan++;
                            break;
                        case SET_CHAMPA:
                            isActSet = true;
                            champa++;
                            break;
                    }
                    if (isActSet) {
                        break;
                    }
                }
            }
        }
    }

    private void setDefault() {
        this.songoku = 0;
        this.thienXinHang = 0;
        this.kirin = 0;
        this.ocTieu = 0;
        this.pikkoroDaimao = 0;
        this.picolo = 0;
        this.kakarot = 0;
        this.cadic = 0;
        this.nappa = 0;
        this.kaio = 0;
        this.cadicM = 0;
        this.nail = 0;
        this.gohan = 0;
        this.champa = 0;
        this.godClothes = false;
        this.ctHaiTac = -1;
    }

    public int getKaioCriticalBonus() {
        return kaio >= 2 ? 10 : 0;
    }

    public int getKaiokenCostReduction() {
        return kaio >= 5 ? 25 : kaio >= 2 ? 10 : 0;
    }

    public int getKaiokenDamageBonus() {
        return kaio >= 5 ? 25 : 0;
    }

    public int getCadicMExplosionDamageBonus() {
        return cadicM >= 5 ? 30 : cadicM >= 4 ? 10 : 0;
    }

    public int getCadicMExplosionRangeBonus() {
        return cadicM >= 2 ? 10 : 0;
    }

    public int getNailCriticalDamageBonus() {
        return nail >= 2 ? 10 : 0;
    }

    public int getNailMasenkoDamageBonus() {
        return nail >= 5 ? 20 : 0;
    }

    public int getNailMasenkoCooldownReduction() {
        return nail >= 5 ? 30 : nail >= 4 ? 10 : 0;
    }

    public int getChampaBossDamageBonus() {
        return champa >= 5 ? 50 : champa >= 4 ? 25 : champa >= 2 ? 10 : 0;
    }

    public int getChampaCriticalDamageBonus() {
        return champa >= 5 ? 20 : 0;
    }

    public int getGohanLuckBonus() {
        return gohan >= 5 ? 300 : 0;
    }

    public void dispose() {
        this.player = null;
    }
}
