from datetime import date
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from principal_eventos.settings import DEFAULT_FROM_EMAIL
from .models import AsistenteEvento
from app_usuarios.models import Asistente, Usuario
from django.utils.timezone import now, localtime
from django.contrib.auth.hashers import make_password
from app_admin_eventos.models import Evento
from .forms import AsistenteForm, EditarUsuarioAsistenteForm
import qrcode
import string
import random
import os
from django.core.files.base import ContentFile
from io import BytesIO
from django.utils.decorators import method_decorator
from principal_eventos.decorador import asistente_required
from django.views.generic import DetailView
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from app_admin_eventos.models import Evento, MemoriaEvento
from app_admin_eventos.models import Evento, MemoriaEvento
from app_asistentes.models import AsistenteEvento
from app_participantes.models import ParticipanteEvento
from app_evaluadores.models import EvaluadorEvento
from django.db.models import Q
from django.db import models



###### MEMORIAS DE ASISTENTE ######
@method_decorator(login_required, name='dispatch')
class MemoriasAsistenteView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        inscrito = AsistenteEvento.objects.filter(
            asi_eve_evento_fk=evento,
            asi_eve_asistente_fk__usuario=request.user
        ).exists()
        if not inscrito:
            messages.error(request, "❌ No estás inscrito como asistente en este evento.")
            return redirect('dashboard_user')
        memorias = MemoriaEvento.objects.filter(evento=evento).order_by('-subido_en')
        return render(request, 'dashboard_memorias_asistente.html', {
            'evento': evento,
            'memorias': memorias
        })


###### DASHBOARD DE ASISTENTE ######
@method_decorator(asistente_required, name='dispatch')
class DashboardAsistenteView(View):
    template_name = 'dashboard_principal_asistente.html'

    def get(self, request):
        asistente_id = request.session.get('asistente_id')
        if not asistente_id:
            messages.error(request, "Debe iniciar sesión como asistente.")
            return redirect('login_view')

        try:
            asistente = Asistente.objects.get(id=asistente_id)
        except Asistente.DoesNotExist:
            messages.error(request, "Asistente no encontrado.")
            return redirect('login_view')

        # Filtrar relaciones del asistente con eventos
        relaciones = AsistenteEvento.objects.filter(asi_eve_asistente_fk=asistente).select_related('asi_eve_evento_fk')

        # Separar eventos aprobados y pendientes
        eventos_aprobados = [rel.asi_eve_evento_fk for rel in relaciones if rel.asi_eve_estado == 'Aprobado']
        eventos_pendientes = [rel.asi_eve_evento_fk for rel in relaciones if rel.asi_eve_estado == 'Pendiente']

        relacion = AsistenteEvento.objects.filter(asi_eve_asistente_fk=asistente).first()

        context = {
            'asistente': asistente,
            'eventos': eventos_aprobados,
            'eventos_pendientes': eventos_pendientes,
            'relacion': relacion,  # <-- esto es importante
        }
        return render(request, self.template_name, context)




###### CREACIÓN DE ASISTENTE ######
class AsistenteCreateView(View):
    def get(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        form = AsistenteForm()
        es_de_pago = evento.eve_tienecosto.lower() == "de pago"

        return render(request, 'crear_asistente.html', {
            'form': form,
            'evento': evento,
            'es_de_pago': es_de_pago,
        })

    def post(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        form = AsistenteForm(request.POST, request.FILES)
        es_de_pago = evento.eve_tienecosto.lower() == "de pago"

        # 🔹 Validar capacidad disponible
        if evento.eve_capacidad <= 0:
            messages.error(request, "❌ No hay más cupos disponibles para este evento.")
            return render(request, 'crear_asistente.html', {
                'form': form, 'evento': evento, 'es_de_pago': es_de_pago
            })

        # 🔹 Validar comprobante si el evento es de pago
        if es_de_pago and not request.FILES.get('asi_eve_soporte'):
            messages.error(request, "⚠️ Debe cargar una imagen del comprobante de pago para este evento.")
            return render(request, 'crear_asistente.html', {
                'form': form, 'evento': evento, 'es_de_pago': es_de_pago
            })

        if form.is_valid():
            cedula = form.cleaned_data['cedula']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            telefono = form.cleaned_data['telefono']
            username = form.cleaned_data['username']

            # 🔹 Buscar usuario existente por cédula, correo o username
            usuario = Usuario.objects.filter(
                models.Q(cedula=cedula) | models.Q(email=email) | models.Q(username=username)
            ).first()

            if usuario:
                # ✅ Si existe, se actualiza la info y se reutiliza
                usuario.first_name = first_name
                usuario.last_name = last_name
                usuario.telefono = telefono
                usuario.email = email
                usuario.username = username  # mantenemos el mismo username
                usuario.save(update_fields=['first_name', 'last_name', 'telefono', 'email', 'username'])

                asistente, _ = Asistente.objects.get_or_create(usuario=usuario)
                password_plana = "Tu contraseña actual"
            else:
                # ✅ Crear nuevo usuario y asistente solo si no existe
                password_plana = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                usuario = Usuario.objects.create(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    telefono=telefono,
                    cedula=cedula,
                    is_superuser=False,
                    is_staff=False,
                    is_active=True,
                    date_joined=timezone.now(),
                    rol=Usuario.Roles.ASISTENTE,
                    password=make_password(password_plana),
                )
                asistente = Asistente.objects.create(usuario=usuario)

            # 🔹 Verificar si ya está inscrito en este mismo evento
            if AsistenteEvento.objects.filter(
                asi_eve_evento_fk=evento,
                asi_eve_asistente_fk=asistente
            ).exists():
                messages.warning(request, "⚠️ Ya estás inscrito como asistente en este evento.")
                return render(request, 'crear_asistente.html', {
                    'form': form, 'evento': evento, 'es_de_pago': es_de_pago
                })

            # 🔹 Manejar comprobante y estado
            documento_pago = request.FILES.get('asi_eve_soporte') if es_de_pago else None
            estado = "Pendiente" if es_de_pago else "Aprobado"

            # 🔹 Generar clave y QR solo si el evento NO es de pago
            clave = ""
            qr_img_file = None
            qr_bytes = None
            qr_filename = None

            if not es_de_pago:
                clave = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                qr_data = f"Asistente: {first_name} {last_name}\nEvento: {evento.eve_nombre}\nClave: {clave}"
                qr = qrcode.make(qr_data)
                buffer = BytesIO()
                qr.save(buffer, format='PNG')
                qr_bytes = buffer.getvalue()
                qr_filename = f"qr_{cedula}_{evento.pk}.png"
                qr_img_file = ContentFile(qr_bytes, name=qr_filename)

            # 🔹 Crear registro de participación
            AsistenteEvento.objects.create(
                asi_eve_evento_fk=evento,
                asi_eve_asistente_fk=asistente,
                asi_eve_estado=estado,
                asi_eve_clave=clave,
                asi_eve_qr=qr_img_file if qr_img_file else None,
                asi_eve_soporte=documento_pago,
                asi_eve_fecha_hora=timezone.now(),
            )

            # 🔹 Reducir capacidad disponible
            evento.eve_capacidad -= 1
            evento.save(update_fields=['eve_capacidad'])

            # 🔹 Enviar correo con credenciales
            subject = f"🎟️ Registro exitoso - Evento \"{evento.eve_nombre}\""
            body = (
                f"Hola {first_name},\n\n"
                f"Tu registro al evento \"{evento.eve_nombre}\" fue exitoso.\n\n"
                f"Credenciales de acceso:\n"
                f"- Correo: {email}\n"
                f"- Contraseña: {password_plana}\n\n"
            )

            if not es_de_pago:
                body += (
                    f"Tu clave de acceso al evento es: {clave}\n"
                    f"Adjunto encontrarás tu código QR para el ingreso.\n\n"
                )

            body += "¡Gracias por registrarte!\nEquipo de Event-Soft."

            email_msg = EmailMessage(subject, body, DEFAULT_FROM_EMAIL, [email])
            if not es_de_pago and qr_bytes and qr_filename:
                email_msg.attach(qr_filename, qr_bytes, 'image/png')
            email_msg.send(fail_silently=False)

            messages.success(request, f"✅ Te has inscrito correctamente al evento \"{evento.eve_nombre}\".")
            return redirect('pagina_principal')

        # 🔹 Si el formulario no es válido
        return render(request, 'crear_asistente.html', {
            'form': form,
            'evento': evento,
            'es_de_pago': es_de_pago
        })



####### CAMBIO PASSWORD ASISTENTE ######
@method_decorator(asistente_required, name='dispatch')
class CambioPasswordAsistenteView(View):
    template_name = 'cambio_password_asistente.html'

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

        asistente_id = request.session.get('asistente_id')
        asistente = get_object_or_404(Asistente, pk=asistente_id)
        usuario = asistente.usuario

        usuario.set_password(password1)
        usuario.last_login = timezone.now()  # ✅ Se actualiza solo aquí
        usuario.save()

        messages.success(request, "✅ Contraseña cambiada correctamente.")
        return redirect('dashboard_asistente')


####### ELIMINAR DATOS ASISTENTE ######
@method_decorator(asistente_required, name='dispatch')
class EliminarAsistenteView(View):
    def get(self, request, asistente_id):
        asistente = get_object_or_404(Asistente, id=asistente_id)
        usuario = asistente.usuario

        # 🔹 Buscar todas las inscripciones del asistente
        inscripciones = AsistenteEvento.objects.filter(asi_eve_asistente_fk=asistente)

        # 🔹 Verificar si tiene inscripciones activas (aprobadas)
        tiene_inscripciones_activas = inscripciones.filter(asi_eve_estado="Aprobado").exists()
        if tiene_inscripciones_activas:
            messages.error(
                request,
                "❌ No puedes eliminar tu cuenta mientras tengas inscripciones activas. "
                "Por favor, cancela tus inscripciones antes de eliminar tu cuenta."
            )
            return redirect('pagina_principal')

        # 🔹 Liberar cupos solo de eventos aprobados
        for inscripcion in inscripciones:
            if inscripcion.asi_eve_estado == "Aprobado":
                evento = inscripcion.asi_eve_evento_fk
                evento.eve_capacidad += 1
                evento.save(update_fields=["eve_capacidad"])

        # 🔹 Obtener el último evento inscrito (para referencia en el correo)
        ultimo_evento = inscripciones.first()
        nombre_evento = ultimo_evento.asi_eve_evento_fk.eve_nombre if ultimo_evento else "uno de nuestros eventos"

        # 🔹 Enviar correo antes de eliminar
        if usuario.email:
            send_mail(
                subject='🗑️ Notificación de eliminación de cuenta como Asistente',
                message=(
                    f'Estimado/a {usuario.first_name},\n\n'
                    f'Le informamos que su cuenta ha sido eliminada correctamente de Event-Soft.\n\n'
                    f'Todos sus datos, incluyendo sus inscripciones en eventos como "{nombre_evento}", '
                    f'han sido eliminados por razones de seguridad.\n\n'
                    f'Si desea volver a participar, puede registrarse nuevamente en cualquier momento.\n\n'
                    f'Atentamente,\nEquipo de organización de eventos.'
                ),
                from_email=DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                fail_silently=False
            )

        # 🔹 Cerrar sesión del usuario
        request.session.flush()

        # 🔹 Eliminar usuario (y asistente por cascada)
        usuario.delete()

        messages.success(request, "✅ Tu cuenta y tus inscripciones han sido eliminadas correctamente.")
        return redirect('pagina_principal')




####### CANCELAR EVENTO ASISTENTE  ######
@method_decorator(asistente_required, name='dispatch')
class AsistenteCancelacionView(View):
    """
    Permite a un asistente cancelar una preinscripción activa a un evento.
    El cupo se libera explícitamente al aumentar la capacidad del evento.
    """
    def post(self, request, evento_id):
        asistente = get_object_or_404(Asistente, usuario=request.user)
        evento = get_object_or_404(Evento, id=evento_id)

        # CA-10.1: Prohibir la cancelación si el evento ya terminó
        if evento.eve_fecha_fin < timezone.localdate():
            messages.error(request, "❌ No puedes cancelar una inscripción a un evento que ya finalizó.")
            return redirect('dashboard_asistente')

        # 1. Buscar inscripción activa (estado 'Aprobado')
        inscripcion = AsistenteEvento.objects.filter(
            asi_eve_asistente_fk=asistente,
            asi_eve_evento_fk=evento,
            asi_eve_estado='Aprobado'
        ).first()

        # CA-10.5: No inscrito o no tiene estado 'Aprobado'
        if not inscripcion:
            messages.error(request, "❌ No tienes una inscripción activa para este evento.")
            return redirect('dashboard_asistente')

        # 2. Cambiar el estado a 'Cancelado'
        inscripcion.asi_eve_estado = 'Cancelado'
        inscripcion.save(update_fields=['asi_eve_estado'])

        # 3. 🔹 Liberar cupo explícitamente
        evento.eve_capacidad += 1
        evento.save(update_fields=['eve_capacidad'])

        # 4. Mensaje de éxito
        messages.success(
            request,
            f"✅ Has cancelado exitosamente tu inscripción al evento '{evento.eve_nombre}'. "
            f"Tu cupo ha sido liberado."
        )
        return redirect('dashboard_asistente')


######### EDITAR PREINSCRIPCION ########
@method_decorator(asistente_required, name='dispatch')
class EditarPreinscripcionAsistenteView(View):
    template_name = 'editar_preinscripcion_asistente.html'

    def get(self, request, id):
        relacion = get_object_or_404(AsistenteEvento, pk=id)
        asistente = relacion.asi_eve_asistente_fk
        evento = relacion.asi_eve_evento_fk
        form = EditarUsuarioAsistenteForm(instance=asistente.usuario)

        # 🔹 Traer todos los eventos donde está inscrito
        todas_relaciones = AsistenteEvento.objects.filter(
            asi_eve_asistente_fk=asistente
        ).select_related("asi_eve_evento_fk")

        return render(request, self.template_name, {
            'form': form,
            'evento': evento,
            'relacion': relacion,
            'usuario': asistente.usuario,
            'asistente': asistente,
            'todas_relaciones': todas_relaciones
        })

    def post(self, request, id):
        relacion = get_object_or_404(AsistenteEvento, pk=id)
        asistente = relacion.asi_eve_asistente_fk
        evento = relacion.asi_eve_evento_fk
        usuario = asistente.usuario

        form = EditarUsuarioAsistenteForm(request.POST, instance=usuario)

        # Contraseñas
        contrasena_actual = request.POST.get('nueva_contrasena')
        nueva_contrasena = request.POST.get('confirmar_contrasena_nueva')
        confirmar_nueva = request.POST.get('confirmar_contrasena')

        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.ultimo_acceso = localtime(now())

            # Validar y cambiar contraseña si hay datos ingresados
            if contrasena_actual or nueva_contrasena or confirmar_nueva:
                if not usuario.check_password(contrasena_actual):
                    messages.error(request, "La contraseña actual no es correcta.")
                    return redirect('editar_preinscripcion_asistente', id=id)

                if nueva_contrasena != confirmar_nueva:
                    messages.error(request, "Las contraseñas nuevas no coinciden.")
                    return redirect('editar_preinscripcion_asistente', id=id)

                if len(nueva_contrasena) < 6:
                    messages.error(request, "La nueva contraseña debe tener al menos 6 caracteres.")
                    return redirect('editar_preinscripcion_asistente', id=id)

                usuario.set_password(nueva_contrasena)
                update_session_auth_hash(request, usuario)

            usuario.save()

            # 🔹 Procesar soportes para TODOS los eventos donde está inscrito
            todas_relaciones = AsistenteEvento.objects.filter(
                asi_eve_asistente_fk=asistente
            )

            for r in todas_relaciones:
                file_key = f"asi_eve_soporte_{r.id}"
                documento_pago = request.FILES.get(file_key)
                if documento_pago:
                    r.asi_eve_soporte = documento_pago
                    r.save()

            messages.success(request, "Tu información fue actualizada correctamente.")
            return redirect('editar_preinscripcion_asistente', id=id)

        # Si hay errores, volvemos a mostrar el formulario
        todas_relaciones = AsistenteEvento.objects.filter(
            asi_eve_asistente_fk=asistente
        ).select_related("asi_eve_evento_fk")

        return render(request, self.template_name, {
            'form': form,
            'evento': evento,
            'relacion': relacion,
            'usuario': asistente.usuario,
            'asistente': asistente,
            'todas_relaciones': todas_relaciones
        })


####### EVENTO DETALLE ######
@method_decorator(asistente_required, name='dispatch')
class EventoDetailView(DetailView):
    model = Evento
    template_name = 'info_evento_evento_asi.html'
    context_object_name = 'evento'
    pk_url_kwarg = 'pk'

    def dispatch(self, request, *args, **kwargs):
        evento = get_object_or_404(self.model, pk=kwargs['pk'])
        asistente_id = request.session.get('asistente_id')
        
        # Lógica de bloqueo/redirección (CORRECTA)
        if asistente_id:
            asistente = get_object_or_404(Asistente, id=asistente_id)
            if not AsistenteEvento.objects.filter(asi_eve_asistente_fk=asistente, asi_eve_evento_fk=evento).exists():
                messages.error(request, "No tienes permiso para ver este evento.")
                # Asumo que 'pagina_principal' es el alias de 'dashboard_asistente'
                return redirect('dashboard_asistente') 
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener el objeto Evento
        evento = context['evento']
        
        # 🌟 PASO DE CORRECCIÓN: CALCULAR LA URL PÚBLICA ABSOLUTA 🌟
        # 1. Obtener la URL relativa de la vista pública.
        #    Asumimos que el nombre de la URL pública es 'ver_detalle_evento'
        relative_url = reverse('ver_info_evento_asi', kwargs={'pk': evento.pk})
        
        # 2. Construir la URL absoluta usando request.build_absolute_uri()
        public_absolute_url = self.request.build_absolute_uri(relative_url)
        
        # 3. Añadirla al contexto.
        context['url_para_compartir'] = public_absolute_url 

        # Datos adicionales
        context['asistente'] = get_object_or_404(Asistente, id=self.request.session.get('asistente_id'))
        
        return context




####### ACCESO A EVENTO ######
@method_decorator(asistente_required, name='dispatch')
class IngresoEventoAsistenteView(View):
    template_name = 'ingreso_evento_asi.html'

    def get(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        asistente = get_object_or_404(Asistente, usuario=request.user)
        asistente_evento = get_object_or_404(AsistenteEvento, asi_eve_evento_fk=evento, asi_eve_asistente_fk=asistente)

        context = {
            'evento': evento,
            'asistente': asistente_evento  # este es el objeto que tiene el QR y el soporte
        }
        return render(request, self.template_name, context)
    

    
####### MEMORIAS DEL EVENTO PARA USUARIOS ######
@method_decorator(login_required, name='dispatch')
class MemoriasAsistenteView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        # Verificar inscripción como asistente
        inscrito = AsistenteEvento.objects.filter(
            asi_eve_evento_fk=evento,
            asi_eve_asistente_fk__usuario=request.user
        ).exists()
        if not inscrito:
            messages.error(request, "❌ No estás inscrito como asistente en este evento.")
            return redirect('dashboard_user')
        memorias = MemoriaEvento.objects.filter(evento=evento).order_by('-subido_en')
        return render(request, 'memorias_asistente.html', {'evento': evento, 'memorias': memorias})
