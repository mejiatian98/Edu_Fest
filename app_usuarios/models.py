from django.db import models
from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    class Roles(models.TextChoices):
        PARTICIPANTE = 'PARTICIPANTE', 'Participante'
        EVALUADOR = 'EVALUADOR', 'Evaluador'
        ADMIN_EVENTO = 'ADMIN_EVENTO', 'Administrador de Evento'
        ASISTENTE = 'ASISTENTE', 'Asistente'
        VISITANTE = 'VISITANTE', 'Visitante Web'
        SUPERADMIN = 'SUPERADMIN', 'Super Admin'

    telefono = models.CharField(max_length=15, blank=True, null=True)
    rol = models.CharField(max_length=30, choices=Roles.choices, default=Roles.ASISTENTE)

    def __str__(self):
        return f"{self.username} ({self.rol})"


class Asistente(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.usuario.first_name} {self.usuario.last_name} - Asistente"


class Participante(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.usuario.first_name} {self.usuario.last_name} - Participante"


class Evaluador(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.usuario.first_name} {self.usuario.last_name} - Evaluador"


class AdministradorEvento(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.usuario.first_name} {self.usuario.last_name} - Administrador de Evento"



