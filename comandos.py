"""Comandos de voz locais para trocar o que aparece na tela (não gastam IA).

Exemplos:  "Bimo, mostra o relógio"  |  "Bimo, volta pro rosto"  |  "Bimo, os dois"
Palavras configuráveis no .env (separadas por vírgula, sem se preocupar com acento):
    BIMO_PALAVRAS_RELOGIO=relogio
    BIMO_PALAVRAS_ROSTO=rosto,carinha,face
    BIMO_PALAVRAS_AMBOS=ambos,os dois,juntos
"""
import os
import re
import unicodedata

MAX_PALAVRAS = 7  # frases longas vão para a IA (assim uma pergunta normal não vira comando)

MENSAGENS = {
    "rosto": "Mostrando o rosto.",
    "relogio": "Mostrando o relógio.",
    "ambos": "Mostrando o rosto e o relógio.",
}


def _norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip()


def _lista(nome, padrao):
    return [_norm(p) for p in os.environ.get(nome, padrao).split(",") if p.strip()]


RELOGIO = _lista("BIMO_PALAVRAS_RELOGIO", "relogio")
ROSTO = _lista("BIMO_PALAVRAS_ROSTO", "rosto,carinha,face")
AMBOS = _lista("BIMO_PALAVRAS_AMBOS", "ambos,os dois,juntos")


def _tem(lista, t):
    return any(re.search(rf"\b{re.escape(p)}\b", t) for p in lista)


def detectar_modo(texto):
    """Devolve 'rosto', 'relogio', 'ambos' ou None (se não for um comando de tela)."""
    t = _norm(texto)
    if not t or len(t.split()) > MAX_PALAVRAS:
        return None
    if _tem(AMBOS, t):
        return "ambos"
    r, c = _tem(RELOGIO, t), _tem(ROSTO, t)
    if r and c:
        return "ambos"
    if r:
        return "relogio"
    if c:
        return "rosto"
    return None
