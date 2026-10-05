"""Rosto do Bimo: olhos com íris e brilho, pálpebras, sobrancelhas, bochechas e boca.

Estados: waiting (dormindo), listening, thinking, speaking.
"""
import math
import os
import platform
import random
import time

import pygame

BRANCO = (245, 248, 255)
ESCURO = (10, 14, 26)


class Rosto:
    cor_legenda = (120, 130, 150)

    def __init__(self, cor=(0, 220, 255), fundo=(12, 16, 28)):
        self.cor, self.fundo = cor, fundo
        self.abertura = 0.2          # 0 = olho fechado, 1 = aberto
        self.olhar = [0.0, 0.0]      # -1..1 (x, y)
        self.sobr = [0.0, 0.0]       # deslocamento das sobrancelhas (esq, dir)
        self.prox_piscada = time.time() + 3
        self.fim_piscada = 0.0
        self.ultimo = time.time()
        self.fonte = pygame.font.SysFont(None, 34)
        self.bochecha = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(self.bochecha, (255, 110, 150, 70), (30, 30), 20)

    def desenhar(self, tela, estado):
        agora = time.time()
        dt = min(agora - self.ultimo, 0.1)
        self.ultimo = agora
        suave = min(1.0, dt * 12)
        rapido = min(1.0, dt * 25)

        # --- piscar ---
        if agora > self.prox_piscada:
            self.fim_piscada = agora + 0.14
            self.prox_piscada = agora + random.uniform(2, 6)
        piscando = agora < self.fim_piscada and estado != "waiting"

        # --- alvos de cada estado ---
        alvo_ab = {"waiting": 0.1, "listening": 1.0, "thinking": 0.85, "speaking": 0.95}.get(estado, 0.9)
        if piscando:
            alvo_ab = 0.0
        alvo_olhar = [0.0, 0.0]
        alvo_sobr = [0.0, 0.0]
        if estado == "thinking":
            alvo_olhar = [0.8 * math.sin(agora * 1.6), -0.8]
            alvo_sobr = [4.0, -16.0]
        elif estado == "listening":
            alvo_sobr = [-12.0, -12.0]
        elif estado == "speaking":
            salto = -4.0 * abs(math.sin(agora * 5))
            alvo_sobr = [salto, salto]

        self.abertura += (alvo_ab - self.abertura) * rapido
        for i in range(2):
            self.olhar[i] += (alvo_olhar[i] - self.olhar[i]) * suave
            self.sobr[i] += (alvo_sobr[i] - self.sobr[i]) * suave

        tela.fill(self.fundo)

        # --- olhos ---
        EW, EH, CY = 120, 130, 115
        topo = CY - EH // 2
        coberto = EH * (1 - self.abertura)
        for cx in (150, 330):
            pygame.draw.ellipse(tela, BRANCO, (cx - EW // 2, topo, EW, EH))
            ix = cx + self.olhar[0] * 14
            iy = CY + self.olhar[1] * 12
            pygame.draw.circle(tela, self.cor, (ix, iy), 38)
            pygame.draw.circle(tela, ESCURO, (ix, iy), 19)
            pygame.draw.circle(tela, BRANCO, (ix - 12, iy - 14), 9)
            if coberto > 1:  # pálpebra
                pygame.draw.rect(tela, self.fundo, (cx - EW // 2 - 2, topo - 2, EW + 4, coberto + 2))
                pygame.draw.line(tela, self.cor, (cx - EW // 2 + 8, topo + coberto),
                                 (cx + EW // 2 - 8, topo + coberto), 6)

        # --- bochechas ---
        tela.blit(self.bochecha, (60, 175))
        tela.blit(self.bochecha, (360, 175))

        # --- sobrancelhas ---
        if estado != "waiting":
            by = 30
            e, d = self.sobr
            pygame.draw.line(tela, self.cor, (110, by + 8 + e), (190, by + e), 8)
            pygame.draw.line(tela, self.cor, (290, by + d), (370, by + 8 + d), 8)

        # --- boca ---
        mx, my = 240, 238
        if estado == "speaking":
            m = 0.25 + 0.75 * abs(math.sin(agora * 11)) * (0.65 + 0.35 * math.sin(agora * 3.7))
            r = pygame.Rect(0, 0, 76, int(10 + 44 * m))
            r.center = (mx, my)
            pygame.draw.ellipse(tela, (90, 20, 45), r)
            pygame.draw.ellipse(tela, self.cor, r, 4)
        elif estado == "listening":
            r = pygame.Rect(0, 0, 28, 32)
            r.center = (mx, my)
            pygame.draw.ellipse(tela, self.cor, r, 5)
        elif estado == "thinking":
            pygame.draw.line(tela, self.cor, (mx - 24, my + 4), (mx + 24, my - 4), 6)
        elif estado == "waiting":
            pygame.draw.arc(tela, self.cor, (mx - 28, my - 28, 56, 40), math.pi, 2 * math.pi, 5)
        else:
            pygame.draw.arc(tela, self.cor, (mx - 45, my - 35, 90, 60), math.pi, 2 * math.pi, 6)

        # --- detalhes de estado ---
        if estado == "thinking":
            for i in range(3):
                raio = 5 + 3 * max(0.0, math.sin(agora * 6 - i * 1.2))
                pygame.draw.circle(tela, self.cor, (400 + i * 22, 28), raio)
        elif estado == "waiting":
            y = 60 - (agora * 14) % 30
            tela.blit(self.fonte.render("z", True, self.cor), (400, y))


class RostoRetro:
    """Estilo tela de videogame portátil: fundo menta, olhos de bolinha e sorriso largo."""

    cor_legenda = (35, 80, 70)
    FUNDO = (150, 222, 190)
    MOLDURA = (22, 32, 36)
    TRACO = (22, 48, 44)

    def __init__(self, *_):
        self.ab = 1.0
        self.olhar = [0.0, 0.0]
        self.prox_piscada = time.time() + 3
        self.fim_piscada = 0.0
        self.ultimo = time.time()
        self.fonte = pygame.font.SysFont(None, 40)
        self.linhas = pygame.Surface((480, 320), pygame.SRCALPHA)
        for y in range(0, 320, 4):  # linhas de varredura, efeito de tela antiga
            pygame.draw.line(self.linhas, (0, 40, 30, 26), (0, y), (480, y))
        try:
            self.linhas = self.linhas.convert_alpha()  # blit bem mais rápido no Pi
        except pygame.error:
            pass

    def _boca(self, tela, cx, cy, w, prof):
        """Boca aberta em forma de D deitado: reta em cima, curva embaixo."""
        pygame.draw.ellipse(tela, self.TRACO, (cx - w // 2, cy - prof, w, 2 * prof))
        pygame.draw.rect(tela, self.FUNDO, (cx - w // 2 - 2, cy - prof - 2, w + 4, prof + 2))

    def desenhar(self, tela, estado):
        agora = time.time()
        dt = min(agora - self.ultimo, 0.1)
        self.ultimo = agora
        suave, rapido = min(1.0, dt * 12), min(1.0, dt * 25)

        if agora > self.prox_piscada:
            self.fim_piscada = agora + 0.14
            self.prox_piscada = agora + random.uniform(2, 6)
        piscando = agora < self.fim_piscada and estado != "waiting"

        alvo_ab = 0.1 if estado == "waiting" else 1.0
        if piscando:
            alvo_ab = 0.05
        alvo_olhar = [0.0, 0.0]
        if estado == "thinking":
            alvo_olhar = [math.sin(agora * 1.6), -0.8]
        self.ab += (alvo_ab - self.ab) * rapido
        for i in range(2):
            self.olhar[i] += (alvo_olhar[i] - self.olhar[i]) * suave

        tela.fill(self.MOLDURA)
        pygame.draw.rect(tela, self.FUNDO, (10, 10, 460, 300), border_radius=28)

        # olhos
        r = 20 if estado == "listening" else 15
        h = max(5, int(2 * r * self.ab))
        for cx in (160, 320):
            olho = pygame.Rect(0, 0, 2 * r, h)
            olho.center = (cx + self.olhar[0] * 12, 100 + self.olhar[1] * 10)
            pygame.draw.ellipse(tela, self.TRACO, olho)

        # boca
        mx, my = 240, 185
        if estado == "speaking":
            m = 0.2 + 0.8 * abs(math.sin(agora * 11)) * (0.65 + 0.35 * math.sin(agora * 3.7))
            self._boca(tela, mx, my, 130, int(8 + 52 * m))
        elif estado == "listening":
            pygame.draw.ellipse(tela, self.TRACO, (mx - 20, my - 4, 40, 48))
        elif estado == "thinking":
            pygame.draw.line(tela, self.TRACO, (mx - 30 + self.olhar[0] * 8, my + 20),
                             (mx + 30 + self.olhar[0] * 8, my + 20), 8)
        elif estado == "waiting":
            pygame.draw.arc(tela, self.TRACO, (mx - 30, my - 10, 60, 40), math.pi, 2 * math.pi, 6)
        else:
            self._boca(tela, mx, my, 150, 55)

        if estado == "thinking":
            for i in range(3):
                raio = 5 + 3 * max(0.0, math.sin(agora * 6 - i * 1.2))
                pygame.draw.circle(tela, self.TRACO, (395 + i * 22, 45), raio)
        elif estado == "waiting":
            y = 70 - (agora * 14) % 30
            tela.blit(self.fonte.render("z", True, self.TRACO), (390, y))

        tela.blit(self.linhas, (0, 0))


# =====================================================================
#  Estilo BMO (fundo menta, olhos ovais pretos, sorriso fino) + relógio
# =====================================================================
LARG, ALT = 480, 320
MENTA = (192, 249, 222)
PRETO = (0, 0, 0)
_ARM = platform.machine().lower().startswith(("arm", "aarch"))
FONTES = "dejavusansmono,couriernew,monospace"
DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _escala():
    """Suavização das bordas: 2 no PC; 1 no Pi (mais leve). Troque com BIMO_SUAVE=1|2|3."""
    try:
        return max(1, min(3, int(os.environ.get("BIMO_SUAVE", "1" if _ARM else "2"))))
    except ValueError:
        return 1


class RostoBMO:
    """Rosto estilo BMO. Estados: waiting (dormindo), listening, thinking, speaking."""

    cor_legenda = (30, 90, 70)

    def __init__(self, *_):
        self.K = _escala()
        self.buf = pygame.Surface((LARG * self.K, ALT * self.K)) if self.K > 1 else None
        self.ab = 1.0
        self.olhar = [0.0, 0.0]
        self.prox_piscada = time.time() + 3
        self.fim_piscada = 0.0
        self.ultimo = time.time()
        self.fonte = pygame.font.SysFont(None, 40)

    @staticmethod
    def _curva(s, pts, esp):
        """Linha grossa com pontas redondas."""
        r = esp / 2
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            passos = max(1, int(math.hypot(x1 - x0, y1 - y0) / (r * 0.6)))
            for i in range(passos + 1):
                t = i / passos
                pygame.draw.circle(s, PRETO, (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t), r)

    def _olho_u(self, s, cx, cy, w, h, esp):
        pts = []
        for i in range(25):
            t = i / 24
            pts.append((cx - w / 2 + w * t, cy - h / 2 + h * (1 - (2 * t - 1) ** 2) * 0.95))
        self._curva(s, pts, esp)

    def _sorriso(self, s, cx, cy, larg, prof, esp):
        pts = []
        for i in range(31):
            t = i / 30
            pts.append((cx - larg / 2 + larg * t,
                        cy - prof / 2 + prof * (1 - (2 * t - 1) ** 2) * (1.0 + 0.12 * (1 - t))))
        self._curva(s, pts, esp)

    @staticmethod
    def _boca_aberta(s, cx, cy, larg, prof):
        pts = [(cx - larg / 2, cy), (cx + larg / 2, cy)]
        for i in range(31):
            a = math.pi * i / 30
            pts.append((cx + math.cos(a) * larg / 2, cy + math.sin(a) * prof))
        pygame.draw.polygon(s, PRETO, pts)

    def desenhar(self, tela, estado):
        K = self.K
        s = tela if K == 1 else self.buf
        s.fill(MENTA)

        agora = time.time()
        dt = min(agora - self.ultimo, 0.1)
        self.ultimo = agora
        suave, rapido = min(1.0, dt * 10), min(1.0, dt * 25)

        if agora > self.prox_piscada:
            self.fim_piscada = agora + 0.16
            self.prox_piscada = agora + random.uniform(2.5, 6)
        piscando = agora < self.fim_piscada and estado != "waiting"

        alvo_ab = 0.0 if (estado == "waiting" or piscando) else 1.0
        alvo_olhar = [math.sin(agora * 1.6), -0.8] if estado == "thinking" else [0.0, 0.0]
        self.ab += (alvo_ab - self.ab) * rapido
        for i in range(2):
            self.olhar[i] += (alvo_olhar[i] - self.olhar[i]) * suave

        ex = (LARG * 0.26 * K, LARG * 0.74 * K)
        ey = ALT * 0.40 * K
        ew, eh = (36 * K, 50 * K) if estado == "listening" else (30 * K, 40 * K)
        esp = 7 * K
        mx, my = LARG * 0.50 * K, ALT * 0.62 * K

        for cx in ex:
            x = cx + self.olhar[0] * 18 * K
            y = ey + self.olhar[1] * 12 * K
            if self.ab > 0.5:
                h = max(6 * K, eh * self.ab)
                pygame.draw.ellipse(s, PRETO, (x - ew / 2, y - h / 2, ew, h))
            else:
                self._olho_u(s, x, y, ew * 1.5, eh * 0.55, esp)

        if estado == "speaking":
            m = 0.2 + 0.8 * abs(math.sin(agora * 11)) * (0.65 + 0.35 * math.sin(agora * 3.7))
            self._boca_aberta(s, mx, my - 10 * K, 90 * K, (10 + 40 * m) * K)
        elif estado == "listening":
            pygame.draw.ellipse(s, PRETO, (mx - 14 * K, my - 6 * K, 28 * K, 34 * K), esp // 2)
        elif estado == "thinking":
            off = self.olhar[0] * 8 * K
            self._curva(s, [(mx - 22 * K + off, my + 8 * K), (mx + 22 * K + off, my + 4 * K)], esp)
        elif estado == "waiting":
            self._sorriso(s, mx, my, 70 * K, 14 * K, esp)
        else:
            self._sorriso(s, mx, my, 90 * K, 24 * K, esp)

        if K != 1:
            tela.blit(pygame.transform.smoothscale(s, (LARG, ALT)), (0, 0))

        if estado == "thinking":
            for i in range(3):
                raio = 5 + 3 * max(0.0, math.sin(agora * 6 - i * 1.2))
                pygame.draw.circle(tela, PRETO, (395 + i * 22, 45), raio)
        elif estado == "waiting":
            y = 70 - (agora * 14) % 30
            tela.blit(self.fonte.render("z", True, PRETO), (400, y))


class RelogioBMO:
    """Relógio no mesmo estilo. desenhar() = tela cheia; mini() = hora pequena no topo (rosto + relógio)."""

    cor_legenda = (30, 90, 70)

    def __init__(self):
        self.f_hora = pygame.font.SysFont(FONTES, 125, bold=True)
        self.f_data = pygame.font.SysFont(FONTES, 30, bold=True)
        self.f_mini = pygame.font.SysFont(FONTES, 52, bold=True)
        self._k_full = self._k_mini = None
        self._full = self._mini = None

    @staticmethod
    def _hhmm(fonte, agora):
        """HH:MM com os dois pontos piscando (a largura não muda ao piscar)."""
        dp = PRETO if agora.tm_sec % 2 == 0 else MENTA
        a = fonte.render(time.strftime("%H", agora), True, PRETO)
        b = fonte.render(":", True, dp)
        c = fonte.render(time.strftime("%M", agora), True, PRETO)
        surf = pygame.Surface((a.get_width() + b.get_width() + c.get_width(), a.get_height()), pygame.SRCALPHA)
        surf.blit(a, (0, 0))
        surf.blit(b, (a.get_width(), 0))
        surf.blit(c, (a.get_width() + b.get_width(), 0))
        return surf

    def desenhar(self, tela, estado=None):
        agora = time.localtime()
        if self._k_full != agora.tm_sec:  # só redesenha 1 vez por segundo
            self._k_full = agora.tm_sec
            img = pygame.Surface((LARG, ALT))
            img.fill(MENTA)
            hora = self._hhmm(self.f_hora, agora)
            img.blit(hora, ((LARG - hora.get_width()) // 2, int(ALT * 0.14)))
            data = f"{DIAS[agora.tm_wday]}, {agora.tm_mday:02d} {MESES[agora.tm_mon - 1]} {agora.tm_year}"
            d = self.f_data.render(data, True, PRETO)
            img.blit(d, ((LARG - d.get_width()) // 2, int(ALT * 0.70)))
            w = LARG * 0.6
            x0, y0 = (LARG - w) / 2, ALT * 0.855
            pygame.draw.rect(img, PRETO, (x0, y0, w, 5), 1)
            pygame.draw.rect(img, PRETO, (x0, y0, w * (agora.tm_sec + 1) / 60, 5))
            self._full = img
        tela.blit(self._full, (0, 0))

    def mini(self, tela):
        agora = time.localtime()
        chave = (agora.tm_min, agora.tm_hour, agora.tm_sec % 2)
        if self._k_mini != chave:
            self._k_mini = chave
            hora = self._hhmm(self.f_mini, agora)
            img = pygame.Surface((hora.get_width() + 28, hora.get_height() + 6), pygame.SRCALPHA)
            pygame.draw.rect(img, MENTA, img.get_rect(), border_radius=14)  # caixinha: legível em qualquer fundo
            img.blit(hora, (14, 3))
            self._mini = img
        tela.blit(self._mini, ((LARG - self._mini.get_width()) // 2, 8))
