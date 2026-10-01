# Prompt inicial para Claude Code (pegar en `claude`, dentro de la carpeta del repositorio)

```text
Vamos a levantar este laboratorio en este Debian siguiendo CLAUDE.md, paso a paso y
en orden. Reglas:
- No leas, imprimas ni edites el .env; cuando haga falta una clave, dime que la pegue
  yo con nano .env y espera a que te confirme.
- No inventes nombres de modelo: usa make modelos.
- En cada paso dime en una linea que vas a hacer, ejecutalo y confirma el criterio de
  exito de CLAUDE.md antes de pasar al siguiente. Si algo falla, diagnostica con
  make logs y la documentacion oficial, corrige y vuelve a probar.
- Usa LLM_PROVIDER=<gemini|openai> con el modelo <nombre del modelo>.
Empieza por el paso 1 (Docker).
```

## Prompts utiles despues

- `Cambia el proveedor a openai con el modelo <X>, vuelve a levantar y corre make humo.`
- `Los turnos tardan mas de 30 segundos: revisa make logs y dime si es cuota del modelo.`
- `Muestrame las ultimas detecciones de AI Guardrails con make guard-logs y explicamelas.`
- `Cambia al perfil endurecido, vuelve a levantar y compara make ataques con el vulnerable.`
