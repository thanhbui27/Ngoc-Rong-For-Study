package nro.models.item;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.function.IntPredicate;
import nro.resources.EffectAssetResolver;
import nro.server.Manager;

/** Resolve visual IDs in their own namespace, never through an item-ID lookup. */
public final class VisualEquipment {
    private record Check(boolean valid, long expires) { }
    private static final java.util.concurrent.ConcurrentMap<Integer, Check> EFFECTS = new java.util.concurrent.ConcurrentHashMap<>();
    private static final java.util.concurrent.ConcurrentMap<Integer, Check> ICONS = new java.util.concurrent.ConcurrentHashMap<>();
    private VisualEquipment() { }

    public static short mount(ItemTemplate item, int gender, IntPredicate available) {
        if (item == null || (item.type != 23 && item.type != 24)
                || (item.gender != 3 && item.gender != gender)) return -1;
        if (item.part >= 0) {
            int id = 30000 + item.part;
            return id <= Short.MAX_VALUE && available.test(item.part) ? (short) id : -1;
        }
        return switch (item.id) {
            case 346, 347, 348, 349, 350, 351, 396, 532 -> item.id;
            default -> -1;
        };
    }

    public static boolean mountImages(int part) {
        return namedPair("mount_", part);
    }

    public static boolean namedPair(String prefix, int part) {
        for (int layer = 0; layer < 2; layer++) {
            String name = prefix + part + "_" + layer;
            if (Manager.getNFrameImageByName(name) < 1) return false;
            for (int zoom = 1; zoom <= 4; zoom++) {
                if (!Files.isRegularFile(Path.of("resources/ThanhBN/img_by_name/x" + zoom, name + ".png"))) return false;
            }
        }
        return true;
    }

    public static boolean icon(int id) {
        if (id < 0) return false;
        long now = System.currentTimeMillis();
        Check cached = ICONS.get(id);
        if (cached != null && cached.expires > now) return cached.valid;
        boolean valid = true;
        for (int zoom = 1; zoom <= 4; zoom++) {
            if (!Files.isRegularFile(Path.of("resources/normal/image/" + zoom + "/icon/" + id + ".png"))) {
                valid = false;
                break;
            }
        }
        ICONS.put(id, new Check(valid, now + 30000));
        return valid;
    }

    public static boolean effect(int id) {
        if (id < 0) return false;
        Check cached = EFFECTS.get(id);
        long now = System.currentTimeMillis();
        if (cached != null && cached.expires > now) return cached.valid;
        boolean valid = true;
        try {
            for (int zoom = 1; zoom <= 4; zoom++) EffectAssetResolver.load(Path.of("Eff/effect"), id, zoom);
        } catch (java.io.IOException e) {
            valid = false;
        }
        EFFECTS.put(id, new Check(valid, now + 30000));
        return valid;
    }

    public static boolean flag(FlagBag flag) {
        if (flag == null || flag.id < 0 || flag.id > 254) return false;
        if (flag.id >= 201) return effect(flag.id);
        if (flag.iconEffect == null || flag.iconEffect.length == 0) return false;
        for (short id : flag.iconEffect) if (!icon(id)) return false;
        return true;
    }
}
