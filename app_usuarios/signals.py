# app_usuarios/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Usuario, AdministradorEvento


@receiver(post_save, sender=Usuario)
def crear_admin_evento(sender, instance, created, **kwargs):
    if instance.rol == Usuario.Roles.ADMIN_EVENTO:
        # Solo crea si no existe ya
        if not hasattr(instance, 'administradorevento'):
            AdministradorEvento.objects.create(
                id=instance.id,  # o usa un autoincrement si prefieres
                usuario=instance
            )
