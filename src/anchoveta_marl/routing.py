from __future__ import annotations

import heapq
import math
import numpy as np
import pandas as pd


def haversine_nm(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r_km = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2-lat1)
    dl = math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return (2*r_km*math.atan2(math.sqrt(a), math.sqrt(1-a))) / 1.852


class GridRouter:
    MOVES = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]

    def __init__(self, raw_grid: pd.DataFrame, legal_mask: np.ndarray | None = None):
        self.lons = np.sort(raw_grid["Lon"].unique())
        self.lats = np.sort(raw_grid["Lat"].unique())
        self.lon_i = {round(float(x), 10): i for i, x in enumerate(self.lons)}
        self.lat_j = {round(float(y), 10): j for j, y in enumerate(self.lats)}
        self.nav = np.zeros((len(self.lats), len(self.lons)), dtype=bool)
        for r in raw_grid.itertuples(index=False):
            i = self.lon_i[round(float(r.Lon), 10)]
            j = self.lat_j[round(float(r.Lat), 10)]
            self.nav[j, i] = True
        if legal_mask is not None:
            if legal_mask.shape != self.nav.shape:
                raise ValueError("legal_mask shape mismatch")
            self.nav &= legal_mask.astype(bool)

    def nearest_node(self, lon: float, lat: float) -> tuple[int, int]:
        jj, ii = np.where(self.nav)
        if len(jj) == 0:
            raise ValueError("No navigable cells")
        k = int(np.argmin((self.lons[ii]-lon)**2 + (self.lats[jj]-lat)**2))
        return int(jj[k]), int(ii[k])

    def astar(self, start: tuple[int, int], goal: tuple[int, int]) -> tuple[list[tuple[int,int]], float]:
        def h(node):
            j, i = node
            gj, gi = goal
            return haversine_nm(self.lons[i], self.lats[j], self.lons[gi], self.lats[gj])

        pq = [(h(start), 0.0, start)]
        came = {}
        gscore = {start: 0.0}

        while pq:
            _, g, node = heapq.heappop(pq)
            if g != gscore.get(node):
                continue
            if node == goal:
                path = [node]
                while node in came:
                    node = came[node]
                    path.append(node)
                path.reverse()
                return path, g

            j, i = node
            for dj, di in self.MOVES:
                nj, ni = j+dj, i+di
                if not (0 <= nj < self.nav.shape[0] and 0 <= ni < self.nav.shape[1]):
                    continue
                if not self.nav[nj, ni]:
                    continue
                step = haversine_nm(self.lons[i], self.lats[j], self.lons[ni], self.lats[nj])
                ng = g + step
                nxt = (nj, ni)
                if ng < gscore.get(nxt, np.inf):
                    gscore[nxt] = ng
                    came[nxt] = node
                    heapq.heappush(pq, (ng + h(nxt), ng, nxt))
        return [], math.inf

    def path_lonlat(self, path):
        return [(float(self.lons[i]), float(self.lats[j])) for j, i in path]
