package nro.jdbc.daos;

import nro.models.item.ItemOption;
import nro.models.shop.ItemShop;
import nro.models.shop.Shop;
import nro.models.shop.TabShop;
import nro.services.ItemService;
import nro.utils.Log;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class ShopDAO {

    /** Loads the shop tree in four queries instead of querying once per item. */
    public static List<Shop> getShops(Connection con) {
        Map<Integer, Shop> shops = new LinkedHashMap<>();
        Map<Integer, TabShop> tabs = new HashMap<>();
        Map<Integer, ItemShop> items = new HashMap<>();
        try {
            try (PreparedStatement ps = con.prepareStatement(
                    "SELECT * FROM shop ORDER BY npc_id ASC, shop_order ASC");
                    ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    Shop shop = new Shop();
                    shop.id = rs.getInt("id");
                    shop.npcId = rs.getByte("npc_id");
                    shop.shopOrder = rs.getByte("shop_order");
                    shops.put(shop.id, shop);
                }
            }

            try (PreparedStatement ps = con.prepareStatement("SELECT * FROM tab_shop ORDER BY id");
                    ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    Shop shop = shops.get(rs.getInt("shop_id"));
                    if (shop == null) {
                        continue;
                    }
                    TabShop tab = new TabShop();
                    tab.shop = shop;
                    tab.id = rs.getInt("id");
                    tab.name = rs.getString("NAME").replace("<>", "\n");
                    shop.tabShops.add(tab);
                    tabs.put(tab.id, tab);
                }
            }

            try (PreparedStatement ps = con.prepareStatement(
                    "SELECT * FROM item_shop WHERE is_sell = 1 ORDER BY create_time DESC");
                    ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    TabShop tab = tabs.get(rs.getInt("tab_id"));
                    if (tab == null) {
                        continue;
                    }
                    ItemShop item = new ItemShop();
                    item.tabShop = tab;
                    item.id = rs.getInt("id");
                    item.temp = ItemService.gI().getTemplate(rs.getShort("temp_id"));
                    item.gold = rs.getInt("gold");
                    item.gem = rs.getInt("gem");
                    item.isNew = rs.getBoolean("is_new");
                    item.itemExchange = rs.getInt("item_exchange");
                    if (item.itemExchange != -1) {
                        item.iconSpec = ItemService.gI().getTemplate(item.itemExchange).iconID;
                        item.costSpec = rs.getInt("quantity_exchange");
                    }
                    tab.itemShops.add(item);
                    items.put(item.id, item);
                }
            }

            try (PreparedStatement ps = con.prepareStatement(
                    "SELECT * FROM item_shop_option ORDER BY id_id");
                    ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    ItemShop item = items.get(rs.getInt("item_shop_id"));
                    if (item != null) {
                        item.options.add(new ItemOption(rs.getInt("option_id"), rs.getInt("param")));
                    }
                }
            }
        } catch (Exception e) {
            Log.error(ShopDAO.class, e);
        }
        return new ArrayList<>(shops.values());
    }
}
