from django.db import models
from django.conf import settings
from ads.models import Ad


class Report(models.Model):
    class Reason(models.TextChoices):
        SPAM        = "spam",        "Spam / annonce dupliquée"
        FAKE        = "fake",        "Fausse annonce / arnaque"
        UNDERAGE    = "underage",    "Personne mineure"
        VIOLENCE    = "violence",    "Violence / contenu choquant"
        PROSTITUTION = "prostitution", "Prostitution / traite"
        OTHER       = "other",       "Autre"

    ad         = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="reports")
    reporter   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="submitted_reports",
    )
    reason     = models.CharField(max_length=20, choices=Reason.choices)
    details    = models.TextField(blank=True, max_length=1000)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed   = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["ad", "reviewed"])]

    def __str__(self):
        return f"Report #{self.pk} — {self.ad_id} ({self.reason})"
