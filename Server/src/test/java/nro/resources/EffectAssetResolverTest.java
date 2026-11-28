package nro.resources;

import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import javax.imageio.ImageIO;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;
import static org.junit.Assert.*;

public class EffectAssetResolverTest {
    @Rule public TemporaryFolder temporary = new TemporaryFolder();

    private void definition(Path root, int zoom, int id, byte[] data) throws Exception {
        Path path = root.resolve("x" + zoom + "/data/DataEffect_" + id);
        Files.createDirectories(path.getParent());
        Files.write(path, data);
    }

    private void image(Path root, int zoom, int id, int width, int height) throws Exception {
        Path path = root.resolve("x" + zoom + "/img/ImgEffect_" + id + ".png");
        Files.createDirectories(path.getParent());
        BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
        image.setRGB(0, 0, 0xffed1133);
        ImageIO.write(image, "png", path.toFile());
    }

    @Test public void missingZoomUsesSameFrameDataAndPreservesPixels() throws Exception {
        Path root = temporary.newFolder().toPath();
        definition(root, 1, 7, new byte[]{1, 2});
        definition(root, 4, 7, new byte[]{1, 2});
        image(root, 1, 7, 2, 3);
        EffectAssetResolver.Asset result = EffectAssetResolver.load(root, 7, 4);
        BufferedImage image = ImageIO.read(new ByteArrayInputStream(result.png));
        assertEquals(8, image.getWidth());
        assertEquals(12, image.getHeight());
        assertEquals(0xffed1133, image.getRGB(3, 3));
        assertEquals(1, result.sourceZoom);
    }

    @Test public void mismatchedDefinitionIsNotUsedAsAnAtlas() throws Exception {
        Path root = temporary.newFolder().toPath();
        definition(root, 1, 7, new byte[]{3});
        definition(root, 4, 7, new byte[]{4});
        image(root, 1, 7, 2, 3);
        try {
            EffectAssetResolver.load(root, 7, 4);
            fail("Unrelated frame data must not be used");
        } catch (java.io.IOException expected) { }
    }

    @Test public void clearMajorityRepairsAnOutlierDefinitionAndAtlasTogether() throws Exception {
        Path root = temporary.newFolder().toPath();
        for (int zoom : new int[]{1, 3, 4}) definition(root, zoom, 7, new byte[]{7});
        definition(root, 2, 7, new byte[]{99});
        image(root, 1, 7, 2, 3);
        image(root, 2, 7, 99, 99);
        EffectAssetResolver.Asset result = EffectAssetResolver.load(root, 7, 2);
        assertArrayEquals(new byte[]{7}, result.data);
        assertEquals(4, ImageIO.read(new ByteArrayInputStream(result.png)).getWidth());
    }

    @Test public void nativeMatchingAtlasIsReturnedByteForByte() throws Exception {
        Path root = temporary.newFolder().toPath();
        definition(root, 4, 7, new byte[]{7});
        image(root, 4, 7, 8, 12);
        byte[] original = Files.readAllBytes(root.resolve("x4/img/ImgEffect_7.png"));
        assertArrayEquals(original, EffectAssetResolver.load(root, 7, 4).png);
    }

    @Test public void halfTheDefinitionsAreNotEnoughToOverrideRequestedData() throws Exception {
        Path root = temporary.newFolder().toPath();
        definition(root, 1, 7, new byte[]{7});
        definition(root, 2, 7, new byte[]{7});
        definition(root, 3, 7, new byte[]{8});
        definition(root, 4, 7, new byte[]{9});
        image(root, 4, 7, 8, 12);
        assertArrayEquals(new byte[]{9}, EffectAssetResolver.load(root, 7, 4).data);
    }
}
