from app_admin_eventos.models import  Evento, Categoria, Area
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import DetailView, ListView
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from django.utils.timezone import now
from django.contrib.auth.hashers import check_password
from app_usuarios.models import Usuario, Evaluador, Participante, AdministradorEvento, Asistente
from django.contrib.auth import authenticate, login, logout
from .decorador import visitor_required
from django.utils.decorators import method_decorator
from django.views import View
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth import get_user_model
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings

User = get_user_model()





    

######### LOGIN Y LOGOUT #########

def login_view(request):
    rol = request.session.get('rol')
    if rol == Usuario.Roles.ADMIN_EVENTO:
        return redirect('dashboard_admin')
    elif rol == Usuario.Roles.EVALUADOR:
        return redirect('dashboard_evaluador')
    elif rol == Usuario.Roles.PARTICIPANTE:
        return redirect('dashboard_participante')
    elif rol == Usuario.Roles.ASISTENTE:
        return redirect('dashboard_asistente')

    error = None

    if request.method == 'POST':
        identificador = request.POST.get('email_username')
        contrasena = request.POST.get('password')

        try:
            usuario_obj = Usuario.objects.get(Q(email=identificador) | Q(username=identificador))
        except Usuario.DoesNotExist:
            usuario_obj = None

        if usuario_obj:
            # 👉 Revisar antes si es primer acceso
            primer_acceso = usuario_obj.last_login is None

            user = authenticate(request, username=usuario_obj.username, password=contrasena)
            if user:
                login(request, user)
                user.is_active = True
                user.save(update_fields=["is_active"])
                # No necesitas guardar el rol si usas request.user.rol directamente


                # ADMIN
                if hasattr(user, 'administradorevento'):
                    request.session['admin_id'] = user.administradorevento.id
                    request.session['admin_nombre'] = user.username
                    if primer_acceso:
                        return redirect('cambio_password_admin')
                    return redirect('dashboard_admin')


                # EVALUADOR
                elif hasattr(user, 'evaluador'):
                    request.session['evaluador_id'] = user.evaluador.id
                    request.session['evaluador_nombre'] = user.username
                    if primer_acceso:
                        return redirect('cambio_password_evaluador')
                    return redirect('dashboard_evaluador')

                # PARTICIPANTE
                elif hasattr(user, 'participante'):
                    request.session['participante_id'] = user.participante.id
                    request.session['participante_nombre'] = user.username
                    if primer_acceso:
                        return redirect('cambio_password_participante')
                    return redirect('dashboard_participante')

                # ASISTENTE
                elif hasattr(user, 'asistente'):
                    request.session['asistente_id'] = user.asistente.id
                    request.session['asistente_nombre'] = user.username
                    if primer_acceso:
                        return redirect('cambio_password_asistente')
                    return redirect('dashboard_asistente')

                else:
                    error = "Rol no reconocido."
            else:
                error = "Contraseña incorrecta."
        else:
            error = "Correo o nombre de usuario no encontrado."

    return render(request, 'login.html', {'error': error})


########### Logout ###########

def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect('pagina_principal')

########### Restablecer contraseña ###########

@method_decorator(visitor_required, name='dispatch')
class RestablecerContrasenaView(ListView):
    model = Usuario
    template_name = 'olvide_contra.html'
    context_object_name = 'usuarios'

    def get_queryset(self):
        return Usuario.objects.all()


@method_decorator(visitor_required, name='dispatch')
class RestablecioUnPasswordView(View):
    template_name = "olvide_contra.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"error": None})

    def post(self, request, *args, **kwargs):
        email_username = request.POST.get("email_username")
        error = None

        try:
            user = User.objects.get(email=email_username)
        except User.DoesNotExist:
            error = "El correo no existe en nuestros registros."
            return render(request, self.template_name, {"error": error})

        # Generar token y UID
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        reset_link = f"{request.build_absolute_uri('/reset/')}{uid}/{token}/"

        subject = "Restablecimiento de contraseña - Event-Soft"
        message = f"""
        Hola {user.username},

        Haz clic en el siguiente enlace para restablecer tu contraseña:
        {reset_link}

        Si no solicitaste este cambio, ignora este correo.
        """
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

        return render(request, self.template_name, {
            "error": "Se ha enviado un enlace de restablecimiento a tu correo electrónico."
        })


@method_decorator(visitor_required, name='dispatch')
class ResetPasswordConfirmView(View):
    template_name = "reset_password_confirm.html"

    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            return render(request, self.template_name, {
                "validlink": True,
                "uidb64": uidb64,
                "token": token
            })
        else:
            return render(request, self.template_name, {"validlink": False})

    def post(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            password1 = request.POST.get("password1")
            password2 = request.POST.get("password2")

            if password1 != password2:
                return render(request, self.template_name, {
                    "validlink": True,
                    "uidb64": uidb64,
                    "token": token,
                    "error": "Las contraseñas no coinciden."
                })

            if len(password1) < 6:
                return render(request, self.template_name, {
                    "validlink": True,
                    "uidb64": uidb64,
                    "token": token,
                    "error": "La contraseña debe tener al menos 6 caracteres."
                })

            # Guardar la nueva contraseña
            user.set_password(password1)
            user.save()

            return redirect("login_view")

        else:
            return render(request, self.template_name, {"validlink": False})


########### VISTAS PRINCIPALES VISITANTES ###########
@method_decorator(visitor_required, name='dispatch')
class MenuPrincipalVisitanteView(ListView):
    model = Evento
    template_name = 'base.html'
    context_object_name = 'eventos'

    def get_queryset(self):
        today = now().date()

        # Actualizar eventos cuyo eve_fecha_fin es hoy y están en estado 'Publicado'
        Evento.objects.filter(
            eve_estado__iexact='Publicado',
            eve_fecha_fin=today
        ).update(eve_estado='Finalizado')

        # Filtrar eventos que están publicados o finalizados
        eventos = Evento.objects.filter(
            Q(eve_estado__iexact='Publicado') | Q(eve_estado__iexact='Finalizado')
        ).order_by('-eve_fecha_inicio')

        # Filtros personalizados
        nombre = self.request.GET.get('nombre')
        ciudad = self.request.GET.get('ciudad')
        categoria_id = self.request.GET.get('categoria')
        area_id = self.request.GET.get('area')
        costo = self.request.GET.get('costo')
        estado = self.request.GET.get('estado')

        if nombre:
            eventos = eventos.filter(eve_nombre__icontains=nombre)
        if ciudad:
            eventos = eventos.filter(eve_ciudad__icontains=ciudad)
        if categoria_id:
            eventos = eventos.filter(categorias__id=categoria_id)
        if area_id:
            eventos = eventos.filter(categorias__cat_area_fk__id=area_id)
        if costo:
            eventos = eventos.filter(eve_tienecosto__iexact=costo)
        if estado:
            eventos = eventos.filter(eve_estado__iexact=estado)

        return eventos.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['areas'] = Area.objects.all()
        context['categorias'] = Categoria.objects.all()
        current_time = now().date()
        for evento in context['eventos']:
            if evento.eve_estado.lower() == 'Finalizado':
                evento.deletion_date = evento.eve_fecha_fin + timedelta(days=30)
        return context


########### VISTA DETALLE DE EVENTO ###########
@method_decorator(visitor_required, name='dispatch')
class EventoDetailView(DetailView):
    model = Evento
    template_name = 'info_evento.html'
    context_object_name = 'evento'

    def get_queryset(self):
        # Corrección: Solo permitir la visualización de eventos Publicados o Finalizados
        return self.model.objects.filter(
            Q(eve_estado__iexact='Publicado') | Q(eve_estado__iexact='Finalizado')
        )

@method_decorator(visitor_required, name='dispatch')
class EventoPreinscripcionesView(DetailView):
    model = Evento
    template_name = 'preinscripcion_eva_par.html'
    context_object_name = 'evento'







