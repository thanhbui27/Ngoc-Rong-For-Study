"""Route planning across public map waypoints and planet transport stations."""

from __future__ import annotations

from collections import deque


PLANET_STATIONS = (24, 25, 26)
STATION_NPCS = {24: 10, 25: 11, 26: 12}

# The station menus are race-relative. Each pair is (destination map, menu index).
SHIP_DESTINATIONS = {
    24: ((25, 0), (26, 1), (84, 2)),  # Dr. Brief: Namek, Xayda, supermarket
    25: ((24, 0), (26, 1), (84, 2)),  # Cargo: Earth, Xayda, supermarket
    26: ((24, 0), (25, 1), (84, 2)),  # Cui: Earth, Namek, supermarket
}


class MovementUtility:
    """Plan a legal route and expose one actionable edge at a time.

    Ground edges come from the server's map-template seed. Interplanetary edges
    are only added between the three public space stations, where the server
    exposes an NPC and a known menu choice.
    """

    def __init__(self, routes):
        self.routes = routes

    def plan(self, start: int, goal: int,
             blocked_edges: set[tuple[int, int, str]] | None = None,
             gender: int = 0,
             allow_spaceships: bool = True) -> list[dict] | None:
        if start == goal:
            return []
        if start not in self.routes.maps or goal not in self.routes.maps:
            return None

        blocked_edges = blocked_edges or set()
        queue = deque([start])
        previous: dict[int, tuple[int, dict] | None] = {start: None}

        while queue:
            current = queue.popleft()
            edges = [
                {**waypoint, "kind": "waypoint", "from_map": current}
                for waypoint in self.routes.maps.get(current, ())
            ]
            if allow_spaceships and current in SHIP_DESTINATIONS:
                edges.extend({
                    "kind": "spaceship", "from_map": current, "go_map": destination,
                    "npc_id": STATION_NPCS[current], "menu": menu,
                } for destination, menu in SHIP_DESTINATIONS[current])
            if allow_spaceships and current == 84:
                edges.append({
                    "kind": "spaceship", "from_map": current, "go_map": 24 + min(max(gender, 0), 2),
                    "npc_id": 10, "menu": 0,
                })

            for edge in edges:
                destination = edge["go_map"]
                edge_key = (current, destination, edge["kind"])
                if edge_key in blocked_edges or destination in previous:
                    continue
                if destination not in self.routes.maps:
                    continue
                previous[destination] = (current, edge)
                if destination == goal:
                    return self._reconstruct(previous, start, goal)
                queue.append(destination)
        return None

    @staticmethod
    def _reconstruct(previous: dict[int, tuple[int, dict] | None],
                     start: int, goal: int) -> list[dict]:
        path = []
        current = goal
        while current != start:
            parent, edge = previous[current]
            path.append(edge)
            current = parent
        path.reverse()
        return path

    def next_step(self, start: int, goal: int,
                  blocked_edges: set[tuple[int, int, str]] | None = None,
                  gender: int = 0,
                  allow_spaceships: bool = True) -> dict | None:
        path = self.plan(start, goal, blocked_edges, gender, allow_spaceships)
        return path[0] if path else None

