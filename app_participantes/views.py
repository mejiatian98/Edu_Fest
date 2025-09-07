from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from .models import ParticipanteEvento
from app_usuarios.models import Participante, Usuario
from app_admin_eventos.models import Evento, Criterio
from .forms import EditarUsuarioParticipanteForm, ParticipanteForm
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


def crear_o_obtener_grupo_proyecto(codigo_proyecto, evento_nombre):
    """
    Crea o obtiene un grupo de Django para el proyecto
    """
    nombre_grupo = f"Proyecto_{codigo_proyecto}_{evento_nombre[:20]}"
    grupo, created = Group.objects.get_or_create(
        name=nombre_grupo
    )
    return grupo


######## CREAR PARTICIPANTE ########
@method_decorator(visitor_required, name='dispatch')
class ParticipanteCreateView(View):
    def get(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        form = ParticipanteForm(evento=evento)
        return render(request, 'crear_participante.html', {
            'form': form,
            'evento': evento,
        })

    def post(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        form = ParticipanteForm(request.POST, request.FILES, evento=evento)
        documento = request.FILES.get('par_eve_documentos')

        if not documento:
            messages.error(request, "Debe cargar el documento para continuar.")
            return render(request, 'crear_participante.html', {
                'form': form,
                'evento': evento,
            })

        if form.is_valid():
            try:
                with transaction.atomic():
                    # Verificar si la cédula ya está registrada para ESTE evento específico
                    par_id = form.cleaned_data['par_id']
                    
                    # Verificar si ya existe un participante con esta cédula para este evento
                    participante_existente = Participante.objects.filter(par_id=par_id).first()
                    if participante_existente:
                        # Verificar si ya está registrado en este evento específico
                        if ParticipanteEvento.objects.filter(
                            par_eve_participante_fk=participante_existente,
                            par_eve_evento_fk=evento
                        ).exists():
                            messages.error(request, f"Ya existe un participante con la cédula {par_id} registrado para el evento '{evento.eve_nombre}'.")
                            return render(request, 'crear_participante.html', {
                                'form': form,
                                'evento': evento,
                            })
                        
                        # Si existe el participante pero no está registrado en este evento,
                        # usar el participante existente
                        participante_lider = participante_existente
                        usuario = participante_lider.usuario
                        
                        # Generar nueva contraseña para el evento
                        contrasena_generada = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
                        usuario.set_password(contrasena_generada)
                        usuario.save()
                        
                    else:
                        # Verificar si el email ya está registrado (solo para nuevos usuarios)
                        email_formulario = form.cleaned_data['email']
                        if Usuario.objects.filter(email=email_formulario).exists():
                            messages.error(request, f"El correo {email_formulario} ya está registrado.")
                            return render(request, 'crear_participante.html', {
                                'form': form,
                                'evento': evento,
                            })
                        
                        # Verificar si el username ya está registrado (solo para nuevos usuarios)
                        username_formulario = form.cleaned_data['username']
                        if Usuario.objects.filter(username=username_formulario).exists():
                            messages.error(request, f"El nombre de usuario {username_formulario} ya está registrado.")
                            return render(request, 'crear_participante.html', {
                                'form': form,
                                'evento': evento,
                            })
                        
                        # Crear nuevo Usuario líder
                        usuario = form.save(commit=False)
                        contrasena_generada = ''.join(random.choices(string.ascii_letters + string.digits, k=20))

                        usuario.set_password(contrasena_generada)
                        usuario.is_superuser = False
                        usuario.is_staff = False
                        usuario.is_active = True
                        usuario.date_joined = localtime(now())
                        usuario.rol = "PARTICIPANTE"
                        usuario.save()

                        # Crear el Participante líder
                        participante_lider = Participante.objects.create(par_id=par_id, usuario=usuario)

                    # Determinar si es grupo
                    es_grupo = request.POST.get('tipo_participacion') == 'grupo'

                    # Crear relación Evento - Participante principal (líder)
                    participante_evento_lider = ParticipanteEvento.objects.create(
                        par_eve_evento_fk=evento,
                        par_eve_participante_fk=participante_lider,
                        par_eve_estado="Pendiente",
                        par_eve_clave="",
                        par_eve_qr="",
                        par_eve_documentos=documento,
                        par_eve_es_grupo=es_grupo,
                        par_eve_proyecto_principal=None,  # Es el líder, no tiene proyecto principal
                    )

                    codigo_proyecto = participante_evento_lider.par_eve_codigo_proyecto
                    correos_enviados = [usuario.email]

                    # Crear grupo de Django si es un proyecto grupal
                    grupo_django = None
                    if es_grupo:
                        grupo_django = crear_o_obtener_grupo_proyecto(codigo_proyecto, evento.eve_nombre)
                        # Agregar al líder al grupo
                        usuario.groups.add(grupo_django)

                    # Si es grupo, crear los miembros adicionales
                    if es_grupo:
                        miembros_creados = []
                        
                        # Obtener datos de miembros del POST
                        i = 1
                        while f'miembro_{i}_cedula' in request.POST:
                            cedula = request.POST.get(f'miembro_{i}_cedula')
                            nombre_completo = request.POST.get(f'miembro_{i}_nombre')
                            email = request.POST.get(f'miembro_{i}_email')
                            telefono = request.POST.get(f'miembro_{i}_telefono', '')

                            if cedula and nombre_completo and email:
                                # Verificar si la cédula del miembro ya está registrada para este evento
                                miembro_existente = Participante.objects.filter(par_id=cedula).first()
                                if miembro_existente:
                                    if ParticipanteEvento.objects.filter(
                                        par_eve_participante_fk=miembro_existente,
                                        par_eve_evento_fk=evento
                                    ).exists():
                                        messages.error(request, f"El miembro con cédula {cedula} ya está registrado para el evento '{evento.eve_nombre}'.")
                                        return render(request, 'crear_participante.html', {
                                            'form': form,
                                            'evento': evento,
                                        })

                                # Verificar que el email no esté registrado solo para nuevos usuarios
                                if not miembro_existente and Usuario.objects.filter(email=email).exists():
                                    messages.error(request, f"El correo {email} ya está registrado.")
                                    return render(request, 'crear_participante.html', {
                                        'form': form,
                                        'evento': evento,
                                    })

                                if miembro_existente:
                                    # Usar participante existente
                                    participante_miembro = miembro_existente
                                    usuario_miembro = participante_miembro.usuario
                                    
                                    # Generar nueva contraseña
                                    contrasena_miembro = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
                                    usuario_miembro.set_password(contrasena_miembro)
                                    usuario_miembro.save()
                                    
                                else:
                                    # Crear nuevo miembro
                                    # Separar nombre y apellido
                                    partes_nombre = nombre_completo.strip().split()
                                    nombre = partes_nombre[0] if partes_nombre else nombre_completo
                                    apellido = ' '.join(partes_nombre[1:]) if len(partes_nombre) > 1 else ''

                                    # Crear usuario para el miembro
                                    username_miembro = f"{nombre.lower()}{cedula[-4:]}"
                                    
                                    # Validar que el username no esté registrado
                                    contador = 1
                                    username_original = username_miembro
                                    while Usuario.objects.filter(username=username_miembro).exists():
                                        username_miembro = f"{username_original}{contador}"
                                        contador += 1

                                    contrasena_miembro = ''.join(random.choices(string.ascii_letters + string.digits, k=20))

                                    usuario_miembro = Usuario.objects.create(
                                        username=username_miembro,
                                        first_name=nombre,
                                        last_name=apellido,
                                        email=email,
                                        telefono=telefono,
                                        is_superuser=False,
                                        is_staff=False,
                                        is_active=True,
                                        date_joined=localtime(now()),
                                        rol="PARTICIPANTE"
                                    )
                                    usuario_miembro.set_password(contrasena_miembro)
                                    usuario_miembro.save()

                                    # Crear participante miembro
                                    participante_miembro = Participante.objects.create(
                                        par_id=cedula,
                                        usuario=usuario_miembro
                                    )

                                # Agregar al miembro al grupo de Django
                                if grupo_django:
                                    usuario_miembro.groups.add(grupo_django)

                                # Crear relación con el evento referenciando al proyecto principal
                                ParticipanteEvento.objects.create(
                                    par_eve_evento_fk=evento,
                                    par_eve_participante_fk=participante_miembro,
                                    par_eve_estado="Pendiente",
                                    par_eve_clave="",
                                    par_eve_qr="",
                                    par_eve_es_grupo=True,
                                    par_eve_proyecto_principal=participante_evento_lider,  # Referencia al líder
                                    par_eve_codigo_proyecto=codigo_proyecto,  # Mismo código que el líder
                                )

                                miembros_creados.append({
                                    'nombre': nombre_completo,
                                    'email': email,
                                    'username': usuario_miembro.username if not miembro_existente else usuario_miembro.username,
                                    'password': contrasena_miembro
                                })
                                correos_enviados.append(email)

                            i += 1

                    # Enviar correos
                    try:
                        # Correo al líder
                        mensaje_lider = f"Hola {usuario.first_name} {usuario.last_name},\n\n" \
                                      f"Te has registrado correctamente como {'líder del grupo' if es_grupo else 'participante'} " \
                                      f"al evento \"{evento.eve_nombre}\".\n\n" \
                                      f"Código del proyecto: {codigo_proyecto}\n"
                        
                        if es_grupo and grupo_django:
                            mensaje_lider += f"Grupo asignado: {grupo_django.name}\n"
                            
                        mensaje_lider += f"Puedes ingresar con tu correo: {usuario.email}\n" \
                                        f"Y tu contraseña generada: {contrasena_generada}\n\n"

                        if es_grupo:
                            mensaje_lider += f"Tu grupo tiene {len(miembros_creados)} miembros adicionales que también recibieron sus credenciales.\n\n"

                        mensaje_lider += "Recomendamos cambiar tu contraseña después de iniciar sesión."

                        send_mail(
                            subject="Registro exitoso a EduFest - Líder del proyecto",
                            message=mensaje_lider,
                            from_email=None,
                            recipient_list=[usuario.email],
                            fail_silently=False
                        )

                        # Correos a los miembros del grupo
                        if es_grupo:
                            for miembro in miembros_creados:
                                mensaje_miembro = f"Hola {miembro['nombre']},\n\n" \
                                                f"Has sido registrado como miembro del grupo para el evento \"{evento.eve_nombre}\".\n\n" \
                                                f"Código del proyecto: {codigo_proyecto}\n" \
                                                f"Grupo asignado: {grupo_django.name}\n" \
                                                f"Líder del grupo: {usuario.first_name} {usuario.last_name}\n" \
                                                f"Puedes ingresar con tu correo: {miembro['email']}\n" \
                                                f"Y tu contraseña generada: {miembro['password']}\n\n" \
                                                f"Recomendamos cambiar tu contraseña después de iniciar sesión."

                                send_mail(
                                    subject="Registro exitoso a EduFest - Miembro del grupo",
                                    message=mensaje_miembro,
                                    from_email=None,
                                    recipient_list=[miembro['email']],
                                    fail_silently=False
                                )

                    except Exception as e:
                        messages.warning(request, "Registro exitoso, pero hubo un problema al enviar algunos correos.")

                    tipo_mensaje = "grupal" if es_grupo else "individual"
                    mensaje_exito = f"La preinscripción {tipo_mensaje} fue exitosa al evento \"{evento.eve_nombre}\". " \
                                  f"Código del proyecto: {codigo_proyecto}. "
                    
                    if es_grupo and grupo_django:
                        mensaje_exito += f"Grupo Django creado: {grupo_django.name}. "
                    
                    mensaje_exito += f"Revisa {'los correos' if es_grupo else 'tu correo'} para obtener {'las credenciales' if es_grupo else 'tu contraseña'}."
                    
                    messages.success(request, mensaje_exito)
                    return redirect('pagina_principal')

            except Exception as e:
                messages.error(request, f"Ocurrió un error durante el registro: {str(e)}")
                return render(request, 'crear_participante.html', {
                    'form': form,
                    'evento': evento,
                })

        return render(request, 'crear_participante.html', {
            'form': form,
            'evento': evento,
        })
######## CANCELAR PREINSCRIPCION PARTICIPANTE ########



@method_decorator(participante_required, name='dispatch')
class EliminarParticipanteView(View):
    def get(self, request, participante_id):
        participante = get_object_or_404(Participante, par_id=participante_id)
        usuario = participante.usuario

        # Obtener el evento asignado, si lo hay
        participante_evento = ParticipanteEvento.objects.filter(par_eve_participante_fk=participante).first()
        nombre_evento = participante_evento.par_eve_evento_fk.eve_nombre if participante_evento else "uno de nuestros eventos"

        # Enviar correo antes de eliminar
        if usuario.email:
            send_mail(
                subject='Notificación de eliminación de cuenta como participante',
                message=(
                    f'Estimado/a {usuario.first_name},\n\n'
                    f'Le informamos que ha sido eliminado como participante del evento "{nombre_evento}". '
                    f'Todos sus datos han sido eliminados por razones de seguridad.\n\n'
                    f'Si tiene preguntas o requiere mayor información, no dude en contactarnos.\n\n'
                    f'Atentamente,\nEquipo de organización de eventos.'
                ),
                from_email=DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                fail_silently=False
            )

        # Cerrar sesión antes de eliminar
        request.session.flush()

        # Eliminar al usuario, lo cual también eliminará al participante
        usuario.delete()

        messages.success(request, "El participante ha sido eliminado correctamente.")
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
            participante = get_object_or_404(Participante, par_id=participante_id)
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
            participante = Participante.objects.get(par_id=participante_id)
        except Participante.DoesNotExist:
            messages.error(request, "Participante no encontrado.")
            return redirect('login_view')

        # Relación participante-evento
        relaciones = ParticipanteEvento.objects.filter(par_eve_participante_fk=participante).select_related('par_eve_evento_fk')

        # Separar eventos aprobados y pendientes
        eventos_aprobados = [rel.par_eve_evento_fk for rel in relaciones if rel.par_eve_estado == 'Aprobado']
        eventos_pendientes = [rel.par_eve_evento_fk for rel in relaciones if rel.par_eve_estado == 'Pendiente']

        eventos = Evento.objects.filter(id__in=[e.id for e in eventos_aprobados])

        # ✅ Criterios completos: suma de cri_peso == 100
        criterios_completos = {}
        for evento in eventos:
            suma = Criterio.objects.filter(cri_evento_fk=evento).aggregate(total=Sum('cri_peso'))['total'] or 0
            criterios_completos[evento.id] = (suma == 100)

        # Obtener una relación para usar en la vista (si es necesario)
        relacion = ParticipanteEvento.objects.filter(par_eve_participante_fk=participante).first()

        # Después de criterios_completos
        calificaciones_registradas = {}
        for evento in eventos:
            rel = ParticipanteEvento.objects.filter(
                par_eve_evento_fk=evento,
                par_eve_participante_fk=participante
            ).first()
            calificaciones_registradas[evento.id] = rel.calificacion is not None if rel else False


        context = {
            'participante': participante,
            'eventos': eventos_aprobados,
            'eventos_pendientes': eventos_pendientes,
            'relacion': relacion,
            'criterios_completos': criterios_completos,
            'calificaciones_registradas': calificaciones_registradas,  # ✅ Agregado aquí
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

######### EDITAR PREINSCRIPCION ########
@method_decorator(participante_required, name='dispatch')
class EditarPreinscripcionView(View):
    template_name = 'editar_preinscripcion_participante.html'

    def get(self, request, par_id):
        relacion = get_object_or_404(ParticipanteEvento, pk=par_id)
        participante = relacion.par_eve_participante_fk
        evento = relacion.par_eve_evento_fk
        form = EditarUsuarioParticipanteForm(instance=participante.usuario)

        return render(request, self.template_name, {
            'form': form,
            'evento': evento,
            'relacion': relacion,
            'usuario': participante.usuario,
            'participante': participante
        })

    def post(self, request, par_id):
        relacion = get_object_or_404(ParticipanteEvento, pk=par_id)
        participante = relacion.par_eve_participante_fk
        evento = relacion.par_eve_evento_fk
        usuario = participante.usuario

        form = EditarUsuarioParticipanteForm(request.POST, instance=usuario)
        documento_pago = request.FILES.get('par_eve_documentos')

        # Contraseñas
        contrasena_actual = request.POST.get('nueva_contrasena')
        nueva_contrasena = request.POST.get('confirmar_contrasena_nueva')
        confirmar_nueva = request.POST.get('confirmar_contrasena')

        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.ultimo_acceso = localtime(now())

            # Validar y cambiar la contraseña si se proporcionaron campos
            if contrasena_actual or nueva_contrasena or confirmar_nueva:
                if not usuario.check_password(contrasena_actual):
                    messages.error(request, "La contraseña actual no es correcta.")
                    return redirect('editar_preinscripcion', par_id=par_id)
                if nueva_contrasena != confirmar_nueva:
                    messages.error(request, "La nueva contraseña y su confirmación no coinciden.")
                    return redirect('editar_preinscripcion', par_id=par_id)
                if len(nueva_contrasena) < 6:
                    messages.error(request, "La nueva contraseña debe tener al menos 6 caracteres.")
                    return redirect('editar_preinscripcion', par_id=par_id)

                usuario.set_password(nueva_contrasena)
                update_session_auth_hash(request, usuario)  # Mantiene sesión activa después del cambio

            usuario.save()

            if documento_pago:
                relacion.par_eve_documentos = documento_pago
                relacion.save()

            messages.success(request, "Tu información fue actualizada correctamente.")
            return redirect('editar_preinscripcion', par_id=par_id)

        return render(request, self.template_name, {
            'form': form,
            'evento': evento,
            'relacion': relacion,
            'usuario': participante.usuario,
            'participante': participante
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
        participante = get_object_or_404(Participante, par_id=request.session['participante_id'])

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
