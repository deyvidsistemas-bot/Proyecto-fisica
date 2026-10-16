import math
import sys
from collections import deque

import pygame

# =====================================================================
#  CONFIG  ->  AQUÍ LO HACES TUYO (nombres, colores, valores iniciales)
# =====================================================================
NOMBRE_LAB = "RAMP LAB"
SUBTITULO = "dos masas · una cuerda · dos ángulos distintos"
NOMBRE_A = "A"            # bloque de la izquierda
NOMBRE_B = "B"            # bloque de la derecha

COL_FONDO = (14, 16, 28)
COL_RAMPA = (30, 36, 62)
COL_BORDE = (120, 130, 190)
COL_A = (0, 220, 200)     # turquesa
COL_B = (255, 90, 160)    # rosa neón
COL_TEXTO = (225, 230, 245)
COL_TENUE = (120, 128, 160)
COL_ACENTO = (255, 200, 60)
COL_OK = (90, 240, 140)

# valores iniciales: (min, max, inicial, unidad)
INICIAL = {
    "mA":  (0.5, 30.0, 4.0, "kg"),
    "mB":  (0.5, 30.0, 6.0, "kg"),
    "angA": (15.0, 70.0, 25.0, "°"),
    "angB": (15.0, 70.0, 40.0, "°"),
    "muA": (0.0, 1.2, 0.20, ""),
    "muB": (0.0, 1.2, 0.20, ""),
}
RATIO_CINETICO = 0.75     # mu_k = RATIO * mu_s
# =====================================================================

G = 9.81
CUERDA_M = 4.0            # largo de cuerda en metros
PPM = 50                  # pixeles por metro
BOX = 66
MARGEN_M = 0.7

pygame.init()
WIDTH, HEIGHT = 1200, 780
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(NOMBRE_LAB)
clock = pygame.time.Clock()

f_small = pygame.font.SysFont("Consolas,Courier New,monospace", 14)
f_med = pygame.font.SysFont("Consolas,Courier New,monospace", 17, bold=True)
f_big = pygame.font.SysFont("Consolas,Courier New,monospace", 28, bold=True)


# ---------------------------------------------------------------- UI
class Slider:
    def __init__(self, clave, etiqueta, x, y, w=280):
        self.clave = clave
        self.etiqueta = etiqueta
        self.vmin, self.vmax, self.valor, self.unidad = INICIAL[clave]
        self.rect = pygame.Rect(x, y + 20, w, 8)
        self.activo = False

    def knob_x(self):
        t = (self.valor - self.vmin) / (self.vmax - self.vmin)
        return self.rect.x + t * self.rect.w

    def set_desde_mouse(self, mx):
        t = (mx - self.rect.x) / self.rect.w
        t = max(0.0, min(1.0, t))
        self.valor = self.vmin + t * (self.vmax - self.vmin)

    def evento(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            zona = self.rect.inflate(24, 26)
            if zona.collidepoint(ev.pos):
                self.activo = True
                self.set_desde_mouse(ev.pos[0])
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.activo = False
        elif ev.type == pygame.MOUSEMOTION and self.activo:
            self.set_desde_mouse(ev.pos[0])

    def dibujar(self, color):
        txt = f"{self.etiqueta}: {self.valor:.2f} {self.unidad}"
        screen.blit(f_small.render(txt, True, COL_TEXTO),
                    (self.rect.x, self.rect.y - 20))
        pygame.draw.rect(screen, COL_TENUE, self.rect, border_radius=4)
        llenado = pygame.Rect(self.rect.x, self.rect.y,
                              self.knob_x() - self.rect.x, self.rect.h)
        pygame.draw.rect(screen, color, llenado, border_radius=4)
        pygame.draw.circle(screen, COL_TEXTO,
                           (int(self.knob_x()), self.rect.centery), 9)
        pygame.draw.circle(screen, color,
                           (int(self.knob_x()), self.rect.centery), 6)


sliders = {
    "mA": Slider("mA", f"masa {NOMBRE_A}", 30, 80),
    "mB": Slider("mB", f"masa {NOMBRE_B}", 30, 128),
    "angA": Slider("angA", f"ángulo {NOMBRE_A}", 30, 176),
    "angB": Slider("angB", f"ángulo {NOMBRE_B}", 30, 224),
    "muA": Slider("muA", f"mu estático {NOMBRE_A}", 30, 272),
    "muB": Slider("muB", f"mu estático {NOMBRE_B}", 30, 320),
}
colores_slider = {"mA": COL_A, "mB": COL_B, "angA": COL_A,
                  "angB": COL_B, "muA": COL_A, "muB": COL_B}


def panel(rect, titulo=None):
    pygame.draw.rect(screen, (22, 26, 46), rect, border_radius=14)
    pygame.draw.rect(screen, COL_BORDE, rect, 2, border_radius=14)
    if titulo:
        screen.blit(f_med.render(titulo, True, COL_ACENTO),
                    (rect.x + 18, rect.y + 12))


# ------------------------------------------------------------- Física
def calcular(mA, mB, angA, angB, muA, muB, v):
    """
    Convención: v > 0  ->  B baja por la derecha y A sube por la izquierda.
                v < 0  ->  A baja por la izquierda y B sube.
    Devuelve (aceleración, estado, tensión o None).
    """
    muA_k = RATIO_CINETICO * muA
    muB_k = RATIO_CINETICO * muB

    empuje = mB * G * math.sin(angB) - mA * G * math.sin(angA)
    normalA = mA * G * math.cos(angA)
    normalB = mB * G * math.cos(angB)
    fric_est_max = muA * normalA + muB * normalB

    if abs(v) < 1e-4 and abs(empuje) <= fric_est_max:
        return 0.0, "EQUILIBRIO", None

    if abs(v) >= 1e-4:
        d = math.copysign(1.0, v)
    else:
        d = math.copysign(1.0, empuje)

    fric_k = muA_k * normalA + muB_k * normalB
    a = (empuje - d * fric_k) / (mA + mB)

    # Tensión (de la 2ª ley aplicada al bloque A, positivo = sube su rampa)
    T = mA * (a + G * math.sin(angA) + d * muA_k * G * math.cos(angA))

    estado = f"{NOMBRE_B} BAJA" if d > 0 else f"{NOMBRE_A} BAJA"
    return a, estado, T


# ---------------------------------------------------------- Geometría
def geometria(angA, angB):
    cot_sum = 1 / math.tan(angA) + 1 / math.tan(angB)
    H = min(290.0, 0.85 * (WIDTH - 200) / cot_sum)
    base_y = HEIGHT - 150
    bl = H / math.tan(angA)
    br = H / math.tan(angB)
    apx = WIDTH / 2 - (br - bl) / 2
    apice = (apx, base_y - H)
    izq = (apx - bl, base_y)
    der = (apx + br, base_y)
    Lm_A = H / math.sin(angA) / PPM
    Lm_B = H / math.sin(angB) / PPM
    return apice, izq, der, base_y, Lm_A, Lm_B


def limites_s(Lm_A, Lm_B):
    """Rango permitido para sB (sA = CUERDA - sB)."""
    lo = max(MARGEN_M, CUERDA_M - (Lm_A - MARGEN_M))
    hi = min(Lm_B - MARGEN_M, CUERDA_M - MARGEN_M)
    if lo > hi:
        lo = hi = (lo + hi) / 2
    return lo, hi


def crear_bloque(color, texto, angulo_deg):
    surf = pygame.Surface((BOX, BOX), pygame.SRCALPHA)
    pygame.draw.rect(surf, color, (0, 0, BOX, BOX), border_radius=10)
    pygame.draw.rect(surf, (255, 255, 255), (0, 0, BOX, BOX), 3,
                     border_radius=10)
    t = f_med.render(texto, True, COL_FONDO)
    surf.blit(t, t.get_rect(center=(BOX // 2, BOX // 2)))
    return pygame.transform.rotate(surf, angulo_deg)


# ------------------------------------------------------------- Estado
sB = CUERDA_M / 2
v = 0.0
paused = False
historial = deque(maxlen=420)
running = True

while running:
    dt = clock.tick(60) / 1000.0

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                running = False
            elif ev.key == pygame.K_SPACE:
                paused = not paused
            elif ev.key == pygame.K_r:
                sB = CUERDA_M / 2
                v = 0.0
                historial.clear()
        for sl in sliders.values():
            sl.evento(ev)

    mA = sliders["mA"].valor
    mB = sliders["mB"].valor
    angA = math.radians(sliders["angA"].valor)
    angB = math.radians(sliders["angB"].valor)
    muA = sliders["muA"].valor
    muB = sliders["muB"].valor

    apice, izq, der, base_y, Lm_A, Lm_B = geometria(angA, angB)
    lo, hi = limites_s(Lm_A, Lm_B)

    # --- integración con subpasos para que sea estable
    a, estado, T = calcular(mA, mB, angA, angB, muA, muB, v)
    if not paused:
        SUB = 4
        h = dt / SUB
        for _ in range(SUB):
            a, estado, T = calcular(mA, mB, angA, angB, muA, muB, v)
            v_prev = v
            v += a * h
            if v_prev * v < 0:      # la fricción frenó el sistema
                v = 0.0
            sB += v * h
            if sB < lo:
                sB, v = lo, 0.0
            elif sB > hi:
                sB, v = hi, 0.0
        historial.append(v)
    sB = max(lo, min(hi, sB))
    sA = CUERDA_M - sB

    # --- posiciones de los bloques (centro)
    uA = (-math.cos(angA), math.sin(angA))     # hacia abajo-izquierda
    nA = (-math.sin(angA), -math.cos(angA))    # normal saliente
    uB = (math.cos(angB), math.sin(angB))
    nB = (math.sin(angB), -math.cos(angB))

    cA = (apice[0] + uA[0] * sA * PPM + nA[0] * BOX / 2,
          apice[1] + uA[1] * sA * PPM + nA[1] * BOX / 2)
    cB = (apice[0] + uB[0] * sB * PPM + nB[0] * BOX / 2,
          apice[1] + uB[1] * sB * PPM + nB[1] * BOX / 2)

    # punto de la cuerda en cada bloque (cara que mira al ápice)
    pA = (cA[0] - uA[0] * BOX / 2, cA[1] - uA[1] * BOX / 2)
    pB = (cB[0] - uB[0] * BOX / 2, cB[1] - uB[1] * BOX / 2)
    polea = (apice[0], apice[1] - 24)

    # ================================================================
    #  DIBUJO
    # ================================================================
    screen.fill(COL_FONDO)

    # rejilla suave de fondo
    for gx in range(0, WIDTH, 60):
        pygame.draw.line(screen, (20, 23, 38), (gx, 0), (gx, HEIGHT))
    for gy in range(0, HEIGHT, 60):
        pygame.draw.line(screen, (20, 23, 38), (0, gy), (WIDTH, gy))

    # suelo y rampas
    pygame.draw.line(screen, COL_TENUE, (30, base_y + 4),
                     (WIDTH - 30, base_y + 4), 3)
    pygame.draw.polygon(screen, COL_RAMPA, [apice, izq, der])
    pygame.draw.lines(screen, COL_BORDE, True, [apice, izq, der], 4)

    # polea
    pygame.draw.line(screen, COL_TENUE, apice, polea, 5)
    pygame.draw.circle(screen, COL_BORDE, (int(polea[0]), int(polea[1])), 20)
    pygame.draw.circle(screen, COL_FONDO, (int(polea[0]), int(polea[1])), 12)
    pygame.draw.circle(screen, COL_ACENTO, (int(polea[0]), int(polea[1])), 4)

    # cuerda
    pygame.draw.line(screen, COL_ACENTO, pA, (polea[0] - 15, polea[1] + 12), 3)
    pygame.draw.line(screen, COL_ACENTO, pB, (polea[0] + 15, polea[1] + 12), 3)

    # bloques
    bA = crear_bloque(COL_A, NOMBRE_A, math.degrees(angA))
    bB = crear_bloque(COL_B, NOMBRE_B, -math.degrees(angB))
    screen.blit(bA, bA.get_rect(center=cA))
    screen.blit(bB, bB.get_rect(center=cB))

    # arcos de ángulo
    r = 55
    pygame.draw.arc(screen, COL_A, (izq[0] - r, base_y - r, 2 * r, 2 * r),
                    0, angA, 3)
    pygame.draw.arc(screen, COL_B, (der[0] - r, base_y - r, 2 * r, 2 * r),
                    math.pi - angB, math.pi, 3)
    screen.blit(f_small.render(f"{sliders['angA'].valor:.0f}°", True, COL_A),
                (izq[0] + r + 6, base_y - 24))
    screen.blit(f_small.render(f"{sliders['angB'].valor:.0f}°", True, COL_B),
                (der[0] - r - 40, base_y - 24))

    # ---- panel de controles (sliders)
    panel(pygame.Rect(12, 12, 340, 365))
    screen.blit(f_big.render(NOMBRE_LAB, True, COL_TEXTO), (30, 20))
    screen.blit(f_small.render(SUBTITULO[:38], True, COL_TENUE), (30, 52))
    for k, sl in sliders.items():
        sl.dibujar(colores_slider[k])

    # ---- panel de lectura
    panel(pygame.Rect(WIDTH - 362, 12, 350, 330), "Telemetría")
    lecturas = [
        f"aceleración  {a:+7.3f} m/s²",
        f"velocidad    {v:+7.3f} m/s",
        "tensión      " + (f"{T:7.2f} N" if T is not None else "   indeterminada"),
        f"E. cinética  {0.5 * (mA + mB) * v * v:7.2f} J",
    ]
    y = 46
    for linea in lecturas:
        screen.blit(f_small.render(linea, True, COL_TEXTO),
                    (WIDTH - 344, y))
        y += 22

    col_estado = COL_OK if estado == "EQUILIBRIO" else (
        COL_B if "B" in estado[:1] and estado.startswith(NOMBRE_B) else COL_A)
    screen.blit(f_med.render(estado, True, col_estado), (WIDTH - 344, y + 4))

    # gráfica de velocidad
    gx, gy, gw, gh = WIDTH - 344, 175, 318, 150
    pygame.draw.rect(screen, (14, 16, 28), (gx, gy, gw, gh), border_radius=8)
    pygame.draw.line(screen, COL_TENUE, (gx, gy + gh // 2),
                     (gx + gw, gy + gh // 2), 1)
    screen.blit(f_small.render("v(t)", True, COL_TENUE), (gx + 6, gy + 4))
    if len(historial) > 2:
        vmax = max(1.0, max(abs(x) for x in historial))
        pts = []
        n = len(historial)
        for i, val in enumerate(historial):
            px = gx + i * gw / historial.maxlen
            py = gy + gh / 2 - (val / vmax) * (gh / 2 - 10)
            pts.append((px, py))
        pygame.draw.lines(screen, COL_ACENTO, False, pts, 2)

    # pie
    if paused:
        screen.blit(f_big.render("PAUSA", True, COL_ACENTO),
                    (WIDTH // 2 - 50, 20))
    ayuda = "arrastra los sliders · ESPACIO pausa · R reinicia · ESC sale"
    screen.blit(f_small.render(ayuda, True, COL_TENUE),
                (WIDTH // 2 - 250, HEIGHT - 30))

    pygame.display.flip()

pygame.quit()
sys.exit()
