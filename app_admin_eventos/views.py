from django.core.mail import EmailMessage
import os
import random
import string
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView, DeleteView, DetailView
from django.urls import reverse, reverse_lazy
import qrcode
from .models import Criterio, Evento, EventoCategoria, Area, Categoria
from app_usuarios.models import AdministradorEvento , Usuario
from app_participantes.models import ParticipanteEvento 
from app_asistentes.models import  AsistenteEvento
from app_evaluadores.models import EvaluadorEvento, Calificacion
from app_admin_eventos.forms import EventoForm, EditarUsuarioAdministradorForm, CategoriaForm
from django.views.generic.edit import FormView


from app_usuarios.models import Participante, Asistente, Evaluador
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.timezone import now, timedelta
from datetime import timedelta
from django.core.mail import send_mail
from django.utils import timezone
from principal_eventos.settings import DEFAULT_FROM_EMAIL
import time
from django.db.models import Q
from django.core.files.base import ContentFile
from io import BytesIO
from django.db.models import Exists, OuterRef
from django.utils.decorators import method_decorator
from django.contrib.auth.hashers import check_password, make_password
import re
from principal_eventos.decorador import admin_required
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from twilio.rest import Client
from .utils import enviar_sms
from app_admin_eventos.models import Evento
from django.db.models import Sum, Max
from app_participantes.models import ParticipanteEvento
from app_usuarios.models import Participante
from app_evaluadores.models import Calificacion
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import MemoriaEvento
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.templatetags.static import static
from django.contrib.sites.models import Site

from app_admin_eventos.models import Evento, MemoriaEvento
from app_asistentes.models import AsistenteEvento
from app_participantes.models import ParticipanteEvento
from app_evaluadores.models import EvaluadorEvento





############ MEMORIAS DE ADMINISTRADOR ############
@method_decorator(admin_required, name='dispatch')
class MemoriasAdminView(View):
    """
    Permite al administrador subir y ver las memorias de un evento.
    """
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        memorias = MemoriaEvento.objects.filter(evento=evento).order_by('-subido_en')
        return render(request, 'memorias_admin.html', {
            'evento': evento,
            'memorias': memorias
        })

    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        nombre = request.POST.get('nombre', '').strip()
        archivo = request.FILES.get('archivo')

        if not (nombre and archivo):
            messages.error(request, "❌ Debes indicar un nombre y seleccionar un archivo.")
            return redirect('memorias_admin', evento_id=evento_id)

        MemoriaEvento.objects.create(
            evento=evento,
            nombre=nombre,
            archivo=archivo
        )
        messages.success(request, "✅ Memoria subida con éxito.")
        return redirect('memorias_admin', evento_id=evento_id)

@method_decorator(admin_required, name='dispatch')
class BorrarMemoriaAdminView(View):
    def post(self, request, evento_id, memoria_id):
        memoria = get_object_or_404(MemoriaEvento, id=memoria_id, evento_id=evento_id)
        
        # Eliminar el archivo del sistema de archivos también
        memoria.archivo.delete(save=False)
        
        memoria.delete()
        messages.success(request, "🗑️ Memoria eliminada con éxito.")
        return redirect('memorias_admin', evento_id=evento_id)


#############--- Menu principal Dashboard Admin eventos ---##################

@method_decorator(admin_required, name='dispatch')
class MenuPrincipalView(ListView):
    model = Evento
    template_name = 'dashboard_principal_admin.html'
    context_object_name = 'eventos'

    def get_queryset(self):
        # Obtener el administrador de evento logueado
        admin_evento = get_object_or_404(AdministradorEvento, usuario=self.request.user)

        # Filtrar eventos de este administrador
        return Evento.objects.filter(
            eve_administrador_fk=admin_evento
        ).order_by('eve_fecha_inicio')

    # Forzar que el admin cambie su contraseña en el primer login
    def dispatch(self, request, *args, **kwargs):
        admin_evento = get_object_or_404(AdministradorEvento, usuario=request.user)

        if not admin_evento.usuario.last_login:
            return redirect('cambio_password_admin')

        return super().dispatch(request, *args, **kwargs)




##################### --- Cambio de Contraseña Administrador --- #####################

@method_decorator(admin_required, name='dispatch')
class CambioPasswordAdminView(View):
    template_name = 'cambio_password_admin.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, "❌ Las contraseñas no coinciden.")
            return render(request, self.template_name)

        if len(password1) < 6:
            messages.error(request, "❌ La contraseña debe tener al menos 6 caracteres.")
            return render(request, self.template_name)

        id = request.session.get('id')
        admin = get_object_or_404(AdministradorEvento, pk=id)
        usuario =admin.usuario

        usuario.set_password(password1)
        usuario.last_login = timezone.now()  # ✅ Se actualiza solo aquí
        usuario.save()

        messages.success(request, "✅ Contraseña cambiada correctamente.")
        return redirect('dashboard_admin')


        
    

############################## --- Editar Administrador ---##############################

@method_decorator(admin_required, name='dispatch')
class EditarAdministradorView(View):
    template_name = 'editar_administrador.html'

    def get(self, request, administrador_id):
        administrador = get_object_or_404(AdministradorEvento, usuario=self.request.user)
        usuario = administrador.usuario
        form = EditarUsuarioAdministradorForm(instance=usuario)
        relacion = Evento.objects.filter(eve_administrador_fk=administrador).first()

        return render(request, self.template_name, {
            'form': form,
            'administrador': administrador,
            'usuario': usuario,
            'relacion': relacion
        })

    def post(self, request, administrador_id):
        administrador = get_object_or_404(AdministradorEvento, usuario=self.request.user)
        usuario = administrador.usuario
        relacion = Evento.objects.filter(eve_administrador_fk=administrador).first()

        form = EditarUsuarioAdministradorForm(request.POST, request.FILES, instance=usuario)
        contrasena_actual = request.POST.get('nueva_contrasena')
        nueva_contrasena = request.POST.get('confirmar_contrasena')
        confirmar_contrasena_nueva = request.POST.get('confirmar_contrasena_nueva')

        if form.is_valid():
            # Validar nombre de usuario
            nuevo_usuario = form.cleaned_data['username']
            if Usuario.objects.filter(username=nuevo_usuario).exclude(pk=usuario.pk).exists():
                form.add_error('nombre_usuario', "Este nombre de usuario ya está registrado.")
                return render(request, self.template_name, {
                    'form': form,
                    'administrador': administrador,
                    'usuario': usuario,
                    'relacion': relacion
                })

            # Validar cambio de contraseña si alguno fue llenado
            if contrasena_actual or nueva_contrasena or confirmar_contrasena_nueva:
                # Asegurarse de que todos estén completos
                if not all([contrasena_actual, nueva_contrasena, confirmar_contrasena_nueva]):
                    messages.error(request, "❌ Debes completar todos los campos de contraseña.")
                    return render(request, self.template_name, {
                        'form': form,
                        'administrador': administrador,
                        'usuario': usuario,
                        'relacion': relacion
                    })

                # Verificar contraseña actual
                if not check_password(contrasena_actual, usuario.password):
                    messages.error(request, "❌ La contraseña actual es incorrecta.")
                    return render(request, self.template_name, {
                        'form': form,
                        'administrador': administrador,
                        'usuario': usuario,
                        'relacion': relacion
                    })

                # Verificar coincidencia de contraseñas nuevas
                if nueva_contrasena != confirmar_contrasena_nueva:
                    messages.error(request, "❌ Las nuevas contraseñas no coinciden.")
                    return render(request, self.template_name, {
                        'form': form,
                        'administrador': administrador,
                        'usuario': usuario,
                        'relacion': relacion
                    })

                # Validar seguridad de la nueva contraseña
                if len(nueva_contrasena) < 8 or not re.search(r"[A-Z]", nueva_contrasena) or not re.search(r"[a-z]", nueva_contrasena) or not re.search(r"\d", nueva_contrasena):
                    messages.error(request, "❌ La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula y un número.")
                    return render(request, self.template_name, {
                        'form': form,
                        'administrador': administrador,
                        'usuario': usuario,
                        'relacion': relacion
                    })

                # Guardar nueva contraseña
                usuario.password = make_password(nueva_contrasena)

            form.save()
            usuario.save()

            messages.success(request, "✅ Los datos del administrador se actualizaron correctamente.")
            return redirect('editar_administrador', administrador_id=administrador_id)

        else:
            messages.error(request, "❌ No se pudo guardar. Revisa los errores del formulario.")

        return render(request, self.template_name, {
            'form': form,
            'administrador': administrador,
            'usuario': usuario,
            'relacion': relacion
        })


#############################--- Crear Evento ---##############################



@method_decorator(admin_required, name='dispatch')
class EventoCreateView(CreateView):
    model = Evento
    form_class = EventoForm
    template_name = 'crear_eventos.html'
    context_object_name = 'evento'

    def form_valid(self, form):
        evento = form.save(commit=False)

        # ✅ Obtener administrador desde el usuario logueado
        administrador = get_object_or_404(AdministradorEvento, usuario=self.request.user)
        evento.eve_administrador_fk = administrador
        evento.save()

        # ✅ Guardar categorías seleccionadas
        categorias = form.cleaned_data.get('categorias', [])
        for categoria in categorias:
            EventoCategoria.objects.create(
                eve_cat_evento_fk=evento,
                eve_cat_categoria_fk=categoria
            )

        # ✅ Enviar notificación por correo al superadmin
        send_mail(
            subject=f'Nuevo evento creado: {evento.eve_nombre}',
            message=f'El Administrador "{administrador.usuario.first_name} {administrador.usuario.last_name}" '
                    f'ha creado el evento "{evento.eve_nombre}".',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['halosniper1963@gmail.com'],  # o settings.SUPERADMIN_EMAIL si lo defines en .env
        )

        # ✅ Mensaje de éxito
        messages.success(self.request, "Se ha creado el evento exitosamente")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('dashboard_admin')


############################# --- Crear Categoria y Area ---##############################

@method_decorator(admin_required, name='dispatch')
class CreateCategoriaView(CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "crear_categoria.html"

    def get_success_url(self):
        return reverse("lista_categorias")




############################# --- Lista de Categorías ---##############################


@method_decorator(admin_required, name='dispatch')
class ListaCategoriasView(ListView):
    model = Categoria
    template_name = "lista_categorias.html"
    context_object_name = "categorias"

    def get_queryset(self):
        queryset = super().get_queryset()
        area_id = self.request.GET.get("area")  # obtenemos el id del área desde el filtro
        if area_id:
            queryset = queryset.filter(cat_area_fk_id=area_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["areas"] = Area.objects.all()
        context["area_seleccionada"] = self.request.GET.get("area", "")
        return context



@admin_required
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    area = categoria.cat_area_fk  # Área asociada

    # Guardamos el nombre antes de eliminar
    cat_nombre = categoria.cat_nombre
    area_nombre = area.are_nombre

    # Eliminar la categoría
    categoria.delete()

    # Si el área ya no tiene categorías, la eliminamos también
    if not area.categoria_set.exists():
        area.delete()
        messages.success(
            request,
            f"La categoría '{cat_nombre}' y el área '{area_nombre}' fueron eliminadas exitosamente."
        )
    else:
        messages.success(
            request,
            f"La categoría '{cat_nombre}' fue eliminada exitosamente."
        )

    return redirect("lista_categorias")




    
    


###########################--- Actualizar Evento ---##########################
@method_decorator(admin_required, name='dispatch')
class EventoUpdateView(UpdateView):
    model = Evento
    form_class = EventoForm
    template_name = 'editar_evento.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['areas'] = Area.objects.all()
        context['categorias'] = Categoria.objects.all()
        context['selected_categorias'] = self.object.categorias.all()
        return context

    def form_valid(self, form):
        messages.success(self.request, "Se ha editado el evento exitosamente")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('dashboard_admin')


 
#############################--- Detalle Evento ---##############################   
@method_decorator(admin_required, name='dispatch')
class EventoDetailView(DetailView):
    model = Evento
    template_name = 'info_evento_evento.html'
    context_object_name = 'evento'




#############################--- Cancelar Evento ---##############################
@method_decorator(admin_required, name='dispatch')
class PageCancelarEventoView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        return render(request, 'cancelar_evento.html', {'evento': evento})

@method_decorator(admin_required, name='dispatch')
class CancelarEventoView(View):
    def post(self, request, pk):
        evento = get_object_or_404(Evento, id=pk)
        
        if evento.eve_estado == "Cancelado":
            messages.info(request, "Este evento ya está en estado de cancelación pendiente.")
        else:
            evento.eve_estado = "Cancelado"
            evento.eve_cancelacion_iniciada = now()  
            evento.save()
            messages.success(request, "El evento ha sido marcado como cancelado. Tienes 5 horas para revertir esta decisión.")

        return redirect('cancelar_evento_page', evento_id=evento.id)


@method_decorator(admin_required, name='dispatch')
class EliminarDefiniEvento(DetailView):
    model = Evento
    template_name = 'dashboard_principal_admin.html'
    context_object_name = 'evento'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evento = context['evento']

        if evento.eve_estado == 'Cancelado' and evento.eve_cancelacion_iniciada:
            tiempo_transcurrido = timezone.now() - evento.eve_cancelacion_iniciada
            tiempo_restante = timedelta(hours=5) - tiempo_transcurrido
            segundos_restantes = max(int(tiempo_restante.total_seconds()), 0)
            context['segundos_restantes'] = segundos_restantes

            if segundos_restantes == 0:
                self.enviar_notificaciones_y_eliminar(evento)
                context['dashboard_admin'] = True  # Indica que se debe redirigir

        else:
            context['segundos_restantes'] = None

        return context

    def enviar_notificaciones_y_eliminar(self, evento):
        # Función para enviar correo
        def enviar_correo(destinatarios, asunto, mensaje):
            try:
                send_mail(
                    asunto,
                    mensaje,
                    DEFAULT_FROM_EMAIL,
                    destinatarios,
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Error al enviar correo: {e}")

        # Obtener todos los participantes del evento
        participantes_evento = ParticipanteEvento.objects.filter(par_eve_evento_fk=evento)
        participantes_correos = [pe.par_eve_participante_fk.par_correo for pe in participantes_evento]

        # Obtener todos los asistentes del evento
        asistentes_evento = AsistenteEvento.objects.filter(asi_eve_evento_fk=evento)
        asistentes_correos = [ae.asi_eve_asistente_fk.asi_correo for ae in asistentes_evento]

        # Obtener todos los evaluadores del evento
        evaluadores_evento = EvaluadorEvento.objects.filter(eva_eve_evento_fk=evento)
        evaluadores_correos = [ee.eva_eve_evaluador_fk.usuario.eva_correo for ee in evaluadores_evento]

        # Obtener el administrador del evento
        administrador_correo = [evento.eve_administrador_fk.usuario.correo]

        # Enviar correo electrónico a todos
        destinatarios = participantes_correos + asistentes_correos + evaluadores_correos + administrador_correo
        asunto = 'Evento Cancelado'
        mensaje = f'El evento "{evento.eve_nombre}" ha sido cancelado por motivos administrativos. Por lo tanto, tu inscripción ha sido eliminada de la base de datos por seguridad.'
        enviar_correo(destinatarios, asunto, mensaje)

        # Esperar 5 segundos antes de eliminar
        time.sleep(5)

        # Eliminar todas las relaciones y entidades relacionadas
        self.eliminar_relaciones_y_entidades(evento)

    def eliminar_relaciones_y_entidades(self, evento):
        try:
            # Obtener Participantes, Asistentes y Evaluadores únicos vinculados al evento
            participantes = Participante.objects.filter(participanteevento__par_eve_evento_fk=evento).distinct()
            asistentes = Asistente.objects.filter(asistenteevento__asi_eve_evento_fk=evento).distinct()
            evaluadores = Evaluador.objects.filter(evaluadorevento__eva_eve_evento_fk=evento).distinct()

            # Eliminar relaciones primero
            ParticipanteEvento.objects.filter(par_eve_evento_fk=evento).delete()
            AsistenteEvento.objects.filter(asi_eve_evento_fk=evento).delete()
            EvaluadorEvento.objects.filter(eva_eve_evento_fk=evento).delete()
            EventoCategoria.objects.filter(eve_cat_evento_fk=evento).delete()
            Calificacion.objects.filter(cal_criterio_fk__cri_evento_fk=evento).delete()

            # Eliminar el evento
            evento.delete()

            # Luego eliminar entidades base
            participantes.delete()
            asistentes.delete()
            evaluadores.delete()

        except Exception as e:
            print(f"Error al eliminar entidades relacionadas con el evento: {e}")

@method_decorator(admin_required, name='dispatch')
class RevertirCancelacionEventoView(View):
    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)

        if evento.eve_estado == "Cancelado":
            evento.eve_estado = "Publicado"
            evento.eve_cancelacion_iniciada = None
            evento.save()
            messages.success(request, "La cancelación ha sido revertida. El evento vuelve a estar publicado.")
        else:
            messages.info(request, "El evento no se encuentra en estado de cancelación.")

        return redirect('dashboard_admin')




############--- Boton de preincripcion asistente True o False ---###########
@method_decorator(admin_required, name='dispatch')
class CambiarPreinscripcionAsistenteView(View):
    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        accion = request.POST.get('accion')
        if accion == 'habilitar':
            evento.preinscripcion_habilitada_asistentes = False
            messages.success(request, "Preinscripción habilitada.")
        else:
            evento.preinscripcion_habilitada_asistentes = True
            messages.success(request, "Preinscripción inhabilitada.")
        evento.save()
        return redirect('dashboard_admin')


############--- Boton de preincripcion participante True o False ---###########
@method_decorator(admin_required, name='dispatch')
class CambiarPreinscripcionParticipanteView(View):
    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        accion = request.POST.get('accion')
        if accion == 'habilitar':
            evento.preinscripcion_habilitada_participantes = False
            messages.success(request, "Preinscripción habilitada.")
        else:
            evento.preinscripcion_habilitada_participantes = True
            messages.success(request, "Preinscripción inhabilitada.")
        evento.save()
        return redirect('dashboard_admin')


############--- Boton de preincripcion evaluador True o False ---###########
@method_decorator(admin_required, name='dispatch')
class CambiarPreinscripcionEvaluadorView(View):
    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        accion = request.POST.get('accion')
        if accion == 'habilitar':
            evento.preinscripcion_habilitada_evaluadores = False
            messages.success(request, "Preinscripción habilitada.")
        else:
            evento.preinscripcion_habilitada_evaluadores = True
            messages.success(request, "Preinscripción inhabilitada.")
        evento.save()
        return redirect('dashboard_admin')
    
    


#############################--- Validaciones ---##############################
@method_decorator(admin_required, name='dispatch')
class ValidacionesView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        return render(request, 'validaciones_par_asi_eva.html', {'evento': evento})

#############################--- Validaciones Participante Modificado para Grupos ---##############################

@method_decorator(admin_required, name='dispatch')
class ValidacionParticipanteView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)

        query = request.GET.get('query', '')
        estado = request.GET.get('estado', '')

        # Solo mostrar líderes de grupo o participantes individuales
        participantes_evento = ParticipanteEvento.objects.select_related(
            'par_eve_participante_fk', 
            'par_eve_participante_fk__usuario'
        ).filter(
            par_eve_evento_fk=evento,
            par_eve_proyecto_principal__isnull=True  # Solo líderes o individuales
        )

        if query:
            participantes_evento = participantes_evento.filter(
                Q(par_eve_participante_fk__id__icontains=query) |
                Q(par_eve_participante_fk__usuario__last_name__icontains=query) |
                Q(par_eve_participante_fk__usuario__first_name__icontains=query)
            )

        if estado:
            participantes_evento = participantes_evento.filter(par_eve_estado__iexact=estado)

        data = []
        for par in participantes_evento:
            participante = par.par_eve_participante_fk
            
            # Obtener información del grupo si aplica
            miembros_info = []
            if par.par_eve_es_grupo:
                todos_miembros = par.get_todos_miembros_proyecto()
                for miembro in todos_miembros:
                    miembros_info.append({
                        'nombre': f"{miembro.par_eve_participante_fk.usuario.first_name} {miembro.par_eve_participante_fk.usuario.last_name}",
                        'cedula': miembro.par_eve_participante_fk.id,
                        'es_lider': miembro.par_eve_proyecto_principal is None
                    })

            data.append({
                'id': par.id,
                'cedula': participante.id,
                'nombre': participante.usuario.first_name,
                'apellido': participante.usuario.last_name,
                'correo': participante.usuario.email,
                'telefono': participante.usuario.telefono,
                'documentos': par.par_eve_documentos,
                'qr': par.par_eve_qr,
                'estado': par.par_eve_estado,
                'es_grupo': par.par_eve_es_grupo,
                'codigo_proyecto': par.par_eve_codigo_proyecto,
                'miembros': miembros_info,
                'total_miembros': len(miembros_info) if miembros_info else 1
            })

        return render(request, 'validaciones_par.html', {
            'evento': evento,
            'participantes': data,
            'query': query,
            'estado': estado
        })


@method_decorator(admin_required, name='dispatch')
class AprobarParticipanteView(View):
    def get(self, request, evento_id, participante_id):
        participante_evento = get_object_or_404(ParticipanteEvento, id=participante_id)
        participante = participante_evento.par_eve_participante_fk
        evento = get_object_or_404(Evento, id=evento_id)

        # Verificar si es grupo y obtener todos los miembros
        if participante_evento.par_eve_es_grupo:
            todos_miembros = participante_evento.get_todos_miembros_proyecto()
            
            # Aprobar a todos los miembros del grupo
            miembros_aprobados = []
            correos_enviados = []
            
            for miembro_pe in todos_miembros:
                # Generar clave aleatoria para cada miembro
                clave = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                miembro_pe.par_eve_clave = clave
                miembro_pe.par_eve_estado = 'Aprobado'

                # Contenido del QR para cada miembro
                miembro_participante = miembro_pe.par_eve_participante_fk
                es_lider = miembro_pe.par_eve_proyecto_principal is None
                rol_texto = "Líder" if es_lider else "Miembro"
                
                qr_data = f"Participante: {miembro_participante.usuario.first_name}, Rol: {rol_texto}, Grupo: {participante_evento.par_eve_codigo_proyecto}, Evento: {evento.eve_nombre}, Clave: {clave}"
                qr_img = qrcode.make(qr_data)

                # Guardar QR en memoria como archivo
                buffer = BytesIO()
                qr_img.save(buffer, format='PNG')
                file_name = f"qr_grupo_{participante_evento.par_eve_codigo_proyecto}_{miembro_participante.id}.png"
                miembro_pe.par_eve_qr.save(file_name, ContentFile(buffer.getvalue()), save=False)

                # Guardar en base de datos
                miembro_pe.save()

                # Preparar información para el correo
                miembros_aprobados.append({
                    'participante': miembro_participante,
                    'clave': clave,
                    'es_lider': es_lider,
                    'qr_buffer': buffer.getvalue(),
                    'file_name': file_name
                })

            # Enviar correos a todos los miembros del grupo
            for info in miembros_aprobados:
                rol_texto = "líder" if info['es_lider'] else "miembro"
                
                subject = f"Aprobación de grupo para el evento: {evento.eve_nombre}"
                body = (
                    f"Hola {info['participante'].usuario.first_name},\n\n"
                    f"¡Excelentes noticias! Tu grupo ha sido aprobado para participar en el evento: '{evento.eve_nombre}'.\n\n"
                    f"Rol en el grupo: {rol_texto.capitalize()}\n"
                    f"Código del proyecto: {participante_evento.par_eve_codigo_proyecto}\n"
                    f"Tu clave de acceso personal al evento es: {info['clave']}\n\n"
                    f"Total de miembros aprobados en el grupo: {len(miembros_aprobados)}\n\n"
                    "Adjunto encontrarás tu código QR personal que deberás presentar al ingresar.\n\n"
                    "¡Felicitaciones al equipo completo!\n"
                    "Equipo Event-Soft"
                )

                email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=DEFAULT_FROM_EMAIL,
                    to=[info['participante'].usuario.email],
                )

                # Adjuntar el QR personal
                email.attach(info['file_name'], info['qr_buffer'], 'image/png')

                try:
                    email.send(fail_silently=False)
                    correos_enviados.append(info['participante'].usuario.email)
                except Exception as e:
                    print(f"Error enviando correo a {info['participante'].usuario.email}: {str(e)}")

            # Mensaje de éxito
            if len(correos_enviados) == len(miembros_aprobados):
                messages.success(request, 
                    f"Grupo completo aprobado exitosamente. "
                    f"Código del proyecto: {participante_evento.par_eve_codigo_proyecto}. "
                    f"Se aprobaron {len(miembros_aprobados)} miembros y se enviaron todos los correos.")
            else:
                messages.warning(request, 
                    f"Grupo aprobado pero algunos correos no se pudieron enviar. "
                    f"Aprobados: {len(miembros_aprobados)}, Correos enviados: {len(correos_enviados)}")

        else:
            # Participante individual - mantener lógica original
            clave = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            participante_evento.par_eve_clave = clave
            participante_evento.par_eve_estado = 'Aprobado'

            # Contenido del QR
            qr_data = f"Participante: {participante.usuario.first_name}, Evento: {evento.eve_nombre}, Clave: {clave}"
            qr_img = qrcode.make(qr_data)

            # Guardar QR en memoria como archivo
            buffer = BytesIO()
            qr_img.save(buffer, format='PNG')
            file_name = f"qr_participante_{participante.id}.png"
            participante_evento.par_eve_qr.save(file_name, ContentFile(buffer.getvalue()), save=False)

            # Guardar en base de datos
            participante_evento.save()

            # Enviar correo con QR adjunto
            subject = f"Aprobación para el evento: {evento.eve_nombre}"
            body = (
                f"Hola {participante.usuario.first_name},\n\n"
                f"Has sido aprobado para participar en el evento: '{evento.eve_nombre}'.\n"
                f"Tu clave de acceso al evento es: {clave}\n\n"
                "Adjunto encontrarás el código QR que deberás presentar al ingresar.\n\n"
                "¡Gracias por participar!\n"
                "Equipo Event-Soft"
            )

            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=DEFAULT_FROM_EMAIL,
                to=[participante.usuario.email],
            )

            # Adjuntar el QR
            email.attach(file_name, buffer.getvalue(), 'image/png')

            try:
                email.send(fail_silently=False)
                messages.success(request, f"Participante {participante} aprobado y notificado por correo. Clave: {clave}")
            except Exception as e:
                messages.warning(request, f"Participante aprobado, pero no se pudo enviar el correo: {str(e)}")

        return redirect('validacion_par', evento_id=evento_id)


@method_decorator(admin_required, name='dispatch')   
class RechazarParticipanteView(View):
    def get(self, request, evento_id, participante_id):
        participante_evento = get_object_or_404(ParticipanteEvento, id=participante_id)
        participante = participante_evento.par_eve_participante_fk
        evento = participante_evento.par_eve_evento_fk

        # Verificar si es grupo y obtener todos los miembros
        if participante_evento.par_eve_es_grupo:
            todos_miembros = participante_evento.get_todos_miembros_proyecto()
            
            # Rechazar a todos los miembros del grupo
            miembros_rechazados = []
            correos_enviados = []
            
            for miembro_pe in todos_miembros:
                # Cambiar estado y limpiar datos
                miembro_pe.par_eve_estado = 'Rechazado'
                miembro_pe.par_eve_clave = ''

                # Eliminar archivo QR si existe
                if miembro_pe.par_eve_qr:
                    qr_path = miembro_pe.par_eve_qr.path
                    miembro_pe.par_eve_qr.delete(save=False)
                    if os.path.exists(qr_path):
                        os.remove(qr_path)

                miembro_pe.save()

                # Preparar información para el correo
                miembro_participante = miembro_pe.par_eve_participante_fk
                es_lider = miembro_pe.par_eve_proyecto_principal is None
                
                miembros_rechazados.append({
                    'participante': miembro_participante,
                    'es_lider': es_lider
                })

            # Enviar correos a todos los miembros del grupo
            for info in miembros_rechazados:
                rol_texto = "líder" if info['es_lider'] else "miembro"
                
                subject = f"Rechazo de inscripción grupal al evento: {evento.eve_nombre}"
                message = (
                    f"Hola {info['participante'].usuario.first_name},\n\n"
                    f"Lamentamos informarte que tu grupo ha sido rechazado para participar en el evento: '{evento.eve_nombre}'.\n\n"
                    f"Tu rol en el grupo era: {rol_texto}\n"
                    f"Código del proyecto: {participante_evento.par_eve_codigo_proyecto}\n\n"
                    f"Esta decisión afecta a todo el grupo ({len(miembros_rechazados)} miembros).\n\n"
                    "Si tienes alguna duda, por favor contáctanos.\n\n"
                    "Atentamente,\n"
                    "Equipo de Event-Soft"
                )

                try:
                    send_mail(
                        subject,
                        message,
                        DEFAULT_FROM_EMAIL,
                        [info['participante'].usuario.email],
                        fail_silently=False,
                    )
                    correos_enviados.append(info['participante'].usuario.email)
                except Exception as e:
                    print(f"Error enviando correo a {info['participante'].usuario.email}: {str(e)}")

            # Mensaje de resultado
            if len(correos_enviados) == len(miembros_rechazados):
                messages.success(request, 
                    f"Grupo completo rechazado exitosamente. "
                    f"Se rechazaron {len(miembros_rechazados)} miembros y se enviaron todas las notificaciones.")
            else:
                messages.warning(request, 
                    f"Grupo rechazado pero algunos correos no se pudieron enviar. "
                    f"Rechazados: {len(miembros_rechazados)}, Correos enviados: {len(correos_enviados)}")

        else:
            # Participante individual - mantener lógica original
            participante_evento.par_eve_estado = 'Rechazado'
            participante_evento.par_eve_clave = ''

            # Eliminar archivo QR si existe
            if participante_evento.par_eve_qr:
                qr_path = participante_evento.par_eve_qr.path
                participante_evento.par_eve_qr.delete(save=False)
                if os.path.exists(qr_path):
                    os.remove(qr_path)

            participante_evento.save()

            # Enviar correo electrónico de rechazo
            subject = f"Rechazo de inscripción al evento: {evento.eve_nombre}"
            message = (
                f"Hola {participante.usuario.first_name},\n\n"
                f"Lamentamos informarte que has sido rechazado para participar en el evento: '{evento.eve_nombre}'.\n"
                "Si tienes alguna duda, por favor contáctanos.\n\n"
                "Atentamente,\n"
                "Equipo de Event-Soft"
            )

            try:
                send_mail(
                    subject,
                    message,
                    DEFAULT_FROM_EMAIL,
                    [participante.usuario.email],
                    fail_silently=False,
                )
                messages.success(request, "Participante ha sido rechazado correctamente y se envió una notificación por correo.")
            except Exception as e:
                messages.warning(request, f"Participante rechazado, pero ocurrió un error al enviar el correo: {str(e)}")

        return redirect('validacion_par', evento_id=evento_id)

#############################--- Validaciones Asistente ---##############################

@method_decorator(admin_required, name='dispatch')
class ValidacionAsistentesView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)

        # Obtener filtros desde la URL
        query = request.GET.get('query', '')
        estado = request.GET.get('estado', '')

        # Obtener todos los asistentes del evento
        asistentes_evento = AsistenteEvento.objects.select_related('asi_eve_asistente_fk') \
            .filter(asi_eve_evento_fk=evento)

        # Filtro por cédula o nombre
        if query:
            asistentes_evento = asistentes_evento.filter(
                Q(asi_eve_asistente_fk__id__icontains=query) |
                Q(asi_eve_asistente_fk__asuario_first_name__icontains=query) |
                Q(asi_eve_asistente_fk__asuario_last_name__icontains=query)
            )

        # Filtro por estado exacto
        if estado:
            asistentes_evento = asistentes_evento.filter(asi_eve_estado__iexact=estado)

        # Construcción del contexto
        data = []
        for asi in asistentes_evento:
            asistente = asi.asi_eve_asistente_fk
            data.append({
                'id': asi.id,
                'cedula': asistente.id,
                'nombre': asistente.usuario.first_name,
                'apellido': asistente.usuario.last_name,
                'correo': asistente.usuario.email,
                'telefono': asistente.usuario.telefono,
                'qr': asi.asi_eve_qr,
                'soporte': asi.asi_eve_soporte,
                'estado': asi.asi_eve_estado
            })

        return render(request, 'validaciones_asi.html', {
            'evento': evento,
            'asistentes': data,
            'query': query,
            'estado': estado
        })




@method_decorator(admin_required, name='dispatch')
class AprobarAsistenteView(View):
    def get(self, request, evento_id, asistente_id):
        asistente_evento = get_object_or_404(AsistenteEvento, id=asistente_id)
        asistente = asistente_evento.asi_eve_asistente_fk
        evento = get_object_or_404(Evento, id=evento_id)

        # Validar capacidad
        if evento.eve_capacidad <= 0:
            messages.error(request, "No hay cupos disponibles para este evento.")
            return redirect('validacion_asi', evento_id=evento_id)

        # Generar clave aleatoria
        clave = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        asistente_evento.asi_eve_clave = clave
        asistente_evento.asi_eve_estado = 'Aprobado'

        # Crear QR
        qr_data = f"Asistente: {asistente.usuario.first_name}, Evento: {evento.eve_nombre}, Clave: {clave}"
        qr_img = qrcode.make(qr_data)
        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        file_name = f"qr_asistente_{asistente.id}.png"
        asistente_evento.asi_eve_qr.save(file_name, ContentFile(buffer.getvalue()), save=False)

        # Guardar evento y relación
        evento.eve_capacidad -= 1
        evento.save()
        asistente_evento.save()

        # Enviar correo
        subject = f"Confirmación de inscripción: {evento.eve_nombre}"
        body = (
            f"Hola {asistente.usuario.first_name},\n\n"
            f"Has sido aprobado para asistir al evento: {evento.eve_nombre}.\n"
            f"Tu clave de acceso es: {clave}\n\n"
            f"Adjunto encontrarás tu código QR para el acceso.\n\n"
            f"Gracias por tu interés.\n\n"
            f"Equipo Event-Soft"
        )
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=DEFAULT_FROM_EMAIL,
            to=[asistente.usuario.email],
        )
        email.attach(file_name, buffer.getvalue(), 'image/png')
        email.send(fail_silently=False)

        messages.success(request, f"Asistente {asistente} ha sido aprobado correctamente. Clave: {clave}")
        return redirect('validacion_asi', evento_id=evento_id)


@method_decorator(admin_required, name='dispatch')
class RechazarAsistenteView(View):
    def get(self, request, evento_id, asistente_id):
        asistente_evento = get_object_or_404(AsistenteEvento, id=asistente_id)
        asistente = asistente_evento.asi_eve_asistente_fk
        evento = asistente_evento.asi_eve_evento_fk

        # Cambiar estado y limpiar datos
        asistente_evento.asi_eve_estado = 'Rechazado'
        asistente_evento.asi_eve_clave = ''

        # Eliminar archivo QR si existe
        if asistente_evento.asi_eve_qr:
            qr_path = asistente_evento.asi_eve_qr.path
            asistente_evento.asi_eve_qr.delete(save=False)
            if os.path.exists(qr_path):
                os.remove(qr_path)

        # ✅ Aumentar el cupo del evento
        evento.eve_capacidad += 1
        evento.save()

        # Guardar la relación actualizada
        asistente_evento.save()

        # Enviar correo de rechazo
        subject = f"Rechazo de inscripción al evento: {evento.eve_nombre}"
        message = (
            f"Hola {asistente.usuario.first_name},\n\n"
            f"Lamentamos informarte que has sido rechazado para asistir al evento: '{evento.eve_nombre}'.\n"
            "Si tienes alguna duda, por favor contáctanos.\n\n"
            "Atentamente,\n"
            "Equipo de Event-Soft"
        )
        recipient_email = asistente.usuario.email

        try:
            send_mail(
                subject,
                message,
                DEFAULT_FROM_EMAIL,
                [recipient_email],
                fail_silently=False,
            )
        except Exception as e:
            messages.warning(request, f"Asistente rechazado, pero ocurrió un error al enviar el correo: {str(e)}")
        else:
            messages.success(request, "Asistente ha sido rechazado correctamente y se envió una notificación por correo.")

        return redirect('validacion_asi', evento_id=evento_id)

#############################--- Estadisticas ---##############################
@method_decorator(admin_required, name='dispatch')
class EstadisticasView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)

        # Calcular cupos del evento
        cupos_disponibles = evento.eve_capacidad
        cupos_ocupados = evento.eve_capacidad - cupos_disponibles
        cupos_totales = evento.eve_capacidad
        porcentaje_ocupacion = (cupos_ocupados / cupos_totales * 100) if cupos_totales > 0 else 0

        # Participantes
        total_participantes = ParticipanteEvento.objects.filter(par_eve_evento_fk=evento).count()
        aprobados_participantes = ParticipanteEvento.objects.filter(par_eve_evento_fk=evento, par_eve_estado='Aprobado').count()
        rechazados_participantes = ParticipanteEvento.objects.filter(par_eve_evento_fk=evento, par_eve_estado='Rechazado').count()
        pendientes_participantes = total_participantes - (aprobados_participantes + rechazados_participantes)

        # Asistentes
        total_asistentes = AsistenteEvento.objects.filter(asi_eve_evento_fk=evento).count()
        aprobados_asistentes = AsistenteEvento.objects.filter(asi_eve_evento_fk=evento, asi_eve_estado='Aprobado').count()
        rechazados_asistentes = AsistenteEvento.objects.filter(asi_eve_evento_fk=evento, asi_eve_estado='Rechazado').count()
        pendientes_asistentes = total_asistentes - (aprobados_asistentes + rechazados_asistentes)

        # Contexto para la plantilla
        context = {
            'evento': evento,
            'cupos_disponibles': cupos_disponibles,
            'cupos_ocupados': cupos_ocupados,
            'cupos_totales': cupos_totales,
            'porcentaje_ocupacion': porcentaje_ocupacion,
            'total_participantes': total_participantes,
            'aprobados_participantes': aprobados_participantes,
            'rechazados_participantes': rechazados_participantes,
            'pendientes_participantes': pendientes_participantes,
            'total_asistentes': total_asistentes,
            'aprobados_asistentes': aprobados_asistentes,
            'rechazados_asistentes': rechazados_asistentes,
            'pendientes_asistentes': pendientes_asistentes  
        }

        return render(request, 'estadisticas.html', context)


#############################--- Crear Criterio ---##############################
@method_decorator(admin_required, name='dispatch')
class CriterioListView(ListView):
    model = Criterio
    template_name = 'crear_criterios_evaluacion.html'
    context_object_name = 'criterios'

    def get_queryset(self):
        evento_id = self.kwargs.get('evento_id')
        return Criterio.objects.filter(cri_evento_fk__id=evento_id).order_by('cri_descripcion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evento_id = self.kwargs.get('evento_id')
        evento = get_object_or_404(Evento, id=evento_id)
        criterios = context['criterios']  # queryset con criterios filtrados

        suma_pesos = sum(criterio.cri_peso for criterio in criterios)
        context['evento'] = evento
        context['suma_pesos'] = round(suma_pesos, 2)

        # Validación para saber si ya están completos los 100 puntos
        context['completo_100'] = (suma_pesos == 100)

        return context
 
@method_decorator(admin_required, name='dispatch')
class CrearCriterioView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)
        criterios = Criterio.objects.filter(cri_evento_fk=evento)
        suma_pesos = sum(criterio.cri_peso for criterio in criterios)

        return render(request, 'crear_criterios_evaluacion.html', {
            'evento': evento,
            'criterios': criterios,
            'suma_pesos': round(suma_pesos, 2),
        })

    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)
        descripcion = request.POST.get('cri_descripcion')
        peso_str = request.POST.get('cri_peso')

        # Validar campos vacíos
        if not descripcion or not peso_str:
            messages.error(request, 'Todos los campos son obligatorios.')
            return redirect('crear_criterio', evento_id=evento_id)

        # Intentar convertir el peso a float
        try:
            peso = float(peso_str)
        except ValueError:
            messages.error(request, 'El peso debe ser un número válido.')
            return redirect('crear_criterio', evento_id=evento_id)

        # Obtener los criterios existentes y su suma de pesos
        criterios = Criterio.objects.filter(cri_evento_fk=evento)
        suma_pesos = sum(criterio.cri_peso for criterio in criterios)

        # Validar si ya se alcanzó el máximo
        if suma_pesos >= 100:
            messages.error(request, 'La suma de los pesos ya llegó a 100%. No se pueden agregar más criterios.')
            return redirect('crear_criterio', evento_id=evento_id)

        # Validar que la suma con el nuevo peso no exceda 100
        if suma_pesos + peso > 100:
            messages.error(
                request,
                f'La suma de los pesos no puede superar 100%. Actualmente hay {round(suma_pesos, 2)}%.'
            )
            return redirect('crear_criterio', evento_id=evento_id)

        # Crear el nuevo criterio
        Criterio.objects.create(
            cri_descripcion=descripcion,
            cri_peso=peso,
            cri_evento_fk=evento
        )

        messages.success(request, 'Criterio creado exitosamente.')
        return redirect('crear_criterio', evento_id=evento_id)

@method_decorator(admin_required, name='dispatch')
class ActualizarCriterioView(View):
    def post(self, request, criterio_id):
        criterio = get_object_or_404(Criterio, pk=criterio_id)
        descripcion = request.POST.get('cri_descripcion')
        peso_str = request.POST.get('cri_peso')

        if not descripcion or not peso_str:
            messages.error(request, 'Todos los campos son obligatorios.')
            return redirect('crear_criterio', evento_id=criterio.cri_evento_fk.id)

        try:
            nuevo_peso = float(peso_str)
        except ValueError:
            messages.error(request, 'El peso debe ser un número válido.')
            return redirect('crear_criterio', evento_id=criterio.cri_evento_fk.id)

        # Obtener criterios del mismo evento excepto el que se está actualizando
        criterios = Criterio.objects.filter(cri_evento_fk=criterio.cri_evento_fk).exclude(pk=criterio.pk)
        suma_pesos_otros = sum(c.cri_peso for c in criterios)

        # Validar suma total con nuevo peso
        if suma_pesos_otros + nuevo_peso > 100:
            messages.error(
                request,
                f'La suma total de pesos no puede superar 100%. Actualmente hay {round(suma_pesos_otros, 2)}%.'
            )
            return redirect('crear_criterio', evento_id=criterio.cri_evento_fk.id)

        # Guardar si pasa validación
        criterio.cri_descripcion = descripcion
        criterio.cri_peso = nuevo_peso
        criterio.save()

        messages.success(request, 'Criterio actualizado exitosamente.')
        return redirect('crear_criterio', evento_id=criterio.cri_evento_fk.id)

@method_decorator(admin_required, name='dispatch')
class EliminarCriterioView(View):
    def post(self, request, criterio_id):
        criterio = get_object_or_404(Criterio, pk=criterio_id)
        evento_id = criterio.cri_evento_fk.id
        criterio.delete()

        messages.success(request, 'Criterio eliminado exitosamente.')
        return redirect('crear_criterio', evento_id=evento_id)
    
@method_decorator(admin_required, name='dispatch')
class CriterioAgregadosListView(ListView):
    model = Criterio
    template_name = 'ver_criterios.html'
    context_object_name = 'criterios'

    def get_queryset(self):
        evento_id = self.kwargs.get('evento_id')
        return Criterio.objects.filter(cri_evento_fk__id=evento_id).order_by('cri_descripcion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evento_id = self.kwargs.get('evento_id')
        context['evento'] = get_object_or_404(Evento, id=evento_id)
        return context
    


########## VER PODIO #########

@method_decorator(admin_required, name='dispatch')
class VerPodioParticipantesAdminView(View):
    def get(self, request, evento_id):
        usuario = request.user
        administrador = get_object_or_404(AdministradorEvento, usuario=usuario)

        # ✅ Obtener evento
        evento = get_object_or_404(Evento, pk=evento_id)

        # ✅ Validar que el evento pertenezca al admin logueado
        if evento.eve_administrador_fk != administrador:
            return redirect('acceso_denegado')

        # ✅ Obtener participantes con sus calificaciones
        participantes_evento = ParticipanteEvento.objects.filter(
            par_eve_evento_fk=evento
        ).select_related('par_eve_participante_fk__usuario')

        # ✅ Filtrar los que tienen calificación
        participantes_calificados = [pe for pe in participantes_evento if pe.calificacion is not None]

        # ✅ Ordenar de mayor a menor
        participantes_calificados.sort(key=lambda x: x.calificacion, reverse=True)

        # ✅ (Opcional) Mostrar solo el top 3
        # participantes_calificados = participantes_calificados[:3]

        context = {
            'evento': evento,
            'administrador': administrador,
            'participantes': participantes_calificados,
        }

        return render(request, 'ver_notas_participantes_admin.html', context)


########## VER NOTAS DE PARTICIPANTES #########
@method_decorator(admin_required, name='dispatch')
class DetalleCalificacionAdminView(DetailView):
    template_name = 'ver_detalle_calificacion_podio_admin.html'
    context_object_name = 'participante'
    model = Participante

    def get_object(self):
        return get_object_or_404(Participante, id=self.kwargs['participante_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evento_id = self.kwargs['evento_id']
        participante = self.get_object()
        evento = get_object_or_404(Evento, id=evento_id)

        # Verificamos que el administrador logueado sea el encargado de este evento
        id = self.request.session.get('id')
        administrador = get_object_or_404(AdministradorEvento, pk=id)
        
        if evento.eve_administrador_fk != administrador:
            return redirect('acceso_denegado')

        participante_evento = get_object_or_404(
            ParticipanteEvento,
            par_eve_evento_fk=evento,
            par_eve_participante_fk=participante
        )

        calificaciones = Calificacion.objects.filter(
            cal_participante_fk=participante,
            cal_criterio_fk__cri_evento_fk=evento
        ).select_related('cal_criterio_fk', 'cal_evaluador_fk')

        context.update({
            'evento': evento,
            'participante_evento': participante_evento,
            'calificaciones': calificaciones,
            'administrador': administrador
        })

        return context


########## VALIDACION EVALUADOR #########



@method_decorator(admin_required, name='dispatch')
class ValidacionEvaluadorView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)

        query = request.GET.get('query', '')
        estado = request.GET.get('estado', '')

        evaluadores_evento = EvaluadorEvento.objects.select_related('eva_eve_evaluador_fk', 'eva_eve_evaluador_fk__usuario') \
            .filter(eva_eve_evento_fk=evento)

        if query:
            evaluadores_evento = evaluadores_evento.filter(
                Q(eva_eve_evaluador_fk__id__icontains=query) |
                Q(eva_eve_evaluador_fk__usuario__first_name__icontains=query) |
                Q(eva_eve_evaluador_fk__usuario__last_name__icontains=query)
            )

        if estado:
            evaluadores_evento = evaluadores_evento.filter(eva_eve_estado__iexact=estado)

        

        data = []
        for eva in evaluadores_evento:
            evaluador = eva.eva_eve_evaluador_fk
            data.append({
            'id': eva.id,
            'cedula': evaluador.id,
            'nombre': evaluador.usuario.first_name,
            'apellido': evaluador.usuario.last_name,
            'correo': evaluador.usuario.email,
            'telefono': evaluador.usuario.telefono,
            'qr': eva.eva_eve_qr,
            'documento': eva.eva_eve_documento.url if eva.eva_eve_documento else None,  # ← AÑADIDO
            'estado': eva.eva_eve_estado
        })

        return render(request, 'validaciones_eva.html', {
            'evento': evento,
            'evaluadores': data,
            'query': query,
            'estado': estado
        })
    
    
@method_decorator(admin_required, name='dispatch')
class AprobarEvaluadorView(View):
    def get(self, request, evento_id, evaluador_id):
        evaluador_evento = get_object_or_404(EvaluadorEvento, id=evaluador_id)
        evaluador = evaluador_evento.eva_eve_evaluador_fk
        evento = evaluador_evento.eva_eve_evento_fk

        # Generar clave
        clave = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        evaluador_evento.eva_eve_clave = clave
        evaluador_evento.eva_eve_estado = 'Aprobado'

        # Crear QR
        qr_data = f"Evaluador: {evaluador.usuario.first_name}, Evento: {evento.eve_nombre}, Clave: {clave}"
        qr_img = qrcode.make(qr_data)

        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        file_name = f"qr_evaluador_{evaluador.id}.png"
        evaluador_evento.eva_eve_qr.save(file_name, ContentFile(buffer.getvalue()), save=False)

        evaluador_evento.save()

        # Enviar correo
        subject = f"Aprobación como Evaluador en el evento: {evento.eve_nombre}"
        body = (
            f"Hola {evaluador.usuario.first_name},\n\n"
            f"Has sido aprobado como evaluador en el evento: '{evento.eve_nombre}'.\n"
            f"Tu clave de acceso es: {clave}\n\n"
            "Adjunto encontrarás tu código QR de acceso.\n\n"
            "¡Gracias por tu participación!\n"
            "Equipo Event-Soft"
        )

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=DEFAULT_FROM_EMAIL,
            to=[evaluador.usuario.email],
        )
        email.attach(file_name, buffer.getvalue(), 'image/png')

        try:
            email.send(fail_silently=False)
            messages.success(request, f"Evaluador {evaluador} aprobado y notificado.")
        except Exception as e:
            messages.warning(request, f"Aprobado, pero ocurrió un error al enviar el correo: {str(e)}")

        return redirect('validacion_eva', evento_id=evento_id)

@method_decorator(admin_required, name='dispatch')
class RechazarEvaluadorView(View):
    def get(self, request, evento_id, evaluador_id):
        evaluador_evento = get_object_or_404(EvaluadorEvento, id=evaluador_id)
        evaluador = evaluador_evento.eva_eve_evaluador_fk
        evento = evaluador_evento.eva_eve_evento_fk

        evaluador_evento.eva_eve_estado = 'Rechazado'
        evaluador_evento.eva_eve_clave = ''

        if evaluador_evento.eva_eve_qr:
            qr_path = evaluador_evento.eva_eve_qr.path
            evaluador_evento.eva_eve_qr.delete(save=False)
            if os.path.exists(qr_path):
                os.remove(qr_path)

        evaluador_evento.save()

        subject = f"Rechazo como evaluador en el evento: {evento.eve_nombre}"
        message = (
            f"Hola {evaluador.usuario.first_name},\n\n"
            f"Lamentamos informarte que no has sido aprobado como evaluador para el evento: '{evento.eve_nombre}'.\n"
            "Si tienes preguntas, contáctanos.\n\n"
            "Atentamente,\n"
            "Equipo Event-Soft"
        )

        try:
            send_mail(
                subject,
                message,
                DEFAULT_FROM_EMAIL,
                [evaluador.usuario.email],
                fail_silently=False,
            )
        except Exception as e:
            messages.warning(request, f"Evaluador rechazado, pero hubo error al enviar correo: {str(e)}")
        else:
            messages.success(request, "Evaluador rechazado correctamente y notificado por correo.")

        return redirect('validacion_eva', evento_id=evento_id)

    


######### RÚBRICA DEL EVENTO ##########

@method_decorator(admin_required, name='dispatch')
class InformacionTecnicaEventoView(View):
    template_name = 'info_tecnica_evento.html'

    def get(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        return render(request, self.template_name, {'evento': evento})

    def post(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)

        # Subir archivo
        if 'informacion_tecnica' in request.FILES:
            archivo = request.FILES['informacion_tecnica']
            evento.eve_informacion_tecnica = archivo
            evento.save()
            messages.success(request, "Archivo subido correctamente.")

        # Eliminar archivo
        elif 'eliminar_archivo' in request.POST:
            if evento.eve_informacion_tecnica:
                evento.eve_informacion_tecnica.delete(save=False)  # borra del sistema de archivos
                evento.eve_informacion_tecnica = None
                evento.save()
                messages.success(request, "Archivo eliminado correctamente.")
            else:
                messages.warning(request, "No hay archivo para eliminar.")

        else:
            messages.warning(request, "Por favor selecciona un archivo.")

        return redirect('ver_info_tecnica', pk=pk)


######################## CERTIFICADOS #############################



@method_decorator(admin_required, name='dispatch')
class CertificadosView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        return render(request, 'enviar_certificados.html', {'evento': evento})

    def post(self, request, evento_id):
        tipo = request.POST.get("tipo_persona")
        personas_ids = request.POST.getlist("personas")

        if not (personas_ids and tipo):
            messages.error(request, "❌ Debes seleccionar un tipo de persona y al menos una persona.")
            return redirect('certificados_admin', evento_id=evento_id)

        # Obtener personas según tipo
        personas = []
        template_name = None

        if tipo == "participantes":
            qs = ParticipanteEvento.objects.filter(
                par_eve_evento_fk_id=evento_id,
                par_eve_participante_fk__in=personas_ids
            )
            personas = [rel.par_eve_participante_fk for rel in qs]
            template_name = "certificado_participante.html"

        elif tipo == "evaluadores":
            qs = EvaluadorEvento.objects.filter(
                eva_eve_evento_fk_id=evento_id,
                eva_eve_evaluador_fk__in=personas_ids
            )
            personas = [rel.eva_eve_evaluador_fk for rel in qs]
            template_name = "certificado_evaluador.html"

        elif tipo == "asistentes":
            qs = AsistenteEvento.objects.filter(
                asi_eve_evento_fk_id=evento_id,
                asi_eve_asistente_fk__in=personas_ids
            )
            personas = [rel.asi_eve_asistente_fk for rel in qs]
            template_name = "certificado_asistente.html"

        if not personas:
            messages.warning(request, "⚠️ No se encontró ninguna persona seleccionada.")
            return redirect('certificados_admin', evento_id=evento_id)

        evento = get_object_or_404(Evento, id=evento_id)

        # Generar y enviar certificado para cada persona
        for persona in personas:
            # Renderizar plantilla HTML con datos y el template correspondiente
            html_content = render_to_string(template_name, {
                "persona": persona,
                "evento": evento
            })

            # Convertir HTML a PDF
            pdf_buffer = BytesIO()
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
            if pisa_status.err:
                print(f"Error generando PDF para {persona}")
                continue

            # Enviar por correo
            correo = persona.usuario.email
            nombre_pdf = f"certificado_{tipo}_{str(persona).replace(' ', '_')}.pdf"

            email = EmailMessage(
                subject="🎓 Tu Certificado",
                body=(
                    f"Hola {persona.usuario.first_name},\n\n"
                    f"Adjunto encontrarás tu certificado correspondiente al evento '{evento.eve_nombre}'.\n\n"
                    "¡Gracias por participar!"
                ),
                from_email=DEFAULT_FROM_EMAIL,
                to=[correo],
            )
            email.attach(nombre_pdf, pdf_buffer.getvalue(), "application/pdf")

            try:
                email.send(fail_silently=False)
            except Exception as e:
                print(f"Error al enviar correo a {correo}: {e}")

        messages.success(request, "✅ Certificados enviados correctamente.")
        return redirect('certificados_admin', evento_id=evento_id)


# **NO** usamos @admin_required aquí para evitar redirección al admin login
@login_required
def cargar_personas(request):
    tipo = request.GET.get('tipo')
    evento_id = request.GET.get('evento_id')
    personas = []

    if tipo == 'participantes':
        qs = ParticipanteEvento.objects.filter(par_eve_evento_fk_id=evento_id)
        for rel in qs:
            participante = rel.par_eve_participante_fk
            personas.append({
                'id': participante.pk,
                'nombre': str(participante),
                'correo': participante.usuario.email
            })

    elif tipo == 'evaluadores':
        qs = EvaluadorEvento.objects.filter(eva_eve_evento_fk_id=evento_id)
        for rel in qs:
            evaluador = rel.eva_eve_evaluador_fk
            personas.append({
                'id': evaluador.pk,
                'nombre': str(evaluador),
                'correo': evaluador.usuario.email
            })

    elif tipo == 'asistentes':
        qs = AsistenteEvento.objects.filter(asi_eve_evento_fk_id=evento_id)
        for rel in qs:
            asistente = rel.asi_eve_asistente_fk
            personas.append({
                'id': asistente.pk,
                'nombre': str(asistente),
                'correo': asistente.usuario.email
            })

    return JsonResponse({'personas': personas})



@login_required
def previsualizar_certificado(request, evento_id, tipo, persona_id):
    evento = get_object_or_404(Evento, id=evento_id)

    # Obtener la persona según el tipo
    persona = None
    template_name = None

    if tipo == "participantes":
        rel = get_object_or_404(
            ParticipanteEvento,
            par_eve_evento_fk_id=evento_id,
            par_eve_participante_fk_id=persona_id
        )
        persona = rel.par_eve_participante_fk
        template_name = "certificado_participante.html"

    elif tipo == "evaluadores":
        rel = get_object_or_404(
            EvaluadorEvento,
            eva_eve_evento_fk_id=evento_id,
            eva_eve_evaluador_fk_id=persona_id
        )
        persona = rel.eva_eve_evaluador_fk
        template_name = "certificado_evaluador.html"

    elif tipo == "asistentes":
        rel = get_object_or_404(
            AsistenteEvento,
            asi_eve_evento_fk_id=evento_id,
            asi_eve_asistente_fk_id=persona_id
        )
        persona = rel.asi_eve_asistente_fk
        template_name = "certificado_asistente.html"

    if not persona:
        return HttpResponse("No se encontró la persona.", status=404)

    # Renderizar plantilla normal (HTML en el navegador)
    return render(request, template_name, {
        "persona": persona,
        "evento": evento
    })

################################ CERTIFICADOS DE PUNTUACION ################################



@method_decorator(admin_required, name='dispatch')
class PremiacionView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)

        # Sumamos calificaciones por participante en este evento
        resultados = (
            Calificacion.objects
            .filter(cal_criterio_fk__cri_evento_fk=evento)
            .values('cal_participante_fk')
            .annotate(total=Sum('cal_valor'))
            .order_by('-total')
        )

        # Top 3
        ganadores = []
        for idx, r in enumerate(resultados[:3], start=1):
            participante = Participante.objects.get(pk=r['cal_participante_fk'])
            if ParticipanteEvento.objects.filter(
                par_eve_evento_fk=evento,
                par_eve_participante_fk=participante
            ).exists():
                ganadores.append({
                    'id': participante.pk,
                    'nombre': str(participante),
                    'correo': participante.usuario.email,
                    'puntaje': r['total'],
                    'puesto': idx,
                })

        return render(request, 'premiacion.html', {
            'evento': evento,
            'ganadores': ganadores
        })

    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        seleccionados = request.POST.getlist('participantes')
        archivo = request.FILES.get('archivo')

        if not (seleccionados and archivo):
            messages.error(request, "❌ Debes seleccionar ganadores y subir un certificado.")
            return redirect('premiacion_admin', evento_id=evento_id)

        # Volvemos a calcular posiciones para tener el puesto de cada id
        resultados = (
            Calificacion.objects
            .filter(cal_criterio_fk__cri_evento_fk=evento)
            .values('cal_participante_fk')
            .annotate(total=Sum('cal_valor'))
            .order_by('-total')
        )
        posicion_map = { r['cal_participante_fk']: idx
                         for idx, r in enumerate(resultados[:3], start=1) }

        enviados = 0
        for pid in seleccionados:
            participante = Participante.objects.get(pk=pid)
            puesto = posicion_map.get(participante.pk, '?')
            puntaje = next((r['total'] for r in resultados if r['cal_participante_fk']==participante.pk), None)

            subject = f"🏆 Certificado de Premiación — {evento.eve_nombre}"
            body = (
                f"Hola {participante.usuario.first_name},\n\n"
                f"¡Felicidades! Has obtenido el *puesto {puesto}* con un total de *{puntaje} puntos* "
                f"en el evento \"{evento.eve_nombre}\".\n\n"
                "Adjunto encontrarás tu certificado de premiación.\n\n"
                "¡Gracias por tu participación y éxitos en futuras competencias!\n"
            )

            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[participante.usuario.email],
            )
            nombre_pdf = f"premiacion_puesto{puesto}_{participante.usuario.username}.pdf"
            email.attach(nombre_pdf, archivo.read(), archivo.content_type)
            try:
                email.send(fail_silently=False)
                enviados += 1
            except Exception as e:
                print(f"Error enviando a {participante}: {e}")

        messages.success(request, f"✅ Certificados de premiación enviados: {enviados}")
        return redirect('premiacion_admin', evento_id=evento_id)
    


#############################--- Notificar ---##############################
@method_decorator(admin_required, name='dispatch')
class NotificarEventoView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        return render(request, 'notificar_evento_par_asi_eva.html', {'evento': evento})
    


#############################--- Notificar Asistentes ---##############################
@method_decorator(admin_required, name='dispatch')
class EnviarNotificacionAsistentesView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)

        # 🔹 Mostrar solo asistentes "Pendiente" o "Aprobado"
        asistentes = AsistenteEvento.objects.filter(
            asi_eve_evento_fk=evento,
            asi_eve_estado__in=["Pendiente", "Aprobado"]
        ).select_related('asi_eve_asistente_fk__usuario')

        return render(request, 'notificar_evento_asi.html', {
            'evento': evento,
            'asistentes': asistentes
        })

    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        mensaje = request.POST.get('mensaje', '').strip()
        seleccionados = request.POST.getlist('asistentes')

        # 📌 Corrección CP-3.2: Validación de mensaje vacío
        if not mensaje:
            messages.error(request, "❌ El mensaje no puede estar vacío.")
            return self.get(request, evento_id) 
        
        # 📌 Corrección CP-3.3: Validación de cero asistentes
        if not seleccionados:
            messages.warning(request, "⚠️ No seleccionaste ningún asistente.")
            return self.get(request, evento_id) 

        asistentes = AsistenteEvento.objects.filter(
            id__in=seleccionados
        ).select_related('asi_eve_asistente_fk__usuario')

        enviados = 0
        
        # 📌 CORRECCIÓN CLAVE CP-3.1: Generación de URLs Absolutas (reinsertado)
        # Esto evita el NameError y asegura que las URLs no rompan el cuerpo del correo.
        
        # 1. URL del Logo (Static)
        logo_path = static('img/logo.png')
        logo_url = request.build_absolute_uri(logo_path) 
        
        # 2. URL de la Imagen del Evento (Media)
        img_evento = ''
        if evento.eve_imagen and evento.eve_imagen.name: 
            img_evento_path = evento.eve_imagen.url
            img_evento = request.build_absolute_uri(img_evento_path)
            
        # -----------------------------------------------------------
        
        for rel in asistentes:
            asistente = rel.asi_eve_asistente_fk
            correo = asistente.usuario.email

            subject = f"📢 Notificación sobre el evento: {evento.eve_nombre}"
            
            # El cuerpo del correo ahora usa las variables corregidas
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <p>Hola Asistente {asistente.usuario.first_name} {asistente.usuario.last_name},</p>
                <p>Tienes una nueva notificación sobre el evento <b>{evento.eve_nombre}</b>:</p>
                {f'<img src="{img_evento}" alt="Imagen del evento" width="200"><br><br>' if img_evento else ''}
                <p>{mensaje}</p>
                <br>
                <img src="{logo_url}" alt="Logo Event-Soft" width="100"><br><br>
                <p>¡Gracias por ser parte de nuestro evento!<br>
                Equipo Event-Soft</p>
            </body>
            </html>
            """

            try:
                email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[correo],
                )
                email.content_subtype = "html"
                email.send(fail_silently=False) 
                enviados += 1
            except Exception as e:
                # Si deseas ver el error real durante la depuración, usa 'raise e'.
                # De lo contrario, déjalo con un 'print' (o 'logger') para evitar fallos de servidor.
                print(f"⚠️ Error al enviar correo a {correo}: {e}") 

        messages.success(request, f"✅ Notificaciones enviadas a {enviados} asistentes.")
        return redirect('notificar_asi', evento_id=evento_id)


#############################--- Notificar Evaluadores ---##############################
@method_decorator(admin_required, name='dispatch')
class EnviarNotificacionEvaluadoresView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)

        # 🔹 Mostrar solo evaluadores "Pendiente" o "Aprobado"
        evaluador = EvaluadorEvento.objects.filter(
            eva_eve_evento_fk=evento,
            eva_eve_estado__in=["Pendiente", "Aprobado"]
        ).select_related('eva_eve_evaluador_fk__usuario')

        return render(request, 'notificar_evento_eva.html', {
            'evento': evento,
            'evaluador': evaluador
        })

    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        mensaje = request.POST.get('mensaje', '').strip()
        seleccionados = request.POST.getlist('evaluador')

        if not mensaje:
            messages.error(request, "❌ El mensaje no puede estar vacío.")
            return redirect('notificar_eva', evento_id=evento_id)

        if not seleccionados:
            messages.warning(request, "⚠️ No seleccionaste ningún asistente.")
            return redirect('notificar_eva', evento_id=evento_id)

        evaluador = EvaluadorEvento.objects.filter(
            id__in=seleccionados
        ).select_related('eva_eve_evaluador_fk__usuario')

        enviados = 0
        domain = Site.objects.get_current().domain
        logo_url = f"https://{domain}{static('img/logo.png')}"
        img_evento = evento.eve_imagen.url if evento.eve_imagen else ''

        for rel in evaluador:
            evaluador = rel.eva_eve_evaluador_fk
            correo = evaluador.usuario.email

            subject = f"📢 Notificación sobre el evento: {evento.eve_nombre}"
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <p>Hola Evaluador {evaluador.usuario.first_name} {evaluador.usuario.last_name},</p>
                <p>Tienes una nueva notificación sobre el evento <b>{evento.eve_nombre}</b>:</p>
                {'<img src="' + img_evento + '" alt="Imagen del evento" width="200"><br><br>' if img_evento else ''}
                <p>{mensaje}</p>
                <br>
                <img src="{logo_url}" alt="Logo Event-Soft" width="100"><br><br>
                <p>¡Gracias por ser parte de nuestro evento!<br>
                Equipo Event-Soft</p>
            </body>
            </html>
            """

            try:
                email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=DEFAULT_FROM_EMAIL,
                    to=[correo],
                )
                email.content_subtype = "html"
                email.send(fail_silently=False)
                enviados += 1
            except Exception as e:
                print(f"⚠️ Error al enviar correo a {correo}: {e}")

        messages.success(request, f"✅ Notificaciones enviadas a {enviados} evaluador.")
        return redirect('notificar_eva', evento_id=evento_id)



#############################--- Notificar Participantes ---##############################

@method_decorator(admin_required, name='dispatch')
class EnviarNotificacionParticipantesView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)

        # 🔹 Solo líderes o participantes individuales (no miembros de grupo)
        participantes = ParticipanteEvento.objects.filter(
            par_eve_evento_fk=evento,
            par_eve_proyecto_principal__isnull=True,  # Solo líderes o individuales
            par_eve_estado__in=["Pendiente", "Aprobado"]
        ).select_related('par_eve_participante_fk__usuario')

        return render(request, 'notificar_evento_par.html', {
            'evento': evento,
            'participantes': participantes
        })

    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        mensaje = request.POST.get('mensaje', '').strip()
        seleccionados = request.POST.getlist('participantes')

        if not mensaje:
            messages.error(request, "❌ El mensaje no puede estar vacío.")
            return redirect('notificar_par', evento_id=evento_id)

        if not seleccionados:
            messages.warning(request, "⚠️ No seleccionaste ningún participante.")
            return redirect('notificar_par', evento_id=evento_id)

        seleccionados_qs = ParticipanteEvento.objects.filter(
            id__in=seleccionados
        ).select_related('par_eve_participante_fk__usuario')

        enviados = 0
        domain = Site.objects.get_current().domain
        logo_url = f"https://{domain}{static('img/logo.png')}"
        img_evento = evento.eve_imagen.url if evento.eve_imagen else ''

        for rel in seleccionados_qs:
            # Si es líder de grupo, obtener todos los miembros
            miembros = []
            if rel.par_eve_es_grupo:
                miembros = rel.get_todos_miembros_proyecto()
            else:
                miembros = [rel]  # participante individual

            for miembro in miembros:
                participante = miembro.par_eve_participante_fk
                correo = participante.usuario.email

                subject = f"📢 Notificación sobre el evento: {evento.eve_nombre}"
                body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <p>Hola Exponente {participante.usuario.first_name} {participante.usuario.last_name},</p>
                    <p>Tienes una nueva notificación sobre el evento <b>{evento.eve_nombre}</b>:</p>
                    {'<img src="' + img_evento + '" alt="Imagen del evento" width="200"><br><br>' if img_evento else ''}
                    <p>{mensaje}</p>
                    <br>
                    <img src="{logo_url}" alt="Logo Event-Soft" width="100"><br><br>
                    <p>¡Gracias por ser parte de nuestro evento!<br>
                    Equipo Event-Soft</p>
                </body>
                </html>
                """

                try:
                    email = EmailMessage(
                        subject=subject,
                        body=body,
                        from_email=DEFAULT_FROM_EMAIL,
                        to=[correo],
                    )
                    email.content_subtype = "html"
                    email.send(fail_silently=False)
                    enviados += 1
                except Exception as e:
                    print(f"⚠️ Error al enviar correo a {correo}: {e}")

        messages.success(request, f"✅ Notificaciones enviadas a {enviados} participantes (incluyendo grupos).")
        return redirect('notificar_par', evento_id=evento_id)



