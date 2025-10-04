from django.db import models
from app_admin_eventos.models import Evento, Criterio
from app_usuarios.models import Participante
from django.core.exceptions import ValidationError





class Calificacion(models.Model):
    cal_evaluador_fk = models.ForeignKey('app_usuarios.Evaluador', on_delete=models.CASCADE)
    cal_criterio_fk = models.ForeignKey(Criterio, on_delete=models.CASCADE)
    cal_participante_fk = models.ForeignKey(Participante, on_delete=models.CASCADE)
    cal_valor = models.IntegerField()



class EvaluadorEvento(models.Model):
    eva_eve_evaluador_fk = models.ForeignKey('app_usuarios.Evaluador', on_delete=models.CASCADE)
    eva_eve_evento_fk = models.ForeignKey(Evento, on_delete=models.CASCADE)
    eva_eve_fecha_hora = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    eva_eve_estado = models.CharField(max_length=45, null=True, blank=True)
    eva_eve_qr = models.ImageField(upload_to='upload/', null=True, blank=True)
    eva_eve_clave = models.CharField(max_length=45, null=True, blank=True)
    eva_eve_documento = models.FileField(upload_to='upload/', null=True, blank=True)

    def clean(self):
        usuario = self.eva_eve_evaluador_fk.usuario
        evento = self.eva_eve_evento_fk

        from app_asistentes.models import AsistenteEvento
        from app_participantes.models import ParticipanteEvento

        

        if ParticipanteEvento.objects.filter(par_eve_participante_fk__usuario=usuario, par_eve_evento_fk=evento).exists():
            raise ValidationError("Este usuario ya está inscrito como Participante en este evento.")
        if AsistenteEvento.objects.filter(asi_eve_asistente_fk__usuario=usuario, asi_eve_evento_fk=evento).exists():
            raise ValidationError("Este usuario ya está inscrito como Asistente en este evento.")
        if EvaluadorEvento.objects.filter(eva_eve_evaluador_fk__usuario=usuario, eva_eve_evento_fk=evento).exclude(pk=self.pk).exists():
            raise ValidationError("Este usuario ya está inscrito como Evaluador en este evento.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)