"""Teste do rosto estilo BMO — SEM IA, SEM microfone, SEM .env, SEM internet.

Só precisa de:  pip install pygame
Rodar:          python teste_rosto_bmo.py
Tela cheia:     python teste_rosto_bmo.py --fullscreen

Teclas:
  1 = dormindo (olhos fechados em "U")   2 = ouvindo (olhos grandes)
  3 = pensando (olha pra cima/lados)     4 = falando (boca abre e fecha)
  0 = parado/normal (pisca sozinho)
  R = mostra o RELÓGIO     F = mostra o ROSTO     TAB = alterna rosto/relógio
  A = alterna modo automático (troca de estado sozinho, só no rosto)
  S = salva um print em bmo_print.png
  ESC ou Q = sair
"""
import math
import random
import sys
import time

import pygame

LARGURA, ALTURA = 480, 320        # mesmo tamanho da telinha 3,5"
ESCALA = 2                        # desenha 2x maior e reduz (bordas suaves)
FUNDO = (192, 249, 222)           # menta do template
TRACO = (0, 0, 0)

ESTADOS = {
    pygame.K_0: "idle",
    pygame.K_1: "waiting",
    pygame.K_2: "listening",
    pygame.K_3: "thinking",
    pygame.K_4: "speaking",
}


class RostoBMO:
    def __init__(self):
        self.ab = 1.0                  # 1 = olho aberto, 0 = fechado ("U")
        self.olhar = [0.0, 0.0]
        self.prox_piscada = time.time() + 3
        self.fim_piscada = 0.0
        self.ultimo = time.time()

    # ---------- formas ----------
    @staticmethod
    def _curva(surf, pts, esp):
        """Linha grossa com pontas redondas (como no template)."""
        r = esp / 2
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            passos = max(1, int(math.hypot(x1 - x0, y1 - y0) / (r * 0.4)))
            for i in range(passos + 1):
                t = i / passos
                pygame.draw.circle(surf, TRACO, (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t), r)

    def _olho_aberto(self, s, cx, cy, w, h):
        pygame.draw.ellipse(s, TRACO, (cx - w / 2, cy - h / 2, w, h))

    def _olho_u(self, s, cx, cy, w, h, esp):
        """Olho fechado/feliz: curva em U (Rosto-04)."""
        pts = []
        for i in range(31):
            t = i / 30
            x = cx - w / 2 + w * t
            y = cy - h / 2 + h * (1 - (2 * t - 1) ** 2) * 0.95
            pts.append((x, y))
        self._curva(s, pts, esp)

    def _sorriso(self, s, cx, cy, larg, prof, esp):
        """Sorriso levemente assimétrico, como o do template."""
        pts = []
        for i in range(41):
            t = i / 40
            x = cx - larg / 2 + larg * t
            y = cy - prof / 2 + prof * (1 - (2 * t - 1) ** 2) * (1.0 + 0.12 * (1 - t))
            pts.append((x, y))
        self._curva(s, pts, esp)

    def _boca_aberta(self, s, cx, cy, larg, prof, esp):
        """Boca em D deitado: reta em cima, curva embaixo."""
        pts = [(cx - larg / 2, cy), (cx + larg / 2, cy)]
        for i in range(41):
            a = math.pi * i / 40
            pts.append((cx + math.cos(a) * larg / 2, cy + math.sin(a) * prof))
        pygame.draw.polygon(s, TRACO, pts)

    # ---------- desenho ----------
    def desenhar(self, estado):
        K = ESCALA
        s = pygame.Surface((LARGURA * K, ALTURA * K))
        s.fill(FUNDO)

        agora = time.time()
        dt = min(agora - self.ultimo, 0.1)
        self.ultimo = agora
        suave, rapido = min(1.0, dt * 10), min(1.0, dt * 25)

        # piscar
        if agora > self.prox_piscada:
            self.fim_piscada = agora + 0.16
            self.prox_piscada = agora + random.uniform(2.5, 6)
        piscando = agora < self.fim_piscada and estado != "waiting"

        alvo_ab = 0.0 if (estado == "waiting" or piscando) else 1.0
        alvo_olhar = [0.0, 0.0]
        if estado == "thinking":
            alvo_olhar = [math.sin(agora * 1.6), -0.8]
        self.ab += (alvo_ab - self.ab) * rapido
        for i in range(2):
            self.olhar[i] += (alvo_olhar[i] - self.olhar[i]) * suave

        # proporções tiradas do template (olhos a 26%/74%, y 40%; boca y 63%)
        ex = (LARGURA * 0.26 * K, LARGURA * 0.74 * K)
        ey = ALTURA * 0.40 * K
        ew, eh = 30 * K, 40 * K
        if estado == "listening":
            ew, eh = 36 * K, 50 * K
        esp = 7 * K
        mx, my = LARGURA * 0.50 * K, ALTURA * 0.62 * K

        # olhos
        for cx in ex:
            x = cx + self.olhar[0] * 18 * K
            y = ey + self.olhar[1] * 12 * K
            if self.ab > 0.5:
                h = max(6 * K, eh * self.ab)
                self._olho_aberto(s, x, y, ew, h)
            else:
                self._olho_u(s, x, y, ew * 1.5, eh * 0.55, esp)

        # boca
        if estado == "speaking":
            m = 0.2 + 0.8 * abs(math.sin(agora * 11)) * (0.65 + 0.35 * math.sin(agora * 3.7))
            self._boca_aberta(s, mx, my - 10 * K, 90 * K, (10 + 40 * m) * K, esp)
        elif estado == "listening":
            pygame.draw.ellipse(s, TRACO, (mx - 14 * K, my - 6 * K, 28 * K, 34 * K), esp // 2)
        elif estado == "thinking":
            off = self.olhar[0] * 8 * K
            self._curva(s, [(mx - 22 * K + off, my + 8 * K), (mx + 22 * K + off, my + 4 * K)], esp)
        elif estado == "waiting":
            self._sorriso(s, mx, my, 70 * K, 14 * K, esp)
        else:
            self._sorriso(s, mx, my, 90 * K, 24 * K, esp)

        return pygame.transform.smoothscale(s, (LARGURA, ALTURA))


DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


class RelogioBMO:
    """Relógio no mesmo estilo: fundo menta, números pretos, ':' piscando."""

    def __init__(self):
        K = ESCALA
        self.f_hora = pygame.font.SysFont("dejavusansmono,couriernew,monospace", 125 * K, bold=True)
        self.f_data = pygame.font.SysFont("dejavusansmono,couriernew,monospace", 30 * K, bold=True)

    def desenhar(self, estado=None):
        K = ESCALA
        s = pygame.Surface((LARGURA * K, ALTURA * K))
        s.fill(FUNDO)
        agora = time.localtime()
        hh, mm = time.strftime("%H", agora), time.strftime("%M", agora)
        cor_dp = TRACO if agora.tm_sec % 2 == 0 else FUNDO   # pisca a cada segundo

        a, dp, b = (self.f_hora.render(t, True, c) for t, c in ((hh, TRACO), (":", cor_dp), (mm, TRACO)))
        total = a.get_width() + dp.get_width() + b.get_width()
        x, y = (LARGURA * K - total) // 2, ALTURA * K * 0.18
        for surf in (a, dp, b):
            s.blit(surf, (x, y))
            x += surf.get_width()

        data = f"{DIAS[agora.tm_wday]}, {agora.tm_mday:02d} {MESES[agora.tm_mon - 1]} {agora.tm_year}"
        d = self.f_data.render(data, True, TRACO)
        s.blit(d, ((LARGURA * K - d.get_width()) // 2, ALTURA * K * 0.72))

        # barrinha dos segundos
        w = LARGURA * K * 0.6
        x0, y0 = (LARGURA * K - w) / 2, ALTURA * K * 0.90
        pygame.draw.rect(s, TRACO, (x0, y0, w, 5 * K), 1 * K)
        pygame.draw.rect(s, TRACO, (x0, y0, w * (agora.tm_sec + 1) / 60, 5 * K))

        return pygame.transform.smoothscale(s, (LARGURA, ALTURA))


def main():
    pygame.init()
    flags = pygame.FULLSCREEN | pygame.SCALED if "--fullscreen" in sys.argv else pygame.SCALED
    tela = pygame.display.set_mode((LARGURA, ALTURA), flags)
    pygame.display.set_caption("Teste BMO — rosto / relógio")
    clock = pygame.time.Clock()
    rosto, relogio = RostoBMO(), RelogioBMO()
    modo = "rosto"

    estado, auto, t_auto, seq = "idle", False, time.time(), ["idle", "listening", "thinking", "speaking", "waiting"]
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    return
                if ev.key == pygame.K_r:
                    modo = "relogio"
                elif ev.key == pygame.K_f:
                    modo = "rosto"
                elif ev.key == pygame.K_TAB:
                    modo = "relogio" if modo == "rosto" else "rosto"
                elif ev.key in ESTADOS:
                    estado, auto, modo = ESTADOS[ev.key], False, "rosto"
                elif ev.key == pygame.K_a:
                    auto, t_auto = not auto, time.time()
                elif ev.key == pygame.K_s:
                    pygame.image.save(tela, "bmo_print.png")
                    print("salvo: bmo_print.png")
        if auto and modo == "rosto" and time.time() - t_auto > 3:
            estado = seq[(seq.index(estado) + 1) % len(seq)]
            t_auto = time.time()

        tela.blit((rosto if modo == "rosto" else relogio).desenhar(estado), (0, 0))
        pygame.display.flip()
        clock.tick(30)


if __name__ == "__main__":
    main()
