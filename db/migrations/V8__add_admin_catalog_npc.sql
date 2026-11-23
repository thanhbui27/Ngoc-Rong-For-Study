-- Add the admin-only catalog NPC template without changing existing NPCs.
INSERT IGNORE INTO npc_template (id, NAME, head, body, leg)
VALUES (80, 'Kho admin', 74, 75, 265);
