from django.db import models
from app_admin_eventos.models import Evento
from django.core.exceptions import ValidationError
from cloudinary.models import CloudinaryField


class AsistenteEvento(models.Model):
    asi_eve_asistente_fk = models.ForeignKey(
        'app_usuarios.Asistente', 
        on_delete=models.CASCADE
    )
    asi_eve_evento_fk = models.ForeignKey(Evento, on_delete=models.CASCADE)
    asi_eve_fecha_hora = models.DateTimeField()
    asi_eve_estado = models.CharField(max_length=45)

    # 🔥 Cambiamos los FileField / ImageField por CloudinaryField
    asi_eve_soporte = CloudinaryField(resource_type='image')  # archivos PDF, DOCX, ZIP, etc.
    asi_eve_qr = CloudinaryField(resource_type='image')     # imágenes PNG, JPG
    asi_eve_clave = models.CharField(max_length=45)

    def clean(self):
        from app_evaluadores.models import EvaluadorEvento
        from app_participantes.models import ParticipanteEvento

        usuario = self.asi_eve_asistente_fk.usuario
        evento = self.asi_eve_evento_fk

        # No puede estar inscrito como Participante
        if ParticipanteEvento.objects.filter(
            par_eve_participante_fk__usuario=usuario,
            par_eve_evento_fk=evento
        ).exists():
            raise ValidationError({
                'asi_eve_asistente_fk': "Este usuario ya está inscrito como Participante en este evento."
            })

        # No puede estar inscrito como Evaluador
        if EvaluadorEvento.objects.filter(
            eva_eve_evaluador_fk__usuario=usuario,
            eva_eve_evento_fk=evento
        ).exists():
            raise ValidationError({
                'asi_eve_asistente_fk': "Este usuario ya está inscrito como Evaluador en este evento."
            })

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('asi_eve_asistente_fk', 'asi_eve_evento_fk')
        verbose_name = "Inscripción de Asistente"
        verbose_name_plural = "Inscripciones de Asistentes"
