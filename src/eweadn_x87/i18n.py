"""Traduções: os textos ficam em português no código e tr() devolve o inglês quando ativo."""

import json
import os

CONFIG = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
                      "eweadn-x87", "settings.json")

LANGS = ("auto", "pt", "en")
_lang = "pt"


def system_language():
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var, "")
        if val:
            return "pt" if val.lower().startswith("pt") else "en"
    return "en"


def set_language(choice):
    """choice: 'auto', 'pt' ou 'en'."""
    global _lang
    _lang = system_language() if choice not in ("pt", "en") else choice


def language():
    return _lang


def saved_choice():
    try:
        with open(CONFIG) as f:
            return json.load(f).get("lang", "auto")
    except (OSError, ValueError):
        return "auto"


def tr(text):
    return EN.get(text, text) if _lang == "en" else text


EN = {
    # ----- efeitos de luz -----
    "Desligado": "Off",
    "Estático": "Static",
    "Ponto único aceso": "Single key on",
    "Ponto único apagado": "Single key off",
    "Estrelas": "Starry sky",
    "Neve caindo": "Snowfall",
    "Flores variadas": "Blooming flowers",
    "Respiração": "Breathing",
    "Ciclo espectral": "Spectrum cycle",
    "Jatos coloridos": "Color fountain",
    "Cores em movimento": "Moving colors",
    "Ondas": "Waves",
    "Curvas e recuos": "Twists and turns",
    "Pronto para disparar": "One touch to fire",
    "Dois pássaros": "Two birds",
    "Ondas de expansão": "Ripples",
    "Fluxo contínuo": "Endless flow",
    "Montanhas em camadas": "Layered mountains",
    "Chuva leve": "Gentle rain",
    "Ida e volta": "Back and forth",
    "Momento emocionante": "Heartbeat",
    # ----- teclas -----
    "Espaço": "Space",
    "Shift D": "R Shift",
    "Alt D": "R Alt",
    "Ctrl D": "R Ctrl",
    "Ctrl esq.": "Left Ctrl",
    "Shift esq.": "Left Shift",
    "Alt esq.": "Left Alt",
    "Win esq.": "Left Win",
    "Ctrl dir.": "Right Ctrl",
    "Shift dir.": "Right Shift",
    "Alt dir.": "Right Alt (AltGr)",
    "Win dir.": "Right Win",
    "Tecla extra ABNT2 (ao lado do Shift esq.)": "Extra ABNT2 key (next to Left Shift)",
    "Tecla extra ABNT2 (ao lado do Shift dir.)": "Extra ABNT2 key (next to Right Shift)",
    "Reproduzir/Pausar": "Play/Pause",
    "Parar": "Stop",
    "Anterior": "Previous track",
    "Próxima": "Next track",
    "Silenciar": "Mute",
    "Calculadora": "Calculator",
    "Meu computador": "My computer",
    "Multimídia": "Media player",
    "Navegador: início": "Browser: home",
    "Navegador: atualizar": "Browser: refresh",
    "Navegador: avançar": "Browser: forward",
    "Navegador: voltar": "Browser: back",
    "Favoritos": "Favorites",
    "Pesquisar": "Search",
    "Mouse: botão esquerdo": "Mouse: left button",
    "Mouse: botão direito": "Mouse: right button",
    "Mouse: botão do meio": "Mouse: middle button",
    "Mouse: voltar": "Mouse: back",
    "Mouse: avançar": "Mouse: forward",
    "Mouse: rolar para cima": "Mouse: scroll up",
    "Mouse: rolar para baixo": "Mouse: scroll down",
    "Mídia 0x{:03x}": "Media 0x{:03x}",
    "Ação {}": "Action {}",
    # ----- erros -----
    "Teclado X87 não encontrado (dongle 2.4G ou cabo).": "X87 keyboard not found (2.4G dongle or cable).",
    "Sem permissão para abrir {}.": "No permission to open {}.",
    "Sem resposta do teclado (cmd 0x{:02x}). Ele está ligado?":
        "No response from the keyboard (cmd 0x{:02x}). Is it turned on?",
    "Fn+F1…F12 são fixas de fábrica.": "Fn+F1…F12 are fixed factory functions.",
    "Erro: {}": "Error: {}",
    # ----- linha de comando -----
    "Configura o teclado EWEADN X87 no Linux.": "Configure the EWEADN X87 keyboard on Linux.",
    "bateria, firmware e configuração atual": "battery, firmware and current settings",
    "iluminação": "lighting",
    "número do efeito (veja 'efeitos')": "effect number (see 'effects')",
    "cor em hex, ex.: ff0080": "hex color, e.g. ff0080",
    "brilho de 1 a 5": "brightness from 1 to 5",
    "velocidade de 1 a 5": "speed from 1 to 5",
    "lista os efeitos de luz": "list lighting effects",
    "tempo de sono em minutos (0 = desligado)": "sleep time in minutes (0 = off)",
    "lista teclas remapeadas": "list remapped keys",
    "volta todas as teclas (normal e Fn) ao padrão": "reset all keys (normal and Fn) to default",
    "Conexão:   {}": "Connection: {}",
    "2.4G (dongle)": "2.4G (dongle)",
    "cabo": "cable",
    "Bateria:   {}%": "Battery:    {}%",
    "Firmware:  {}": "Firmware:   {}",
    "Sono:      {}": "Sleep:      {}",
    "{} min": "{} min",
    "desligado": "off",
    "Luz:       {}, cor #{}, {}, brilho {}/{}, velocidade {}/{}":
        "Lighting:   {}, color #{}, {}, brightness {}/{}, speed {}/{}",
    "colorido": "rainbow",
    "cor única": "single color",
    "Sono: {}": "Sleep: {}",
    "Normal:": "Normal:",
    "Com Fn:": "With Fn:",
    "  nada remapeado": "  nothing remapped",
    "Teclas e camada Fn restauradas.": "Keys and Fn layer reset.",
    # ----- interface -----
    "Status": "Status",
    "Iluminação": "Lighting",
    "Teclas": "Keys",
    "Ajustes": "Settings",
    "Ler do teclado": "Read from keyboard",
    "Seguir o sistema": "Follow system",
    "Claro": "Light",
    "Escuro": "Dark",
    "Aparência": "Appearance",
    "Idioma": "Language",
    "Automático": "Automatic",
    "Menu": "Menu",
    "Desconectado": "Disconnected",
    "Conectando…": "Connecting…",
    "Conectado": "Connected",
    "Atualiza a cada 30 segundos": "Updates every 30 seconds",
    "Aparelho": "Device",
    "Conexão": "Connection",
    "Sem fio 2.4G (dongle)": "Wireless 2.4G (dongle)",
    "Cabo USB": "USB cable",
    "Pré-visualização aproximada. Nos efeitos que reagem às teclas, digite com o app em foco para ver.":
        "Approximate preview. For effects that react to keys, type with the app focused to see them.",
    "Efeito": "Effect",
    "Colorido (arco-íris)": "Rainbow",
    "Desligado usa a cor escolhida abaixo": "When off, uses the color chosen below",
    "Cor": "Color",
    "Ajustes do efeito": "Effect settings",
    "Brilho": "Brightness",
    "Velocidade": "Speed",
    "Inverter direção": "Reverse direction",
    "Clique numa tecla para mudar o que ela faz, sozinha ou com Fn.":
        "Click a key to change what it does, on its own or with Fn.",
    "remapeada": "remapped",
    "tem função Fn": "has Fn function",
    "Restaurar": "Reset",
    "Restaurar teclas normais": "Reset normal keys",
    "Restaurar funções Fn": "Reset Fn functions",
    "Restaurar tudo": "Reset everything",
    "Tecla Fn": "Fn key",
    "Modo de sono": "Sleep mode",
    "Minutos sem uso até o teclado dormir. Desligar pode evitar que a conexão 2.4G caia, "
    "mas gasta mais bateria.":
        "Idle minutes before the keyboard sleeps. Turning it off may keep the 2.4G link from "
        "dropping, but uses more battery.",
    "Ativar modo de sono": "Enable sleep mode",
    "Minutos": "Minutes",
    "Aplicar": "Apply",
    "Gravar no teclado": "Save to keyboard",
    "Setas e navegação": "Arrows and navigation",
    "Letras, números e símbolos": "Letters, numbers and symbols",
    "Teclas F": "F keys",
    "Modificadores": "Modifiers",
    "Mídia e sistema": "Media and system",
    "Teclado numérico": "Numeric keypad",
    "↑  Seta para cima": "↑  Up arrow",
    "↓  Seta para baixo": "↓  Down arrow",
    "←  Seta para a esquerda": "←  Left arrow",
    "→  Seta para a direita": "→  Right arrow",
    "não existe no X87, só no ABNT2": "not on the X87, ABNT2 layouts only",
    "tecla física {}": "physical key {}",
    "com Shift: {}   ·   {}": "with Shift: {}   ·   {}",
    "No seu layout digita: {}": "Types on your layout: {}",
    "  (Shift: {})": "  (Shift: {})",
    "Tecla {}": "Key {}",
    "função de fábrica": "factory function",
    "padrão": "default",
    "atual: {}": "current: {}",
    "Ao apertar {}": "When pressing {}",
    "Ao apertar Fn + {}": "When pressing Fn + {}",
    "Fn + F1…F12 são funções de fábrica": "Fn + F1…F12 are factory functions",
    "ou escolha na lista abaixo": "or pick from the list below",
    "Aperte a tecla que {} deve virar": "Press the key {} should become",
    "Voltar à função de fábrica": "Back to factory function",
    "Voltar ao padrão": "Back to default",
    "Buscar função…": "Search function…",
    "Essa tecla não pode ser capturada, escolha na lista": "That key can't be captured, pick it from the list",
    "Teclas restauradas": "Keys reset",
    "Sono: {} min": "Sleep: {} min",
    "Modo de sono desligado": "Sleep mode off",
}

set_language(saved_choice())
