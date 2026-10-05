"""Robô com rosto animado: microfone -> modelo de IA -> voz.

Telas: rosto, relógio ou os dois. Troque por voz: "Bimo, mostra o relógio",
"Bimo, volta pro rosto", "Bimo, os dois". No teclado (PC): R = relógio, F = rosto, B = os dois.

Uso:
    python robo.py              # janela no PC, com microfone (fale "BIMO" para ativar)
    python robo.py --texto      # sem microfone: você digita no terminal
    python robo.py --fullscreen # tela cheia (para o display do Raspberry Pi)
"""
import argparse
import os
import platform
import re
import shutil
import subprocess
import textwrap
import threading
import time
from pathlib import Path

import numpy as np
import pygame
import sounddevice as sd
import speech_recognition as sr
from openai import BadRequestError, OpenAI
from dotenv import load_dotenv
from framebuffer import Framebuffer
from comandos import MENSAGENS, detectar_modo
from rosto import RelogioBMO, Rosto, RostoBMO, RostoRetro

load_dotenv(Path(__file__).with_name(".env"))

W, H = 480, 320

LINUX = platform.system() == "Linux"
ARM = platform.machine().lower().startswith(("arm", "aarch"))  # Raspberry Pi
if LINUX:
    os.environ.setdefault("DISPLAY", ":0")  # funciona também via SSH ou boot automático


def _inteiro(nome, padrao):
    try:
        return int(os.environ.get(nome, padrao))
    except ValueError:
        return int(padrao)


FPS = _inteiro("BIMO_FPS", 20 if ARM else 30)  # no Pi 3B, 20 quadros por segundo é mais leve
MIC = os.environ.get("BIMO_MIC", "").strip()  # número ou parte do nome (python -m sounddevice)
VOZ_VEL = _inteiro("BIMO_VOZ_VEL", 160)  # velocidade da voz (espeak)


def _cor(hexa, padrao):
    try:
        h = hexa.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return padrao


COR = _cor(os.environ.get("BIMO_COR", "00DCFF"), (0, 220, 255))  # cor do rosto (hex)
FUNDO = (12, 16, 28)
ESTILO = os.environ.get("BIMO_ESTILO", "bmo").lower()  # bmo | retro | fofo
MODO_INICIAL = os.environ.get("BIMO_MODO", "rosto").lower()  # rosto | relogio | ambos

# Quem responde: "nvidia" (API da NVIDIA direto) ou "hermes" (seu Hermes Agent)
BACKEND = os.environ.get("BIMO_BACKEND", "nvidia").lower()
if BACKEND == "hermes":
    BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:8642/v1")
    MODELO = os.environ.get("HERMES_MODEL", "hermes-agent")
    API_KEY = os.environ.get("HERMES_API_KEY", "")  # = API_SERVER_KEY do Hermes
    SISTEMA_PADRAO = (
        "Sua resposta será falada em voz alta por um robô com rosto animado. "
        "Responda em português do Brasil, em no máximo 3 frases curtas, "
        "sem markdown, listas, emojis ou links. "
        "Sem abreviar, sempre falar por extenso, tipo trocar H por hora. "
        "Sempre que eu pedir para abrir algum app, utiliza o psexec"
    )
else:
    BASE_URL = os.environ.get("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    MODELO = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    API_KEY = os.environ.get("NVIDIA_API_KEY", "")
    SISTEMA_PADRAO = (
        "Você é um robozinho simpático e curioso. "
        "Responda sempre em português do Brasil, em no máximo 2 frases curtas."
    )
SISTEMA = os.environ.get("BIMO_SISTEMA", SISTEMA_PADRAO)
# Velocidade: fala frase por frase enquanto a resposta chega (BIMO_STREAM=0 desliga)
STREAM = os.environ.get("BIMO_STREAM", "1") == "1"
# No modo Hermes o raciocínio longo do modelo fica desligado (BIMO_RACIOCINIO=1 liga)
RACIOCINIO = os.environ.get("BIMO_RACIOCINIO", "0") == "1"

RATE = 16000
# Palavras de ativação (inclui variações que o reconhecimento costuma ouvir).
# Pode trocar no .env: WAKE_WORDS=bimo,bemo,vimo
PALAVRAS = [p.strip().lower() for p in os.environ.get("WAKE_WORDS", "bimo,bemo,vimo,bimu,ok").split(",") if p.strip()]

state = "waiting"  # waiting | listening | thinking | speaking
legenda = ""
modo = MODO_INICIAL if MODO_INICIAL in ("rosto", "relogio", "ambos") else "rosto"


USA_ESPEAK = (
    LINUX and shutil.which("espeak-ng") is not None and os.environ.get("BIMO_VOZ", "").lower() != "pyttsx3"
)


def falar(texto):
    if USA_ESPEAK:
        # No Pi: chama o espeak-ng direto. É bem mais rápido que iniciar o pyttsx3 a cada frase.
        subprocess.run(["espeak-ng", "-v", "pt-br", "-s", str(VOZ_VEL), "--", texto], check=False)
        return
    import pyttsx3  # só no PC (Windows)

    engine = pyttsx3.init()
    for v in engine.getProperty("voices"):
        info = f"{v.name} {v.id}".lower()
        if any(k in info for k in ("brazil", "pt-br", "pt_br", "portug")):
            engine.setProperty("voice", v.id)
            break
    engine.setProperty("rate", VOZ_VEL + 10)
    engine.say(texto)
    engine.runAndWait()
    engine.stop()


def _abrir_microfone(passo):
    """Abre o microfone em 16 kHz; se ele não aceitar, usa a taxa padrão dele (comum em USB)."""
    dev = int(MIC) if MIC.isdigit() else (MIC or None)
    try:
        return sd.InputStream(samplerate=RATE, channels=1, dtype="int16",
                              blocksize=int(RATE * passo), device=dev), RATE
    except sd.PortAudioError:
        taxa = int(sd.query_devices(dev, "input")["default_samplerate"])
        return sd.InputStream(samplerate=taxa, channels=1, dtype="int16",
                              blocksize=int(taxa * passo), device=dev), taxa


def gravar(timeout=10, limite=8, silencio=0.8):
    """Grava do microfone: espera você falar e para quando fica em silêncio."""
    passo = 0.05
    entrada, taxa = _abrir_microfone(passo)
    bloco = int(taxa * passo)
    with entrada as stream:
        ruido = np.mean([
            np.sqrt(np.mean(stream.read(bloco)[0].astype("float32") ** 2)) for _ in range(10)
        ])
        limiar = max(ruido * 3, 300)
        frames, falando, mudo = [], False, 0.0
        t0 = inicio = time.time()
        while True:
            dados, _ = stream.read(bloco)
            rms = np.sqrt(np.mean(dados.astype("float32") ** 2))
            if not falando:
                if rms > limiar:
                    falando, inicio = True, time.time()
                    frames.append(dados.copy())
                elif time.time() - t0 > timeout:
                    raise sr.WaitTimeoutError()
            else:
                frames.append(dados.copy())
                mudo = mudo + passo if rms < limiar else 0.0
                if mudo >= silencio or time.time() - inicio > limite:
                    break
    audio = np.concatenate(frames).ravel()
    if taxa != RATE:  # reamostra para 16 kHz, que é o que o reconhecimento espera
        n = int(len(audio) * RATE / taxa)
        audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype("int16")
    return sr.AudioData(audio.tobytes(), RATE, 2)


def escutar(r, modo_texto, timeout=10):
    """Devolve o texto falado/digitado, ou None se não entendeu nada."""
    try:
        if modo_texto:
            return input("Você: ").strip() or None
        audio = gravar(timeout=timeout)
        texto = r.recognize_google(audio, language="pt-BR")
        print("Ouvi:", texto)
        return texto
    except (sr.WaitTimeoutError, sr.UnknownValueError):
        return None
    except sr.RequestError as e:
        print("Erro no reconhecimento:", e)
        time.sleep(2)
        return None
    except sd.PortAudioError as e:
        print("Erro no microfone:", e, "(veja BIMO_MIC no .env e `python -m sounddevice`)")
        time.sleep(3)
        return None


def limpar_para_fala(t):
    """Tira markdown, links e emojis, que ficam estranhos na voz e na tela."""
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"^\s*[-•*]\s+", "", t, flags=re.M)
    t = re.sub(r"[*_`#>~|]", "", t)
    t = re.sub(r"[\U00010000-\U0010ffff\u2600-\u27bf]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def tirar_palavra(texto):
    """Devolve (ativou, resto). Só ativa se a palavra-chave estiver no texto."""
    for p in PALAVRAS:
        m = re.search(rf"\b{re.escape(p)}\b", texto.lower())
        if m:
            resto = f"{texto[:m.start()]} {texto[m.end():]}"
            return True, re.sub(r"\s+", " ", resto).strip(" ,.!?")
    return False, texto


FIM_FRASE = re.compile(r"(?<=[.!?…])\s+|\n+")


_aceita_extra = True  # vira False se a API recusar o parâmetro que desliga o raciocínio


def _pedido(client, mensagens, stream):
    global _aceita_extra
    extra = {}
    if _aceita_extra and not RACIOCINIO:
        if BACKEND == "hermes":
            extra["extra_body"] = {"model_options": {"reasoning": {"enabled": False}}}
        else:  # NVIDIA: modelos de raciocínio costumam aceitar isto
            extra["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
    try:
        return client.chat.completions.create(model=MODELO, messages=mensagens, stream=stream, **extra)
    except BadRequestError:
        if not extra:
            raise
        _aceita_extra = False  # não tenta de novo nas próximas perguntas
        return client.chat.completions.create(model=MODELO, messages=mensagens, stream=stream)


def _dizer(frase):
    global state, legenda
    frase = limpar_para_fala(frase)
    if frase:
        state, legenda = "speaking", frase
        falar(frase)


def _sem_think(t):
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S)


def responder(client, mensagens):
    """Pede a resposta e já vai falando frase por frase. Devolve o texto completo."""
    t0 = time.time()
    marcas = {}

    def dizer(frase):
        marcas.setdefault("primeira", time.time() - t0)
        _dizer(frase)

    completo, buf, pendente = "", "", ""
    if STREAM:
        try:
            for chunk in _pedido(client, mensagens, True):
                if not getattr(chunk, "choices", None):
                    continue  # eventos extras do Hermes (progresso de ferramenta)
                delta = chunk.choices[0].delta.content or ""
                if not delta:
                    continue
                completo += delta
                buf += delta
                if "<think>" in buf and "</think>" not in buf:
                    continue
                buf = _sem_think(buf)
                *prontas, buf = FIM_FRASE.split(buf)
                for p in prontas:
                    pendente += " " + p
                    if len(pendente.strip()) >= 15:
                        dizer(pendente)
                        pendente = ""
        except Exception as e:  # noqa: BLE001
            if not completo:
                print("Streaming falhou, tentando sem stream:", e)
                return _sem_stream(client, mensagens, t0)
            print("Resposta interrompida:", e)
        resto = f"{pendente} {_sem_think(buf)}"
        if resto.strip():
            dizer(resto)
    else:
        return _sem_stream(client, mensagens, t0)

    print(f"[tempo] primeira frase em {marcas.get('primeira', 0):.1f}s | total {time.time() - t0:.1f}s")
    return limpar_para_fala(_sem_think(completo))


def _sem_stream(client, mensagens, t0):
    resp = _pedido(client, mensagens, False)
    texto = limpar_para_fala(_sem_think(resp.choices[0].message.content or ""))
    print(f"[tempo] resposta completa em {time.time() - t0:.1f}s")
    if texto:
        _dizer(texto)
    return texto


def cerebro(modo_texto):
    global state, legenda, modo
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=120)
    historico = []
    r = sr.Recognizer()

    while True:
        state, legenda = "waiting", f'Diga "{PALAVRAS[0].upper()}"'
        texto = escutar(r, modo_texto)
        if not texto:
            continue
        ativou, comando = tirar_palavra(texto)
        if not ativou:
            continue  # sem palavra-chave: ignora e NÃO chama o modelo

        if not comando:  # só disse o nome: espera o pedido
            state, legenda = "listening", "Ouvindo..."
            comando = escutar(r, modo_texto, timeout=8)
            if not comando:
                continue

        novo = detectar_modo(comando)  # troca de tela é local: não chama a IA
        if novo:
            modo = novo
            _dizer(MENSAGENS[novo])
            continue

        state, legenda = "thinking", "Pensando..."
        historico.append({"role": "user", "content": comando})
        mensagens = [{"role": "system", "content": SISTEMA}] + historico[-10:]
        try:
            fala = responder(client, mensagens)
        except Exception as e:  # noqa: BLE001
            legenda = "Erro ao falar com o modelo"
            print("Erro na API:", e)
            historico.pop()
            time.sleep(2)
            continue

        if not fala:
            legenda = "O modelo não respondeu"
            historico.pop()
            continue
        historico.append({"role": "assistant", "content": fala})
        print("Robô:", fala)


TECLAS_MODO = {pygame.K_r: "relogio", pygame.K_f: "rosto", pygame.K_b: "ambos"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--texto", action="store_true", help="digitar em vez de usar o microfone")
    ap.add_argument("--fullscreen", action="store_true", help="tela cheia (Pi)")
    args = ap.parse_args()

    if not API_KEY:
        var = "HERMES_API_KEY" if BACKEND == "hermes" else "NVIDIA_API_KEY"
        raise SystemExit(f"Falta a chave: defina {var} no arquivo .env")

    threading.Thread(target=cerebro, args=(args.texto,), daemon=True).start()

    pygame.display.init()
    pygame.font.init()

    if LINUX and ARM:
        # Raspberry Pi + LCD ILI9486
        tela = pygame.Surface((W, H))
        fb = Framebuffer("/dev/fb1", W, H)
    else:
        pygame.display.set_caption("Bimo")
        tela = pygame.display.set_mode(
            (W, H),
            pygame.FULLSCREEN if args.fullscreen else 0
        )
        fb = None

    if args.fullscreen:
        pygame.mouse.set_visible(False)

    global modo
    if ESTILO == "retro":
        rosto = RostoRetro()
    elif ESTILO == "fofo":
        rosto = Rosto(COR, FUNDO)
    else:
        rosto = RostoBMO()
    relogio = RelogioBMO()
    fonte = pygame.font.SysFont(None, 22)
    clock = pygame.time.Clock()

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                return
            if e.type == pygame.KEYDOWN and e.key in TECLAS_MODO:
                modo = TECLAS_MODO[e.key]

        m = modo  # cópia: a voz pode trocar o modo no meio do desenho
        if m == "relogio":
            relogio.desenhar(tela, state)
        else:
            rosto.desenhar(tela, state)
            if m == "ambos":
                relogio.mini(tela)
        cor_legenda = relogio.cor_legenda if m == "relogio" else rosto.cor_legenda

        #for i, linha in enumerate(textwrap.wrap(legenda, 55)[:2]):
        #   img = fonte.render(linha, True, cor_legenda)
        #   tela.blit(img, (W // 2 - img.get_width() // 2, 280 + i * 20))

        if fb:
            fb.show(tela)
        else:
            pygame.display.flip()

        clock.tick(FPS)


if __name__ == "__main__":
    main()
