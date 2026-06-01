from fastapi import FastAPI, Response

# Fournir un `app` au niveau supérieur afin que Vercel détecte l'entrypoint.
app = FastAPI()

try:

	from backend.app import app as _backend_app
	app = _backend_app
except Exception:
	import traceback
	tb = traceback.format_exc()

	@app.get("/{full_path:path}", include_in_schema=False)
	async def _import_error(full_path: str = ""):
		content = (
			"IMPORT_ERROR\n\n"
			"L'import de 'backend.app' a échoué sur cette instance.\n\n"
			"Traceback:\n\n"
			f"{tb}"
		)
		return Response(content=content, media_type="text/plain", status_code=500)
