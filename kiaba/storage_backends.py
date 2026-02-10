"""
Storage backends pour compatibilité Supabase / S3.
Supabase rejette application/octet-stream : on force le Content-Type selon l'extension.
"""
import mimetypes

from storages.backends.s3boto3 import S3Boto3Storage


# Extensions courantes pour les médias (images) — Supabase accepte ces MIME types
MEDIA_EXTENSION_TO_CONTENT_TYPE = {
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
}


def get_content_type_for_name(name, content=None):
    """Retourne un Content-Type valide pour Supabase (jamais application/octet-stream)."""
    if content is not None:
        ct = getattr(content, "content_type", None)
        if ct and ct != "application/octet-stream" and ct.startswith("image/"):
            return ct
    if name:
        ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext in MEDIA_EXTENSION_TO_CONTENT_TYPE:
            return MEDIA_EXTENSION_TO_CONTENT_TYPE[ext]
        guessed, _ = mimetypes.guess_type(name)
        if guessed and guessed.startswith("image/"):
            return guessed
    return "image/jpeg"


class _ContentTypeWrapper:
    """Wrapper qui expose un content_type correct pour que le backend S3 l'envoie à Supabase."""

    def __init__(self, content, content_type):
        self._content = content
        self.content_type = content_type

    def __getattr__(self, name):
        return getattr(self._content, name)


class SupabaseS3Storage(S3Boto3Storage):
    """
    S3Boto3Storage qui force un Content-Type accepté par Supabase (pas application/octet-stream).
    Corrige l'erreur "mime type application/octet-stream is not supported" sur filigrane/thumbnail.
    """

    # Éviter le défaut application/octet-stream que Supabase rejette
    default_content_type = "image/jpeg"

    def _save(self, name, content):
        ct = get_content_type_for_name(name, content)
        content = _ContentTypeWrapper(content, ct)
        return super()._save(name, content)

    def _get_write_parameters(self, name, content=None):
        params = super()._get_write_parameters(name, content)
        if params.get("ContentType") == "application/octet-stream" or "ContentType" not in params:
            params["ContentType"] = get_content_type_for_name(name, content)
        return params
