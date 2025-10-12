from io import BytesIO
from django.utils import timezone
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
import qrcode
from django.db.models import Q

from app_participantes.utils import send_mail_participante_grupo
from .models import ParticipanteEvento
from app_usuarios.models import Evaluador, Participante, Usuario
from app_admin_eventos.models import Evento, Criterio
from .forms import EditarUsuarioParticipanteForm, ParticipanteForm, MiembroParticipanteForm
from django.contrib import messages
from principal_eventos.settings import DEFAULT_FROM_EMAIL
from django.core.mail import send_mail
from django.utils.timezone import now, localtime
import random
import string
from django.utils.decorators import method_decorator
from principal_eventos.decorador import participante_required, visitor_required
from django.contrib.auth import update_session_auth_hash
from django.views.generic import DetailView
from django.db.models import Sum
from app_evaluadores.models import Calificacion
from django.contrib.auth.decorators import login_required
from app_admin_eventos.models import Evento, MemoriaEvento
from django.db import transaction
from django.contrib.auth.models import Group
from django.contrib.auth import logout
from app_asistentes.models import AsistenteEvento
from app_evaluadores.models import EvaluadorEvento
from django.contrib.auth.hashers import make_password 
from django.utils.crypto import get_random_string
from django.core.files.base import ContentFile


def crear_o_obtener_grupo_proyecto(codigo_proyecto, evento_nombre):
    # ... (Tu código de la función)
    nombre_grupo = f"Proyecto_{codigo_proyecto}_{evento_nombre[:20]}"
    grupo, created = Group.objects.get_or_create(
        name=nombre_grupo
    )
    return grupo



######## CREAR PARTICIPANTE ########
MAX_MIEMBROS_GRUPO = 5  # Incluye al líder
@method_decorator(visitor_required, name='dispatch')
class ParticipanteCreateView(View):
    """
    Vista para manejar el formulario de preinscripción de un Participante (Individual o Grupal)
    a un Evento específico.
    """
    
    # ----------------------------------------------------------------------
    # 1. GET: Mostrar el formulario de inscripción
    # ----------------------------------------------------------------------
    def get(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        form = ParticipanteForm(evento=evento) 
        return render(request, 'crear_participante.html', {
            'form': form,
            'evento': evento,
        })

    # ----------------------------------------------------------------------
    # 2. POST: Procesar el formulario de inscripción
    # ----------------------------------------------------------------------
    def post(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        form = ParticipanteForm(request.POST, request.FILES, evento=evento)
        
        documento = request.FILES.get('par_eve_documentos') 
        es_grupo = request.POST.get('tipo_participacion') == 'grupo'
        
        # Validaciones iniciales
        if not documento:
            messages.error(request, "Debe cargar el documento para continuar.")
            return render(request, 'crear_participante.html', {'form': form, 'evento': evento})

        if es_grupo:
            # === Validación de Límite de Miembros Adicionales ===
            miembros_adicionales_enviados = 0
            i = 1
            while f'miembro_{i}_cedula' in request.POST:
                cedula_miembro = request.POST.get(f'miembro_{i}_cedula')
                # Contamos si los campos esenciales del miembro están presentes.
                if cedula_miembro and request.POST.get(f'miembro_{i}_nombre') and request.POST.get(f'miembro_{i}_email'):
                    miembros_adicionales_enviados += 1
                i += 1
            
            total_personas = 1 + miembros_adicionales_enviados # Líder (1) + Adicionales
            
            if total_personas > MAX_MIEMBROS_GRUPO:
                messages.error(request, f"El grupo excede el límite. El máximo permitido es de {MAX_MIEMBROS_GRUPO} personas (incluyendo al líder). Se detectaron {total_personas}.")
                return render(request, 'crear_participante.html', {'form': form, 'evento': evento})
        # ======================================================

        if form.is_valid():
            try:
                with transaction.atomic():
                    cedula_lider = str(form.cleaned_data['cedula']).strip()
                    contrasena_generada = None 
                    
                    # ----------------------------------------------------------------
                    # A. Lógica para el Participante Líder / Individual
                    # ----------------------------------------------------------------
                    usuario_existente = Usuario.objects.filter(cedula=cedula_lider).first()
                    participante_lider = None
                    usuario = None
                    
                    if usuario_existente:
                        # 1. 🛑 Validación de Roles Cruzados (Líder) 🛑
                        if AsistenteEvento.objects.filter(asi_eve_evento_fk=evento, asi_eve_asistente_fk__usuario=usuario_existente).exists():
                            messages.error(request, f"🚫 El líder ({cedula_lider}) ya está inscrito como ASISTENTE en este evento.")
                            return render(request, 'crear_participante.html', {'form': form, 'evento': evento})
                        if EvaluadorEvento.objects.filter(eva_eve_evento_fk=evento, eva_eve_evaluador_fk__usuario=usuario_existente).exists():
                            messages.error(request, f"🚫 El líder ({cedula_lider}) ya está inscrito como EVALUADOR en este evento.")
                            return render(request, 'crear_participante.html', {'form': form, 'evento': evento})
                        
                        # Intentar obtener perfil Participante
                        try:
                            participante_existente = usuario_existente.participante 
                        except Participante.DoesNotExist:
                            participante_existente = None

                        if participante_existente:
                            # Validar que no esté ya inscrito en este evento
                            if ParticipanteEvento.objects.filter(par_eve_participante_fk=participante_existente, par_eve_evento_fk=evento).exists():
                                messages.error(request, f"Ya existe un participante con la cédula {cedula_lider} registrado para el evento '{evento.eve_nombre}'.")
                                return render(request, 'crear_participante.html', {'form': form, 'evento': evento})
                            
                            # Usuario y Perfil Participante existen (Solo actualizar datos de usuario)
                            participante_lider = participante_existente
                            usuario = usuario_existente
                            
                            usuario.first_name = form.cleaned_data['first_name']
                            usuario.last_name = form.cleaned_data['last_name']
                            usuario.telefono = form.cleaned_data['telefono']
                            usuario.username = form.cleaned_data['username']
                            usuario.rol = Usuario.Roles.PARTICIPANTE # Asegura el rol
                            usuario.save(update_fields=['first_name', 'last_name', 'telefono', 'username', 'rol'])
                            
                        else:
                            # Usuario existe, pero NO tiene perfil de Participante (Crearlo)
                            usuario_existente.first_name = form.cleaned_data['first_name']
                            usuario_existente.last_name = form.cleaned_data['last_name']
                            usuario_existente.telefono = form.cleaned_data['telefono']
                            usuario_existente.username = form.cleaned_data['username']
                            usuario_existente.rol = Usuario.Roles.PARTICIPANTE
                            usuario_existente.save(update_fields=['first_name', 'last_name', 'telefono', 'username', 'rol'])
                            
                            participante_lider = Participante.objects.create(usuario=usuario_existente)
                            usuario = usuario_existente
                            
                    else:
                        # Usuario y Participante son COMPLETAMENTE nuevos (Creación total y generación de contraseña)
                        contrasena_generada = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
                        
                        usuario = Usuario.objects.create(
                            username=form.cleaned_data['username'],
                            first_name=form.cleaned_data['first_name'],
                            last_name=form.cleaned_data['last_name'],
                            email=form.cleaned_data['email'],
                            telefono=form.cleaned_data['telefono'],
                            is_active=True,
                            date_joined=localtime(now()),
                            rol=Usuario.Roles.PARTICIPANTE,
                            cedula=cedula_lider,
                        )
                        usuario.password = make_password(contrasena_generada)
                        usuario.save(update_fields=['password'])
                        
                        participante_lider = Participante.objects.create(usuario=usuario)

                    # ----------------------------------------------------------------
                    # B. Creación de ParticipanteEvento (Registro del Proyecto)
                    # ----------------------------------------------------------------
                    participante_evento_lider = ParticipanteEvento.objects.create(
                        par_eve_evento_fk=evento,
                        par_eve_participante_fk=participante_lider,
                        par_eve_estado="Pendiente",
                        par_eve_documentos=documento,
                        par_eve_es_grupo=es_grupo,
                        # par_eve_proyecto_principal y par_eve_codigo_proyecto se manejan en el modelo/default
                    )

                    codigo_proyecto = participante_evento_lider.par_eve_codigo_proyecto 
                    correos_enviados = [usuario.email]
                    
                    # Manejo de Grupo de Django (para permisos/etc.)
                    grupo_django = None
                    if es_grupo:
                        nombre_grupo = f"{evento.eve_nombre[:20].strip()}-{codigo_proyecto}"
                        grupo_django, _ = Group.objects.get_or_create(name=nombre_grupo)
                        usuario.groups.add(grupo_django)

                    # ----------------------------------------------------------------
                    # C. Lógica para Miembros Adicionales (Si es Grupal)
                    # ----------------------------------------------------------------
                    miembros_creados = []
                    if es_grupo:
                        i = 1
                        # Iterar sobre los posibles campos de miembros (miembro_1, miembro_2, etc.)
                        while f'miembro_{i}_cedula' in request.POST:
                            cedula_miembro = request.POST.get(f'miembro_{i}_cedula')
                            nombre_miembro = request.POST.get(f'miembro_{i}_nombre')     # <--- Campo de Nombre
                            apellido_miembro = request.POST.get(f'miembro_{i}_apellido') # <--- Campo de Apellido
                            email_miembro = request.POST.get(f'miembro_{i}_email')
                            telefono_miembro = request.POST.get(f'miembro_{i}_telefono', '')

                            # Usamos nombre_miembro y apellido_miembro por separado
                            if cedula_miembro and nombre_miembro and apellido_miembro and email_miembro:
                                cedula_miembro = str(cedula_miembro).strip()
                                
                                # A diferencia de antes, YA NO NECESITAS la lógica de separación de nombre/apellido 
                                # porque los estás recibiendo separados del formulario.
                                nombre = nombre_miembro.strip()
                                apellido = apellido_miembro.strip()

                                usuario_miembro_existente = Usuario.objects.filter(cedula=cedula_miembro).first()
                                contrasena_miembro = None 
                                
                                if usuario_miembro_existente:
                                    # 🛑 Validación de Roles Cruzados (Miembro) 🛑
                                    if AsistenteEvento.objects.filter(asi_eve_evento_fk=evento, asi_eve_asistente_fk__usuario=usuario_miembro_existente).exists():
                                        messages.error(request, f"🚫 El miembro ({cedula_miembro}) ya está inscrito como ASISTENTE en este evento.")
                                        raise Exception("Error de rol cruzado.")
                                    if EvaluadorEvento.objects.filter(eva_eve_evento_fk=evento, eva_eve_evaluador_fk__usuario=usuario_miembro_existente).exists():
                                        messages.error(request, f"🚫 El miembro ({cedula_miembro}) ya está inscrito como EVALUADOR en este evento.")
                                        raise Exception("Error de rol cruzado.")

                                    # Obtener/Crear Perfil Participante para el miembro
                                    try:
                                        participante_miembro_existente = usuario_miembro_existente.participante
                                    except Participante.DoesNotExist:
                                        participante_miembro_existente = None
                                    
                                    if participante_miembro_existente:
                                        # Validar que no esté ya inscrito en este evento
                                        if ParticipanteEvento.objects.filter(par_eve_participante_fk=participante_miembro_existente, par_eve_evento_fk=evento).exists():
                                            messages.error(request, f"El miembro ({cedula_miembro}) ya está registrado para el evento '{evento.eve_nombre}'.")
                                            raise Exception("Participante ya inscrito.")

                                        participante_miembro = participante_miembro_existente
                                        usuario_miembro = participante_miembro.usuario
                                        
                                        # Actualizar datos de Usuario Existente
                                        usuario_miembro.first_name = nombre 
                                        usuario_miembro.last_name = apellido
                                        usuario_miembro.telefono = telefono_miembro
                                        usuario_miembro.rol = Usuario.Roles.PARTICIPANTE
                                        usuario_miembro.save(update_fields=['first_name', 'last_name', 'telefono', 'rol'])
                                    else:
                                        # Usuario Existe, Crear Perfil Participante
                                        usuario_miembro = usuario_miembro_existente
                                        
                                        # Actualizar datos de Usuario Existente
                                        usuario_miembro.first_name = nombre 
                                        usuario_miembro.last_name = apellido
                                        usuario_miembro.telefono = telefono_miembro
                                        usuario_miembro.rol = Usuario.Roles.PARTICIPANTE
                                        usuario_miembro.save(update_fields=['first_name', 'last_name', 'telefono', 'rol'])
                                        
                                        participante_miembro = Participante.objects.create(usuario=usuario_miembro)
                                        
                                else:
                                    # Usuario y Participante son COMPLETAMENTE nuevos (Creación total y generación de contraseña)
                                    username_miembro = f"{nombre.lower()}{cedula_miembro[-4:]}"
                                    contador = 1
                                    username_original = username_miembro
                                    # Asegurar que el username es único
                                    while Usuario.objects.filter(username=username_miembro).exists():
                                        username_miembro = f"{username_original}{contador}"
                                        contador += 1
                                    
                                    contrasena_miembro = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
                                    
                                    usuario_miembro = Usuario.objects.create(
                                        username=username_miembro,
                                        first_name=nombre, 
                                        last_name=apellido, 
                                        email=email_miembro,
                                        telefono=telefono_miembro,
                                        is_active=True,
                                        date_joined=localtime(now()),
                                        rol=Usuario.Roles.PARTICIPANTE,
                                        cedula=cedula_miembro
                                    )
                                    usuario_miembro.password = make_password(contrasena_miembro)
                                    usuario_miembro.save(update_fields=['password'])

                                    participante_miembro = Participante.objects.create(usuario=usuario_miembro)

                                # Añadir a grupo de Django y ParticipanteEvento
                                if grupo_django:
                                    usuario_miembro.groups.add(grupo_django)

                                # Crear la relación ParticipanteEvento (miembro)
                                ParticipanteEvento.objects.create(
                                    par_eve_evento_fk=evento,
                                    par_eve_participante_fk=participante_miembro,
                                    par_eve_estado="Pendiente",
                                    par_eve_es_grupo=True,
                                    par_eve_proyecto_principal=participante_evento_lider,
                                    par_eve_codigo_proyecto=codigo_proyecto,
                                )

                                # Registrar datos del miembro para el correo de notificación
                                miembros_creados.append({
                                    'nombre': nombre, # Usamos solo el nombre para el saludo
                                    'nombre_completo': f"{nombre} {apellido}", # Para el saludo completo si se requiere
                                    'email': email_miembro,
                                    'password': contrasena_miembro
                                })
                                correos_enviados.append(email_miembro)

                            i += 1
                    
                    # ----------------------------------------------------------------
                    # D. Envío de Correos y Mensajes de Éxito
                    # ----------------------------------------------------------------
                    try:
                        # Correo para Líder/Individual
                        accion_lider = "generada" if contrasena_generada else "actual (la misma que ya usas)"
                        mensaje_lider = f"Hola {usuario.first_name} {usuario.last_name},\n\n" \
                                        f"Te has registrado correctamente como {'líder del grupo' if es_grupo else 'participante'} " \
                                        f"al evento \"{evento.eve_nombre}\".\n\n" \
                                        f"Código del proyecto: {codigo_proyecto}\n"
                        if es_grupo and grupo_django:
                            mensaje_lider += f"Grupo asignado: {grupo_django.name}\n"

                        mensaje_lider += f"Puedes ingresar con tu correo: {usuario.email}\n" \
                                         f"Tu contraseña es: {contrasena_generada if contrasena_generada else 'la que ya tenías'}. "

                        send_mail(
                            subject=f"🎟️ Registro exitoso - Evento \"{evento.eve_nombre}\" - Líder/Participante",
                            message=mensaje_lider,
                            from_email=None,
                            recipient_list=[usuario.email],
                            fail_silently=False
                        )

                        # Correo para Miembros (si es grupo)
                        if es_grupo:
                            for miembro in miembros_creados:
                                accion_miembro = "generada" if miembro['password'] else "actual"
                                # Usamos 'nombre_completo' para el saludo del correo del miembro
                                mensaje_miembro = f"Hola {miembro['nombre_completo']},\n\n" \
                                                  f"Has sido registrado como miembro del grupo para el evento \"{evento.eve_nombre}\".\n\n" \
                                                  f"Código del proyecto: {codigo_proyecto}\n" \
                                                  f"Grupo asignado: {grupo_django.name}\n" \
                                                  f"Líder: {usuario.first_name} {usuario.last_name}\n" \
                                                  f"Puedes ingresar con tu correo: {miembro['email']}\n" \
                                                  f"Tu contraseña es: {miembro['password'] if miembro['password'] else 'la que ya tenías'}. "
                                
                                send_mail(
                                    subject=f"🎟️ Registro exitoso - Evento \"{evento.eve_nombre}\" - Miembro del grupo",
                                    message=mensaje_miembro,
                                    from_email=None,
                                    recipient_list=[miembro['email']],
                                    fail_silently=False
                                )

                    except Exception as e:
                        messages.warning(request, f"Registro exitoso, pero hubo un problema al enviar algunos correos: {e}")

                    tipo_mensaje = "grupal" if es_grupo else "individual"
                    mensaje_exito = f"La preinscripción {tipo_mensaje} fue exitosa al evento \"{evento.eve_nombre}\". " \
                                    f"Código del proyecto: {codigo_proyecto}. " \
                                    f"Revisa {'los correos' if es_grupo else 'tu correo'} para obtener las credenciales."
                    messages.success(request, mensaje_exito)
                    return redirect('pagina_principal') # Redirección a la página principal (o la que corresponda)

            except Exception as e:
                # Si una excepción fue lanzada (como en el error de rol cruzado), el transaction.atomic() se encargará del rollback
                if not messages.get_messages(request): # Si no hay mensajes de error previos (como el de rol cruzado)
                    messages.error(request, f"Ocurrió un error grave durante el registro: {str(e)}")
                
                return render(request, 'crear_participante.html', {
                    'form': form,
                    'evento': evento,
                })

        # Si el formulario no es válido
        return render(request, 'crear_participante.html', {
            'form': form,
            'evento': evento,
        })




#Ocurrió un error grave durante el registro: cannot access local variable 'make_password' where it is not associated with a value


######## CANCELAR PREINSCRIPCION PARTICIPANTE ########

@method_decorator(participante_required, name='dispatch')
class EliminarParticipanteView(View):
    def get(self, request, participante_id):
        # Aseguramos que el ID del participante coincida con el usuario logueado por seguridad (aunque participante_required ya ayuda)
        participante = get_object_or_404(Participante, id=participante_id)
        usuario = participante.usuario

        # 🔹 Buscar todas las inscripciones del participante
        inscripciones = ParticipanteEvento.objects.filter(par_eve_participante_fk=participante)

        # 🔹 Verificar si tiene inscripciones activas (aprobadas)
        # Esto previene la eliminación del perfil si está activamente asignado a un evento.
        tiene_inscripciones_activas = inscripciones.filter(par_eve_estado="Aprobado").exists()
        if tiene_inscripciones_activas:
            messages.error(
                request,
                "❌ No puedes eliminar tu perfil de Exponente mientras tengas inscripciones activas. "
                "Por favor, cancela tus inscripciones antes de eliminar tu perfil."
            )
            return redirect('pagina_principal')


        # 🔹 Obtener el último evento inscrito (para referencia en el correo)
        ultimo_evento = inscripciones.first()
        nombre_evento = ultimo_evento.par_eve_evento_fk.eve_nombre if ultimo_evento else "uno de nuestros eventos"

        # 🔑 PASO 1: ELIMINAR LA RELACIÓN (Perfil) PARTICIPANTE
        # Esto elimina automáticamente todas las inscripciones en ParticipanteEvento (por CASCADE)
        participante.delete()
        

        # 🔹 Enviar correo
        if usuario.email:
             try:
                send_mail(
                    subject='🗑️ Notificación de eliminación de perfil como Exponente',
                    message=(
                        f'Estimado/a {usuario.first_name},\n\n'
                        f'Le informamos que su perfil de **Exponente** ha sido eliminado correctamente de Event-Soft.\n\n'
                        f'Todos sus datos de evaluación en eventos como "{nombre_evento}" '
                        f'han sido eliminados. **Su cuenta de usuario principal no ha sido eliminada**.\n\n'
                        f'Si desea volver a inscribirse como Exponente en el futuro, puede hacerlo usando su cuenta existente.\n\n'
                        f'Atentamente,\nEquipo de organización de eventos.'
                    ),
                    from_email=DEFAULT_FROM_EMAIL,
                    recipient_list=[usuario.email],
                    fail_silently=False
                )
             except Exception:
                 messages.warning(request, "El perfil de Exponente fue eliminado, pero no se pudo enviar el correo de notificación.")

        # 🔹 Cerrar sesión del usuario
        logout(request)

        messages.success(request, "✅ Tu perfil de Exponente y tus inscripciones han sido eliminadas correctamente. Hemos cerrado tu sesión.")
        return redirect('pagina_principal')




########### VER INFORMACIÓN EVENTO ###########
@method_decorator(participante_required, name='dispatch')
class EventoDetailView(DetailView):
    model = Evento
    template_name = 'info_evento_evento_par.html'
    context_object_name = 'evento'
    pk_url_kwarg = 'pk'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evento = self.get_object()
        participante_id = self.request.session.get('participante_id')
        
        # Verificar si el participante está asignado a este evento
        if participante_id:
            participante = get_object_or_404(Participante, id=participante_id)
            if not ParticipanteEvento.objects.filter(par_eve_participante_fk=participante, par_eve_evento_fk=evento).exists():
                messages.error(self.request, "No tienes permiso para ver este evento.")
                return redirect('pagina_principal')

        context['participante'] = participante if participante_id else None
        return context



######## DASHBOARD PARTICIPANTE ########
@method_decorator(participante_required, name='dispatch')
class DashboardParticipanteView(View):
    template_name = 'dashboard_principal_participante.html'

    def get(self, request):
        participante_id = request.session.get('participante_id')
        if not participante_id:
            messages.error(request, "Debe iniciar sesión como participante.")
            return redirect('login_view')

        try:
            participante = Participante.objects.get(id=participante_id)
        except Participante.DoesNotExist:
            messages.error(request, "Participante no encontrado.")
            return redirect('login_view')

        # Relación participante-evento: obtenemos todas las inscripciones del participante
        relaciones = ParticipanteEvento.objects.filter(
            par_eve_participante_fk=participante
        ).select_related('par_eve_evento_fk')

        # Separar eventos aprobados y pendientes
        eventos_aprobados = [rel.par_eve_evento_fk for rel in relaciones if rel.par_eve_estado == 'Aprobado']
        eventos_pendientes = [rel.par_eve_evento_fk for rel in relaciones if rel.par_eve_estado == 'Pendiente']

        # Obtener el primer registro de relación para el link "Editar Perfil" en el header
        relacion_perfil = relaciones.first()
        
        # Diccionarios para almacenar datos por evento
        criterios_completos = {}
        calificaciones_registradas = {}
        
        # ✅ NUEVAS ESTRUCTURAS DE DATOS PARA LIDERAZGO Y CONTEO DE MIEMBROS
        es_lider_proyecto = {}
        miembros_proyecto_count = {}
        relacion_actual_por_evento = {}


        for evento in eventos_aprobados:
            # Encontrar la relación específica para el participante actual en este evento
            rel_actual = ParticipanteEvento.objects.filter(
                par_eve_evento_fk=evento,
                par_eve_participante_fk=participante
            ).first()
            
            if rel_actual:
                relacion_actual_por_evento[evento.id] = rel_actual
                
                # Lógica de Liderazgo
                # El usuario es líder si su propio registro NO apunta a otro como principal (es decir, el campo es NULL)
                # O si su registro es el principal (código de proyecto) y el evento permite grupos.
                # Asumiremos que es líder si par_eve_proyecto_principal es NULL.
                lider = rel_actual.par_eve_proyecto_principal is None 
                es_lider_proyecto[evento.id] = lider

                # Lógica de Conteo de Miembros
                if lider:
                    # Si es líder, contamos su propio registro (par_eve_proyecto_principal=NULL) 
                    # más todos los registros que apuntan a él.
                    conteo = ParticipanteEvento.objects.filter(
                        par_eve_evento_fk=evento,
                        par_eve_proyecto_principal=rel_actual # Registros que apuntan al líder
                    ).count() + 1 # +1 para incluir al líder mismo (donde es NULL)
                    
                    miembros_proyecto_count[evento.id] = conteo
                else:
                    # Si no es líder, el conteo se basa en el registro principal al que apunta
                    if rel_actual.par_eve_proyecto_principal:
                        lider_rel = rel_actual.par_eve_proyecto_principal
                        conteo = ParticipanteEvento.objects.filter(
                            par_eve_evento_fk=evento,
                            par_eve_proyecto_principal=lider_rel 
                        ).count() + 1 # +1 para incluir al líder
                        miembros_proyecto_count[evento.id] = conteo
                    else:
                        miembros_proyecto_count[evento.id] = 1 # Caso de proyecto individual sin apuntador principal
                
                # Lógica de Criterios (mantener la original)
                suma = Criterio.objects.filter(cri_evento_fk=evento).aggregate(total=Sum('cri_peso'))['total'] or 0
                criterios_completos[evento.id] = (suma == 100)

                # Lógica de Calificaciones (mantener la original)
                calificaciones_registradas[evento.id] = rel_actual.calificacion is not None
            
            else:
                # Caso de seguridad: si no hay relación (aunque debería haberla al estar en eventos_aprobados)
                es_lider_proyecto[evento.id] = False
                miembros_proyecto_count[evento.id] = 1 # Asumimos 1 si no hay relación clara
                criterios_completos[evento.id] = False
                calificaciones_registradas[evento.id] = False


        context = {
            'participante': participante,
            'eventos': eventos_aprobados,
            'eventos_pendientes': eventos_pendientes,
            'relacion': relacion_perfil, # Usamos la primera relación para el link del perfil
            'criterios_completos': criterios_completos,
            'calificaciones_registradas': calificaciones_registradas,
            # NUEVAS VARIABLES
            'es_lider_proyecto': es_lider_proyecto,
            'miembros_proyecto_count': miembros_proyecto_count,
            'relacion_actual_por_evento': relacion_actual_por_evento, # Puede ser útil para otros datos
        }

        return render(request, self.template_name, context)



##################### --- Cambio de Contraseña Participante --- #####################

@method_decorator(participante_required, name='dispatch')
class CambioPasswordParticipanteView(View):
    template_name = 'cambio_password_participante.html'

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

        participante_id = request.session.get('participante_id')
        participante = get_object_or_404(Participante, pk=participante_id)
        usuario = participante.usuario

        usuario.set_password(password1)
        usuario.last_login = timezone.now()  # ✅ Se actualiza solo aquí
        usuario.save()

        messages.success(request, "✅ Contraseña cambiada correctamente.")
        return redirect('dashboard_participante')

######### EDITAR PREINSCRIPCION PARTICIPANTE ########
@method_decorator(participante_required, name='dispatch')
class EditarPreinscripcionView(View):
    template_name = 'editar_preinscripcion_participante.html'

    def get(self, request, id):
        # La relación actual (puede ser líder o miembro)
        relacion_actual = get_object_or_404(ParticipanteEvento, pk=id)
        participante = relacion_actual.par_eve_participante_fk
        evento = relacion_actual.par_eve_evento_fk
        form = EditarUsuarioParticipanteForm(instance=participante.usuario)

        # 🔹 LÓGICA CLAVE PARA IDENTIFICAR AL LÍDER Y OBTENER EL DOCUMENTO
        # 1. Determinar si el usuario actual es el líder:
        #    Es líder si par_eve_proyecto_principal es NULL (es el registro principal)
        es_lider_del_proyecto = relacion_actual.par_eve_proyecto_principal is None 
        
        # 2. Encontrar la relación que posee el documento (la del líder/proyecto principal):
        if es_lider_del_proyecto:
            # Si es el líder, su propia relación (relacion_actual) es la que tiene el documento.
            relacion_documento_principal = relacion_actual
        else:
            # Si es un miembro, buscamos el registro principal asociado.
            relacion_documento_principal = relacion_actual.par_eve_proyecto_principal
            # Nos aseguramos de que el líder del proyecto exista para el miembro.
            if not relacion_documento_principal:
                 # Esto debería ser raro si la lógica de inscripción es correcta, pero es una buena salvaguarda.
                messages.error(request, "Error: El proyecto principal no fue encontrado.")
                return redirect('dashboard_participante')
                

        # 🔹 Traer todas las relaciones donde está inscrito (para la lista de eventos)
        todas_relaciones = ParticipanteEvento.objects.filter(
            par_eve_participante_fk=participante
        ).select_related("par_eve_evento_fk")


        return render(request, self.template_name, {
            'form': form,
            'evento': evento,
            'relacion': relacion_actual, # La relación del usuario actual
            'usuario': participante.usuario,
            'participante': participante,
            'todas_relaciones': todas_relaciones,
            # NUEVAS VARIABLES
            'es_lider_del_proyecto': es_lider_del_proyecto,
            'relacion_principal': relacion_documento_principal # Relación que tiene el campo 'par_eve_documentos'
        })

    def post(self, request, id):
        relacion_actual = get_object_or_404(ParticipanteEvento, pk=id)
        participante = relacion_actual.par_eve_participante_fk
        evento = relacion_actual.par_eve_evento_fk
        usuario = participante.usuario
        form = EditarUsuarioParticipanteForm(request.POST, instance=usuario)
        
        # Lógica de identificación de líder, igual que en GET
        es_lider_del_proyecto = relacion_actual.par_eve_proyecto_principal is None
        if es_lider_del_proyecto:
            relacion_documento_principal = relacion_actual
        elif relacion_actual.par_eve_proyecto_principal:
             relacion_documento_principal = relacion_actual.par_eve_proyecto_principal
        else:
            messages.error(request, "Error: El proyecto principal no fue encontrado.")
            return redirect('dashboard_participante')


        # Contraseñas
        contrasena_actual = request.POST.get('nueva_contrasena')
        nueva_contrasena = request.POST.get('confirmar_contrasena_nueva')
        confirmar_nueva = request.POST.get('confirmar_contrasena')

        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.ultimo_acceso = localtime(now())

            # Validar y cambiar la contraseña (Lógica completa)
            if contrasena_actual or nueva_contrasena or confirmar_nueva:
                if not contrasena_actual or not nueva_contrasena or not confirmar_nueva:
                    messages.error(request, "Debe completar los tres campos de contraseña para realizar el cambio.")
                    return redirect('editar_preinscripcion', id=id)

                if not usuario.check_password(contrasena_actual):
                    messages.error(request, "La contraseña actual no es correcta.")
                    return redirect('editar_preinscripcion', id=id)
                if nueva_contrasena != confirmar_nueva:
                    messages.error(request, "La nueva contraseña y su confirmación no coinciden.")
                    return redirect('editar_preinscripcion', id=id)
                if len(nueva_contrasena) < 6:
                    messages.error(request, "La nueva contraseña debe tener al menos 6 caracteres.")
                    return redirect('editar_preinscripcion', id=id)

                usuario.set_password(nueva_contrasena)
                update_session_auth_hash(request, usuario)
            
            usuario.save()

            # 🔹 LÓGICA DE ACTUALIZACIÓN DE DOCUMENTO (SOLO PARA EL LÍDER)
            file_key = "par_eve_documentos" # El input ahora tiene un nombre genérico en el template
            documento = request.FILES.get(file_key)
            
            if documento:
                if es_lider_del_proyecto and relacion_documento_principal.par_eve_estado != "Aprobado":
                    relacion_documento_principal.par_eve_documentos = documento
                    relacion_documento_principal.save()
                elif not es_lider_del_proyecto:
                    messages.error(request, "🚫 Solo el líder del proyecto puede subir o actualizar el documento de exposición.")
                elif relacion_documento_principal.par_eve_estado == "Aprobado":
                    messages.warning(request, f"El documento del evento {relacion_documento_principal.par_eve_evento_fk.eve_nombre} ya está aprobado. No puedes subir un nuevo documento.")

            messages.success(request, "Tu información de perfil fue actualizada correctamente.")
            return redirect('editar_preinscripcion', id=id)

        # Si el formulario no es válido, volvemos a renderizar
        todas_relaciones = ParticipanteEvento.objects.filter(par_eve_participante_fk=participante).select_related("par_eve_evento_fk")
        relacion_documento_principal = relacion_actual if es_lider_del_proyecto else relacion_actual.par_eve_proyecto_principal

        return render(request, self.template_name, {
            'form': form,
            'evento': evento,
            'relacion': relacion_actual,
            'usuario': participante.usuario,
            'participante': participante,
            'todas_relaciones': todas_relaciones,
            'es_lider_del_proyecto': es_lider_del_proyecto,
            'relacion_principal': relacion_documento_principal
        })




####### ACCESO A EVENTO ######
@method_decorator(participante_required, name='dispatch')
class IngresoEventoParticipanteView(View):
    template_name = 'ingreso_evento_par.html'

    def get(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        participante = get_object_or_404(Participante, usuario=request.user)
        participante_evento = get_object_or_404(ParticipanteEvento, par_eve_evento_fk=evento, par_eve_participante_fk=participante)

        context = {
            'evento': evento,
            'participante': participante_evento  # este es el objeto que tiene el QR y el soporte
        }
        return render(request, self.template_name, context)
  


####### VER CRITERIOS ######
@method_decorator(participante_required, name='dispatch')
class VerCriteriosParticipanteView(View):
    template_name = 'ver_criterios_par.html'

    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)
        criterios = Criterio.objects.filter(cri_evento_fk=evento).order_by('cri_descripcion')
        participante = get_object_or_404(Participante, id=request.session['participante_id'])

        return render(request, self.template_name, {
            'evento': evento,
            'criterios': criterios,
            'participante': participante,
        })
    


####### VER CALIFICACIÓN ######
@method_decorator(participante_required, name='dispatch')
class VerCalificacionView(View):
    template_name = 'ver_notas.html'

    def get(self, request, evento_id):
        participante_id = request.session.get('participante_id')
        participante = get_object_or_404(Participante, pk=participante_id)
        evento = get_object_or_404(Evento, pk=evento_id)

        # Obtener relación del participante con el evento
        relacion = get_object_or_404(
            ParticipanteEvento,
            par_eve_evento_fk=evento,
            par_eve_participante_fk=participante
        )

        # Calificación del participante actual
        calificacion = relacion.calificacion

        # Obtener todos los participantes con calificación para este evento (para ranking)
        relaciones = ParticipanteEvento.objects.filter(
            par_eve_evento_fk=evento,
            calificacion__isnull=False
        ).select_related('par_eve_participante_fk__usuario').order_by('-calificacion')

        puesto_actual = None
        for index, rel in enumerate(relaciones, start=1):
            if rel.par_eve_participante_fk.pk == participante.pk:
                puesto_actual = index
                break

        context = {
            'evento': evento,
            'participante': participante,
            'nombre_limpio': participante.usuario.first_name,
            'apellido_limpio': participante.usuario.last_name,
            'calificacion': calificacion,
            'puesto_actual': puesto_actual,
        }
        return render(request, self.template_name, context)

####### VER DETALLE CALIFICACIÓN ######
@method_decorator(participante_required, name='dispatch')
class DetalleCalificacionView(View):
    template_name = 'ver_detalle_calificacion.html'

    def get(self, request, evento_id):
        participante_id = request.session.get('participante_id')
        participante = get_object_or_404(Participante, pk=participante_id)
        evento = get_object_or_404(Evento, id=evento_id)

        participante_evento = get_object_or_404(
            ParticipanteEvento,
            par_eve_evento_fk=evento,
            par_eve_participante_fk=participante
        )

        calificaciones = Calificacion.objects.filter(
            cal_participante_fk=participante,
            cal_criterio_fk__cri_evento_fk=evento
        ).select_related('cal_criterio_fk', 'cal_evaluador_fk')

        context = {
            'participante': participante,
            'evento': evento,
            'participante_evento': participante_evento,
            'calificaciones': calificaciones,
        }
        return render(request, self.template_name, context)
    
####### VER MEMORIAS DE PARTICIPANTE ######
@method_decorator(login_required, name='dispatch')
class MemoriasParticipanteView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        # Verificar inscripción como participante
        inscrito = ParticipanteEvento.objects.filter(
            par_eve_evento_fk=evento,
            par_eve_participante_fk__usuario=request.user
        ).exists()
        if not inscrito:
            messages.error(request, "❌ No estás inscrito como participante en este evento.")
            return redirect('dashboard_user')
        memorias = MemoriaEvento.objects.filter(evento=evento).order_by('-subido_en')
        return render(request, 'memorias_participante.html', {'evento': evento, 'memorias': memorias})

@method_decorator(login_required, name='dispatch')  # Puedes reemplazarlo luego por participante_required
class ParticipanteCancelacionView(View):

    def post(self, request, evento_id):
        """
        Permite al participante cancelar su inscripción al evento.
        Si es líder de grupo, cancela también la inscripción de todos los miembros.
        """

        # 1️⃣ Obtener el participante logueado
        participante = get_object_or_404(Participante, usuario=request.user)

        # 2️⃣ Obtener la inscripción activa del participante en ese evento
        inscripcion = ParticipanteEvento.objects.filter(
            par_eve_participante_fk=participante,
            par_eve_evento_fk_id=evento_id
        ).select_related('par_eve_evento_fk').first()

        if not inscripcion:
            messages.error(request, "❌ No se encontró tu inscripción activa en este evento.")
            return redirect('dashboard_participante')

        # 3️⃣ Verificar propiedad
        if inscripcion.par_eve_participante_fk.usuario != request.user:
            return HttpResponseForbidden("No tienes permiso para cancelar esta inscripción.")

        # 4️⃣ Si ya estaba cancelada
        if inscripcion.par_eve_estado.upper() == 'Cancelado':
            messages.warning(request, "⚠️ Esta inscripción ya se encuentra cancelada.")
            return redirect('dashboard_participante')

        # 5️⃣ Cancelar inscripción (con manejo de grupos)
        with transaction.atomic():
            evento = inscripcion.par_eve_evento_fk

            if inscripcion.es_lider_proyecto:
                # Caso: LÍDER DE GRUPO
                miembros = inscripcion.get_todos_miembros_proyecto()

                for miembro in miembros:
                    if miembro.par_eve_estado.upper() != 'Cancelado':
                        miembro.par_eve_estado = 'Cancelado'
                        miembro.save()

                messages.success(
                    request,
                    f"✅ Tu proyecto en el evento '{evento.eve_nombre}' ha sido Cancelado. "
                    "Todos los miembros han sido notificados."
                )
            else:
                # Caso: PARTICIPANTE INDIVIDUAL o MIEMBRO DE GRUPO
                inscripcion.par_eve_estado = 'Cancelado'
                inscripcion.save()

                messages.success(
                    request,
                    f"✅ Tu inscripción individual al evento '{evento.eve_nombre}' ha sido cancelada."
                )

        # 6️⃣ Redirigir al dashboard del participante
        return redirect('dashboard_participante')

    





############# AGREGAR MIEMBROS ################
@method_decorator(login_required, name='dispatch') 
class AgregarMiembrosView(View):
    template_name = 'agregar_miembros.html'
    
    # Máximo permitido de miembros en un grupo (incluido el líder)
    MAX_MIEMBROS = 5

    def get(self, request, evento_id):
        participante_lider_id = request.session.get('participante_id')
        if not participante_lider_id:
            messages.error(request, "Error de sesión. No se encontró el ID del líder.")
            return redirect('login_view')

        lider = get_object_or_404(Participante, id=participante_lider_id)
        evento = get_object_or_404(Evento, id=evento_id)
        
        # Obtener el registro principal del LÍDER (es_grupo=1 y principal=NULL)
        relacion_lider = get_object_or_404(
            ParticipanteEvento, 
            par_eve_participante_fk=lider, 
            par_eve_evento_fk=evento,
            par_eve_es_grupo=1, 
            par_eve_proyecto_principal__isnull=True 
        )
        
        # Contar miembros: (Miembros que apuntan al líder) + 1 (el líder)
        miembros_actuales = ParticipanteEvento.objects.filter(
            par_eve_evento_fk=evento,
            par_eve_proyecto_principal=relacion_lider
        ).count() + 1 
        
        if miembros_actuales >= self.MAX_MIEMBROS:
            messages.error(request, f"El grupo del evento {evento.eve_nombre} ya alcanzó el máximo de {self.MAX_MIEMBROS} miembros.")
            return redirect('dashboard_participante')
            
        form = MiembroParticipanteForm() 
        
        return render(request, self.template_name, {
            'form': form,
            'evento': evento,
            'miembros_actuales': miembros_actuales,
            'max_miembros': self.MAX_MIEMBROS,
        })

    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        participante_lider_id = request.session.get('participante_id')
        lider = get_object_or_404(Participante, id=participante_lider_id)
        
        # Obtener el registro principal del LÍDER
        relacion_lider = get_object_or_404(
            ParticipanteEvento, 
            par_eve_participante_fk=lider, 
            par_eve_evento_fk=evento,
            par_eve_es_grupo=1, 
            par_eve_proyecto_principal__isnull=True 
        )
        
        miembros_actuales = ParticipanteEvento.objects.filter(
            par_eve_evento_fk=evento,
            par_eve_proyecto_principal=relacion_lider
        ).count() + 1
        
        if miembros_actuales >= self.MAX_MIEMBROS:
            messages.error(request, f"El grupo del evento {evento.eve_nombre} ya alcanzó el máximo de {self.MAX_MIEMBROS} miembros.")
            return redirect('dashboard_participante')

        form = MiembroParticipanteForm(request.POST)

        if form.is_valid():
            cedula = form.cleaned_data['cedula']
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            telefono = form.cleaned_data['telefono']

            # 1. Validación de unicidad de Usuario
            if Usuario.objects.filter(cedula=cedula).exists() or \
               Usuario.objects.filter(username=username).exists() or \
               Usuario.objects.filter(email=email).exists():
                messages.error(request, "Error: Cédula, nombre de usuario o correo ya existen.")
                return redirect('agregar_miembro_par', evento_id=evento_id)

            contrasena_temporal = get_random_string(length=10)
            
            try:
                with transaction.atomic():
                    # 1. Crear el nuevo Usuario con el rol establecido
                    nuevo_usuario = Usuario.objects.create(
                        cedula=cedula,
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        telefono=telefono,
                        is_active=True,
                        password=make_password(contrasena_temporal),
                        last_login=None,
                        rol='PARTICIPANTE'  # Rol fijo para miembros
                    )
                    
                    # 2. Asignar el nuevo Usuario al Grupo del Evento (app_usuarios_usuario_groups)
                    codigo_proyecto = relacion_lider.par_eve_codigo_proyecto 
                    
                    # Búsqueda robusta por el código de proyecto
                    evento_group = Group.objects.filter(name__icontains=codigo_proyecto).first()
                    
                    if not evento_group:
                         raise Group.DoesNotExist(f"No se encontró el grupo de Django cuyo nombre contiene el código de proyecto: {codigo_proyecto}. Por favor, verifique la tabla auth_group.")

                    nuevo_usuario.groups.add(evento_group) # CREA LA RELACIÓN

                    # 3. Crear el registro de Participante
                    nuevo_participante = Participante.objects.create(
                        usuario=nuevo_usuario
                    )
                    
                    # 4. Crear el registro en ParticipanteEvento para el MIEMBRO (CORREGIDO)
                    nueva_relacion = ParticipanteEvento(
                        par_eve_participante_fk=nuevo_participante,
                        par_eve_evento_fk=evento,
                        par_eve_estado='Aprobado',
                        
                        # --- CORRECCIONES SOLICITADAS ---
                        par_eve_es_grupo=0, # 0 para miembros
                        par_eve_proyecto_principal=relacion_lider, # Apunta al ID del líder
                        par_eve_codigo_proyecto=None, # Solo el líder tiene el código
                        # --------------------------------
                    )

                    # Lógica de generación de CLAVE y QR
                    clave_acceso = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                    nueva_relacion.par_eve_clave = clave_acceso
                    qr_data = f"Participante: {nuevo_usuario.username}, Evento: {evento.eve_nombre}, Clave: {clave_acceso}"
                    qr_img = qrcode.make(qr_data)
                    buffer = BytesIO()
                    qr_img.save(buffer, format='PNG')
                    file_name = f"qr_participante_{nuevo_participante.id}.png"
                    nueva_relacion.par_eve_qr.save(file_name, ContentFile(buffer.getvalue()), save=False)
                    nueva_relacion.save()

                # 5. Envío de correo electrónico
                try:
                    qr_file_path = nueva_relacion.par_eve_qr.path 
                    send_mail_participante_grupo(
                        to_email=nuevo_usuario.email,
                        event_name=evento.eve_nombre,
                        group_name='Participante', 
                        username=nuevo_usuario.username,
                        password=contrasena_temporal,
                        clave_acceso=clave_acceso,
                        qr_file_path=qr_file_path
                    )
                    messages.success(request, f"Miembro **{nuevo_usuario.username}** agregado y correo de bienvenida enviado. 🎉")
                except Exception as e:
                    messages.warning(request, f"Miembro **{nuevo_usuario.username}** agregado. ¡PERO! Hubo un error al enviar el correo. Verifique la configuración. 📧")
                    
                return redirect('dashboard_participante')

            except Group.DoesNotExist as e:
                messages.error(request, f"Error de configuración de Grupo: {e}")
                return redirect('agregar_miembro_par', evento_id=evento_id)
            except Exception as e:
                messages.error(request, f"Ocurrió un error al guardar el miembro: {e}")
                return redirect('agregar_miembro_par', evento_id=evento_id)
        
        # Si el formulario no es válido, renderizar de nuevo con errores
        miembros_actuales = ParticipanteEvento.objects.filter(
            par_eve_evento_fk=evento,
            par_eve_proyecto_principal=relacion_lider
        ).count() + 1
        
        return render(request, self.template_name, {
            'form': form,
            'evento': evento,
            'miembros_actuales': miembros_actuales,
            'max_miembros': self.MAX_MIEMBROS,
        })


@method_decorator(login_required, name='dispatch') 
class ListaMiembrosView(View):
    template_name = 'lista_miembros.html'
    MAX_MIEMBROS = 5

    def _get_context_data(self, request, evento_id):
        # ... (La función auxiliar _get_context_data se mantiene sin cambios) ...
        participante_logueado_id = request.session.get('participante_id')
        if not participante_logueado_id:
            return None, None, None, None, "Error de sesión. No se encontró el ID del participante logueado."

        participante = get_object_or_404(Participante, id=participante_logueado_id)
        evento = get_object_or_404(Evento, id=evento_id)

        try:
            relacion_participante = ParticipanteEvento.objects.get(
                par_eve_participante_fk=participante, 
                par_eve_evento_fk=evento,
            )
        except ParticipanteEvento.DoesNotExist:
            return None, None, None, None, "No estás registrado como participante en este evento."

        if relacion_participante.par_eve_es_grupo == 1 and relacion_participante.par_eve_proyecto_principal is None:
            es_lider = True
            relacion_lider = relacion_participante
        elif relacion_participante.par_eve_es_grupo == 0 and relacion_participante.par_eve_proyecto_principal is not None:
            es_lider = False
            relacion_lider = relacion_participante.par_eve_proyecto_principal
        else:
            return None, None, None, None, "Error en la estructura del grupo de participación."

        miembros_del_grupo = ParticipanteEvento.objects.filter(
            Q(par_eve_evento_fk=evento) &
            (Q(par_eve_proyecto_principal=relacion_lider) | Q(id=relacion_lider.id))
        ).select_related('par_eve_participante_fk__usuario').order_by('-par_eve_es_grupo', 'par_eve_participante_fk__usuario__first_name') 
        
        miembros_actuales = miembros_del_grupo.count()
        
        miembros_a_borrar = [
            rel for rel in miembros_del_grupo if rel.par_eve_es_grupo == 0
        ]
        
        context = {
            'evento': evento,
            'relacion_lider': relacion_lider,
            'es_lider': es_lider, 
            'miembros': miembros_del_grupo,
            'miembros_a_borrar': miembros_a_borrar,
            'miembros_actuales': miembros_actuales,
            'max_miembros': self.MAX_MIEMBROS,
        }
        return context, participante, relacion_lider, es_lider, None
    # ----------------------------------------------------------------------------------

    def get(self, request, evento_id):
        # ... (get se mantiene igual) ...
        context, _, _, _, error_msg = self._get_context_data(request, evento_id)
        
        if error_msg:
            messages.error(request, error_msg)
            return redirect('dashboard_participante')
            
        return render(request, self.template_name, context)

    
    def post(self, request, evento_id):
        action = request.POST.get('action', 'eliminar')
        miembro_id_objetivo = request.POST.get('miembro_id')

        # ... (Validaciones iniciales de miembro_id, contexto, y es_lider se mantienen) ...
        if not miembro_id_objetivo:
            messages.error(request, "No se especificó el miembro objetivo.")
            return redirect('ver_miembros_par', evento_id=evento_id)

        context, _, relacion_lider_actual, es_lider, error_msg = self._get_context_data(request, evento_id)
        
        if error_msg:
            messages.error(request, error_msg)
            return redirect('dashboard_participante')
        
        if not es_lider:
            messages.error(request, "Solo el líder del grupo puede realizar esta acción.")
            return redirect('ver_miembros_par', evento_id=evento_id)

        # 1. Buscar la relación ParticipanteEvento del miembro objetivo
        try:
            relacion_miembro_objetivo = ParticipanteEvento.objects.get(
                id=miembro_id_objetivo,
                par_eve_proyecto_principal=relacion_lider_actual, 
                par_eve_es_grupo=0 # Debe ser un miembro
            )
        except ParticipanteEvento.DoesNotExist:
            messages.error(request, "El miembro no existe o no pertenece a tu grupo.")
            return redirect('ver_miembros_par', evento_id=evento_id)
        
        usuario_miembro = relacion_miembro_objetivo.par_eve_participante_fk.usuario
        nombre_miembro = f"{usuario_miembro.first_name} {usuario_miembro.last_name} ({usuario_miembro.username})"

        # -----------------------------------------------------------------
        # LÓGICA DE ELIMINAR MIEMBRO (Se mantiene igual)
        # -----------------------------------------------------------------
        if action == 'eliminar':
            # ... (Lógica de eliminación anterior) ...
            try:
                with transaction.atomic():
                    relacion_miembro_objetivo.delete()
                    relacion_miembro_objetivo.par_eve_participante_fk.usuario.delete() 
                    messages.success(request, f"El miembro **{usuario_miembro.first_name}** ha sido eliminado del grupo. 🗑️")
            except Exception as e:
                messages.error(request, f"Error al intentar eliminar al miembro: {e}")
            
            return redirect('ver_miembros_par', evento_id=evento_id)

        # -----------------------------------------------------------------
        # LÓGICA DE TRANSFERIR LIDERAZGO (CORREGIDA Y OPTIMIZADA)
        # -----------------------------------------------------------------
        elif action == 'transferir_liderazgo':
            try:
                with transaction.atomic():
                    
                    # El registro del LÍDER ACTUAL es 'relacion_lider_actual'
                    # El registro del NUEVO LÍDER es 'relacion_miembro_objetivo'
                    
                    # 1. Capturar los datos del proyecto del líder actual (código y documentos)
                    codigo_proyecto_antiguo = relacion_lider_actual.par_eve_codigo_proyecto
                    documentos_antiguos = getattr(relacion_lider_actual, 'par_eve_documentos', None) 

                    # 2. Promover al Miembro a Líder (Nuevo Líder)
                    # NOTA: Guardamos los cambios de liderazgo/código/documentos antes
                    # de actualizar a los demás miembros en el paso 4.
                    relacion_miembro_objetivo.par_eve_es_grupo = 1
                    relacion_miembro_objetivo.par_eve_proyecto_principal = None # El líder no tiene principal
                    relacion_miembro_objetivo.par_eve_codigo_proyecto = codigo_proyecto_antiguo # HEREDA CÓDIGO
                    relacion_miembro_objetivo.par_eve_documentos = documentos_antiguos # HEREDA DOCUMENTOS
                    relacion_miembro_objetivo.save() 
                    
                    # 3. Degradar al Líder Actual a Miembro (Antiguo Líder)
                    relacion_lider_actual.par_eve_es_grupo = 0
                    relacion_lider_actual.par_eve_proyecto_principal = relacion_miembro_objetivo # APUNTA al NUEVO LÍDER
                    relacion_lider_actual.par_eve_codigo_proyecto = None # CÓDIGO A NULL
                    relacion_lider_actual.par_eve_documentos = None # DOCUMENTOS A NULL
                    relacion_lider_actual.save()
                    
                    # 4. 🔥 CRUCIAL: Actualizar a TODOS los miembros restantes para que apunten al NUEVO líder.
                    # Se excluye al nuevo líder (ya está actualizado en el paso 2 y su principal es NULL).
                    # Se incluye al líder saliente (ya está actualizado en el paso 3 y su principal es el nuevo líder).
                    evento = relacion_lider_actual.par_eve_evento_fk  # Obtener el evento desde la relación del líder actual
                    ParticipanteEvento.objects.filter(
                        par_eve_evento_fk=evento,
                        par_eve_proyecto_principal=relacion_lider_actual # Apuntaban al antiguo líder
                    ).exclude(
                        id=relacion_miembro_objetivo.id # Excluye al nuevo líder (aunque ya tiene principal=NULL)
                    ).update(
                        par_eve_proyecto_principal=relacion_miembro_objetivo # ¡Asignan el nuevo líder!
                    )
                    
                    # NOTA: La lógica se puede simplificar en el paso 4 para actualizar todos
                    # los que apuntaban al antiguo líder, incluyendo al antiguo líder
                    # si no lo hubiéramos actualizado en el paso 3. Pero tal como está, 
                    # ya el paso 3 se encarga del antiguo líder y el paso 4 de los miembros.
                    # Mantenemos esta estructura explícita para mayor claridad de la transición.

                    messages.success(request, f"El liderazgo se ha transferido exitosamente a **{usuario_miembro.first_name}**. Ahora eres un miembro del proyecto. ✨")
                    
                return redirect('ver_miembros_par', evento_id=evento_id)

            except Exception as e:
                messages.error(request, f"Error al transferir el liderazgo: {e}")
                return redirect('ver_miembros_par', evento_id=evento_id)
        
        # -----------------------------------------------------------------
        
        messages.error(request, "Acción desconocida.")
        return redirect('ver_miembros_par', evento_id=evento_id)


