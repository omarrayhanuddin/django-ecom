from django.db import models


class SiteVisit(models.Model):
    """One row per unique session (not per page view)."""

    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    visited_at = models.DateTimeField(auto_now_add=True)
    page_url = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name = "ভিজিট"
        verbose_name_plural = "ভিজিটসমূহ"
        ordering = ["-visited_at"]

    def __str__(self):
        return f"Visit {self.session_key} @ {self.visited_at:%Y-%m-%d %H:%M}"

    @classmethod
    def total_count(cls):
        return cls.objects.count()
