from fastapi import FastAPI, Request, Header, HTTPException
from pydantic import BaseModel
import os

from parser import parse_message
from database import leads
from sessions import sessions
from history import history
from required_fields import required_fields
from status import statuses, status_options
from rules import optional_fields

app = FastAPI()

# TOKEN VIA RAILWAY VARIABLES
API_TOKEN = os.getenv("API_TOKEN")


class ChatRequest(BaseModel):
    user: str
    message: str


# =========================
# CHAT INTERNO
# =========================
@app.post("/chat")
def chat(data: ChatRequest):

    parsed = parse_message(data.message)

    # PROTEÇÃO CONTRA RETORNO VAZIO
    if not parsed:
        return {
            "message": "Não consegui entender sua solicitação"
        }

    intent = parsed.get("intent")
    msg_type = parsed.get("type")

    user = data.user

    # VERIFICA SE EXISTE SESSÃO
    if user in sessions:

        session = sessions[user]

        # =========================
        # CONTINUE FILL
        # =========================
        if session["step"] == "CONTINUE_FILL":

            current_field = session["missing_fields"][0]

            session["lead"][current_field] = data.message

            session["missing_fields"].pop(0)

            if len(session["missing_fields"]) == 0:

                session["lead"]["status"] = "NOVO"

                history.append({
                    "lead_id": session["lead"]["id"],
                    "user": user,
                    "action": "COMPLETE_PRE_CADASTRO"
                })

                sessions.pop(user)

                return {
                    "success": True,
                    "message": "Cadastro concluído com sucesso"
                }

            next_field = session["missing_fields"][0]

            return {
                "message": f"Agora preciso do campo: {next_field}"
            }

        # =========================
        # CREATE LEAD
        # =========================
        if session["step"] == "CREATE_LEAD":

            current_field = session["missing_fields"][0]

            session["data"][current_field] = data.message

            session["missing_fields"].pop(0)

            # TERMINOU CADASTRO
            if len(session["missing_fields"]) == 0:

                filled_optional = any(
                    field in session["data"]
                    for field in optional_fields
                )

                status = "NOVO"

                if not filled_optional:
                    status = "EM_PRE_CADASTRO"

                new_lead = {
                    "id": len(leads) + 1,
                    **session["data"],
                    "status": status,
                    "responsavel": user
                }

                leads.append(new_lead)

                history.append({
                    "lead_id": new_lead["id"],
                    "user": user,
                    "action": "CREATE_LEAD"
                })

                sessions.pop(user)

                return {
                    "success": True,
                    "message": "Lead criado com sucesso",
                    "lead": new_lead
                }

            next_field = session["missing_fields"][0]

            return {
                "message": f"Agora preciso do campo: {next_field}"
            }

        # =========================
        # OPÇÕES NUMÉRICAS
        # =========================
        if msg_type == "OPTION":

            # CONTINUAR CADASTRO
            if session["step"] == "CONTINUE_SELECT_LEAD":

                option = parsed["value"] - 1

                selected = session["options"][option]

                missing_optional = [
                    field for field in optional_fields
                    if field not in selected
                ]

                sessions[user] = {
                    "step": "CONTINUE_FILL",
                    "lead": selected,
                    "missing_fields": missing_optional
                }

                return {
                    "message": f"Agora preciso do campo: {missing_optional[0]}"
                }

            # ESCOLHA DE LEAD
            if session["step"] == "SELECT_LEAD":

                option = parsed["value"] - 1

                selected = session["options"][option]

                sessions[user] = {
                    "step": "SELECT_ACTION",
                    "lead": selected
                }

                return {
                    "message": f"Lead selecionado: {selected['nome do lead']}",
                    "options": [
                        "1. Atualizar lead existente",
                        "2. Registrar observação",
                        "3. Alterar status",
                        "4. Agendar retorno"
                    ]
                }

            # ESCOLHA DA AÇÃO
            if session["step"] == "SELECT_ACTION":

                if parsed["value"] == 1:

                    sessions[user] = {
                        "step": "SELECT_STATUS",
                        "lead": session["lead"]
                    }

                    return {
                        "message": "Escolha o novo status",
                        "options": status_options
                    }

            # ESCOLHA DO STATUS
            if session["step"] == "SELECT_STATUS":

                new_status = statuses.get(parsed["value"])

                lead = session["lead"]

                lead["status"] = new_status

                # SALVA HISTÓRICO
                history.append({
                    "lead_id": lead["id"],
                    "user": user,
                    "action": "CHANGE_STATUS",
                    "new_status": new_status,
                    "lead_name": lead["nome do lead"]
                })

                # FINALIZA SESSÃO
                sessions.pop(user)

                return {
                    "success": True,
                    "message": f"Lead atualizado para {new_status}"
                }

    # =========================
    # CONTINUE LEAD
    # =========================
    if intent == "CONTINUE_LEAD":

        found = [
            lead for lead in leads
            if lead["status"] == "EM_PRE_CADASTRO"
        ]

        if len(found) == 0:
            return {
                "message": "Nenhum pré-cadastro encontrado"
            }

        sessions[user] = {
            "step": "CONTINUE_SELECT_LEAD",
            "options": found
        }

        return {
            "message": "Selecione o lead para continuar cadastro",
            "options": [
                f"{i+1}. {lead['nome do lead']}"
                for i, lead in enumerate(found)
            ]
        }

    # =========================
    # UPDATE LEAD
    # =========================
    if intent == "UPDATE_LEAD":

        found = [
            lead for lead in leads
            if "joão silva" in lead["nome do lead"].lower()
        ]

        if len(found) > 1:

            sessions[user] = {
                "step": "SELECT_LEAD",
                "options": found
            }

            return {
                "message": "Encontrei múltiplos leads",
                "options": [
                    f"{i+1}. {lead['nome do lead']} - {lead['empreendimento']}"
                    for i, lead in enumerate(found)
                ]
            }

    # =========================
    # CREATE LEAD
    # =========================
    if intent == "CREATE_LEAD":

        sessions[user] = {
            "step": "CREATE_LEAD",
            "data": {},
            "missing_fields": required_fields.copy()
        }

        first_field = sessions[user]["missing_fields"][0]

        return {
            "message": f"Para criar o lead preciso do campo: {first_field}"
        }

    return {
        "message": "Comando não reconhecido"
    }


# =========================
# WEBHOOK EXTERNO
# =========================
@app.post("/webhook")
async def webhook(
    request: Request,
    authorization: str = Header(None)
):

    # VALIDA TOKEN
    if authorization != API_TOKEN:

        raise HTTPException(
            status_code=401,
            detail="Token inválido"
        )

    body = await request.json()

    user = body.get("user", "external_user")
    message = body.get("message", "")

    response = chat(ChatRequest(
        user=user,
        message=message
    ))

    return response


# =========================
# HISTÓRICO
# =========================
@app.get("/history")
def get_history():

    return history