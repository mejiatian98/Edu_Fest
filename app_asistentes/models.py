from django.db import models
from app_admin_eventos.models import Evento



class AsistenteEvento(models.Model):
    asi_eve_asistente_fk = models.ForeignKey('app_usuarios.Asistente', on_delete=models.CASCADE)
    asi_eve_evento_fk = models.ForeignKey(Evento, on_delete=models.CASCADE)
    asi_eve_fecha_hora = models.DateTimeField()
    asi_eve_estado = models.CharField(max_length=45)
    asi_eve_soporte = models.FileField(upload_to='upload/')
    asi_eve_qr = models.ImageField(upload_to='upload/')
    asi_eve_clave = models.CharField(max_length=45)
    