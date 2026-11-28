package nro.resources;

import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import javax.imageio.ImageIO;

/** Resolves the same effect across zooms using matching frame data only. */
public final class EffectAssetResolver {
    private EffectAssetResolver() { }

    public static final class Asset {
        public final byte[] data;
        public final byte[] png;
        public final int sourceZoom;

        private Asset(byte[] data, byte[] png, int sourceZoom) {
            this.data = data;
            this.png = png;
            this.sourceZoom = sourceZoom;
        }
    }

    public static Asset load(Path root, int id, int zoom) throws IOException {
        if (id < 0 || zoom < 1 || zoom > 4) {
            throw new IOException("Invalid effect ID or zoom");
        }
        byte[][] definitions = new byte[5][];
        int availableDefinitions = 0;
        for (int candidate = 1; candidate <= 4; candidate++) {
            Path path = root.resolve("x" + candidate).resolve("data/DataEffect_" + id);
            if (Files.isRegularFile(path)) {
                definitions[candidate] = Files.readAllBytes(path);
                availableDefinitions++;
            }
        }
        byte[] selected = definitions[zoom];
        // A unique majority of at least two definitions can identify an outlier.
        // Ties keep the requested definition; an unrelated effect is never used.
        List<byte[]> groups = new ArrayList<>();
        int best = 0;
        boolean tied = false;
        byte[] majority = null;
        for (int candidate = 1; candidate <= 4; candidate++) {
            byte[] definition = definitions[candidate];
            if (definition == null || groups.stream().anyMatch(value -> Arrays.equals(value, definition))) {
                continue;
            }
            groups.add(definition);
            int count = 0;
            for (int other = 1; other <= 4; other++) {
                if (Arrays.equals(definition, definitions[other])) {
                    count++;
                }
            }
            if (count > best) {
                majority = definition;
                best = count;
                tied = false;
            } else if (count == best) {
                tied = true;
            }
        }
        if (best >= 2 && best * 2 > availableDefinitions && !tied) {
            selected = majority;
        }
        if (selected == null) {
            throw new IOException("Missing effect definition " + id + " x" + zoom);
        }
        int[] choices = {zoom, 1, 2, 3, 4};
        for (int sourceZoom : choices) {
            if (!Arrays.equals(selected, definitions[sourceZoom])) {
                continue;
            }
            Path image = root.resolve("x" + sourceZoom).resolve("img/ImgEffect_" + id + ".png");
            if (!Files.isRegularFile(image)) {
                continue;
            }
            byte[] png = Files.readAllBytes(image);
            if (sourceZoom == zoom) {
                return new Asset(selected, png, sourceZoom);
            }
            BufferedImage source = ImageIO.read(new ByteArrayInputStream(png));
            if (source == null) {
                continue;
            }
            int width = Math.max(1, (int) Math.round((double) source.getWidth() * zoom / sourceZoom));
            int height = Math.max(1, (int) Math.round((double) source.getHeight() * zoom / sourceZoom));
            if ((long) width * height > 16_777_216L) {
                throw new IOException("Effect image is too large");
            }
            BufferedImage scaled = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
            Graphics2D graphics = scaled.createGraphics();
            try {
                graphics.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_NEAREST_NEIGHBOR);
                graphics.drawImage(source, 0, 0, width, height, null);
            } finally {
                graphics.dispose();
            }
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            ImageIO.write(scaled, "png", output);
            return new Asset(selected, output.toByteArray(), sourceZoom);
        }
        throw new IOException("No matching atlas for effect " + id + " x" + zoom);
    }
}
