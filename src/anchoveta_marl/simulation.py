from __future__ import annotations

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter


def interpolate_path(coords, n_frames=60):
    pts = np.asarray(coords, dtype=float)
    if len(pts) == 1:
        return np.repeat(pts, n_frames, axis=0)
    seg = np.sqrt(((pts[1:] - pts[:-1])**2).sum(axis=1))
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    if cum[-1] == 0:
        return np.repeat(pts[:1], n_frames, axis=0)
    targets = np.linspace(0, cum[-1], n_frames)
    out = np.zeros((n_frames, 2), dtype=float)
    for k, t in enumerate(targets):
        idx = min(max(np.searchsorted(cum, t, side="right")-1, 0), len(seg)-1)
        den = max(cum[idx+1]-cum[idx], 1e-12)
        w = (t-cum[idx])/den
        out[k] = pts[idx]*(1-w)+pts[idx+1]*w
    return out


def save_map(prob, ports, zones, routes, out_path, title):
    out_path = Path(out_path)
    fig, ax = plt.subplots(figsize=(9, 10))
    sc = ax.scatter(prob["Lon"], prob["Lat"], c=prob["Prob"], s=8, alpha=.65)
    plt.colorbar(sc, ax=ax, label="Probabilidad")
    for name, (x,y) in ports.items():
        ax.scatter(x, y, marker="^", s=100)
        ax.annotate(name, (x,y), xytext=(5,5), textcoords="offset points")
    ax.scatter(zones["Lon"], zones["Lat"], marker="x", s=45)
    for coords in routes.values():
        arr = np.asarray(coords)
        ax.plot(arr[:,0], arr[:,1], linewidth=.9, alpha=.55)
    ax.set_title(title)
    ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud"); ax.grid(alpha=.2)
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_animation(prob, ports, zones, routes, out_path, n_frames=60):
    out_path = Path(out_path)
    xy = {aid: interpolate_path(coords, n_frames) for aid, coords in routes.items()}
    fig, ax = plt.subplots(figsize=(9, 10))
    sc = ax.scatter(prob["Lon"], prob["Lat"], c=prob["Prob"], s=7, alpha=.45)
    plt.colorbar(sc, ax=ax, label="Probabilidad")
    for name, (x,y) in ports.items():
        ax.scatter(x, y, marker="^", s=100)
        ax.annotate(name, (x,y), xytext=(5,5), textcoords="offset points")
    ax.scatter(zones["Lon"], zones["Lat"], marker="x", s=40)
    for coords in routes.values():
        arr = np.asarray(coords)
        ax.plot(arr[:,0], arr[:,1], linewidth=.6, alpha=.25)
    boats = ax.scatter([], [], s=32)
    status = ax.text(.02,.98,"",transform=ax.transAxes,va="top")
    ax.set_xlim(prob["Lon"].min()-.1, prob["Lon"].max()+.1)
    ax.set_ylim(prob["Lat"].min()-.1, prob["Lat"].max()+.1)
    ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud"); ax.grid(alpha=.15)
    ax.set_aspect("equal", adjustable="box")

    def update(frame):
        pos = np.array([xy[k][frame] for k in sorted(xy)])
        boats.set_offsets(pos)
        status.set_text(f"Simulación: {100*frame/(n_frames-1):.0f}%")
        return boats, status

    anim = FuncAnimation(fig, update, frames=n_frames, interval=100, blit=False)
    anim.save(out_path, writer=PillowWriter(fps=10))
    plt.close(fig)
