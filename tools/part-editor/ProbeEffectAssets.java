import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import nro.resources.EffectAssetResolver;

/** Prints effective runtime availability; never writes or replaces resource PNGs. */
public class ProbeEffectAssets {
    public static void main(String[] args) throws Exception {
        Path root = Path.of(args[0]);
        StringBuilder output = new StringBuilder("[");
        boolean first = true;
        for (String value : args[1].split(",")) {
            int id = Integer.parseInt(value);
            for (int zoom = 1; zoom <= 4; zoom++) {
                if (!first) output.append(',');
                first = false;
                output.append("{\"id\":").append(id).append(",\"zoom\":").append(zoom);
                try {
                    EffectAssetResolver.Asset asset = EffectAssetResolver.load(root, id, zoom);
                    Path definition = root.resolve("x" + zoom + "/data/DataEffect_" + id);
                    boolean changed = !Files.isRegularFile(definition)
                            || !Arrays.equals(Files.readAllBytes(definition), asset.data)
                            || asset.sourceZoom != zoom;
                    output.append(",\"available\":true,\"resolved\":").append(changed)
                            .append(",\"source_zoom\":").append(asset.sourceZoom);
                } catch (java.io.IOException error) {
                    output.append(",\"available\":false");
                }
                output.append('}');
            }
        }
        System.out.println(output.append(']'));
    }
}
