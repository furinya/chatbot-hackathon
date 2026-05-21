def parse_message(message):

    text = message.lower().strip()

    # COMANDOS PRINCIPAIS
    if "criar" in text or "crie" in text:
        return {
            "type": "COMMAND",
            "intent": "CREATE_LEAD"
        }

    if "continuar cadastro" in text:
        return {
            "type": "COMMAND",
            "intent": "CONTINUE_LEAD"
        }

    if "atualize" in text:
        return {
            "type": "COMMAND",
            "intent": "UPDATE_LEAD"
        }

    if "status" in text or "mover" in text:
        return {
            "type": "COMMAND",
            "intent": "CHANGE_STATUS"
        }

    # OPÇÕES NUMÉRICAS
    if text.isdigit():
        return {
            "type": "OPTION",
            "value": int(text)
        }

    return {
        "type": "UNKNOWN"
    }