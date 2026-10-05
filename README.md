# Como rodar o robô (Bimo) no Raspberry Pi

Fluxo: **microfone → texto → IA → voz**, com um rosto animado.
O robô só chama a IA depois que você diz **"Bimo"**.

---

## 0. Antes de começar

Você precisa de:

- Raspberry Pi OS com ou sem desktop
- Microfone USB e saída de áudio
- Telinha 3,5": instale antes o driver dela (`LCD35-show`).
  Em Linux/ARM o `robo.py` desenha direto em `/dev/fb1`.
- Uma chave de IA. Há duas opções, definidas por `BIMO_BACKEND` no `.env`:
  - **`nvidia`** (padrão): chave `nvapi-...` da NVIDIA
  - **`hermes`**: o Hermes Agent precisa estar rodando (veja o passo 6)

Arquivos da pasta `~/robo-face`:

```
robo-face/
├── robo.py            # programa principal
├── rosto.py           # desenho do rosto (BMO, retro, fofo) e do relógio
├── comandos.py        # comandos de voz para trocar a tela
├── teste_rosto_bmo.py # teste visual SEM IA (só pygame)
├── framebuffer.py     # saída para a telinha LCD
├── instalar_pi.sh     # instalador
├── .env.example       # modelo de configuração
└── .env               # sua configuração (NÃO compartilhe)
```

> **Atenção:** o `.env` contém chaves reais. Nunca envie o arquivo para ninguém
> nem suba para o GitHub.

---

## 1. Instalar

```bash
cd ~/robo-face
bash instalar_pi.sh
```

O script:

1. instala os pacotes do sistema (`python3-venv`, `python3-pygame`, `python3-numpy`, `libportaudio2`, `espeak-ng`, `flac`)
2. adiciona seu usuário aos grupos `video` e `audio` (acesso ao LCD e ao áudio)
3. cria a `.venv` com `--system-site-packages`
4. cria o `requirements-pi.txt` (se não existir) e instala: `openai`, `python-dotenv`, `SpeechRecognition`, `sounddevice`, `standard-aifc`, `audioop-lts`
5. cria o `.env` a partir do `.env.example`
6. pergunta se o Bimo deve iniciar junto com a área de trabalho

Ao terminar, **reinicie o Pi** para os grupos valerem:

```bash
sudo reboot
```

---

## 2. Configurar o `.env`

```bash
cd ~/robo-face
nano .env
```

Para usar a **NVIDIA**:

```ini
NVIDIA_API_KEY=nvapi-cole_sua_chave_aqui
NVIDIA_MODEL=nvidia/nemotron-3-super-120b-a12b
BIMO_COR=00DCFF
BIMO_ESTILO=bmo
BIMO_MODO=rosto
```

Se o seu `.env` tiver `BIMO_BACKEND=hermes`, o robô fala com o Hermes e **não**
com a NVIDIA. Ou remova essa linha, ou siga o passo 6.

---

## 3. Testar por partes

Teste cada peça antes de rodar tudo junto:

```bash
# voz
espeak-ng -v pt-br "olá, eu sou o Bimo"

# lista os microfones
.venv/bin/python -m sounddevice

# só o cérebro, digitando (sem microfone)
.venv/bin/python robo.py --texto
```

Se o microfone certo não for o padrão, coloque o número dele no `.env`:

```ini
BIMO_MIC=1
```

---

## 4. Rodar

```bash
cd ~/robo-face
DISPLAY=:0 .venv/bin/python robo.py --fullscreen
```

Para sair: `Ctrl+C` no terminal.

Se você ativou o início automático no instalador, o Bimo sobe sozinho quando a
área de trabalho carregar.

---

## 5. Como usar (palavra de ativação)

| Você diz | O que acontece |
|---|---|
| "Bimo, que horas são?" | Responde direto |
| "Bimo" (sozinho) | Os olhos abrem e ele espera o seu pedido |
| Qualquer frase sem "Bimo" | Ignorada (não gasta tokens) |

O terminal mostra `Ouvi: ...` para cada frase. Se ele não acordar, veja como o
reconhecimento escreveu "bimo" e adicione essa variação:

```ini
WAKE_WORDS=bimo,bemo,vimo,bimu,ok
```

### Trocar a tela por voz (rosto / relógio / os dois)

Funciona como qualquer pedido: diga **"Bimo"** e depois o comando. É resolvido
no próprio robô, **sem chamar a IA** (não gasta tokens).

| Você diz | Tela |
|---|---|
| "Bimo, mostra o relógio" / "modo relógio" | relógio grande (hora, data e barra dos segundos) |
| "Bimo, volta pro rosto" / "mostra a carinha" | só o rosto |
| "Bimo, os dois" / "ambos" / "rosto e relógio" | rosto com a hora pequena no topo |

Frases com mais de 7 palavras vão para a IA (assim uma pergunta normal sobre
relógios não vira comando). As palavras podem ser trocadas no `.env`:

```ini
BIMO_PALAVRAS_RELOGIO=relogio
BIMO_PALAVRAS_ROSTO=rosto,carinha,face
BIMO_PALAVRAS_AMBOS=ambos,os dois,juntos
```

No PC também dá pra trocar pelo teclado: **R** relógio, **F** rosto, **B** os dois.
Para testar só o visual, sem IA nem microfone: `python teste_rosto_bmo.py`.

### Estados do rosto

| Estado | O que acontece |
|---|---|
| Esperando a palavra | olhos quase fechados, sorriso |
| Ouvindo | olhos mais abertos |
| Pensando | olhos se mexem de lado |
| Falando | boca abre e fecha |

### Ajustes rápidos no `.env`

| Variável | Para que serve |
|---|---|
| `BIMO_ESTILO` | `bmo` (padrão), `retro` ou `fofo` |
| `BIMO_MODO` | tela ao ligar: `rosto`, `relogio` ou `ambos` |
| `BIMO_SUAVE` | bordas do rosto BMO: `1` leve (padrão no Pi), `2` mais suave (padrão no PC) |
| `BIMO_COR` | cor do rosto em hexadecimal (ex.: `FF7AC8` rosa) |
| `BIMO_ESTILO` | `retro` (padrão) ou `fofo` |
| `BIMO_FPS` | quadros por segundo (padrão no Pi: 20) |
| `BIMO_VOZ_VEL` | velocidade da voz (padrão: 160) |
| `BIMO_STREAM` | `1` = fala frase por frase enquanto a resposta chega |
| `BIMO_RACIOCINIO` | `1` = deixa o modelo "pensar" mais (mais lento) |

---

## 6. Usar o Hermes Agent em vez da NVIDIA

1. Na máquina onde o Hermes roda, edite `~/.hermes/.env`:

   ```ini
   API_SERVER_ENABLED=true
   API_SERVER_KEY=uma-chave-longa-com-16-ou-mais-caracteres
   ```

2. Inicie o Hermes:

   ```bash
   hermes gateway
   ```

   Deve aparecer `API server listening on http://127.0.0.1:8642`.

3. No `.env` do robô:

   ```ini
   BIMO_BACKEND=hermes
   HERMES_API_KEY=uma-chave-longa-com-16-ou-mais-caracteres
   LLM_BASE_URL=http://localhost:8642/v1
   ```

**Hermes em outra máquina** (o robô no Pi e o Hermes no PC, por exemplo):
no Pi, `localhost` aponta para o próprio Pi. Coloque `API_SERVER_HOST=0.0.0.0`
no `.env` do Hermes e use o IP real no `.env` do robô:

```ini
LLM_BASE_URL=http://IP_DA_MAQUINA:8642/v1
```

> Cuidado: essa API dá acesso às ferramentas do agente, inclusive terminal.
> Use apenas em rede de confiança.

---

## 7. Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `Permission denied` em `/dev/fb1` | Usuário fora do grupo `video` | `sudo usermod -aG video,audio $USER` e reinicie |
| Tela do LCD em branco | Driver não instalado | Instale o `LCD35-show`; confira com `ls -l /dev/fb1` |
| `ModuleNotFoundError` | Dependência faltando | `.venv/bin/pip install -r requirements-pi.txt` |
| Sem voz | `espeak-ng` não instalado | `sudo apt install espeak-ng` |
| Não ouve nada | Microfone errado | `.venv/bin/python -m sounddevice` e defina `BIMO_MIC` |
| Não acorda com "Bimo" | Reconhecimento escreveu outra grafia | Ajuste `WAKE_WORDS` |
| Não responde com `BIMO_BACKEND=hermes` | Hermes parado ou `localhost` errado | Passo 6 |
