from django.db import models
from app_admin_eventos.models import Evento, Criterio
from app_usuarios.models import Participante
from django.core.exceptions import ValidationError

from cloudinary.models import CloudinaryField   # ← IMPORTANTE


class Calificacion(models.Model):
    cal_evaluador_fk = models.ForeignKey('app_usuarios.Evaluador', on_delete=models.CASCADE)
    cal_criterio_fk = models.ForeignKey(Criterio, on_delete=models.CASCADE)
    cal_participante_fk = models.ForeignKey(Participante, on_delete=models.CASCADE)
    cal_valor = models.IntegerField()

    class Meta:
        unique_together = ('cal_evaluador_fk', 'cal_criterio_fk', 'cal_participante_fk')


class EvaluadorEvento(models.Model):
    eva_eve_evaluador_fk = models.ForeignKey('app_usuarios.Evaluador', on_delete=models.CASCADE)
    eva_eve_evento_fk = models.ForeignKey(Evento, on_delete=models.CASCADE)
    eva_eve_fecha_hora = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    eva_eve_estado = models.CharField(max_length=45, null=True, blank=True)

    # -----------------------------
    #   CON CLOUDINARY
    # -----------------------------
    eva_eve_qr = CloudinaryField(
        "qr_code",
        folder="edu_fest/qr",
        resource_type="image",
        blank=True,
        null=True
    )

    eva_eve_documento = CloudinaryField(
        "documento_evaluador",
        folder="edu_fest/documentos",
        resource_type="raw",     # Solo PDFs
        blank=True,
        null=True
    )

    eva_eve_clave = models.CharField(max_length=45, null=True, blank=True)

    def clean(self):
        from app_asistentes.models import AsistenteEvento
        from app_participantes.models import ParticipanteEvento

        usuario = self.eva_eve_evaluador_fk.usuario
        evento = self.eva_eve_evento_fk

        # Usuario NO puede ser Participante
        if ParticipanteEvento.objects.filter(
            par_eve_participante_fk__usuario=usuario,
            par_eve_evento_fk=evento
        ).exists():
            raise ValidationError(
                {'eva_eve_evaluador_fk': "Este usuario ya está inscrito como Participante en este evento."}
            )

        # Usuario NO puede ser Asistente
        if AsistenteEvento.objects.filter(
            asi_eve_asistente_fk__usuario=usuario,
            asi_eve_evento_fk=evento
        ).exists():
            raise ValidationError(
                {'eva_eve_evaluador_fk': "Este usuario ya está inscrito como Asistente en este evento."}
            )

    class Meta:
        unique_together = ('eva_eve_evaluador_fk', 'eva_eve_evento_fk')
        verbose_name = "Inscripción de Evaluador"
        verbose_name_plural = "Inscripciones de Evaluadores"
