package nro.tools;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.HashSet;
import java.util.Set;
import java.util.Map;
import java.util.Properties;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import javax.imageio.ImageIO;

/** Local-only web editor. All writes go through checked JDBC transactions. */
public final class PartEditorServer {

    private static final int[] FRAME_COUNTS = {3, 17, 14, 2};
    private static final Object WRITE_LOCK = new Object();
    private static final Map<String,Map<Integer,PendingImage>> PENDING_IMAGES = new ConcurrentHashMap<>();
    private record PendingImage(byte[] source,int sourceZoom,int logicalWidth,int logicalHeight) {
        byte[] atZoom(int zoom) throws IOException {
            BufferedImage image=ImageIO.read(new ByteArrayInputStream(source));
            return zoomVariants(source,image,sourceZoom,logicalWidth,logicalHeight)[zoom];
        }
        long size(){return source.length;}
    }
    private static final String SOURCE = "dragon14.teamobi.com:18001";
    private static final Path ROOT = locateRoot();
    private static final Path UI = ROOT.resolve("tools/part-editor");
    private static final Path ICONS = ROOT.resolve("Server/resources/normal/image");
    private static final Path SOURCE_ICONS = ROOT.getParent().resolve("NRO-server15-assets/image");
    private static final List<JsonObject> REFERENCE_PARTS = loadReferenceParts();
    private static final String TOKEN = newToken();
    private static Properties config;
    private static GamePartEditorClient remoteClient;
    private static String remoteHost;
    private static int remotePort;
    private static String remoteStageSession;

    private PartEditorServer() {
    }

    public static void main(String[] args) throws Exception {
        int port = 8182;
        if (args.length >= 2) {
            remoteHost = args[0];
            remotePort = Integer.parseInt(args[1]);
            if (remotePort < 1 || remotePort > 65535) throw new IllegalArgumentException("Cổng game không hợp lệ");
        } else {
            if (args.length == 1) port = Integer.parseInt(args[0]);
            initConfig();
        }
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        server.createContext("/", PartEditorServer::handle);
        server.setExecutor(Executors.newFixedThreadPool(4));
        server.start();
        String url = "http://127.0.0.1:" + port + "/?token=" + TOKEN;
        System.out.println("Part editor: " + url);
        System.out.println(remoteHost == null ? "Local SQL mode" : "Game server: " + remoteHost + ":" + remotePort);
        if (!Boolean.getBoolean("partstudio.noBrowser")
                && System.getProperty("os.name", "").toLowerCase().contains("windows")) {
            try {
                if (java.awt.Desktop.isDesktopSupported()
                        && java.awt.Desktop.getDesktop().isSupported(java.awt.Desktop.Action.BROWSE)) {
                    java.awt.Desktop.getDesktop().browse(java.net.URI.create(url));
                }
            } catch (Exception ignored) {
                // The printed URL remains usable when no desktop browser is available.
            }
        }
    }

    private static Path locateRoot() {
        Path here = Path.of(System.getProperty("user.dir")).toAbsolutePath().normalize();
        if (Files.isDirectory(here.resolve("tools/part-editor"))) return here;
        if (Files.isDirectory(here.getParent().resolve("tools/part-editor"))) return here.getParent();
        if (Files.isDirectory(here.resolve("Server/resources/config"))) return here;
        if (Files.isDirectory(here.resolve("resources/config"))) return here.getParent();
        throw new IllegalStateException("Run from the repository root or Server directory");
    }

    private static String newToken() {
        byte[] bytes = new byte[24];
        new SecureRandom().nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private static List<JsonObject> loadReferenceParts() {
        Path path=ROOT.resolve("Server/resources/reference/server14/part.bin");
        if(!Files.isRegularFile(path))return List.of();
        List<JsonObject> parts=new ArrayList<>();
        try(DataInputStream in=new DataInputStream(Files.newInputStream(path))){
            int count=in.readUnsignedShort();
            for(int id=0;id<count;id++){
                int type=in.readUnsignedByte();
                if(type>=FRAME_COUNTS.length)throw new IOException("Unknown part type " + type);
                JsonArray frames=new JsonArray();
                for(int f=0;f<FRAME_COUNTS[type];f++){
                    JsonArray row=new JsonArray();row.add(in.readUnsignedShort());row.add(in.readByte());row.add(in.readByte());frames.add(row);
                }
                JsonObject part=new JsonObject();part.addProperty("id",id);part.addProperty("type",type);part.add("frames",frames);parts.add(part);
            }
            if(in.read()!=-1)throw new IOException("Extra bytes in part.bin");
        }catch(IOException ex){throw new IllegalStateException("Cannot decode " + path,ex);}
        return parts;
    }

    private static Connection connect() throws SQLException {
        try { initConfig(); } catch (Exception ex) { throw new SQLException("Không đọc được cấu hình DB", ex); }
        String host = config.getProperty("server.db.ip", "localhost").trim();
        String port = config.getProperty("server.db.port", "3306").trim();
        String name = config.getProperty("server.db.name", "").trim();
        String url = config.getProperty("server.db.url", "jdbc:mysql://" + host + ":" + port + "/" + name
                + "?useUnicode=true&characterEncoding=utf8&serverTimezone=UTC");
        return DriverManager.getConnection(url, config.getProperty("server.db.us"),
                config.getProperty("server.db.pw"));
    }

    private static synchronized void initConfig() throws Exception {
        if (config != null) return;
        Properties loaded = new Properties();
        try (var input = Files.newInputStream(ROOT.resolve("Server/resources/config/server.properties"))) {
            loaded.load(input);
        }
        Class.forName(loaded.getProperty("server.db.driver", "com.mysql.cj.jdbc.Driver"));
        config = loaded;
    }

    public static JsonObject executeGameAction(String action, JsonObject request) throws Exception {
        return switch (action) {
            case "status" -> status();
            case "list" -> list(string(request, "kind", "costume"), string(request, "q", ""));
            case "item" -> item(number(request, "id", -1));
            case "part" -> part(number(request, "id", -1), "reference".equals(string(request, "from", "runtime")));
            case "save" -> save(request);
            case "delete" -> delete(request);
            case "import-parts" -> importParts(request);
            case "prepare-reference" -> prepareReference(request);
            case "upload" -> upload(request);
            case "asset-check" -> assetCheck(request);
            case "asset" -> gameAsset(request);
            case "image-list" -> imageList(request);
            default -> throw new ApiException(404, "Không có action này");
        };
    }

    private static JsonObject gameAsset(JsonObject request) throws IOException {
        int id = number(request, "id", -1), zoom = number(request, "zoom", 1);
        if (id < 0 || id > 32767 || zoom < 1 || zoom > 4) fail(400, "Ảnh không hợp lệ");
        PendingImage pending=pendingImages(string(request,"studioSession","local")).get(id);
        if(pending!=null){JsonObject out=new JsonObject();out.addProperty("png",Base64.getEncoder().encodeToString(pending.atZoom(zoom)));return out;}
        Path file = ICONS.resolve(zoom + "/icon/" + id + ".png");
        if (!Files.isRegularFile(file)) fail(404, "Chưa có ảnh " + id);
        JsonObject out = new JsonObject();
        out.addProperty("png", Base64.getEncoder().encodeToString(Files.readAllBytes(file)));
        return out;
    }

    private static JsonObject assetCheck(JsonObject request){
        int id=number(request,"id",-1),zoom=number(request,"zoom",4);
        if(id<0||id>32767||zoom<1||zoom>4)fail(400,"Ảnh không hợp lệ");
        JsonObject out=new JsonObject();out.addProperty("id",id);
        out.addProperty("exists",Files.isRegularFile(ICONS.resolve(zoom+"/icon/"+id+".png")));
        return out;
    }

    private static Map<Integer,PendingImage> pendingImages(String session){
        return PENDING_IMAGES.computeIfAbsent(session==null||session.isBlank()?"local":session,key->new ConcurrentHashMap<>());
    }

    private static void handle(HttpExchange exchange) throws IOException {
        try {
            String path = exchange.getRequestURI().getPath();
            if (path.equals("/") || path.equals("/index.html")) {
                sendBytes(exchange, 200, "text/html; charset=utf-8", Files.readAllBytes(UI.resolve("index.html")));
                return;
            }
            if (!TOKEN.equals(exchange.getRequestHeaders().getFirst("X-Editor-Token"))
                    && !(path.equals("/asset") && TOKEN.equals(query(exchange,"token")))) {
                fail(403, "Thiếu mã phiên của trình sửa part");
            }
            if (path.equals("/char-info.json")) {
                sendBytes(exchange, 200, "application/json; charset=utf-8", Files.readAllBytes(UI.resolve("char-info.json")));
                return;
            }
            if (path.equals("/asset")) {
                int id = parameter(exchange, "id", -1);
                int zoom = parameter(exchange, "zoom", 1);
                if (id < 0 || id > 32767 || zoom < 1 || zoom > 4) fail(400, "ID ảnh hoặc zoom không hợp lệ");
                boolean source = "source".equals(query(exchange, "from"));
                Path file = source ? SOURCE_ICONS.resolve("zoom" + zoom + "/icon/" + id + ".png")
                        : ICONS.resolve(zoom + "/icon/" + id + ".png");
                if (remoteHost != null && !source) {
                    JsonObject params = new JsonObject(); params.addProperty("id", id); params.addProperty("zoom", zoom);
                    JsonObject remote = remoteRequest("asset", params);
                    if (remote.has("error")) fail(404, remote.get("error").getAsString());
                    sendBytes(exchange, 200, "image/png", Base64.getDecoder().decode(remote.get("png").getAsString()));
                } else {
                    PendingImage pending=source?null:pendingImages("local").get(id);
                    if(pending!=null){sendBytes(exchange,200,"image/png",pending.atZoom(zoom));return;}
                    if (!Files.isRegularFile(file)) fail(404, "Chưa có ảnh " + id);
                    sendBytes(exchange, 200, "image/png", Files.readAllBytes(file));
                }
                return;
            }
            boolean post = exchange.getRequestMethod().equals("POST");
            if (path.equals("/api/meta")) {
                JsonObject meta = new JsonObject(); meta.addProperty("remote", remoteHost != null);
                if (remoteHost != null) meta.addProperty("host", remoteHost + ":" + remotePort);
                sendJson(exchange, 200, meta); return;
            }
            if (remoteHost != null) {
                if (path.startsWith("/api/")) {
                    String action = path.substring(5);
                    JsonObject request = post ? readBody(exchange) : queryObject(exchange);
                    JsonObject result = remoteRequest(action, request);
                    sendJson(exchange, result.has("error") ? 400 : 200, result); return;
                }
                fail(404, "Không có action này");
            }
            JsonObject result;
            switch (path) {
                case "/api/status" -> result = status();
                case "/api/list" -> result = list(exchange);
                case "/api/item" -> result = item(exchange);
                case "/api/part" -> result = part(exchange);
                case "/api/save" -> result = post ? save(readBody(exchange)) : methodError();
                case "/api/delete" -> result = post ? delete(readBody(exchange)) : methodError();
                case "/api/import-parts" -> result = post ? importParts() : methodError();
                case "/api/prepare-reference" -> result = post ? prepareReference(readBody(exchange)) : methodError();
                case "/api/upload" -> result = post ? upload(readBody(exchange)) : methodError();
                case "/api/asset-check" -> result = assetCheck(queryObject(exchange));
                case "/api/image-list" -> result = imageList(queryObject(exchange));
                default -> throw new ApiException(404, "Không có action này");
            }
            sendJson(exchange, 200, result);
        } catch (ApiException ex) {
            sendJson(exchange, ex.status, error(ex.getMessage()));
        } catch (SQLException ex) {
            if (ex.getSQLState()!=null && ex.getSQLState().startsWith("08"))
                sendJson(exchange, 503, error("Không kết nối được MariaDB theo server.properties. Hãy chạy DB rồi thử lại."));
            else {
                ex.printStackTrace();
                sendJson(exchange, 500, error("Lỗi SQL: " + ex.getMessage()));
            }
        } catch (Exception ex) {
            ex.printStackTrace();
            sendJson(exchange, 500, error(ex.getMessage() == null ? "Lỗi server" : ex.getMessage()));
        } finally {
            exchange.close();
        }
    }

    private static JsonObject queryObject(HttpExchange exchange) {
        JsonObject out = new JsonObject();
        String raw = exchange.getRequestURI().getRawQuery();
        if (raw == null) return out;
        for (String field : raw.split("&")) {
            String[] pair = field.split("=", 2);
            out.addProperty(java.net.URLDecoder.decode(pair[0], StandardCharsets.UTF_8),
                    java.net.URLDecoder.decode(pair.length > 1 ? pair[1] : "", StandardCharsets.UTF_8));
        }
        return out;
    }

    private static synchronized JsonObject remoteRequest(String action, JsonObject request) throws IOException {
        if ("auth".equals(action)) {
            if (remoteClient != null) remoteClient.close();
            remoteClient = new GamePartEditorClient(remoteHost, remotePort);
            remoteStageSession=UUID.randomUUID().toString();
        } else if (remoteClient == null) {
            throw new ApiException(401, "Đăng nhập tài khoản admin trước");
        }
        if(!"auth".equals(action)){
            request=request.deepCopy();
            request.addProperty("studioSession",remoteStageSession);
        }
        if ("prepare-reference".equals(action)) request = withSourceImages(request);
        if ("import-parts".equals(action) && !REFERENCE_PARTS.isEmpty()) {
            request = request.deepCopy();
            JsonArray parts = new JsonArray();
            for (JsonObject part : REFERENCE_PARTS) parts.add(part);
            request.add("referenceParts", parts);
        }
        try { return remoteClient.request(action, request); }
        catch (java.net.SocketTimeoutException ex) {
            remoteClient.close(); remoteClient = null;
            throw new ApiException(504, "Đã kết nối " + remoteHost + ":" + remotePort
                    + " nhưng game server không phản hồi action -126. Cần triển khai JAR BE mới trên chính server đó và khởi động lại.");
        }
        catch (IOException ex) {
            remoteClient.close(); remoteClient = null;
            String detail = ex instanceof java.io.EOFException
                    ? "Game server đã đóng phiên Part Studio. Kiểm tra BE đã cập nhật action admin (xoá bộ đếm chờ đăng nhập) và khởi động lại."
                    : "Mất kết nối Part Studio với game server: " + (ex.getMessage() == null ? ex.getClass().getSimpleName() : ex.getMessage());
            throw new ApiException(503, detail + " Hãy kết nối lại tài khoản admin.");
        }
    }

    private static JsonObject withSourceImages(JsonObject request) throws IOException {
        int id = number(request, "id", -1);
        if (id < 0 || id >= REFERENCE_PARTS.size()) return request;
        JsonObject images = new JsonObject();
        for (JsonElement element : REFERENCE_PARTS.get(id).getAsJsonArray("frames")) {
            int imageId = element.getAsJsonArray().get(0).getAsInt();
            if (imageId <= 0 || images.has(String.valueOf(imageId))) continue;
            JsonArray zooms = new JsonArray();
            for (int z = 1; z <= 4; z++) {
                Path image = SOURCE_ICONS.resolve("zoom" + z + "/icon/" + imageId + ".png");
                zooms.add(Files.isRegularFile(image) ? Base64.getEncoder().encodeToString(Files.readAllBytes(image)) : "");
            }
            images.add(String.valueOf(imageId), zooms);
        }
        JsonObject copy = request.deepCopy();
        copy.add("sourcePart", REFERENCE_PARTS.get(id).deepCopy());
        copy.add("sourceImages", images);
        return copy;
    }

    private static byte[] sourceImage(JsonObject request, int imageId, int zoom) throws IOException {
        if (request.has("sourceImages")) {
            JsonObject images = request.getAsJsonObject("sourceImages");
            JsonArray zooms = images.has(String.valueOf(imageId)) ? images.getAsJsonArray(String.valueOf(imageId)) : null;
            if (zooms == null || zooms.size() < zoom || zooms.get(zoom - 1).getAsString().isEmpty()) return null;
            return Base64.getDecoder().decode(zooms.get(zoom - 1).getAsString());
        }
        Path file = SOURCE_ICONS.resolve("zoom" + zoom + "/icon/" + imageId + ".png");
        return Files.isRegularFile(file) ? Files.readAllBytes(file) : null;
    }

    private static JsonObject methodError() { throw new ApiException(405, "Chỉ nhận POST"); }
    private static void fail(int status, String message) { throw new ApiException(status, message); }
    private static JsonObject error(String message) { JsonObject result = new JsonObject(); result.addProperty("error", message); return result; }
    private static void sendJson(HttpExchange exchange, int status, JsonObject body) throws IOException {
        sendBytes(exchange, status, "application/json; charset=utf-8", body.toString().getBytes(StandardCharsets.UTF_8));
    }
    private static void sendBytes(HttpExchange exchange, int status, String type, byte[] bytes) throws IOException {
        exchange.getResponseHeaders().set("Content-Type", type);
        exchange.getResponseHeaders().set("Cache-Control", "no-store");
        exchange.getResponseHeaders().set("X-Content-Type-Options", "nosniff");
        exchange.sendResponseHeaders(status, bytes.length);
        try (var out = exchange.getResponseBody()) { out.write(bytes); }
    }
    private static JsonObject readBody(HttpExchange exchange) throws IOException {
        byte[] bytes = exchange.getRequestBody().readNBytes(5_000_001);
        if (bytes.length > 5_000_000) fail(413, "Dữ liệu quá lớn");
        try { return JsonParser.parseString(new String(bytes, StandardCharsets.UTF_8)).getAsJsonObject(); }
        catch (Exception ex) { throw new ApiException(400, "JSON không hợp lệ"); }
    }
    private static String query(HttpExchange exchange, String key) {
        String raw = exchange.getRequestURI().getRawQuery();
        if (raw == null) return null;
        for (String field : raw.split("&")) {
            String[] pair = field.split("=", 2);
            if (pair[0].equals(key)) return java.net.URLDecoder.decode(pair.length > 1 ? pair[1] : "", StandardCharsets.UTF_8);
        }
        return null;
    }
    private static int parameter(HttpExchange exchange, String key, int fallback) {
        String value = query(exchange, key);
        try { return value == null ? fallback : Integer.parseInt(value); }
        catch (NumberFormatException ex) { throw new ApiException(400, "Tham số " + key + " không hợp lệ"); }
    }
    private static int number(JsonObject object, String key, int fallback) {
        return object.has(key) && !object.get(key).isJsonNull() ? object.get(key).getAsInt() : fallback;
    }
    private static String string(JsonObject object, String key, String fallback) {
        return object.has(key) && !object.get(key).isJsonNull() ? object.get(key).getAsString() : fallback;
    }
    private static String sha(JsonObject object) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(object.toString().getBytes(StandardCharsets.UTF_8));
            return java.util.HexFormat.of().formatHex(digest);
        } catch (Exception ex) { throw new IllegalStateException(ex); }
    }

    private static JsonObject status() throws SQLException {
        try (Connection c = connect()) {
            JsonObject out = new JsonObject();
            out.addProperty("database", c.getCatalog());
            out.addProperty("items", scalar(c, "SELECT COUNT(*) FROM item_template"));
            out.addProperty("parts", scalar(c, "SELECT COUNT(*) FROM part"));
            out.addProperty("costumes", scalar(c, "SELECT COUNT(*) FROM item_template WHERE TYPE=5"));
            out.addProperty("pets", scalar(c, "SELECT COUNT(*) FROM item_template WHERE TYPE IN (18,21,72)"));
            out.addProperty("avatarUpload", true);
            return out;
        }
    }
    private static int scalar(Connection c, String sql) throws SQLException {
        try (Statement s = c.createStatement(); ResultSet r = s.executeQuery(sql)) { r.next(); return r.getInt(1); }
    }

    private static JsonObject list(HttpExchange exchange) throws SQLException {
        return list(query(exchange, "kind"), query(exchange, "q"));
    }
    private static JsonObject list(String requestedKind, String search) throws SQLException {
        String kind = "pet".equals(requestedKind) ? "pet" : "costume";
        if (search == null) search = "";
        JsonArray items = new JsonArray();
        String sql = "SELECT t.id,t.TYPE,t.gender,t.NAME,t.icon_id,t.part,"
                + (kind.equals("pet") ? "EXISTS(SELECT 1 FROM mini_pet m WHERE m.id_temp=t.id)" :
                "EXISTS(SELECT 1 FROM cai_trang m WHERE m.id_temp=t.id)")
                + " FROM item_template t WHERE " + (kind.equals("pet") ? "t.TYPE IN (18,21,72)" : "t.TYPE=5")
                + " AND t.NAME LIKE ? ORDER BY t.id LIMIT 32767";
        try (Connection c = connect(); PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setString(1, "%" + search + "%");
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    JsonObject row = new JsonObject();
                    row.addProperty("id", rs.getInt(1)); row.addProperty("type", rs.getInt(2));
                    row.addProperty("gender", rs.getInt(3)); row.addProperty("name", rs.getString(4));
                    row.addProperty("iconId", rs.getInt(5)); row.addProperty("part", rs.getInt(6));
                    row.addProperty("hasMapping", rs.getBoolean(7)); items.add(row);
                }
            }
        }
        JsonObject out = new JsonObject(); out.add("items", items); out.addProperty("count", items.size()); return out;
    }

    private static JsonObject item(HttpExchange exchange) throws SQLException {
        return item(parameter(exchange, "id", -1));
    }
    private static JsonObject item(int id) throws SQLException {
        try (Connection c = connect()) {
            JsonObject out = loadItem(c, id);
            if (out == null) fail(404, "Không tìm thấy item " + id);
            out.addProperty("revision", sha(out));
            return out;
        }
    }

    private static JsonObject loadItem(Connection c, int id) throws SQLException {
        JsonObject out = new JsonObject(); JsonObject template = new JsonObject();
        try (PreparedStatement ps = c.prepareStatement("SELECT id,TYPE,gender,NAME,description,icon_id,part,power_require FROM item_template WHERE id=?")) {
            ps.setInt(1, id);
            try (ResultSet r = ps.executeQuery()) {
                if (!r.next()) return null;
                template.addProperty("id", r.getInt(1)); template.addProperty("type", r.getInt(2));
                template.addProperty("gender", r.getInt(3)); template.addProperty("name", r.getString(4));
                template.addProperty("description", r.getString(5)); template.addProperty("iconId", r.getInt(6));
                template.addProperty("part", r.getInt(7)); template.addProperty("power", r.getInt(8));
            }
        }
        out.add("item", template);
        JsonObject mapping = new JsonObject();
        int type = template.get("type").getAsInt();
        String sql = type == 5 ? "SELECT head,body,leg,bag FROM cai_trang WHERE id_temp=?" :
                "SELECT head,body,leg FROM mini_pet WHERE id_temp=? LIMIT 1";
        int[] ids = {-1,-1,-1,-1};
        if (type != 72) try (PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setInt(1, id);
            try (ResultSet r = ps.executeQuery()) {
                if (r.next()) for (int i=0; i<(type==5?4:3); i++) ids[i] = r.getInt(i+1);
            }
        }
        String[] slots = {"head","body","leg"};
        for (int i=0;i<3;i++) {
            JsonObject p = ids[i] < 0 ? null : loadPart(c, ids[i], false);
            if (ids[i]>=0 && p==null) fail(409, "Mapping " + slots[i] + " trỏ tới part thiếu: " + ids[i]);
            if (p==null) { p=new JsonObject(); p.addProperty("id", -1); p.addProperty("type", i); p.add("frames", new JsonArray()); }
            mapping.add(slots[i], p);
        }
        mapping.addProperty("bag", ids[3]);
        out.add("mapping", mapping);
        int avatarId=-1;
        if(type==5 && ids[0]>=0)try(PreparedStatement ps=c.prepareStatement("SELECT avatar_id FROM head_avatar WHERE head_id=? LIMIT 1")){
            ps.setInt(1,ids[0]);try(ResultSet r=ps.executeQuery()){if(r.next())avatarId=r.getInt(1);}
        }
        template.addProperty("avatarId",avatarId);
        try(PreparedStatement ps=c.prepareStatement("SELECT source.source_item_id,ref.part_id FROM admin_catalog_item_source source JOIN reference_item_template ref ON ref.source_server=source.source_server AND ref.id=source.source_item_id WHERE source.item_id=?")){
            ps.setInt(1,id);
            try(ResultSet r=ps.executeQuery()){
                if(r.next()){
                    JsonObject reference=new JsonObject();reference.addProperty("itemId",r.getInt(1));
                    reference.addProperty("partId",r.getInt(2));out.add("reference",reference);
                }
            }
        }catch(SQLException ignored){ /* V4/V9 may not yet be applied */ }
        return out;
    }

    private static JsonObject part(HttpExchange exchange) throws SQLException {
        return part(parameter(exchange, "id", -1), "reference".equals(query(exchange, "from")));
    }
    private static JsonObject part(int id, boolean reference) throws SQLException {
        try (Connection c = connect()) {
            JsonObject out = loadPart(c, id, reference);
            if (out == null) fail(404, "Không tìm thấy part " + id);
            out.addProperty("source", reference ? "reference" : "runtime");
            return out;
        }
    }
    private static JsonObject loadPart(Connection c, int id, boolean reference) throws SQLException {
        if (id < 0) return null;
        if(reference)return id<REFERENCE_PARTS.size()?REFERENCE_PARTS.get(id).deepCopy():null;
        String sql = "SELECT TYPE,DATA FROM part WHERE id=?";
        try (PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setInt(1,id);
            try (ResultSet r = ps.executeQuery()) {
                if (!r.next()) return null;
                JsonObject out = new JsonObject(); out.addProperty("id", id); out.addProperty("type", r.getInt(1));
                out.add("frames", JsonParser.parseString(r.getString(2)));
                return out;
            }
        }
    }

    private static JsonObject save(JsonObject request) throws SQLException,IOException {
        synchronized (WRITE_LOCK) {
            String stageSession=string(request,"studioSession","local");
            Map<Integer,PendingImage> staged=pendingImages(stageSession);
            List<Path> writtenImages=new ArrayList<>();
            try (Connection c = connect()) {
                ensureSupportTables(c);
                c.setAutoCommit(false);
                try {
                    JsonObject item = request.getAsJsonObject("item");
                    JsonObject mapping = request.getAsJsonObject("mapping");
                    if (item==null || mapping==null) fail(400,"Thiếu item hoặc mapping");
                    int id = number(item,"id",-1); int type=number(item,"type",5);
                    if (type==18) type=21;
                    if (type!=5 && type!=18 && type!=21 && type!=72) fail(400,"Chỉ sửa cải trang hoặc pet");
                    String name=string(item,"name","").trim(); String desc=string(item,"description","");
                    int icon=number(item,"iconId",-1), avatar=number(item,"avatarId",-1), gender=number(item,"gender",3);
                    int power=number(item,"power",0), itemPart=number(item,"part",-1);
                    if (name.isBlank() || name.length()>255 || desc.length()>255 || icon<0 || icon>32767
                            || avatar < -1 || avatar>32767 || gender<0 || gender>3 || power<0 || itemPart < -1 || itemPart>32767) fail(400,"Thông tin item không hợp lệ");
                    if (type==72) for (String slot:new String[]{"head","body","leg"}) {
                        JsonObject part=mapping.has(slot) && mapping.get(slot).isJsonObject()?mapping.getAsJsonObject(slot):null;
                        if (part!=null && (number(part,"id",-1)>=0
                                || part.has("frames") && part.get("frames").isJsonArray()
                                && part.getAsJsonArray("frames").size()>0))
                            fail(400,"Pet type 72 dùng pet_follow và ảnh icon, không dùng part đầu/thân/chân");
                    }
                    if(id>=0)lockItem(c,id);
                    JsonObject current = id < 0 ? null : loadItem(c,id);
                    if ((current==null || current.getAsJsonObject("item").get("iconId").getAsInt()!=icon)
                            && !Files.isRegularFile(ICONS.resolve("1/icon/"+icon+".png"))&&!staged.containsKey(icon))
                        fail(400,"Icon ID chưa có PNG trên server: "+icon);
                    if (id>=0 && current==null) fail(404,"Item đã bị xóa");
                    if (current!=null && !sha(current).equals(string(request,"revision",""))) fail(409,"Dữ liệu đã thay đổi, tải lại trước khi lưu");
                    if (id<0) {
                        id=scalar(c,"SELECT COALESCE(MAX(id),-1)+1 FROM item_template");
                    }
                    int head=savePart(c,mapping.getAsJsonObject("head"),0,staged,type==18||type==21);
                    int body=savePart(c,mapping.getAsJsonObject("body"),1,staged,type==18||type==21);
                    int leg=savePart(c,mapping.getAsJsonObject("leg"),2,staged,type==18||type==21);
                    int bag=number(mapping,"bag",-1);
                    if (bag < -1 || bag>32767) fail(400,"Bag ID không hợp lệ");
                    if (current==null && type==5 && head<0 && body<0 && leg<0) fail(400,"Cải trang mới cần ít nhất một part");
                    if ((type==18 || type==21) && (head<0 || body<0 || leg<0))
                        fail(400,"Pet dùng mini_pet cần đủ head/body/leg");
                    // Full costumes and pets commonly keep item_template.part=-1;
                    // their outfit IDs live in cai_trang/mini_pet instead.
                    if (type==5 && head>=0 && body<0 && leg<0) {
                        if (current==null && itemPart<0) itemPart=head;
                        else if (current!=null) {
                            JsonObject oldMapping=current.getAsJsonObject("mapping");
                            int oldHead=oldMapping.getAsJsonObject("head").get("id").getAsInt();
                            int oldBody=oldMapping.getAsJsonObject("body").get("id").getAsInt();
                            int oldLeg=oldMapping.getAsJsonObject("leg").get("id").getAsInt();
                            int oldItemPart=current.getAsJsonObject("item").get("part").getAsInt();
                            if (oldHead>=0 && oldBody<0 && oldLeg<0
                                    && oldItemPart==oldHead && itemPart==oldItemPart)
                                itemPart=head;
                        }
                    }
                    if (current==null) {
                        try (PreparedStatement ps=c.prepareStatement("INSERT INTO item_template (id,TYPE,gender,NAME,description,icon_id,part,is_up_to_up,power_require) VALUES (?,?,?,?,?,?,?,0,?)")) {
                            ps.setInt(1,id); ps.setInt(2,type); ps.setInt(3,gender); ps.setString(4,name); ps.setString(5,desc);
                            ps.setInt(6,icon); ps.setInt(7,itemPart); ps.setInt(8,power); ps.executeUpdate();
                        }
                    } else {
                        try (PreparedStatement ps=c.prepareStatement("UPDATE item_template SET TYPE=?,gender=?,NAME=?,description=?,icon_id=?,part=?,power_require=? WHERE id=?")) {
                            ps.setInt(1,type); ps.setInt(2,gender); ps.setString(3,name); ps.setString(4,desc);
                            ps.setInt(5,icon); ps.setInt(6,itemPart); ps.setInt(7,power); ps.setInt(8,id); ps.executeUpdate();
                        }
                        int oldType=current.getAsJsonObject("item").get("type").getAsInt();
                        if (oldType==5 && type!=5) execute(c,"DELETE FROM cai_trang WHERE id_temp=?",id);
                        if (oldType!=5 && type==5) execute(c,"DELETE FROM mini_pet WHERE id_temp=?",id);
                    }
                    if (type==5 && (head>=0 || body>=0 || leg>=0 || bag>=0)) {
                        try (PreparedStatement ps=c.prepareStatement("INSERT INTO cai_trang (id_temp,head,body,leg,bag) VALUES (?,?,?,?,?) ON DUPLICATE KEY UPDATE head=VALUES(head),body=VALUES(body),leg=VALUES(leg),bag=VALUES(bag)")) {
                            ps.setInt(1,id);ps.setInt(2,head);ps.setInt(3,body);ps.setInt(4,leg);ps.setInt(5,bag);ps.executeUpdate();
                        }
                    } else if (type==5) {
                        execute(c,"DELETE FROM cai_trang WHERE id_temp=?",id);
                    } else {
                        execute(c,"DELETE FROM mini_pet WHERE id_temp=?",id);
                        if (head>=0 || body>=0 || leg>=0) try (PreparedStatement ps=c.prepareStatement("INSERT INTO mini_pet (id_temp,head,body,leg) VALUES (?,?,?,?)")) {
                            ps.setInt(1,id);ps.setInt(2,head);ps.setInt(3,body);ps.setInt(4,leg);ps.executeUpdate();
                        }
                        if (type==18 || type==21) execute(c,"DELETE FROM pet_follow WHERE id_temp=?",id);
                    }
                    if (type==5 && head>=0) {
                        if(avatar<0)fail(400,"Chọn Avatar ID cho part đầu trước khi lưu");
                        if(!Files.isRegularFile(ICONS.resolve("1/icon/"+avatar+".png"))&&!staged.containsKey(avatar))
                            fail(400,"Avatar ID chưa có ảnh trên server: "+avatar);
                        saveHeadAvatar(c,head,avatar);
                    }
                    bump(c,true,true);
                    writePendingImages(referencedPendingImages(request,staged),staged,writtenImages);
                    c.commit();
                    staged.clear();
                    JsonObject out=new JsonObject();out.addProperty("id",id);out.addProperty("message","Đã lưu trực tiếp vào SQL. Khởi động lại BE để nạp cache.");return out;
                } catch (Exception ex) {
                    c.rollback();
                    for(Path path:writtenImages)Files.deleteIfExists(path);
                    throw ex;
                }
            }
        }
    }

    private static Set<Integer> referencedPendingImages(JsonObject request,Map<Integer,PendingImage> staged){
        Set<Integer> referenced=new HashSet<>();
        JsonObject item=request.has("item")?request.getAsJsonObject("item"):null;
        if(item!=null)referenced.add(number(item,"iconId",-1));
        if(item!=null)referenced.add(number(item,"avatarId",-1));
        JsonObject mapping=request.has("mapping")?request.getAsJsonObject("mapping"):null;
        if(mapping!=null)for(String slot:new String[]{"head","body","leg"}){
            JsonObject part=mapping.has(slot)&&mapping.get(slot).isJsonObject()?mapping.getAsJsonObject(slot):null;
            if(part==null||!part.has("frames")||!part.get("frames").isJsonArray())continue;
            for(JsonElement row:part.getAsJsonArray("frames"))if(row.isJsonArray()&&row.getAsJsonArray().size()>0)
                referenced.add(row.getAsJsonArray().get(0).getAsInt());
        }
        referenced.retainAll(staged.keySet());
        return referenced;
    }

    private static void writePendingImages(Set<Integer> ids,Map<Integer,PendingImage> staged,List<Path> written)throws IOException{
        for(int id:ids){
            PendingImage pending=staged.get(id);
            if(pending==null)continue;
            byte[][] variants=new byte[5][];
            for(int z=1;z<=4;z++)variants[z]=pending.atZoom(z);
            for(int z=1;z<=4;z++){
                Path target=ICONS.resolve(z+"/icon/"+id+".png");
                Files.createDirectories(target.getParent());
                Files.write(target,variants[z],StandardOpenOption.CREATE_NEW);
                written.add(target);
            }
        }
    }

    private static int savePart(Connection c, JsonObject part, int expectedType,
            Map<Integer,PendingImage> staged, boolean requireImages) throws SQLException {
        if (part==null) return -1;
        if ("reference".equals(string(part,"source","runtime")))
            fail(400,"Phải nạp part S14 bằng nút Nạp part để xử lý ảnh trùng ID");
        int id=number(part,"id",-1);
        if (id < -1) fail(400,"Part ID không hợp lệ");
        JsonArray frames=part.has("frames") && part.get("frames").isJsonArray() ? part.getAsJsonArray("frames") : new JsonArray();
        if (part.has("missingImages") && part.get("missingImages").isJsonArray())
            for (JsonElement missing:part.getAsJsonArray("missingImages"))
                for (JsonElement frame:frames)
                    if (frame.getAsJsonArray().get(0).getAsInt()==missing.getAsInt())
                        fail(400,"Part còn ảnh nguồn thiếu: " + missing.getAsInt());
        if (id<0 && frames.size()==0) return -1;
        if (frames.size()==0 && id>=0) {
            JsonObject prior=loadPart(c,id,false);
            if (prior==null || prior.get("type").getAsInt()!=expectedType) fail(400,"Part " + id + " không đúng loại");
            return id;
        }
        if (frames.size()!=FRAME_COUNTS[expectedType]) fail(400,"Part loại " + expectedType + " cần " + FRAME_COUNTS[expectedType] + " frame");
        for (JsonElement element:frames) {
            if (!element.isJsonArray() || element.getAsJsonArray().size()!=3) fail(400,"Frame phải có [image,dx,dy]");
            JsonArray row=element.getAsJsonArray(); int image=row.get(0).getAsInt(),dx=row.get(1).getAsInt(),dy=row.get(2).getAsInt();
            if (image < -1 || image>32767 || dx<-128 || dx>127 || dy<-128 || dy>127) fail(400,"Frame vượt giới hạn client");
            if (requireImages && image>0 && !staged.containsKey(image)
                    && !Files.isRegularFile(ICONS.resolve("1/icon/"+image+".png")))
                fail(400,"Frame tham chiếu ảnh chưa có trên server: "+image);
        }
        if (id>=0) {
            JsonObject prior=loadPart(c,id,false);
            if (prior!=null && prior.get("type").getAsInt()==expectedType
                    && prior.get("frames").equals(frames)) return id;
        }
        int next=scalar(c,"SELECT COALESCE(MAX(id),-1)+1 FROM part");
        if (next>32767 || next!=scalar(c,"SELECT COUNT(*) FROM part")) fail(409,"ID part bị khuyết hoặc vượt giới hạn client");
        try (PreparedStatement ps=c.prepareStatement("INSERT INTO part (id,TYPE,DATA) VALUES (?,?,?)")) {
            ps.setInt(1,next);ps.setInt(2,expectedType);ps.setString(3,frames.toString());ps.executeUpdate();
        }
        return next;
    }

    private static void execute(Connection c,String sql,int id) throws SQLException {
        try (PreparedStatement ps=c.prepareStatement(sql)) {ps.setInt(1,id);ps.executeUpdate();}
    }
    private static void saveHeadAvatar(Connection c,int head,int avatar) throws SQLException {
        boolean exists;
        try(PreparedStatement select=c.prepareStatement("SELECT avatar_id FROM head_avatar WHERE head_id=? LIMIT 1 FOR UPDATE")){
            select.setInt(1,head);try(ResultSet row=select.executeQuery()){exists=row.next();}
        }
        if(!exists){
            try(PreparedStatement insert=c.prepareStatement("INSERT INTO head_avatar (head_id,avatar_id) VALUES (?,?)")){
                insert.setInt(1,head);insert.setInt(2,avatar);insert.executeUpdate();
            }
            return;
        }
        try(PreparedStatement update=c.prepareStatement("UPDATE head_avatar SET avatar_id=? WHERE head_id=?")){
            update.setInt(1,avatar);update.setInt(2,head);
            update.executeUpdate();
        }
    }
    private static void lockItem(Connection c,int id) throws SQLException {
        try(PreparedStatement ps=c.prepareStatement("SELECT id FROM item_template WHERE id=? FOR UPDATE")){
            ps.setInt(1,id);try(ResultSet ignored=ps.executeQuery()){while(ignored.next()) { /* row lock */ }}
        }
    }
    private static boolean localGameRunning() {
        try(var socket=new java.net.Socket()){
            socket.connect(new InetSocketAddress("127.0.0.1",Integer.parseInt(config.getProperty("server.port","14445"))),150);
            return true;
        }catch(Exception ignored){return false;}
    }
    private static void bump(Connection c,boolean data,boolean items) throws SQLException {
        try (Statement s=c.createStatement()) {
            s.execute("UPDATE admin_editor_state SET data_version=CASE WHEN data_version>=120 THEN 1 ELSE data_version+"+(data?1:0)+" END, item_version=CASE WHEN item_version>=120 THEN 1 ELSE item_version+"+(items?1:0)+" END WHERE id=1");
        }
    }

    private static void ensureSupportTables(Connection c) throws SQLException {
        // MariaDB DDL commits implicitly; create metadata tables before the edit transaction.
        try (Statement s=c.createStatement()) {
            s.execute("CREATE TABLE IF NOT EXISTS admin_editor_state (id TINYINT NOT NULL PRIMARY KEY, data_version TINYINT NOT NULL, item_version TINYINT NOT NULL)");
            s.execute("INSERT IGNORE INTO admin_editor_state (id,data_version,item_version) VALUES (1,7,8)");
            s.execute("CREATE TABLE IF NOT EXISTS admin_part_alias (source_server VARCHAR(100) NOT NULL, source_part_id INT NOT NULL, part_id INT NOT NULL, PRIMARY KEY (source_server,source_part_id), UNIQUE KEY uq_part_id (part_id))");
            s.execute("CREATE TABLE IF NOT EXISTS admin_editor_image_alias (source_image_id INT NOT NULL PRIMARY KEY, image_id INT NOT NULL UNIQUE)");
        }
    }

    private static JsonObject delete(JsonObject request) throws SQLException {
        int id=number(request,"id",-1); String scope=string(request,"scope","mapping");
        synchronized (WRITE_LOCK) {
            try (Connection c=connect()) {
                ensureSupportTables(c);
                c.setAutoCommit(false);
                try {
                    lockItem(c,id);
                    JsonObject current=loadItem(c,id);if (current==null) fail(404,"Không tìm thấy item");
                    if (!sha(current).equals(string(request,"revision",""))) fail(409,"Dữ liệu đã đổi, tải lại");
                    int type=current.getAsJsonObject("item").get("type").getAsInt();
                    if ("item".equals(scope)) {
                        if(localGameRunning())fail(409,"Dừng BE trước khi xóa hẳn item_template");
                        if (id!=scalar(c,"SELECT MAX(id) FROM item_template")) fail(409,"Chỉ xóa được item ID cuối cùng; xóa giữa bảng làm lệch ID client");
                        for (String table:new String[]{"item_shop","consignment_shop","collection_book","pet_follow"}) {
                            String column=table.equals("item_shop")||table.equals("pet_follow")?"temp_id":"item_id";
                            if (table.equals("pet_follow")) column="id_temp";
                            try (PreparedStatement ps=c.prepareStatement("SELECT 1 FROM "+table+" WHERE "+column+"=? LIMIT 1")) {
                                ps.setInt(1,id);try(ResultSet r=ps.executeQuery()){if(r.next())fail(409,"Item đang được "+table+" sử dụng");}
                            }
                        }
                        try(PreparedStatement ps=c.prepareStatement("SELECT items FROM gift_codes WHERE items LIKE ?")){
                            ps.setString(1,"%"+id+"%");
                            try(ResultSet r=ps.executeQuery()){
                                while(r.next())
                                    if(r.getString(1)!=null && r.getString(1).matches("(?s).*(?<![0-9])"+id+"(?![0-9]).*"))
                                        fail(409,"Item đang có trong gift_codes");
                            }
                        }
                        String pattern="%\"temp_id\":"+id+"%";
                        try (PreparedStatement ps=c.prepareStatement("SELECT items_body,items_bag,items_box,items_box_lucky_round FROM player WHERE items_body LIKE ? OR items_bag LIKE ? OR items_box LIKE ? OR items_box_lucky_round LIKE ?")) {
                            for(int i=1;i<=4;i++)ps.setString(i,pattern);
                            try(ResultSet r=ps.executeQuery()){
                                while(r.next()) for(int i=1;i<=4;i++) if (r.getString(i)!=null && r.getString(i).matches("(?s).*\\\"temp_id\\\":"+id+"(?![0-9]).*")) fail(409,"Item đang nằm trong hành trang nhân vật");
                            }
                        }
                        execute(c,"DELETE FROM item_template WHERE id=?",id);
                        try { execute(c,"DELETE FROM admin_catalog_item_source WHERE item_id=?",id); }
                        catch(SQLException ignored) { /* optional V9 table */ }
                    } else if (!"mapping".equals(scope)) fail(400,"Kiểu xóa không hợp lệ");
                    execute(c,type==5?"DELETE FROM cai_trang WHERE id_temp=?":"DELETE FROM mini_pet WHERE id_temp=?",id);
                    bump(c,true,"item".equals(scope));c.commit();
                    JsonObject out=new JsonObject();out.addProperty("message","Đã xóa "+scope+" trong SQL. Khởi động lại BE.");return out;
                } catch(Exception ex){c.rollback();throw ex;}
            }
        }
    }

    private static JsonObject importParts() throws SQLException {
        return importParts(new JsonObject());
    }
    private static JsonObject importParts(JsonObject request) throws SQLException {
        synchronized (WRITE_LOCK) {
            try(Connection c=connect()){
                ensureSupportTables(c);
                c.setAutoCommit(false);
                try {
                    int added=0, reused=0;
                    List<JsonObject> parts = new ArrayList<>();
                    if(request.has("referenceParts"))
                        for(JsonElement entry:request.getAsJsonArray("referenceParts"))parts.add(entry.getAsJsonObject());
                    else parts.addAll(REFERENCE_PARTS);
                    if(parts.isEmpty())fail(404,"Thiếu file part.bin tham chiếu");
                    for(JsonObject sourcePart:parts){
                                int sourceId=sourcePart.get("id").getAsInt(), type=sourcePart.get("type").getAsInt();
                                String data=sourcePart.get("frames").toString();
                                JsonObject existing=loadPart(c,sourceId,false);
                                if(existing!=null && existing.get("type").getAsInt()==type
                                        && existing.get("frames").equals(JsonParser.parseString(data))){reused++;continue;}
                                try(PreparedStatement check=c.prepareStatement("SELECT part_id FROM admin_part_alias WHERE source_server=? AND source_part_id=?")){
                                    check.setString(1,SOURCE);check.setInt(2,sourceId);
                                    try(ResultSet found=check.executeQuery()){if(found.next()){reused++;continue;}}
                                }
                                int next=scalar(c,"SELECT COALESCE(MAX(id),-1)+1 FROM part");
                                if(next>32767 || next!=scalar(c,"SELECT COUNT(*) FROM part")) fail(409,"Bảng part có ID bị khuyết hoặc quá giới hạn");
                                try(PreparedStatement insert=c.prepareStatement("INSERT INTO part (id,TYPE,DATA) VALUES (?,?,?)")){
                                    insert.setInt(1,next);insert.setInt(2,type);insert.setString(3,data);insert.executeUpdate();
                                }
                                try(PreparedStatement map=c.prepareStatement("INSERT INTO admin_part_alias (source_server,source_part_id,part_id) VALUES (?,?,?)")){
                                    map.setString(1,SOURCE);map.setInt(2,sourceId);map.setInt(3,next);map.executeUpdate();
                                }
                                added++;
                    }
                    if(added>0)bump(c,true,false);c.commit();
                    JsonObject out=new JsonObject();out.addProperty("added",added);out.addProperty("reused",reused);
                    out.addProperty("message","Đã cấp ID part mới cho dữ liệu trùng. Ảnh cùng ID nhưng khác nội dung cần kiểm tra trong editor trước khi gắn vào item.");return out;
                }catch(Exception ex){c.rollback();throw ex;}
            }
        }
    }

    private static JsonObject upload(JsonObject request) throws SQLException, IOException {
        String encoded=string(request,"png","");
        int sourceZoom=number(request,"sourceZoom",1);
        if(sourceZoom<1 || sourceZoom>4)fail(400,"Mức zoom ảnh nguồn phải từ x1 đến x4");
        if(encoded.startsWith("data:image/png;base64,"))encoded=encoded.substring(22);
        byte[] bytes;
        try { bytes=Base64.getDecoder().decode(encoded); } catch(IllegalArgumentException ex){throw new ApiException(400,"Base64 ảnh không hợp lệ");}
        if(bytes.length>2_000_000)fail(413,"Ảnh vượt 2 MB");
        if(bytes.length<24 || (bytes[0]&0xff)!=0x89 || bytes[1]!='P' || bytes[2]!='N' || bytes[3]!='G')
            fail(400,"File nguồn phải là PNG");
        BufferedImage base=ImageIO.read(new ByteArrayInputStream(bytes));
        if(base==null || base.getWidth()<sourceZoom || base.getHeight()<sourceZoom ||
                base.getWidth()/sourceZoom>512 || base.getHeight()/sourceZoom>512)
            fail(400,"Ảnh nguồn cần kích thước logic 1–512 px sau khi chia zoom");
        int logicalWidth=base.getWidth()/sourceZoom, logicalHeight=base.getHeight()/sourceZoom;
        int sourceImageId=imageIdFromName(string(request,"sourceName",""));
        boolean deduplicate=request.has("deduplicate") && request.get("deduplicate").getAsBoolean();
        String stageSession=string(request,"studioSession","local");
        synchronized(WRITE_LOCK){
            int id;
            boolean reused=false;
            Path named=ICONS.resolve(sourceZoom+"/icon/"+sourceImageId+".png");
            if(sourceImageId>=0 && Files.isRegularFile(named) && java.util.Arrays.equals(bytes,Files.readAllBytes(named))){
                id=sourceImageId;
                reused=true;
            }else if((id=findMatchingPendingImage(bytes,sourceZoom,stageSession))>=0){
                reused=true;
            }else if(deduplicate && (id=findMatchingImage(bytes,sourceZoom,stageSession))>=0){
                reused=true;
            }else{
                try(Connection c=connect()){id=allocateImageId(usedImageIds(c));}
                Map<Integer,PendingImage> staged=pendingImages(stageSession);
                long stagedBytes=staged.values().stream().mapToLong(PendingImage::size).sum();
                // A complete pet can use 3 + 17 + 14 distinct frame images,
                // plus its inventory icon and avatar before the first save.
                if(staged.size()>=48||stagedBytes+bytes.length>64_000_000L)
                    fail(413,"Ảnh đang chờ lưu vượt giới hạn; hãy lưu item trước khi nhập thêm ảnh");
                staged.put(id,new PendingImage(bytes,sourceZoom,logicalWidth,logicalHeight));
            }
            JsonObject out=new JsonObject();out.addProperty("imageId",id);out.addProperty("sourceZoom",sourceZoom);
            out.addProperty("logicalWidth",logicalWidth);out.addProperty("logicalHeight",logicalHeight);
            out.addProperty("reused",reused);
            boolean stagedResult=pendingImages(stageSession).containsKey(id);
            out.addProperty("staged",stagedResult);
            out.addProperty("message",reused&&!stagedResult?"Ảnh đã có trên game server; dùng lại Image ID "+id:
                    "Ảnh đang chờ lưu; chưa ghi vào resources. Tạm cấp Image ID "+id);
            return out;
        }
    }

    private static int findMatchingPendingImage(byte[] bytes,int zoom,String stageSession) {
        for(Map.Entry<Integer,PendingImage> entry:pendingImages(stageSession).entrySet())
            if(entry.getValue().sourceZoom()==zoom && java.util.Arrays.equals(bytes,entry.getValue().source()))
                return entry.getKey();
        return -1;
    }

    private static int findMatchingImage(byte[] bytes,int zoom,String stageSession) throws IOException {
        int pending=findMatchingPendingImage(bytes,zoom,stageSession);
        if(pending>=0)return pending;
        try(var files=Files.list(ICONS.resolve(zoom+"/icon"))){
            for(Path file:(Iterable<Path>)files::iterator){
                String name=file.getFileName().toString();
                if(!name.endsWith(".png") || Files.size(file)!=bytes.length)continue;
                int id=imageIdFromName(name);
                if(id>=0 && java.util.Arrays.equals(bytes,Files.readAllBytes(file)))return id;
            }
        }
        return -1;
    }

    private static int imageIdFromName(String name){
        if(name==null)return -1;
        String file=name.replace('\\','/');file=file.substring(file.lastIndexOf('/')+1);
        if(file.toLowerCase(java.util.Locale.ROOT).endsWith(".png"))file=file.substring(0,file.length()-4);
        try{int id=Integer.parseInt(file);return id>=0&&id<=32767?id:-1;}
        catch(NumberFormatException ex){return -1;}
    }

    private static JsonObject imageList(JsonObject request) throws IOException {
        String query=string(request,"q","").trim();
        if(!query.matches("[0-9]*")) fail(400,"Chỉ tìm ảnh theo Image ID");
        int from=number(request,"from",0),to=number(request,"to",32767);
        if(from<0 || to>32767 || from>to) fail(400,"Khoảng Image ID phải từ 0 đến 32767 và Từ ID không lớn hơn Đến ID");
        int page=number(request,"page",0);
        if(page<0 || page>10000) fail(400,"Trang ảnh không hợp lệ");
        List<Integer> ids=new ArrayList<>();
        Path directory=ICONS.resolve("1/icon");
        if(Files.isDirectory(directory))try(var files=Files.list(directory)){
            files.forEach(path->{
                String name=path.getFileName().toString();
                if(!name.toLowerCase(java.util.Locale.ROOT).endsWith(".png"))return;
                int id=imageIdFromName(name);
                if(id>=from && id<=to && (query.isEmpty() || Integer.toString(id).contains(query)))ids.add(id);
            });
        }
        ids.sort(java.util.Comparator.reverseOrder());
        int start=Math.min(ids.size(),page*60);
        JsonArray items=new JsonArray();
        for(int i=start;i<Math.min(ids.size(),start+60);i++){
            int id=ids.get(i);
            JsonObject item=new JsonObject();item.addProperty("id",id);
            boolean zoom4=Files.isRegularFile(ICONS.resolve("4/icon/"+id+".png"));
            item.addProperty("zoom",zoom4?4:1);
            item.addProperty("complete",zoom4
                    && Files.isRegularFile(ICONS.resolve("2/icon/"+id+".png"))
                    && Files.isRegularFile(ICONS.resolve("3/icon/"+id+".png")));
            items.add(item);
        }
        JsonObject out=new JsonObject();out.add("items",items);
        out.addProperty("total",ids.size());out.addProperty("page",page);
        out.addProperty("pageSize",60);return out;
    }

    static byte[][] zoomVariants(byte[] source,BufferedImage image,int sourceZoom,int logicalWidth,int logicalHeight) throws IOException {
        byte[][] variants=new byte[5][];
        for(int z=1;z<=4;z++){
            if(z==sourceZoom){variants[z]=source;continue;}
            BufferedImage scaled=new BufferedImage(logicalWidth*z,logicalHeight*z,BufferedImage.TYPE_INT_ARGB);
            Graphics2D g=scaled.createGraphics();
            g.setRenderingHint(RenderingHints.KEY_INTERPOLATION,RenderingHints.VALUE_INTERPOLATION_NEAREST_NEIGHBOR);
            g.drawImage(image,0,0,scaled.getWidth(),scaled.getHeight(),0,0,logicalWidth*sourceZoom,logicalHeight*sourceZoom,null);
            g.dispose();
            ByteArrayOutputStream buffer=new ByteArrayOutputStream();ImageIO.write(scaled,"png",buffer);
            variants[z]=buffer.toByteArray();
        }
        return variants;
    }

    private static Set<Integer> usedImageIds(Connection c) throws SQLException, IOException {
        Set<Integer> used=new HashSet<>();
        try(Statement s=c.createStatement();ResultSet r=s.executeQuery("SELECT icon_id FROM item_template")){
            while(r.next())used.add(r.getInt(1));
        }
        try(Statement s=c.createStatement();ResultSet r=s.executeQuery("SELECT DATA FROM part")){
            while(r.next())for(JsonElement frame:JsonParser.parseString(r.getString(1)).getAsJsonArray())
                used.add(frame.getAsJsonArray().get(0).getAsInt());
        }
        for(int z=1;z<=4;z++)try(var files=Files.list(ICONS.resolve(z+"/icon"))){
            files.forEach(path->{String name=path.getFileName().toString();
                if(name.endsWith(".png"))try{used.add(Integer.parseInt(name.substring(0,name.length()-4)));}catch(NumberFormatException ignored){}
            });
        }
        for(Map<Integer,PendingImage> staged:PENDING_IMAGES.values())used.addAll(staged.keySet());
        return used;
    }

    private static int allocateImageId(Set<Integer> used) {
        for(int id=32767;id>=18000;id--)if(!used.contains(id))return id;
        fail(409,"Hết ID ảnh trống trong dải ngắn của client");return -1;
    }

    private static Integer mappedImage(Connection c,int sourceId) throws SQLException {
        for(String sql:new String[]{"SELECT image_id FROM admin_editor_image_alias WHERE source_image_id=?",
                "SELECT item_icon_id FROM admin_catalog_icon_alias WHERE source_icon_id=?"}){
            try(PreparedStatement ps=c.prepareStatement(sql)){
                ps.setInt(1,sourceId);
                try(ResultSet r=ps.executeQuery()){if(r.next())return r.getInt(1);}
            }catch(SQLException ex){if(!sql.contains("admin_catalog_icon_alias"))throw ex;}
        }
        return null;
    }

    private static JsonObject prepareReference(JsonObject request) throws SQLException, IOException {
        int sourcePart=number(request,"id",-1);
        synchronized(WRITE_LOCK){
            try(Connection c=connect()){
                ensureSupportTables(c);
                JsonObject part=request.has("sourcePart") ? request.getAsJsonObject("sourcePart").deepCopy()
                        : loadPart(c,sourcePart,true);
                if(part!=null && number(part,"id",-1)!=sourcePart) fail(400,"Part nguồn sai ID");
                if(part==null)fail(404,"Không có part tham chiếu " + sourcePart);
                c.setAutoCommit(false);
                List<Path> written=new ArrayList<>();Set<Integer> used=usedImageIds(c);int created=0;JsonArray missing=new JsonArray();
                try{
                    JsonArray frames=part.getAsJsonArray("frames");
                    for(JsonElement element:frames){
                        JsonArray frame=element.getAsJsonArray();int sourceId=frame.get(0).getAsInt();
                        if(sourceId<=0)continue;
                        boolean complete=true,same=true;
                        for(int z=1;z<=4;z++){
                            Path local=ICONS.resolve(z+"/icon/"+sourceId+".png");
                            byte[] original=sourceImage(request,sourceId,z);
                            if(original==null){complete=false;break;}
                            if(!Files.isRegularFile(local)||!java.util.Arrays.equals(original,Files.readAllBytes(local)))same=false;
                        }
                        if(!complete){missing.add(sourceId);continue;}
                        if(same)continue;
                        Integer alias=mappedImage(c,sourceId);
                        if(alias!=null){
                            boolean matches=true;
                            for(int z=1;z<=4;z++)if(!Files.isRegularFile(ICONS.resolve(z+"/icon/"+alias+".png")) || !java.util.Arrays.equals(
                                    sourceImage(request,sourceId,z),
                                    Files.readAllBytes(ICONS.resolve(z+"/icon/"+alias+".png"))))matches=false;
                            if(!matches)alias=null;
                        }
                        if(alias==null){
                            alias=allocateImageId(used);used.add(alias);created++;
                            for(int z=1;z<=4;z++){
                                Path target=ICONS.resolve(z+"/icon/"+alias+".png");Files.createDirectories(target.getParent());
                                Files.write(target,sourceImage(request,sourceId,z),StandardOpenOption.CREATE_NEW);
                                written.add(target);
                            }
                            try(PreparedStatement ps=c.prepareStatement("INSERT INTO admin_editor_image_alias (source_image_id,image_id) VALUES (?,?) ON DUPLICATE KEY UPDATE image_id=VALUES(image_id)")){
                                ps.setInt(1,sourceId);ps.setInt(2,alias);ps.executeUpdate();
                            }
                        }
                        frame.set(0,new com.google.gson.JsonPrimitive(alias));
                    }
                    c.commit();part.addProperty("source","runtime");part.add("missingImages",missing);
                    part.addProperty("remappedImages",created);return part;
                }catch(Exception ex){c.rollback();for(Path path:written)Files.deleteIfExists(path);throw ex;}
            }
        }
    }

    private static final class ApiException extends RuntimeException {
        final int status; ApiException(int status,String message){super(message);this.status=status;}
    }
}
