from django.db import models
from app_admin_eventos.models import Evento, Criterio
from app_usuarios.models import Participante




class Calificacion(models.Model):
    cal_evaluador_fk = models.ForeignKey('app_usuarios.Evaluador', on_delete=models.CASCADE)
    cal_criterio_fk = models.ForeignKey(Criterio, on_delete=models.CASCADE)
    cal_participante_fk = models.ForeignKey(Participante, on_delete=models.CASCADE)
    cal_valor = models.IntegerField()

class EvaluadorEvento(models.Model):
    eva_eve_evaluador_fk = models.ForeignKey('app_usuarios.Evaluador', on_delete=models.CASCADE)
    eva_eve_evento_fk = models.ForeignKey(Evento, on_delete=models.CASCADE)
    eva_eve_fecha_hora = models.DateTimeField(auto_now_add=True , null=True, blank=True)
    eva_eve_estado = models.CharField(max_length=45 , null=True, blank=True)
    eva_eve_qr = models.ImageField(upload_to='upload/' , null=True, blank=True)
    eva_eve_clave = models.CharField(max_length=45 , null=True, blank=True)
    eva_eve_documento = models.FileField(upload_to='upload/' , null=True, blank=True)


