from django.db import models
from app_admin_eventos.models import Evento
from django.core.exceptions import ValidationError
import random
import string
from cloudinary.models import CloudinaryField


class ParticipanteEvento(models.Model):
    par_eve_evento_fk = models.ForeignKey(Evento, on_delete=models.CASCADE)
    par_eve_participante_fk = models.ForeignKey('app_usuarios.Participante', on_delete=models.CASCADE)
    par_eve_fecha = models.DateTimeField(auto_now_add=True)
    par_eve_estado = models.CharField(max_length=45)

    # ARCHIVOS → Cloudinary
    par_eve_documentos = CloudinaryField(
        folder="eventsoft/documentos/",
        resource_type="auto",
        null=True, blank=True
    )

    par_eve_qr = CloudinaryField(
        folder="eventsoft/qrs/",
        resource_type="image",
        null=True, blank=True
    )

    par_eve_clave = models.CharField(max_length=45)
    calificacion = models.IntegerField(null=True, blank=True)

    # NUEVOS CAMPOS
    par_eve_es_grupo = models.BooleanField(default=False)

    par_eve_proyecto_principal = models.ForeignKey(
        'self',
        related_name='miembros_proyecto',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    par_eve_codigo_proyecto = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return f"{self.par_eve_participante_fk} - {self.par_eve_evento_fk}"

    def clean(self):
        from app_asistentes.models import AsistenteEvento
        from app_evaluadores.models import EvaluadorEvento
        from app_participantes.models import ParticipanteEvento

        usuario = self.par_eve_participante_fk.usuario
        evento = self.par_eve_evento_fk

        # Validación cruzada
        if AsistenteEvento.objects.filter(asi_eve_asistente_fk__usuario=usuario, asi_eve_evento_fk=evento).exists():
            raise ValidationError({'par_eve_participante_fk': "Este usuario ya está inscrito como Asistente."})

        if EvaluadorEvento.objects.filter(eva_eve_evaluador_fk__usuario=usuario, eva_eve_evento_fk=evento).exists():
            raise ValidationError({'par_eve_participante_fk': "Este usuario ya está inscrito como Evaluador."})

        if ParticipanteEvento.objects.filter(
            par_eve_participante_fk__usuario=usuario,
            par_eve_evento_fk=evento
        ).exclude(pk=self.pk).exists():
            raise ValidationError({'par_eve_participante_fk': "Ya está inscrito como Participante en este evento."})

    def save(self, *args, **kwargs):
        # Generar código de proyecto si no existe
        if not self.par_eve_codigo_proyecto and not self.par_eve_proyecto_principal:
            self.par_eve_codigo_proyecto = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=8)
            )
        super().save(*args, **kwargs)

    @property
    def es_lider_proyecto(self):
        return self.par_eve_proyecto_principal is None and self.par_eve_es_grupo

    @property
    def proyecto_principal(self):
        return self.par_eve_proyecto_principal if self.par_eve_proyecto_principal else self

    def get_todos_miembros_proyecto(self):
        if self.par_eve_proyecto_principal:
            return self.par_eve_proyecto_principal.get_todos_miembros_proyecto()
        else:
            miembros = list(self.miembros_proyecto.all())
            miembros.insert(0, self)
            return miembros

    class Meta:
        unique_together = ('par_eve_participante_fk', 'par_eve_evento_fk')
        verbose_name = "Inscripción de Participante"
        verbose_name_plural = "Inscripciones de Participantes"
