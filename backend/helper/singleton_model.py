from django.db import models


class SingletonModel(models.Model):
    """Abstract base class for singleton models."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Selalu pakai pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance
