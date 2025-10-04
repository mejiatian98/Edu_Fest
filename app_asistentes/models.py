from django.db import models
from app_admin_eventos.models import Evento
from django.core.exceptions import ValidationError

    

class AsistenteEvento(models.Model):
    asi_eve_asistente_fk = models.ForeignKey('app_usuarios.Asistente', on_delete=models.CASCADE)
    asi_eve_evento_fk = models.ForeignKey(Evento, on_delete=models.CASCADE)
    asi_eve_fecha_hora = models.DateTimeField()
    asi_eve_estado = models.CharField(max_length=45)
    asi_eve_soporte = models.FileField(upload_to='upload/')
    asi_eve_qr = models.ImageField(upload_to='upload/')
    asi_eve_clave = models.CharField(max_length=45)

    def clean(self):
        usuario = self.asi_eve_asistente_fk.usuario
        evento = self.asi_eve_evento_fk

        from app_evaluadores.models import EvaluadorEvento
        from app_participantes.models import ParticipanteEvento

        if ParticipanteEvento.objects.filter(par_eve_participante_fk__usuario=usuario, par_eve_evento_fk=evento).exists():
            raise ValidationError("Este usuario ya está inscrito como Participante en este evento.")
        if EvaluadorEvento.objects.filter(eva_eve_evaluador_fk__usuario=usuario, eva_eve_evento_fk=evento).exists():
            raise ValidationError("Este usuario ya está inscrito como Evaluador en este evento.")
        if AsistenteEvento.objects.filter(asi_eve_asistente_fk__usuario=usuario, asi_eve_evento_fk=evento).exclude(pk=self.pk).exists():
            raise ValidationError("Este usuario ya está inscrito como Asistente en este evento.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
