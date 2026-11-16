package nro.server;

import java.io.IOException;
import nro.attr.AttributeManager;
import nro.jdbc.DBService;
import nro.jdbc.DBHika;
import nro.jdbc.daos.AccountDAO;
import nro.jdbc.daos.HistoryTransactionDAO;
import nro.jdbc.daos.PlayerDAO;
import nro.login.LoginSession;
import nro.manager.KiGuiManager;
import nro.models.boss.BossFactory;
import nro.models.boss.BossManager;
import nro.models.map.DaiHoiVoThuat.DHVT23Manager;
import nro.models.map.dungeon.DungeonManager;
import nro.models.map.phoban.BanDoKhoBau;
import nro.models.map.phoban.DoanhTrai;
import nro.models.player.Player;
import nro.server.io.Session;
import nro.services.ClanService;
import nro.utils.Log;
import nro.utils.TimeUtil;
import nro.utils.Util;
import lombok.Getter;
import lombok.Setter;

import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.List;
import java.util.Map;
import java.util.Scanner;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import nro.manager.TopManager;
import nro.models.map.DaiHoiVoThuat.DaiHoiVoThuatService;
import nro.models.map.VoDaiSinhTu.VoDaiSinhTuManager;
import nro.models.map.phoban.KhiGas;

public class ServerManager {

    public static String timeStart;

    public static final Map<String, Integer> CLIENTS = new ConcurrentHashMap<>();

    public static String NAME = "";
    public static int PORT = 14445;

    private Controller controller;

    private static ServerManager instance;

    public static ServerSocket listenSocket;
    public static boolean isRunning;

    @Getter
    private LoginSession login;
    public static boolean updateTimeLogin;
    @Getter
    @Setter
    private AttributeManager attributeManager;
    private long lastUpdateAttribute;
    @Getter
    private DungeonManager dungeonManager;

    public void init() {
        Manager.gI();
        HistoryTransactionDAO.deleteHistory();
        BossFactory.initBoss();
        this.controller = new Controller();
        if (updateTimeLogin) {
            AccountDAO.updateLastTimeLoginAllAccount();
        }
    }

    public static ServerManager gI() {
        if (instance == null) {
            instance = new ServerManager();
            instance.init();
        }
        return instance;
    }

    public static void main(String[] args) {
        timeStart = TimeUtil.getTimeNow("dd/MM/yyyy HH:mm:ss");
        ServerManager.gI().run();

    }

    public void run() {
        try {
            isRunning = true;
            activeCommandLine();
            activeGame();
            activeLogin();
            autoTask();

            new Thread(AutoMaintenance.gI(), "Thread Bảo Trì Định Kỳ").start();

            activeServerSocket();
        } catch (Exception e) {
            e.printStackTrace();

        }
    }

    public void activeLogin() {
        login = new LoginSession();
        login.connect(Manager.loginHost, Manager.loginPort);
    }

    private void activeServerSocket() {
        try {
            Log.log("Thread: " + Thread.activeCount());
            listenSocket = new ServerSocket(PORT);
            while (isRunning) {
                Socket sc = null;
                String ip = null;
                boolean slotAcquired = false;
                try {
                    sc = listenSocket.accept();
                    ip = (((InetSocketAddress) sc.getRemoteSocketAddress()).getAddress()).toString().replace("/", "");
                    if (tryAcquireIpSlot(ip)) {
                        slotAcquired = true;
                        new Session(sc, controller, ip);
                    } else {
                        sc.close();
                    }
                } catch (Exception e) {
                    if (slotAcquired) {
                        releaseIpSlot(ip);
                    }
                    if (sc != null) {
                        try {
                            sc.close();
                        } catch (IOException ignored) {
                        }
                    }
                    if (isRunning) {
                        Log.error(ServerManager.class, e, "Lỗi nhận kết nối");
                    }
                }
            }
            listenSocket.close();
        } catch (Exception e) {
            Log.error(ServerManager.class, e, "Lỗi mở port");
            System.exit(1);
        }
    }

    public static boolean tryAcquireIpSlot(String ipAddress) {
        if (ipAddress == null) {
            return false;
        }
        synchronized (CLIENTS) {
            int current = CLIENTS.getOrDefault(ipAddress, 0);
            if (current >= Manager.MAX_PER_IP) {
                return false;
            }
            CLIENTS.put(ipAddress, current + 1);
            return true;
        }
    }

    public void disconnect(Session session) {
        releaseIpSlot(session.ipAddress);
    }

    private static void releaseIpSlot(String ipAddress) {
        if (ipAddress == null) {
            return;
        }
        synchronized (CLIENTS) {
            int current = CLIENTS.getOrDefault(ipAddress, 0);
            if (current <= 1) {
                CLIENTS.remove(ipAddress);
            } else {
                CLIENTS.put(ipAddress, current - 1);
            }
        }
    }

    private void activeCommandLine() {
        new Thread(() -> {
            Scanner sc = new Scanner(System.in);
            while (true) {
                String line = sc.nextLine();
                if (line.equals("baotri")) {
                    new Thread(() -> {
                        Maintenance.gI().start(5);
                    }).start();
                }
            }
        }, "Active line").start();
    }

    private void activeGame() {
        long delay = 100;
        new Thread(() -> {
            while (isRunning) {
                long l1 = System.currentTimeMillis();
                BossManager.gI().updateAllBoss();
                long l2 = System.currentTimeMillis() - l1;
                if (l2 < delay) {
                    try {
                        Thread.sleep(delay - l2);
                    } catch (InterruptedException e) {
                    }
                }
            }
        }, "Update boss").start();

        new Thread(() -> {
            while (isRunning) {
                long start = System.currentTimeMillis();
                for (DoanhTrai dt : DoanhTrai.DOANH_TRAIS) {
                    dt.update();
                }
                for (BanDoKhoBau bdkb : BanDoKhoBau.BAN_DO_KHO_BAUS) {
                    bdkb.update();
                }
                for (KhiGas khiGas : KhiGas.KHI_GAS) {
                    khiGas.update();
                }
                long timeUpdate = System.currentTimeMillis() - start;

                if (timeUpdate < 500) {
                    try {
                        Thread.sleep(500 - timeUpdate);
                    } catch (InterruptedException e) {
                    }
                }
            }
        }, "Update pho ban").start();
        new Thread(() -> {
            while (isRunning) {
                try {
                    long start = System.currentTimeMillis();
                    if (attributeManager != null) {
                        attributeManager.update();
                        if (Util.canDoWithTime(lastUpdateAttribute, 600000)) {
                            Manager.gI().updateAttributeServer();
                        }
                    }
                    long timeUpdate = System.currentTimeMillis() - start;
                    if (timeUpdate < delay) {
                        Thread.sleep(delay - timeUpdate);
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }, "Update Attribute Server").start();

        dungeonManager = new DungeonManager();
        dungeonManager.start();

        new Thread(dungeonManager, "Con Đường Rắn Độc").start();

        new Thread(() -> {
            while (isRunning) {
                try {
                    long start = System.currentTimeMillis();
                    DHVT23Manager.gI().update();
                    VoDaiSinhTuManager.gI().update();
                    long timeUpdate = System.currentTimeMillis() - start;
                    if (timeUpdate < delay) {
                        Thread.sleep(delay - timeUpdate);
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }, "Update dai hoi vo thuat").start();
    }

    public void close(long delay) {
        Manager.shutdownMapUpdates();
        try {
            dungeonManager.shutdown();
        } catch (Exception e) {
            Log.error(ServerManager.class, e);
        }
        try {
            Manager.gI().updateEventCount();
        } catch (Exception e) {
            Log.error(ServerManager.class, e);
        }
        try {
            Manager.gI().updateAttributeServer();
        } catch (Exception e) {
            Log.error(ServerManager.class, e);
        }
        try {
            Client.gI().close();
        } catch (Exception e) {
            Log.error(ServerManager.class, e);
        }
        try {
            ClanService.gI().close();
        } catch (Exception e) {
            Log.error(ServerManager.class, e);
        }
        try {
            KiGuiManager.getInstance().close();
        } catch (Exception e) {
            Log.error(ServerManager.class, e);
        }
        Log.success("SUCCESSFULLY MAINTENANCE!...................................");
        DBHika.close();
        if (System.getProperty("os.name").startsWith("Windows")) {
            try {
                new ProcessBuilder("cmd", "/c", "start", "run.bat").start();
            } catch (IOException e) {
                Log.error(ServerManager.class, e, "Cannot restart server");
            }
        }
        System.exit(0);
    }

    public void saveAll(boolean updateTimeLogout) {
        try (Connection conn = DBService.gI().getConnectionForAutoSave()) {
            List<Player> list = Client.gI().getPlayers();
            for (Player player : list) {
                try {
                    PlayerDAO.updateTimeLogout = updateTimeLogout;
                    PlayerDAO.updatePlayer(player, conn);
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        } catch (SQLException ex) {
            ex.printStackTrace();
        }
    }

    public void autoTask() {
        ScheduledExecutorService autoSave = Executors.newScheduledThreadPool(1);
        autoSave.scheduleWithFixedDelay(() -> {
            saveAll(false);
        }, 300000, 300000, TimeUnit.MILLISECONDS);

        ScheduledExecutorService autoDHVTM = Executors.newScheduledThreadPool(1);
        autoDHVTM.scheduleWithFixedDelay(() -> {
            DaiHoiVoThuatService.gI().initDaiHoiVoThuat();
        }, 0, 1, TimeUnit.MINUTES);

        ScheduledExecutorService autoTopPower = Executors.newScheduledThreadPool(1);
        autoTopPower.scheduleWithFixedDelay(() -> {
            TopManager.getInstance().loadTopNangDong();
            //  TopManager.getInstance().loadTopVnd();
            //TopPowerManager.getInstance().load();
//            TopRichManManager.getInstance().load();
//            TopKillWhisManager.getInstance().load();
//            TopBanDoKhoBau.getInstance().load();
        }, 0, 600000, TimeUnit.MILLISECONDS);

    }
}
