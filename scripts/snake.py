#!/usr/bin/env python3
"""Serpiente que se come la gráfica de contribuciones, da vueltas en espiral hasta el centro y explota.

Uso: python3 snake.py usuario salida.svg
Solo usa la librería estándar, así corre tal cual dentro de una GitHub Action.
"""
import math, random, re, sys, urllib.request

THEME = dict(bg='#0a0c10', line='#1f2430', empty='#161a22',
             lv=['#0e4429', '#006d32', '#26a641', '#39d353'], snake='#22d3ee', head='#ffffff')
P, S, X0, Y0 = 14, 11, 24, 24          # paso de la cuadrícula, tamaño de celda, márgenes
SPEED = P / 0.055                      # px por segundo
BODY = P * 7                           # largo de la serpiente


def parse(raw):
    grid = {}
    for tag in re.findall(r'<td[^>]*contribution-day-component[^>]*>', raw):
        pos = re.search(r'contribution-day-component-(\d+)-(\d+)', tag)
        lvl = re.search(r'data-level="(\d)"', tag)
        if pos and lvl:
            grid[(int(pos.group(1)), int(pos.group(2)))] = int(lvl.group(1))
    cols = max(c for _, c in grid) + 1
    return [[grid.get((r, c), -1) for c in range(cols)] for r in range(7)]


def fetch(user):
    req = urllib.request.Request(f'https://github.com/users/{user}/contributions', headers={'User-Agent': 'Mozilla/5.0'})
    return parse(urllib.request.urlopen(req, timeout=30).read().decode())


def route(grid):
    """Recorrido por la cuadrícula: siempre a la celda con color más cercana, y al final a la entrada de la espiral."""
    cols = len(grid[0])
    todo = {(r, c) for r in range(7) for c in range(cols) if grid[r][c] > 0}
    pos, cells = (3, -1), [(3, -1)]

    def walk(target):
        nonlocal pos
        r, c = pos
        while c != target[1]:
            c += 1 if target[1] > c else -1
            cells.append((r, c))
            todo.discard((r, c))
        while r != target[0]:
            r += 1 if target[0] > r else -1
            cells.append((r, c))
            todo.discard((r, c))
        pos = (r, c)

    while todo:
        walk(min(todo, key=lambda p: (abs(p[0] - pos[0]) + abs(p[1] - pos[1]), p[1])))
    center = (3, cols // 2)
    walk((3, center[1] + 3))
    return cells, center


def build(grid, th=THEME):
    cols = len(grid[0])
    W, H = X0 * 2 + cols * P - (P - S), Y0 * 2 + 7 * P - (P - S)
    px = lambda r, c: (X0 + c * P + S / 2, Y0 + r * P + S / 2)
    cells, (cr, cc) = route(grid)
    cx, cy = px(cr, cc)
    pts = [px(r, c) for r, c in cells]
    # espiral de dos vueltas que se cierra en el centro
    R = 3 * P
    for k in range(1, 121):
        a = k / 120 * 4 * math.pi
        rad = R * (1 - k / 120)
        pts.append((cx + rad * math.cos(a), cy - rad * math.sin(a) * .9))
    dist = [0.0]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        dist.append(dist[-1] + math.hypot(x2 - x1, y2 - y1))
    total = dist[-1]
    t_boom = (total + BODY) / SPEED
    T = t_boom + 3.4
    pct = lambda t: f'{min(t, T) / T * 100:.2f}%'
    gap = total + BODY * 3
    css = [f'.sn{{fill:none;stroke-linecap:round;stroke-linejoin:round;animation:mv {T:.2f}s linear infinite}}'
           f'.hd{{animation-name:mh}}.fx{{transform-box:fill-box;transform-origin:center;opacity:0}}'
           f'@keyframes mv{{0%{{stroke-dashoffset:{BODY};opacity:1}}{pct(t_boom - .01)}{{opacity:1}}{pct(t_boom)},100%{{stroke-dashoffset:{-total};opacity:0}}}}'
           f'@keyframes mh{{0%{{stroke-dashoffset:1;opacity:1}}{pct(t_boom - .01)}{{opacity:1}}{pct(t_boom)},100%{{stroke-dashoffset:{1 - total - BODY};opacity:0}}}}']
    body = [f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="{th["bg"]}" stroke="{th["line"]}"/>']
    first = {}
    for i, (r, c) in enumerate(cells):
        first.setdefault((r, c), dist[i])
    far = math.hypot(cols * P / 2, 4 * P)
    keys = {}
    for r in range(7):
        for c in range(cols):
            lvl = grid[r][c]
            if lvl < 0:
                continue
            x, y = X0 + c * P, Y0 + r * P
            body.append(f'<rect x="{x}" y="{y}" width="{S}" height="{S}" rx="3" fill="{th["empty"]}"/>')
            if lvl > 0:
                te = first[(r, c)] / SPEED
                tr = t_boom + .3 + math.hypot(x - cx, y - cy) / far * 1.4
                k = (pct(te), pct(te + .15), pct(tr), pct(tr + .35))
                cls = keys.setdefault(k, f'e{len(keys)}')
                body.append(f'<rect class="fx {cls}" x="{x}" y="{y}" width="{S}" height="{S}" rx="3" '
                            f'fill="{th["lv"][lvl - 1]}"/>')
    for (a, b, c, d), cls in keys.items():
        css.append(f'.{cls}{{animation:{cls} {T:.2f}s linear infinite}}@keyframes {cls}{{0%,{a}{{opacity:1;transform:none}}'
                   f'{b},{c}{{opacity:0;transform:scale(.3)}}{d},100%{{opacity:1;transform:none}}}}')
    ease = 'animation-timing-function:cubic-bezier(.1,.8,.3,1)'
    # portal: se abre cuando la cuadrícula ya se regeneró y de él sale la siguiente serpiente,
    # así el último cuadro y el primero son el mismo estado
    sx, sy = pts[0]
    css.append(f'.portal{{animation:portal {T:.2f}s linear infinite}}@keyframes portal{{0%,{pct(.55)}{{opacity:1;transform:scale(1)}}'
               f'{pct(.95)}{{opacity:0;transform:scale(0)}}{pct(T - 1)}{{opacity:0;transform:scale(0);{ease}}}'
               f'{pct(T - .35)}{{opacity:1;transform:scale(1.35)}}100%{{opacity:1;transform:scale(1)}}}}'
               f'.spin{{transform-box:fill-box;transform-origin:center;animation:spin 1.2s linear infinite}}'
               f'@keyframes spin{{to{{transform:rotate(360deg)}}}}')
    body.append(f'<g class="fx portal" style="opacity:1"><circle cx="{sx}" cy="{sy}" r="9" fill="{th["snake"]}" fill-opacity=".25"/>'
                f'<circle class="spin" cx="{sx}" cy="{sy}" r="9" fill="none" stroke="{th["snake"]}" stroke-width="2" '
                f'stroke-dasharray="10 4"/><circle cx="{sx}" cy="{sy}" r="3" fill="{th["head"]}"/></g>')
    line = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    body.append(f'<polyline class="sn" points="{line}" stroke="{th["snake"]}" stroke-width="9" '
                f'stroke-dasharray="{BODY} {gap:.0f}"/>'
                f'<polyline class="sn hd" points="{line}" stroke="{th["head"]}" stroke-width="10" '
                f'stroke-dasharray="1 {gap:.0f}"/>')
    # explosión
    css.append(f'.boom{{animation:boom {T:.2f}s linear infinite}}@keyframes boom{{0%,{pct(t_boom)}{{opacity:0;transform:scale(.2);{ease}}}'
               f'{pct(t_boom + .08)}{{opacity:.95;transform:scale(1.5)}}{pct(t_boom + .6)},100%{{opacity:0;transform:scale(3.2)}}}}'
               f'.wave{{animation:wave {T:.2f}s linear infinite}}@keyframes wave{{0%,{pct(t_boom)}{{opacity:0;transform:scale(.3);{ease}}}'
               f'{pct(t_boom + .05)}{{opacity:1}}{pct(t_boom + 1.1)},100%{{opacity:0;transform:scale(11)}}}}')
    body.append(f'<circle class="fx wave" cx="{cx}" cy="{cy}" r="10" fill="none" stroke="{th["snake"]}" stroke-width="2.5" vector-effect="non-scaling-stroke"/>'
                f'<circle class="fx boom" cx="{cx}" cy="{cy}" r="12" fill="#ffffff"/>')
    rnd = random.Random(7)
    for i in range(34):
        ang = rnd.uniform(0, 2 * math.pi)
        d = rnd.uniform(70, 360)
        dx, dy = math.cos(ang) * d, math.sin(ang) * d * .35
        size = rnd.choice([6, 8, 8, 11])
        col = rnd.choice(th['lv'][1:] + [th['snake'], th['head']])
        css.append(f'.pt{i}{{animation:pt{i} {T:.2f}s linear infinite}}@keyframes pt{i}{{0%,{pct(t_boom)}'
                   f'{{opacity:0;transform:translate(0,0) rotate(0);{ease}}}{pct(t_boom + .04)}{{opacity:1}}'
                   f'{pct(t_boom + rnd.uniform(.9, 1.4))},100%{{opacity:0;transform:translate({dx:.0f}px,{dy:.0f}px) '
                   f'rotate({rnd.randint(-300, 300)}deg)}}}}')
        body.append(f'<rect class="fx pt{i}" x="{cx - size / 2:.1f}" y="{cy - size / 2:.1f}" width="{size}" '
                    f'height="{size}" rx="2" fill="{col}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="A snake eats my contribution graph, spirals to the center and explodes">'
            f'<style>{"".join(css)}</style>{"".join(body)}</svg>')


if __name__ == '__main__':
    user, out = sys.argv[1:3]
    svg = build(fetch(user))
    with open(out, 'w') as f:
        f.write(svg)
