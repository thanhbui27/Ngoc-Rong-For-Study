package nro.services.func;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import nro.consts.ConstNpc;
import nro.models.item.ItemTemplate;
import nro.models.npc.Npc;
import nro.models.player.Player;
import nro.server.Manager;
import nro.services.Service;

/** Paginated admin shop backed by the item templates loaded by this BE. */
public final class AdminCatalogService {

    private static final AdminCatalogService INSTANCE = new AdminCatalogService();
    private static final int PAGE_SIZE = 50;
    private final Map<Long, Selection> selections = new ConcurrentHashMap<>();

    private enum Category {
        COSTUME("Cải trang"), PET("Pet"), ACCESSORY("Trang bị / phụ kiện"),
        OTHER("Vật phẩm khác"), ALL("Tất cả");

        private final String label;

        Category(String label) {
            this.label = label;
        }
    }

    private record Selection(Category category, int page) {
    }

    private AdminCatalogService() {
    }

    public static AdminCatalogService gI() {
        return INSTANCE;
    }

    public void showMenu(Npc npc, Player player) {
        if (!player.isAdmin()) {
            return;
        }
        Selection selected = selections.get(player.id);
        if (selected == null) {
            npc.createOtherMenu(player, ConstNpc.BASE_MENU,
                    "Kho vật phẩm kiểm thử cho admin. Mỗi lượt mua nhận 1 món miễn phí.",
                    "Cải trang", "Pet", "Trang bị\nphụ kiện", "Khác", "Tất cả");
            return;
        }
        int count = itemsFor(selected.category).size();
        int pageCount = Math.max(1, (count + PAGE_SIZE - 1) / PAGE_SIZE);
        int page = Math.min(selected.page, pageCount - 1);
        selections.put(player.id, new Selection(selected.category, page));
        npc.createOtherMenu(player, ConstNpc.ADMIN_ITEM_CATALOG_PAGE_MENU,
                selected.category.label + " - trang " + (page + 1) + "/" + pageCount
                        + " (" + count + " mục). Mua miễn phí cho admin.",
                "Xem trang", "Trang trước", "Trang sau", "Đổi nhóm");
    }

    public void chooseCategory(Player player, int index) {
        if (!player.isAdmin() || index < 0 || index >= Category.values().length) {
            return;
        }
        openPage(player, Category.values()[index], 0);
    }

    public void selectPageAction(Npc npc, Player player, int index) {
        if (!player.isAdmin()) {
            return;
        }
        Selection selected = selections.get(player.id);
        if (selected == null) {
            showMenu(npc, player);
            return;
        }
        switch (index) {
            case 0 -> openPage(player, selected.category, selected.page);
            case 1 -> openPage(player, selected.category, selected.page - 1);
            case 2 -> openPage(player, selected.category, selected.page + 1);
            case 3 -> {
                selections.remove(player.id);
                showMenu(npc, player);
            }
            default -> {
            }
        }
    }

    private void openPage(Player player, Category category, int requestedPage) {
        List<ItemTemplate> items = itemsFor(category);
        if (items.isEmpty()) {
            Service.gI().sendThongBao(player, "Nhóm này chưa có vật phẩm hiển thị được.");
            return;
        }
        int pageCount = (items.size() + PAGE_SIZE - 1) / PAGE_SIZE;
        int page = Math.max(0, Math.min(requestedPage, pageCount - 1));
        selections.put(player.id, new Selection(category, page));
        int from = page * PAGE_SIZE;
        String title = category.label + " " + (page + 1) + "/" + pageCount;
        ShopService.gI().openAdminCatalog(player, title,
                items.subList(from, Math.min(from + PAGE_SIZE, items.size())));
    }

    public ItemTemplate getSelectedItem(Player player, int itemId) {
        if (!player.isAdmin() || player.zone == null
                || player.zone.map.mapId != nro.consts.ConstMap.DAO_KAME) {
            return null;
        }
        Selection selected = selections.get(player.id);
        if (selected == null) {
            return null;
        }
        List<ItemTemplate> items = itemsFor(selected.category);
        int from = selected.page * PAGE_SIZE;
        if (from < 0 || from >= items.size()) {
            return null;
        }
        for (ItemTemplate item : items.subList(from, Math.min(from + PAGE_SIZE, items.size()))) {
            if (item.id == itemId) {
                return item;
            }
        }
        return null;
    }

    private List<ItemTemplate> itemsFor(Category category) {
        List<ItemTemplate> items = new ArrayList<>();
        for (ItemTemplate item : Manager.ITEM_TEMPLATES) {
            if (item == null || item.id < 0 || item.iconID < 0
                    || item.name == null || item.name.isBlank()) {
                continue;
            }
            if (category == Category.ALL || category == classify(item)) {
                items.add(item);
            }
        }
        items.sort(Comparator.comparingInt(item -> item.id));
        return items;
    }

    private Category classify(ItemTemplate item) {
        String name = item.name.toLowerCase(Locale.ROOT);
        if (item.type == 5 || name.startsWith("cải trang") || name.startsWith("avatar")) {
            return Category.COSTUME;
        }
        if (item.type == 21 || name.startsWith("pet ")) {
            return Category.PET;
        }
        if ((item.type >= 0 && item.type <= 4) || item.type == 23 || item.type == 24
                || item.type == 28 || item.type == 39 || item.type == 72 || item.type == 88
                || name.contains("phụ kiện")) {
            return Category.ACCESSORY;
        }
        return Category.OTHER;
    }
}
