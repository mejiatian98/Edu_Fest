from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


from .models import (
    Usuario, AdministradorEvento, Asistente, Participante, Evaluador,
)
from app_admin_eventos.models import Evento, Categoria, Area, Criterio, MemoriaEvento, EventoCategoria
from app_asistentes.models import AsistenteEvento
from app_evaluadores.models import EvaluadorEvento


# --------------------------
# Configuración de Usuarios
# --------------------------
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Rol y teléfono', {'fields': ('rol', 'telefono')}),
    )
    list_display = ['username', 'email', 'rol', 'telefono', 'is_staff']

    # HU88: Enviar código de acceso único por correo
    def enviar_codigo_acceso(self, request, queryset):
        for usuario in queryset:
            if usuario.rol == "AdministradorEvento":
                codigo = f"ADM-{usuario.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
                send_mail(
                    subject="Código de acceso a Eventos",
                    message=f"Hola {usuario.username}, tu código de acceso es: {codigo}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[usuario.email],
                )
        self.message_user(request, "Códigos de acceso enviados con éxito.", level=messages.SUCCESS)

    enviar_codigo_acceso.short_description = " Enviar código de acceso a administradores seleccionados"

    actions = [enviar_codigo_acceso]


# --------------------------
# Configuración de Eventos
# --------------------------
class EventoAdmin(admin.ModelAdmin):
    list_display = ['eve_nombre', 'eve_ciudad', 'eve_lugar', 'eve_fecha_inicio', 'eve_fecha_fin', 'eve_estado']
    list_filter = ['eve_estado', 'eve_fecha_inicio', 'eve_fecha_fin']
    search_fields = ['eve_nombre', 'eve_ciudad', 'eve_lugar']

    # HU93: Publicar evento en sitio web
    def publicar_evento(self, request, queryset):
        updated = queryset.update(eve_estado="Publicado")
        self.message_user(request, f"{updated} evento(s) publicados en el sitio web.", level=messages.SUCCESS)

    publicar_evento.short_description = "HU93 - Publicar evento en el sitio Web"

    # HU95: Cerrar eventos después de un tiempo
    def cerrar_eventos_vencidos(self, request, queryset):
        hoy = timezone.now().date()
        cerrados = 0
        for evento in queryset:
            if evento.eve_fecha_fin < hoy and evento.eve_estado != "Cerrado":
                evento.eve_estado = "Cerrado"
                evento.save()
                cerrados += 1
        self.message_user(request, f"{cerrados} evento(s) cerrados automáticamente.", level=messages.WARNING)

    cerrar_eventos_vencidos.short_description = "HU95 - Cerrar eventos vencidos"

    # HU96: Eliminar eventos pasados
    def eliminar_eventos_pasados(self, request, queryset):
        hoy = timezone.now().date()
        eliminados = 0
        for evento in queryset:
            if evento.eve_fecha_fin < hoy:
                evento.delete()
                eliminados += 1
        self.message_user(request, f"{eliminados} evento(s) eliminados del sitio.", level=messages.ERROR)

    eliminar_eventos_pasados.short_description = "HU96 - Eliminar eventos pasados"

    actions = [publicar_evento, cerrar_eventos_vencidos, eliminar_eventos_pasados]


# --------------------------
# Configuración de Categorías y Áreas
# --------------------------
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['cat_nombre', 'cat_area_fk']
    search_fields = ['cat_nombre']


class AreaAdmin(admin.ModelAdmin):
    list_display = ['are_nombre']
    search_fields = ['are_nombre']


# --------------------------
# Configuración de Criterios
# --------------------------
class CriterioAdmin(admin.ModelAdmin):
    list_display = ['cri_descripcion', 'cri_peso', 'cri_evento_fk']
    list_filter = ['cri_evento_fk']


# --------------------------
# Configuración de Memorias
# --------------------------
class MemoriaEventoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'evento', 'subido_en']
    list_filter = ['evento']
    search_fields = ['nombre']





# --------------------------
# Registro en admin
# --------------------------
admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(AdministradorEvento)
admin.site.register(Asistente)
admin.site.register(Participante)
admin.site.register(Evaluador)

admin.site.register(Evento, EventoAdmin)
admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(Area, AreaAdmin)
admin.site.register(Criterio, CriterioAdmin)
admin.site.register(MemoriaEvento, MemoriaEventoAdmin)
admin.site.register(EventoCategoria)
admin.site.register(AsistenteEvento)
admin.site.register(EvaluadorEvento)