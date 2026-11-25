/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package nro.models;

import com.google.gson.Gson;
import nro.jdbc.DBService;
import nro.server.io.Message;
import nro.utils.Log;
import java.io.DataOutputStream;
import java.io.IOException;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

import lombok.Getter;

/**
 *
 * @Build by bkt
 */
public class PartManager {

    private static final int[] FRAME_COUNTS = {3, 17, 14, 2};

    private static final PartManager instance = new PartManager();

    public static PartManager getInstance() {
        return instance;
    }

    @Getter
    private List<Part> parts;
    @Getter
    private byte[] data;

    public PartManager() {
        parts = new ArrayList<>();
    }

    public void load() {
        try (java.sql.Connection con = DBService.gI().getConnectionForGame()) {
            Gson gson = new Gson();
            // Part IDs are positions in the binary data sent to clients.
            PreparedStatement ps = con.prepareStatement("SELECT * FROM part ORDER BY id");
            ResultSet rs = ps.executeQuery();
            while (rs.next()) {
                short id = rs.getShort("id");
                byte type = rs.getByte("TYPE");
                String partJson = rs.getString("DATA");
                int[][] partData = gson.fromJson(partJson, int[][].class);
                if (id != parts.size()) {
                    throw new IllegalStateException("Part ID must be contiguous: expected "
                            + parts.size() + " but found " + id);
                }
                int originalFrameCount = partData == null ? 0 : partData.length;
                partData = normalizePartData(id, type, partData);
                if (originalFrameCount != partData.length) {
                    Log.warning("Part " + id + " type " + type + " has " + originalFrameCount
                            + " frames; normalized to " + partData.length + " for the client packet");
                }
                Part part = new Part();
                part.setId(id);
                part.setType(type);
                part.setPartData(partData);
                add(part);
            }
            Log.success("Load part thành công (" + parts.size() + ")");
            rs.close();
            ps.close();
            setData();
        } catch (SQLException ex) {
            ex.printStackTrace();
        }
    }

    static int[][] normalizePartData(int id, byte type, int[][] source) {
        if (type < 0 || type >= FRAME_COUNTS.length) {
            throw new IllegalStateException("Part " + id + " has unsupported type " + type);
        }
        int[][] normalized = new int[FRAME_COUNTS[type]][3];
        if (source == null) {
            return normalized;
        }
        int frames = Math.min(source.length, normalized.length);
        for (int i = 0; i < frames; i++) {
            if (source[i] != null) {
                System.arraycopy(source[i], 0, normalized[i], 0, Math.min(source[i].length, 3));
            }
        }
        return normalized;
    }

    public void add(Part part) {
        parts.add(part);
    }

    public void remove(Part part) {
        parts.remove(part);
    }

    public Part find(int id) {
        for (Part part : parts) {
            if (part.getId() == id) {
                return part;
            }
        }
        return null;
    }

    public Part get(int index) {
        return parts.get(index);
    }

    public void setData() {
        try {
            Message ms = new Message();
            DataOutputStream ds = ms.writer();
            ds.writeShort(parts.size());
            for (Part part : parts) {
                ds.writeByte(part.getType());
                int[][] partData = part.getPartData();
                for (int[] rowData : partData) {
                    ds.writeShort(rowData[0]);
                    ds.writeByte(rowData[1]);
                    ds.writeByte(rowData[2]);
                }
            }
            ds.flush();
            this.data = ms.getData();
            ds.close();
        } catch (IOException ex) {
            ex.printStackTrace();
        }
    }

}
