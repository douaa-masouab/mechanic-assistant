"""
Entrée Vercel : tenter d'importer l'application FastAPI principale.
Si l'import échoue (erreur sur Vercel), fournir une app minimale qui
retourne la trace pour faciliter le debug du déploiement.

ATTENTION: la trace complète est renvoyée pour débogage. Retirer
ou limiter cette sortie en production publique.
"""
try:
	from backend.app import app
except Exception:
	import traceback
	tb = traceback.format_exc()

	from fastapi import FastAPI, Response

	app = FastAPI()

	@app.get("/{full_path:path}", include_in_schema=False)
	async def _import_error(full_path: str = ""):
		content = (
			"IMPORT_ERROR\n\n"
			"L'import de 'backend.app' a échoué sur cette instance.\n\n"
			"Traceback:\n\n"
			f"{tb}"
		)
		return Response(content=content, media_type="text/plain", status_code=500)
