from django.db import models
from app_admin_eventos.models import Evento


class ParticipanteEvento(models.Model):
    par_eve_evento_fk = models.ForeignKey(Evento, on_delete=models.CASCADE)
    par_eve_participante_fk = models.ForeignKey('app_usuarios.Participante', on_delete=models.CASCADE)
    par_eve_fecha = models.DateTimeField(auto_now_add=True)
    par_eve_estado = models.CharField(max_length=45)
    par_eve_documentos = models.FileField(upload_to='upload/', null=True, blank=True)
    par_eve_qr = models.ImageField(upload_to='upload/', null=True, blank=True)
    par_eve_clave = models.CharField(max_length=45)
    calificacion = models.IntegerField(null=True, blank=True)
    
    # Nuevos campos para manejo de grupos
    par_eve_es_grupo = models.BooleanField(default=False)
    par_eve_proyecto_principal = models.ForeignKey('self', 
                                                  related_name='miembros_proyecto',
                                                  on_delete=models.CASCADE, 
                                                  null=True, blank=True)
    par_eve_codigo_proyecto = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return f"{self.par_eve_participante_fk} - {self.par_eve_evento_fk}"

    def save(self, *args, **kwargs):
        # Generar código único de proyecto si no existe y es el proyecto principal
        if not self.par_eve_codigo_proyecto and not self.par_eve_proyecto_principal:
            import random
            import string
            self.par_eve_codigo_proyecto = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        super().save(*args, **kwargs)

    @property
    def es_lider_proyecto(self):
        """Retorna True si este participante es el líder del proyecto (no tiene proyecto_principal)"""
        return self.par_eve_proyecto_principal is None and self.par_eve_es_grupo

    @property
    def proyecto_principal(self):
        """Retorna el proyecto principal (si es miembro) o self (si es líder)"""
        return self.par_eve_proyecto_principal if self.par_eve_proyecto_principal else self

    def get_todos_miembros_proyecto(self):
        """Retorna todos los miembros del proyecto incluyendo el líder"""
        if self.par_eve_proyecto_principal:
            # Si es miembro, obtener desde el proyecto principal
            return self.par_eve_proyecto_principal.get_todos_miembros_proyecto()
        else:
            # Si es líder, obtener todos los miembros + self
            miembros = list(self.miembros_proyecto.all())
            miembros.insert(0, self)  # Agregar el líder al inicio
            return miembros