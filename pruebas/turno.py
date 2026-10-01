"""Un turno contra el agente: llamadas a guardrails y lo que queda en la sesion."""
import asyncio, logging, sys
logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s")
logging.getLogger("google_adk").setLevel(logging.ERROR)

from google.adk.runners import InMemoryRunner
from google.genai import types
from bank_agents.shared import protec_tools as pt
from bank_agents import memoria as mem
from bank_agents.agent import root_agent

registro = []

def espiar(mod):
    orig = mod.evaluar
    async def espia(mensajes, punto="?"):
        v = await orig(mensajes, punto=punto)
        registro.append(f"{punto}:{'CORTA' if v and v['bloqueado'] else 'pasa'}")
        return v
    mod.evaluar = espia

espiar(pt); espiar(mem)
TEXTO = " ".join(sys.argv[1:]) or "Hola, cual es mi saldo?"
APP, USR = "lab-guardrails", "cliente-local-1"

async def main():
    r = InMemoryRunner(agent=root_agent, app_name=APP)
    s = await r.session_service.create_session(app_name=APP, user_id=USR)
    inv = set()
    async for ev in r.run_async(user_id=USR, session_id=s.id,
            new_message=types.Content(role="user", parts=[types.Part(text=TEXTO)])):
        inv.add(ev.invocation_id)
        if ev.content and ev.content.parts:
            for p in ev.content.parts:
                if getattr(p, "text", None):
                    print("[agente]", p.text.strip()[:300])
    s2 = await r.session_service.get_session(app_name=APP, user_id=USR, session_id=s.id)
    print("\n-> llamadas:", registro)
    print("-> en la sesion:")
    for g in (s2.state.get("guardrails") or []):
        print(f"   punto={g['punto']} detectores={g['detectores']} "
              f"bloqueado={g['bloqueado']} turno_actual={g['inv'] in inv}")

asyncio.run(main())
