package nro.server;

import static org.junit.Assert.assertEquals;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.Test;

public class IpLimitTest {
    @Test
    public void concurrentConnectionsCannotExceedPerIpLimit() throws Exception {
        String ip = "test-ip-limit";
        byte originalLimit = Manager.MAX_PER_IP;
        ExecutorService workers = Executors.newFixedThreadPool(12);
        try {
            Manager.MAX_PER_IP = 5;
            CountDownLatch start = new CountDownLatch(1);
            List<Future<Boolean>> results = new ArrayList<>();
            for (int i = 0; i < 40; i++) {
                results.add(workers.submit((Callable<Boolean>) () -> {
                    start.await();
                    return ServerManager.tryAcquireIpSlot(ip);
                }));
            }
            start.countDown();
            int accepted = 0;
            for (Future<Boolean> result : results) {
                if (result.get()) {
                    accepted++;
                }
            }
            assertEquals(5, accepted);
            assertEquals(Integer.valueOf(5), ServerManager.CLIENTS.get(ip));
        } finally {
            workers.shutdownNow();
            ServerManager.CLIENTS.remove(ip);
            Manager.MAX_PER_IP = originalLimit;
        }
    }
}
