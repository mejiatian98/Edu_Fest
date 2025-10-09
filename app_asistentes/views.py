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

###### CREACION DE ASISTENTE ######
class AsistenteCreateView(View):
    def get(self, request, pk):
        form = AsistenteForm()
        evento = get_object_or_404(Evento, pk=pk)
        es_de_pago = evento.eve_tienecosto.lower() == "de pago"
        return render(request, 'crear_asistente.html', {
            'form': form,
            'evento': evento,
            'es_de_pago': es_de_pago,
        })

    def post(self, request, pk):
        form = AsistenteForm(request.POST, request.FILES)
        evento = get_object_or_404(Evento, pk=pk)
        es_de_pago = evento.eve_tienecosto.lower() == "de pago"

        if evento.eve_capacidad <= 0:
            messages.error(request, "No hay más cupos disponibles para este evento.")
            return render(request, 'crear_asistente.html', {
                'form': form, 'evento': evento, 'es_de_pago': es_de_pago
            })

        if es_de_pago and not request.FILES.get('asi_eve_soporte'):
            messages.error(request, "Debe cargar el comprobante de pago para este evento.")
            return render(request, 'crear_asistente.html', {
                'form': form, 'evento': evento, 'es_de_pago': es_de_pago
            })

        if form.is_valid():
            id = form.cleaned_data['id']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            telefono = form.cleaned_data['telefono']
            username = form.cleaned_data['username']

            # 🔹 Validar si ya existe inscrito al mismo evento
            if AsistenteEvento.objects.filter(
                asi_eve_evento_fk=evento,
                asi_eve_asistente_fk__usuario__email=email
            ).exists():
                messages.error(request, "Ya estás inscrito como asistente en este evento.")
                return render(request, 'crear_asistente.html', {
                    'form': form, 'evento': evento, 'es_de_pago': es_de_pago
                })

            # 🔹 Permitir múltiples eventos, pero validar correo único global
            if not Usuario.objects.filter(email=email).exists():
                # Crear nuevo usuario solo si no existe
                password_plana = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
                usuario = Usuario.objects.create(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    telefono=telefono,
                    is_superuser=False,
                    is_staff=False,
                    is_active=True,
                    date_joined=timezone.now(),
                    rol="ASISTENTE",
                    password=make_password(password_plana),
                )

                # 🔹 Crear el asistente sin pasar 'id', Django lo genera automáticamente
                asistente = Asistente.objects.create(usuario=usuario)

            else:
                # Reutilizar usuario existente
                usuario = Usuario.objects.get(email=email)
                # 🔹 Reutilizar o crear el Asistente asociado sin duplicar la PK
                asistente, _ = Asistente.objects.get_or_create(usuario=usuario)

                password_plana = "Tu contraseña actual"  
 

            documento_pago = request.FILES.get('asi_eve_soporte') if es_de_pago else None
            estado = "Pendiente" if es_de_pago else "Aprobado"

            clave = ""
            qr_img_file = None
            qr_bytes = None
            qr_filename = None

            if not es_de_pago:
                clave = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                qr_data = f"Asistente: {first_name}, Evento: {evento.eve_nombre}, Clave: {clave}"
                qr = qrcode.make(qr_data)
                buffer = BytesIO()
                qr.save(buffer, format='PNG')
                qr_bytes = buffer.getvalue()
                qr_filename = f"qr_{id}.png"
                qr_img_file = ContentFile(qr_bytes, name=qr_filename)

            AsistenteEvento.objects.create(
                asi_eve_evento_fk=evento,
                asi_eve_asistente_fk=asistente,
                asi_eve_estado=estado,
                asi_eve_clave=clave,
                asi_eve_qr=qr_img_file if qr_img_file else "",
                asi_eve_soporte=documento_pago,
                asi_eve_fecha_hora=timezone.now(),
            )

            evento.eve_capacidad -= 1
            evento.save(update_fields=['eve_capacidad'])

            subject = f"Datos de acceso - Evento \"{evento.eve_nombre}\""
            body = (
                f"Hola Asistente {first_name},\n\n"
                f"Te has registrado exitosamente al evento \"{evento.eve_nombre}\".\n\n"
                f"Ahora puedes iniciar sesión en el sistema usando:\n"
                f"- Correo: {email}\n"
                f"- Contraseña: {password_plana}\n\n"
            )

            if not es_de_pago:
                body += (
                    f"Tu clave de acceso al evento es: {clave}\n"
                    f"Adjunto encontrarás tu código QR que deberás presentar el día del evento.\n\n"
                )

            body += "¡Gracias por registrarte!\nEquipo de Event-Soft."

            email_msg = EmailMessage(
                subject=subject,
                body=body,
                from_email=DEFAULT_FROM_EMAIL,
                to=[email],
            )

            if not es_de_pago and qr_bytes and qr_filename:
                email_msg.attach(qr_filename, qr_bytes, 'image/png')

            email_msg.send(fail_silently=False)

            messages.success(request, f"La preinscripción fue exitosa al evento \"{evento.eve_nombre}\".")
            return redirect('pagina_principal')

        return render(request, 'crear_asistente.html', {
            'form': form, 'evento': evento, 'es_de_pago': es_de_pago
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


####### CANCELAR PREINSCRIPCION ######
@method_decorator(asistente_required, name='dispatch')
class EliminarAsistenteView(View):
    def get(self, request, asistente_id):
        asistente = get_object_or_404(Asistente, id=asistente_id)
        usuario = asistente.usuario

        # Obtener el evento asignado, si lo hay
        asistente_evento = AsistenteEvento.objects.filter(asi_eve_asistente_fk=asistente).first()
        nombre_evento = asistente_evento.asi_eve_evento_fk.eve_nombre if asistente_evento else "uno de nuestros eventos"

        # Enviar correo antes de eliminar
        if usuario.email:
            send_mail(
                subject='Notificación de eliminación de cuenta como Asistente',
                message=(
                    f'Estimado/a {usuario.first_name},\n\n'
                    f'Le informamos que ha sido eliminado como Asistente del evento "{nombre_evento}". '
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

        messages.success(request, "El Asistente ha sido eliminado correctamente.")
        return redirect('pagina_principal')   



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
    

